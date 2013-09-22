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

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject

from paperwork.frontend.util.canvas.drawers import PillowImageDrawer


class ImgGrip(object):
    """
    Represents one of the grip that user can move to cut an image.
    """
    GRIP_SIZE = 20
    COLOR = (0.0, 0.0, 1.0)

    def __init__(self, pos_x, pos_y):
        self.position = (int(pos_x), int(pos_y))

    def is_on_grip(self, position, ratio):
        """
        Indicates if position is on the grip

        Arguments:
            position --- tuple (int, int)
            ratio --- Scale at which the image is represented

        Returns:
            True or False
        """
        x_min = int(ratio * self.position[0]) - self.GRIP_SIZE
        y_min = int(ratio * self.position[1]) - self.GRIP_SIZE
        x_max = int(ratio * self.position[0]) + self.GRIP_SIZE
        y_max = int(ratio * self.position[1]) + self.GRIP_SIZE
        return (x_min <= position[0] and position[0] <= x_max
                and y_min <= position[1] and position[1] <= y_max)


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

        img_size = self.img.size

        visible_size = self.img_widget.visible_size

        factor = min(
            1.0,
            float(visible_size[0]) / img_size[0],
            float(visible_size[1]) / img_size[1],
        )
        self.img_sizes = [
            (factor, (int(factor * img_size[0]),
                      int(factor * img_size[1]))),
            (1.0, (int(img_size[0]), int(img_size[1]))),
        ]

        self.img_drawer = PillowImageDrawer((0, 0), self.img)
        self.img_drawer.size = self.img_sizes[0][1]

        self.img_widget.remove_all_drawers()
        self.img_widget.add_drawer(self.img_drawer)
        self.img_widget.upd_actors()
        self.img_widget.set_size(self.img_sizes[0][1])

        self.img_widget = img_widget
        self.img = img
        img_size = self.img.size
        self.grips = (
            ImgGrip(0, 0),
            ImgGrip(img_size[0], img_size[1]))
        self.selected = None  # the grip being moved

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

    def __move_grip(self, event_pos):
        """
        Move a grip, based on the position
        """
        (mouse_x, mouse_y) = event_pos

        if not self.selected:
            return None

        new_x = mouse_x / self.img_sizes[0][0]
        new_y = mouse_y / self.img_sizes[0][0]
        self.selected.position = (new_x, new_y)

    def __on_mouse_button_released_cb(self, event):
        if self.selected:
            if not self.__visible:
                return
            self.__move_grip(event.get_coords())
            self.selected = None
        else:
            # figure out the cursor position on the image
            (mouse_x, mouse_y) = (event.x, event.y)
            img_size = self.img_sizes.pop(0)
            self.img_sizes.append(img_size)
            self.img_drawer.size = self.img_sizes[0][1]
            self.img_widget.set_size(self.img_sizes[0][1])
            self.img_widget.upd_actors()

        self.emit('grip-moved')

    def __get_visible(self):
        return self.__visible

    def __set_visible(self, visible):
        self.__visible = visible
        self.img_widget.get_window().set_cursor(self.__cursors['default'])
        # TODO

    visible = property(__get_visible, __set_visible)

    def get_coords(self):
        return ((int(self.grips[0].position[0]),
                 int(self.grips[0].position[1])),
                (int(self.grips[1].position[0]),
                 int(self.grips[1].position[1])))


GObject.type_register(ImgGripHandler)
