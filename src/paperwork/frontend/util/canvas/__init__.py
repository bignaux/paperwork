"""
The main canvas is where page(s) are drawn. This is the biggest and most
important part of the main window.

Here are the elements that must drawn on it:
    - images (pages, icons)
    - boxes
    - various overlay (progression line, etc)
"""

import copy
import heapq
import sys

from gi.repository import Clutter
from gi.repository import GObject
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GtkClutter

from paperwork.backend.util import image2surface
from paperwork.frontend.util import PriorityQueue


class Canvas(GtkClutter.Embed, Gtk.Scrollable):
    """
    The main canvas is where page(s) are drawn. This is the biggest and most
    important part of the main window.
    """
    hadjustment = GObject.property(type=Gtk.Adjustment,
                                   default=Gtk.Adjustment(),
                                   flags=GObject.PARAM_READWRITE)
    hscroll_policy = GObject.property(type=Gtk.ScrollablePolicy,
                                      default=Gtk.ScrollablePolicy.MINIMUM,
                                      flags=GObject.PARAM_READWRITE)
    vadjustment = GObject.property(type=Gtk.Adjustment,
                                   default=Gtk.Adjustment(),
                                   flags=GObject.PARAM_READWRITE)
    vscroll_policy = GObject.property(type=Gtk.ScrollablePolicy,
                                      default=Gtk.ScrollablePolicy.MINIMUM,
                                      flags=GObject.PARAM_READWRITE)

    __gsignals__ = {
        'absolute-button-press-event': (GObject.SignalFlags.RUN_LAST, None,
                                        (GObject.TYPE_PYOBJECT,)),
        'absolute-motion-notify-event': (GObject.SignalFlags.RUN_LAST, None,
                                         (GObject.TYPE_PYOBJECT,)),
        'absolute-button-release-event': (GObject.SignalFlags.RUN_LAST, None,
                                          (GObject.TYPE_PYOBJECT,)),
    }

    def __init__(self, hadj, vadj):
        GtkClutter.Embed.__init__(self)

        self.size_forced = False
        self.full_size = (1, 1)
        self.visible_size = (1, 1)

        self.get_stage().set_background_color(
            Clutter.Color.get_static(Clutter.StaticColor.LIGHT_GRAY))

        self.drawers = PriorityQueue()

        self.set_hadjustment(hadj)
        self.set_vadjustment(vadj)

        self.add_events(Gdk.EventMask.SCROLL_MASK)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.add_events(Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
        self.connect("size-allocate", self.__on_size_allocate)
        self.connect("scroll-event", self.__on_scroll_event)
        self.connect("button-press-event", self.__on_button_pressed)
        self.connect("motion-notify-event", self.__on_motion)
        self.connect("button-release-event", self.__on_button_released)

    def get_hadjustment(self):
        return self.hadjustment

    def set_hadjustment(self, h):
        Gtk.Scrollable.set_hadjustment(self, h)
        self.set_property("hadjustment", h)
        h.set_lower(0.0)
        h.set_upper(float(self.full_size[0]))
        h.set_step_increment(10.0)
        h.set_page_increment(100.0)  # TODO(Jflesch)
        h.set_page_size(0.0)
        h.connect("value-changed", self.__on_adjustment_changed)

    def get_vadjustment(self):
        return self.vadjustment

    def set_vadjustment(self, v):
        Gtk.Scrollable.set_vadjustment(self, v)
        self.set_property("vadjustment", v)
        v.set_lower(0.0)
        v.set_upper(float(self.full_size[1]))
        v.set_step_increment(10.0)
        v.set_page_increment(100.0)  # TODO(Jflesch)
        v.set_page_size(0.0)
        v.connect("value-changed", self.__on_adjustment_changed)

    def __on_adjustment_changed(self, adjustment):
        self.upd_actors()

    def __on_size_allocate(self, _, size_allocate):
        self.visible_size = (size_allocate.width, size_allocate.height)
        self.upd_adjustments()
        self.upd_actors()

    def recompute_size(self):
        if self.size_forced:
            return
        (full_x, full_y) = (1, 1)
        for drawer in self.drawers:
            x = drawer.position[0] + drawer.size[0]
            y = drawer.position[1] + drawer.size[1]
            if (full_x < x):
                full_x = x
            if (full_y < y):
                full_y = y
        new_size = (full_x, full_y)
        if (new_size[0] != self.full_size[0]
            or new_size[1] != self.full_size[1]):
            self.full_size = new_size
            self.set_size_request(10000, 10000)
            self.upd_adjustments()

    def set_size(self, size):
        size = (int(size[0]), int(size[1]))
        self.full_size = size
        self.size_forced = True
        self.set_size_request(10000, 10000)
        self.upd_adjustments()
        self.upd_actors()

    def unforce_size(self):
        self.size_forced = False
        self.recompute_size()

    def upd_adjustments(self):
        val_h = float(self.hadjustment.get_value())
        val_v = float(self.vadjustment.get_value())
        if val_h > self.full_size[0]:
            val_h = self.full_size[0]
        if val_v > self.full_size[1]:
            val_v = self.full_size[1]
        self.hadjustment.set_lower(0.0)
        self.hadjustment.set_upper(0.0)
        self.hadjustment.set_upper(float(self.full_size[0]))
        self.vadjustment.set_upper(float(self.full_size[1]))
        self.hadjustment.set_page_size(self.visible_size[0])
        self.vadjustment.set_page_size(self.visible_size[1])
        self.hadjustment.set_value(int(val_h))
        self.vadjustment.set_value(int(val_v))

    def upd_actors(self):
        self.recompute_size()

        x = int(self.hadjustment.get_value())
        y = int(self.vadjustment.get_value())

        for drawer in self.drawers:
            drawer.upd_actors(self.get_stage(), (x, y),
                              self.visible_size)

    def add_drawer(self, drawer):
        drawer.set_canvas(self)

        x = drawer.position[0] + drawer.size[0]
        y = drawer.position[1] + drawer.size[1]

        self.drawers.add(drawer.layer, drawer)

    def remove_drawer(self, drawer):
        drawer.hide(self.get_stage())
        self.drawers.remove(drawer)

    def remove_all_drawers(self):
        for drawer in self.drawers:
            drawer.hide(self.get_stage())
        self.get_stage().remove_all_children()
        self.drawers.purge()

    def set_background(self, rgb_int):
        self.get_stage().set_background_color(
            Clutter.Color.new(rgb_int[0], rgb_int[1], rgb_int[2], 255))

    def __on_scroll_event(self, _, event):
        ops = {
            Gdk.ScrollDirection.UP:
            lambda h, v: (0, v.get_step_increment()),
            Gdk.ScrollDirection.DOWN:
            lambda h, v: (0, -1 * v.get_step_increment()),
            Gdk.ScrollDirection.RIGHT:
            lambda h, v: (h.get_step_incremented(), 0),
            Gdk.ScrollDirection.LEFT:
            lambda h, v: (-1 * h.get_step_increment(), 0),
        }

        if not event.direction in ops:
            return

        ops = ops[event.direction]
        ops = ops(self.hadjustment, self.vadjustment)

        for (op, adj) in [
                (ops[0], self.hadjustment),
                (ops[1], self.vadjustment)
            ]:
            val = adj.get_value()
            val += op
            if val < adj.get_lower():
                val = adj.get_lower()
            if val >= adj.get_upper():
                val = adj.get_upper() - 1
            if val != adj.get_value():
                adj.set_value(val)

    def __get_absolute_event(self, event):
        off_x = int(self.hadjustment.get_value())
        off_y = int(self.vadjustment.get_value())
        event = event.copy()
        event.x += off_x
        event.y += off_y
        return event;

    def __on_button_pressed(self, _, event):
        event = self.__get_absolute_event(event)
        self.emit('absolute-button-press-event', event)

    def __on_motion(self, _, event):
        event = self.__get_absolute_event(event)
        self.emit('absolute-motion-notify-event', event)

    def __on_button_released(self, _, event):
        event = self.__get_absolute_event(event)
        self.emit('absolute-button-release-event', event)

GObject.type_register(Canvas)
