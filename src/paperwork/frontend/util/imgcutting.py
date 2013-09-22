#   Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2013  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.

import PIL.ImageDraw

import cairo
from gi.repository import Clutter
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject

from paperwork.frontend.util.canvas.drawers import SimpleDrawer
from paperwork.frontend.util.canvas.drawers import PillowImageDrawer


class Grip(object):
    """
    Represents one of the grip that user can move to cut an image.
    """

    GRIP_SIZE = 30
    DEFAULT_COLOR = (0.0, 0.0, 1.0)
    SELECTED_COLOR = (0.0, 1.0, 0.0)

    def __init__(self, pos_x, pos_y):
        self.position = (int(pos_x), int(pos_y))

    def __get_real_pos(self, factor):
        x = int(factor * self.position[0])
        y = int(factor * self.position[1])
        return (x, y)

    def __get_select_area(self, factor):
        (x, y) = self.__get_real_pos(factor)
        x_min = x - (self.GRIP_SIZE / 2)
        y_min = y - (self.GRIP_SIZE / 2)
        x_max = x + (self.GRIP_SIZE / 2)
        y_max = y + (self.GRIP_SIZE / 2)
        return ((x_min, y_min), (x_max, y_max))

    def is_on_grip(self, position, factor):
        """
        Indicates if position is on the grip

        Arguments:
            position --- tuple (int, int)
            factor --- Scale at which the image is represented

        Returns:
            True or False
        """
        ((x_min, y_min), (x_max, y_max)) = self.__get_select_area(factor)
        return (x_min <= position[0] and position[0] <= x_max
                and y_min <= position[1] and position[1] <= y_max)

    def draw(self, cairo_ctx, factor, selected=False):
        ((a_x, a_y), (b_x, b_y)) = self.__get_select_area(factor)
        color = {
            False: self.DEFAULT_COLOR,
            True: self.SELECTED_COLOR,
        }[selected]
        cairo_ctx.set_source_rgb(color[0], color[1], color[2])
        cairo_ctx.set_line_width(1.0)
        cairo_ctx.rectangle(a_x, a_y, b_x - a_x, b_y - a_y)
        cairo_ctx.stroke()


class GripDrawer(SimpleDrawer):
    layer = SimpleDrawer.BOX_LAYER

    def __init__(self, grip_handler, size):
        SimpleDrawer.__init__(self, (0, 0))
        self.grip_handler = grip_handler
        self.content = Clutter.Canvas()

        self.set_size(size)

        self.actor.set_position(0, 0)
        self.actor.set_background_color(
            Clutter.Color.new(255, 0, 255, 0))
        self.content.connect("draw", self._draw_grips)
        self.actor.set_content(self.content)

    def set_size(self, size):
        self.size = size
        self.content.set_size(size[0], size[1])

    def _draw_grips(self, _, cairo_ctx, width, height):
        grips = self.grip_handler.grips
        selected = self.grip_handler.selected
        factor = self.grip_handler.img_sizes[0][0]

        cairo_ctx.save()
        try:
            cairo_ctx.set_operator(cairo.OPERATOR_CLEAR)
            cairo_ctx.paint()
        finally:
            cairo_ctx.restore()

        cairo_ctx.set_operator(cairo.OPERATOR_OVER)
        cairo_ctx.set_source_rgb(Grip.DEFAULT_COLOR[0],
                                 Grip.DEFAULT_COLOR[1],
                                 Grip.DEFAULT_COLOR[2])
        cairo_ctx.set_line_width(1.0)

        ((a_x, a_y), (b_x, b_y)) = self.grip_handler.get_coords()
        a_x *= factor
        a_y *= factor
        b_x *= factor
        b_y *= factor

        cairo_ctx.set_line_width(1)
        cairo_ctx.rectangle(a_x, a_y, b_x - a_x - 1, b_y - a_y - 1)
        cairo_ctx.stroke()

        for grip in grips:
            grip.draw(cairo_ctx, factor, grip == selected)

    def redraw(self):
        self.content.invalidate()


