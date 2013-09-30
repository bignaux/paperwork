import cairo

from gi.repository import Clutter
from gi.repository import Cogl
from gi.repository import GLib
from gi.repository import GObject

from paperwork.frontend.util.canvas.drawers import Drawer
from paperwork.frontend.util.canvas.drawers import SimpleDrawer
from paperwork.frontend.util.img import image2clutter_img
from paperwork.frontend.util.jobs import Job
from paperwork.frontend.util.jobs import JobFactory
from paperwork.frontend.util.jobs import JobScheduler
from paperwork.frontend.util.jobs import JobFactoryProgressUpdater


class JobPageLoader(Job):
    can_stop = False
    priority = 350

    __gsignals__ = {
        'page-loading-start': (GObject.SignalFlags.RUN_LAST, None, ()),
        'page-loading-img': (GObject.SignalFlags.RUN_LAST, None,
                             (GObject.TYPE_PYOBJECT,)),
        'page-loading-boxes': (GObject.SignalFlags.RUN_LAST, None,
                               (GObject.TYPE_PYOBJECT,)),  # array of boxes
        'page-loading-done': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, factory, job_id, page):
        Job.__init__(self, factory, job_id)
        self.page = page

    def do(self):
        self.emit('page-loading-start')
        try:
            img = self.page.img
            img.load()
            self.emit('page-loading-img', img)
        finally:
            self.emit('page-loading-done')

GObject.type_register(JobPageLoader)


class JobFactoryPageLoader(JobFactory):
    def __init__(self):
        JobFactory.__init__(self, "PageLoader")

    def make(self, drawer, page):
        job = JobPageLoader(self, next(self.id_generator), page)
        job.connect('page-loading-img',
                    lambda job, img:
                    GLib.idle_add(drawer.on_page_loading_img,
                                  job.page, img))
        # TODO(Jflesch): boxes
        return job


class PageDrawer(SimpleDrawer):
    IMG_PRELOAD_MARGIN = 1000 # px
    BACKGROUND_COLOR = Clutter.Color.get_static(
        Clutter.StaticColor.GRAY)

    def __init__(self, position, page, job_factory, scheduler):
        SimpleDrawer.__init__(self, position)
        self.position = position
        self.page = page
        self._job_factory = job_factory
        self._scheduler = scheduler
        self.visible = False

        self.img_actor = None

        # XXX(Jflesch):
        # we don't use the image content and we don't call
        # img.load() here --> PIL will (hopefully) only read the
        # header of the image
        img = self.page.img
        self.max_size = img.size
        self.size = self.max_size

        # self.actor is a parent actor containing the others
        self.content = None
        self.preloading = False
        self.actor.set_background_color(self.BACKGROUND_COLOR)

    def show(self, stage):
        SimpleDrawer.show(self, stage)

        assert(self.img_actor is None)
        self.img_actor = Clutter.Actor()
        self.img_actor.set_position(0, 0)
        self.img_actor.set_content_scaling_filters(Clutter.ScalingFilter.TRILINEAR,
                                                   Clutter.ScalingFilter.LINEAR)
        self.img_actor.set_size(self.size[0], self.size[1])
        if self.content is not None:
            self.img_actor.set_content(self.content)
            self.content = None
        self.actor.add_child(self.img_actor)

    def upd_actors(self, clutter_stage, offset, visible_area_size):
        size = self.size
        large_pos = (self.position[0] - (self.IMG_PRELOAD_MARGIN),
                     self.position[1] - (self.IMG_PRELOAD_MARGIN))
        large_size = (size[0] + (2 * self.IMG_PRELOAD_MARGIN),
                      size[1] + (2 * self.IMG_PRELOAD_MARGIN))
        if self.compute_visibility(offset, visible_area_size, large_pos,
                                   large_size) and not self.preloading:
            # preload the content
            self.preloading = True
            job = self._job_factory.make(self, self.page)
            self._scheduler.schedule(job)

        SimpleDrawer.upd_actors(self, clutter_stage, offset, visible_area_size)

    def set_size_ratio(self, ratio):
        self.size = (int(ratio * self.max_size[0]),
                     int(ratio * self.max_size[1]))

    def _set_size(self, size):
        SimpleDrawer._set_size(self, size)
        if self.img_actor is not None:
            self.img_actor.set_size(self.size[0], self.size[1])

    def _get_size(self):
        return SimpleDrawer._get_size(self)

    size = property(_get_size, _set_size)

    def on_page_loading_img(self, page, img):
        self.content = image2clutter_img(img)
        if self.img_actor is None:
            return
        self.img_actor.set_content(self.content)
        self.content = None

    def hide(self, stage):
        SimpleDrawer.hide(self, stage)
        self.content = None
        self.preloading = False
        if self.img_actor is not None:
            # throw away the current actor and replace it
            # with an empty one
            # otherwise we may end up using too much RAM
            # (either the graphic card RAM or the CPU RAM)
            current_size = self.size
            self.actor.remove_child(self.img_actor)
            del(self.img_actor)
            self.img_actor = None
            self.size = current_size
