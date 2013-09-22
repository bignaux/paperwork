from gi.repository import Clutter
from gi.repository import Cogl

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
        self.canvas.get_stage().add_child(self.rectangle)

    def __get_size(self):
        assert(self.canvas is not None)
        return (self.canvas.full_size[0], self.canvas.full_size[1])

    size = property(__get_size)

    def upd_actors(self, clutter_stage, offset, visible_area_size):
        self.rectangle.set_size(visible_area_size[0],
                                visible_area_size[1])

    def hide(self, stage):
        stage.remove_child(self.rectangle)


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

    def __init__(self, position, expected_total_size, wanted_size):
        SimpleDrawer.__init__(self, position)
        self.canvas = None

        self.last_add = 0
        self.factor = min(
            1.0,
            float(wanted_size[0]) / expected_total_size[0],
            float(wanted_size[1]) / expected_total_size[1],
        )

        self.size = wanted_size

    def set_canvas(self, canvas):
        self.canvas = canvas

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
        self.actor.add_child(actor)