class ImgGripHandler(GObject.GObject):
    __gsignals__ = {
        'grip-moved': (GObject.SignalFlags.RUN_LAST, None, ())
    }

    def __init__(self, img, img_widget):
        """
        Arguments:
            img --- PIL img
            img_eventbox --- Image area eventbox
            img_widget --- Widget displaying the image
        """
        GObject.GObject.__init__(self)
        self.__visible = False

        self.img_widget = img_widget
        self.img = img
        self.img_size = self.img.size

        visible_size = self.img_widget.visible_size
        self.img_widget.remove_all_drawers()

        factor = min(
            1.0,
            float(visible_size[0]) / self.img_size[0],
            float(visible_size[1]) / self.img_size[1],
        )
        self.img_sizes = [
            (factor, (int(factor * self.img_size[0]),
                      int(factor * self.img_size[1]))),
            (1.0, (int(self.img_size[0]), int(self.img_size[1]))),
        ]

        self.img_drawer = PillowImageDrawer((0, 0), self.img)
        self.img_drawer.size = self.img_sizes[0][1]

        self.img_widget.add_drawer(self.img_drawer)
        self.img_widget.set_size(self.img_sizes[0][1])

        self.grips = (
            Grip(0, 0),
            Grip(self.img_size[0] - 1 , self.img_size[1] - 1))
        self.selected = None  # the grip being moved
        self.grip_drawer = GripDrawer(self, self.img_sizes[0][1])
        self.img_widget.add_drawer(self.grip_drawer)
        self.grip_drawer.redraw()

        self.img_widget.upd_actors()

        self.__cursors = {
            'default': Gdk.Cursor.new(Gdk.CursorType.HAND1),
            'visible': Gdk.Cursor.new(Gdk.CursorType.HAND1),
            'on_grip': Gdk.Cursor.new(Gdk.CursorType.TCROSS)
        }

        img_widget.connect("absolute-button-press-event",
                           lambda _, event:
                           GLib.idle_add(self.__on_mouse_button_pressed_cb,
                                         event))
        img_widget.connect("absolute-motion-notify-event",
                           lambda _, event:
                           GLib.idle_add(self.__on_mouse_motion_cb, event))
        img_widget.connect("absolute-button-release-event",
                           lambda _, event:
                           GLib.idle_add(self.__on_mouse_button_released_cb,
                                         event))
        self.__last_cursor_pos = None  # relative to the image size

    def __on_mouse_button_pressed_cb(self, event):
        if not self.__visible:
            return

        (mouse_x, mouse_y) = (event.x, event.y)

        self.selected = None
        for grip in self.grips:
            if grip.is_on_grip((mouse_x, mouse_y), self.img_sizes[0][0]):
                self.selected = grip
                break

        self.grip_drawer.redraw()

    def __move_grip(self, event):
        """
        Move a grip, based on the position
        """
        (mouse_x, mouse_y) = (event.x, event.y)

        if not self.selected:
            return None

        new_x = float(mouse_x) / self.img_sizes[0][0]
        new_y = float(mouse_y) / self.img_sizes[0][0]
        if new_x < 0:
            new_x = 0
        if new_y < 0:
            new_y = 0
        if new_x >= self.img_size[0]:
            new_x = self.img_size[0]
        if new_y >= self.img_size[1]:
            new_y = self.img_size[1]
        self.selected.position = (new_x, new_y)

    def __on_mouse_motion_cb(self, event):
        if not self.__visible:
            return

        (mouse_x, mouse_y) = (event.x, event.y)

        if self.selected:
            is_on_grip = True
        else:
            is_on_grip = False
            for grip in self.grips:
                if grip.is_on_grip((mouse_x, mouse_y), self.img_sizes[0][0]):
                    is_on_grip = True
                    break

        if is_on_grip:
            cursor = self.__cursors['on_grip']
        else:
            cursor = self.__cursors['visible']
        self.img_widget.get_window().set_cursor(cursor)

        if self.selected:
            self.__move_grip(event)
            self.grip_drawer.redraw()

    def __on_mouse_button_released_cb(self, event):
        if self.selected:
            if not self.__visible:
                return
            self.__move_grip(event)
            self.selected = None
        else:
            # figure out the cursor position on the image
            (mouse_x, mouse_y) = (event.x, event.y)
            img_size = self.img_sizes.pop(0)
            self.img_sizes.append(img_size)
            self.img_drawer.size = self.img_sizes[0][1]
            self.grip_drawer.set_size(self.img_sizes[0][1])
            self.img_widget.set_size(self.img_sizes[0][1])
            self.img_widget.upd_actors()

        self.emit('grip-moved')
        self.grip_drawer.redraw()

    def __get_visible(self):
        return self.__visible

    def __set_visible(self, visible):
        self.__visible = visible
        self.img_widget.get_window().set_cursor(self.__cursors['default'])

    visible = property(__get_visible, __set_visible)

    def get_coords(self):
        grips = self.grips
        a_x = int(min(grips[0].position[0], grips[1].position[0]))
        a_y = int(min(grips[0].position[1], grips[1].position[1]))
        b_x = int(max(grips[0].position[0], grips[1].position[0])) + 1
        b_y = int(max(grips[0].position[1], grips[1].position[1])) + 1
        return ((a_x, a_y), (b_x, b_y))

GObject.type_register(ImgGripHandler)
