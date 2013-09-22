import math

import cairo
from gi.repository import Clutter
from gi.repository import Cogl
from gi.repository import GLib

from paperwork.frontend.util import gen_float_range
from paperwork.frontend.util.img import image2clutter_img


class Drawer(object):
    # layer number == priority --> higher is drawn first
    BACKGROUND_LAYER = 1000
    IMG_LAYER = 200
    PROGRESSION_INDICATOR_LAYER = 100
    BOX_LAYER = 50
    FADDING_EFFECT_LAYER = 0
    # layer number == priority --> lower is drawn last

    layer = -1  # must be set by subclass

    position = (0, 0)  # (x, y)
    size = (0, 0)  # (width, height)
    visible = False  # to update in upd_actors()

    def __init__(self):
        pass

    def set_canvas(self, canvas):
        pass

    def upd_actors(self, clutter_stage, offset, visible_area_size):
        """
        Arguments:
            offset --- Position of the area in which to draw:
                       (offset_x, offset_y)
            visible_area_size --- Size of the area in which to draw: (width, height) = size
        """
        assert()

    def hide(self, canvas):
        pass


class SimpleDrawer(Drawer):
    def __init__(self, position):
        self.position = position
        self.visible = False
        self.actor = Clutter.Actor()  # must be filled in by child classes

    def __get_size(self):
        return self.actor.get_size()

    def __set_size(self, size):
        self.actor.set_size(size[0], size[1])

    size = property(__get_size, __set_size)

    def upd_actors(self, clutter_stage, offset, visible_area_size):
        size = self.size

        should_be_visible = True
        if (self.position[0] + size[0] < offset[0]):
            should_be_visible = False
        elif (offset[0] + visible_area_size[0] < self.position[0]):
            should_be_visible = False
        elif (self.position[1] + size[1] < offset[1]):
            should_be_visible = False
        elif (offset[1] + visible_area_size[1] < self.position[1]):
            should_be_visible = False

        pos_x = self.position[0] - offset[0]
        pos_y = self.position[1] - offset[1]

        if should_be_visible and not self.visible:
            clutter_stage.add_child(self.actor)
        elif not should_be_visible and self.visible:
            clutter_stage.remove_child(self.actor)
        self.visible = should_be_visible
        self.actor.set_position(pos_x, pos_y)

    def hide(self, stage):
        if self.visible:
            stage.remove_child(self.actor)
        self.visible = False


class PillowImageDrawer(SimpleDrawer):
    layer = Drawer.IMG_LAYER

    def __init__(self, position, image):
        SimpleDrawer.__init__(self, position)

        self.img = image2clutter_img(image)

        self.actor.set_content_scaling_filters(Clutter.ScalingFilter.TRILINEAR,
                                               Clutter.ScalingFilter.LINEAR)
        self.actor.set_size(image.size[0], image.size[1])
        self.actor.set_content(self.img)
        self.actor.set_position(position[0], position[1])


class ScanDrawer(SimpleDrawer):
    layer = Drawer.IMG_LAYER

    ANIM_HEIGHT = 5
    ANIM_FPS = 27
    ANIM_LENGTH = 1.0  # seconds

    def __init__(self, position, expected_total_size, wanted_size):
        SimpleDrawer.__init__(self, position)
        self._visible = False

        self.last_add = 0
        self.factor = min(
            1.0,
            float(wanted_size[0]) / expected_total_size[0],
            float(wanted_size[1]) / expected_total_size[1],
        )

        self.size = (
            (expected_total_size[0] * self.factor),
            (expected_total_size[1] * self.factor) + (self.ANIM_HEIGHT/2),
        )

        self.anim = {
            "position": 0,
            "interval": 1000 / self.ANIM_FPS,
            "offset": float(wanted_size[1]) / self.ANIM_FPS / self.ANIM_LENGTH,
            "content": Clutter.Canvas(),
            "actor": Clutter.Actor(),
        }

        self.anim['content'].set_size(self.size[0], self.ANIM_HEIGHT)
        self.anim['actor'].set_size(self.size[0], self.ANIM_HEIGHT)
        self.anim['actor'].set_position(0, -1 * (self.ANIM_HEIGHT / 2))
        self.anim['actor'].set_background_color(
            Clutter.Color.new(0, 0, 0, 0))
        self.anim['content'].connect("draw", self._draw_anim)
        self.anim['actor'].set_content(self.anim['content'])

        self.actor.add_child(self.anim['actor'])

    def _draw_anim(self, _, cairo_ctx, width, height):
        cairo_ctx.save()
        try:
            cairo_ctx.set_operator(cairo.OPERATOR_CLEAR)
            cairo_ctx.paint()
        finally:
            cairo_ctx.restore()

        if self.last_add > 0:
            cairo_ctx.save()
            try:
                cairo_ctx.set_operator(cairo.OPERATOR_OVER)
                cairo_ctx.set_source_rgb(0.5, 0.0, 0.0)
                cairo_ctx.set_line_width(1.0)
                cairo_ctx.move_to(0, self.ANIM_HEIGHT / 2)
                cairo_ctx.line_to(self.size[1], self.ANIM_HEIGHT / 2)
                cairo_ctx.stroke()

                cairo_ctx.set_source_rgb(1.0, 0.0, 0.0)
                cairo_ctx.arc(self.anim['position'],
                              float(self.ANIM_HEIGHT) / 2,
                              float(self.ANIM_HEIGHT) / 2,
                              0.0, math.pi * 2)
                cairo_ctx.stroke()

            finally:
                cairo_ctx.restore()

    def _upd_anim(self, _=None):
        if not self._visible:
            return False

        self.anim['position'] += self.anim['offset']
        if self.anim['position'] < 0 or self.anim['position'] >= self.size[0]:
            self.anim['position'] = max(0, self.anim['position'])
            self.anim['position'] = min(self.size[0], self.anim['position'])
            self.anim['offset'] *= -1

        self.anim['content'].invalidate()
        return True

    def __get_visible(self):
        return self._visible

    def __set_visible(self, visible):
        if visible and not self._visible:
            Clutter.threads_add_timeout(GLib.PRIORITY_LOW,
                                        self.anim['interval'],
                                        self._upd_anim, None)
        self._visible = visible

    visible = property(__get_visible, __set_visible)

    def add_chunk(self, pil_img):
        img = image2clutter_img(pil_img)
        actor = Clutter.Actor()
        actor.set_content_scaling_filters(Clutter.ScalingFilter.TRILINEAR,
                                          Clutter.ScalingFilter.LINEAR)
        actor.set_size(int(self.factor * pil_img.size[0]),
                       int(self.factor * pil_img.size[1]))

        actor.set_position(0, self.last_add)
        actor.set_content(img)

        self.last_add += actor.get_size()[1]
        self.anim['actor'].set_position(
            0, self.last_add - (self.ANIM_HEIGHT/2))
        self.actor.insert_child_below(actor, self.anim['actor'])
