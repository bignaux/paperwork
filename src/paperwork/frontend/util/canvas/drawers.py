from gi.repository import Clutter
from gi.repository import Cogl

from paperwork.backend.util import image2surface
from paperwork.frontend.util.img import image2pixbuf


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


class BackgroundDrawer(Drawer):
    layer = Drawer.BACKGROUND_LAYER
    visible = True  # always visible

    def __init__(self, rgb):
        self.rgb = rgb
        self.canvas = None
        self.position = (0, 0)

        color = Clutter.Color.new(int(rgb[0] * 255),
                                  int(rgb[1] * 255),
                                  int(rgb[2] * 255),
                                  255)
        self.rectangle = Clutter.Rectangle()
        self.rectangle.set_color(color)
        self.rectangle.set_size(100, 100)
        self.rectangle.set_position(0, 0)

    def set_canvas(self, canvas):
        self.canvas = canvas
        self.canvas.get_stage().add_actor(self.rectangle)

    def __get_size(self):
        assert(self.canvas is not None)
        return (self.canvas.full_size_x, self.canvas.full_size_y)

    size = property(__get_size)

    def upd_actors(self, clutter_stage, offset, visible_area_size):
        self.rectangle.set_size(visible_area_size[0],
                                visible_area_size[1])


class PillowImageDrawer(Drawer):
    layer = Drawer.IMG_LAYER

    def __init__(self, position, image):
        self.max_size = image.size
        self.position = position
        self.visible = False

        pixbuf = image2pixbuf(image)
        fmt = Cogl.PixelFormat.RGB_888
        if pixbuf.get_has_alpha():
            fmt = Cogl.PixelFormat.RGB_8888

        self.img = Clutter.Image()
        self.img.set_data(pixbuf.get_pixels(), fmt,
                          pixbuf.get_width(), pixbuf.get_height(),
                          pixbuf.get_rowstride())

        self.actor = Clutter.Actor()
        self.actor.set_content_scaling_filters(Clutter.ScalingFilter.TRILINEAR,
                                               Clutter.ScalingFilter.LINEAR)
        self.actor.set_size(self.max_size[0], self.max_size[1])
        self.actor.set_content(self.img)
        self.actor.set_position(position[0], position[1])

    def set_canvas(self, canvas):
        self.canvas = canvas

    def __get_size(self):
        return self.actor.get_size()

    def __set_size(self, size):
        self.actor.set_size(size[0], size[1])

    size = property(__get_size, __set_size)

    def upd_actors(self, clutter_stage, offset, visible_area_size):
        assert(self.canvas)

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

        self.actor.set_position(self.position[0] - offset[0],
                                self.position[1] - offset[1])

        if should_be_visible and not self.visible:
            clutter_stage.add_actor(self.actor)
        elif not should_be_visible and self.visible:
            clutter_stage.remove_actor(self.actor)
        self.visible = should_be_visible
