import json
from GtkHelper.ItemListComboRow import ItemListComboRow, ItemListComboRowListItem
from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.PluginManager.ActionHolder import ActionHolder
from src.backend.DeckManagement.InputIdentifier import Input
from src.backend.PluginManager.ActionInputSupport import ActionInputSupport

# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

import sys
import os
from PIL import Image
from loguru import logger as log
import requests
from datetime import datetime

# Add plugin to sys.paths
sys.path.append(os.path.dirname(__file__))

# Import globals
import globals as gl

# Import own modules
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page

from AnalogClockGenerator import AnalogClockGenerator

class AnalogClock(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.generator = AnalogClockGenerator(
            hour_markings_width=9,
            hour_hand_width=15,
            minute_hand_width=11,
            second_hand_width=6
        )
        
    def on_ready(self):
        self.show()

    def on_tick(self):
        self.show()

    def show(self):
        clock = self.generator.get_current_clock()

        self.set_media(image=clock)


class DigitalClock(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.has_configuration = True
        
        self.points_visible: bool = False # Keep track of ":" status for the clock

    def on_ready(self):
        self.show()

    def get_config_rows(self) -> list:
        self.twenty_four_format_switch = Adw.SwitchRow(title=self.plugin_base.lm.get("actions.digital-clock.twenty-four-format"),
                                                       tooltip_text=self.plugin_base.lm.get("actions.digital-clock.twenty-four-format.tooltip"))

        self.show_seconds_switch = Adw.SwitchRow(title=self.plugin_base.lm.get("actions.digital-clock.show-seconds"))

        self.load_defaults()

        self.twenty_four_format_switch.connect("notify::active", self.on_twenty_four_format_switch_toggled)
        self.show_seconds_switch.connect("notify::active", self.on_show_seconds_switch_toggled)

        return [self.twenty_four_format_switch, self.show_seconds_switch]
    
    def load_defaults(self):
        settings = self.get_settings()

        self.twenty_four_format_switch.set_active(settings.get("twenty-four-format", True))
        self.show_seconds_switch.set_active(settings.get("show-seconds", False))

    def on_twenty_four_format_switch_toggled(self, *args):
        settings = self.get_settings()
        settings["twenty-four-format"] = self.twenty_four_format_switch.get_active()
        self.set_settings(settings)

        self.show()

    def on_show_seconds_switch_toggled(self, *args):
        settings = self.get_settings()
        settings["show-seconds"] = self.show_seconds_switch.get_active()
        self.set_settings(settings)

        self.show()

    def on_tick(self):
        self.show()

    def show(self):
        settings = self.get_settings()

        seperator = " " if self.points_visible else ":"
        # Don't blink points if seconds are enabled
        if settings.get("show-seconds", False):
            seperator = ":"


        now = datetime.now()

        label = now.strftime(f"%H{seperator}%M")
        font_size = 18

        if settings.get("show-seconds", False):
            label += now.strftime(f"{seperator}%S")
            font_size -= 4

        if settings.get("twenty-four-format", True):
            self.set_bottom_label(None)
        else:
            label = now.strftime(f"%I{seperator}%M")
            self.set_bottom_label(now.strftime("%p"), font_size=font_size)

        self.set_center_label(label, font_size=font_size)

        self.points_visible = not self.points_visible


class Date(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.has_configuration = True

    def get_config_rows(self) -> list:
        self.key_entry = Adw.EntryRow(title="Date time format")
        self.label_positions = [ItemListComboRowListItem("top", "Top"), ItemListComboRowListItem("center", "Center"), ItemListComboRowListItem("bottom", "Bottom")]
        self.label_position_row = ItemListComboRow(self.label_positions, title="Label position")

        self.load_config_values()

        self.key_entry.connect("changed", self.on_key_entry_changed)
        self.label_position_row.connect("notify::selected", self.on_label_position_changed)

        return [self.key_entry, self.label_position_row]
    
    def load_config_values(self):
        settings = self.get_settings()
        self.key_entry.set_text(settings.get("key", "%d-%m-%Y"))
        self.label_position_row.set_selected_item_by_key(settings.get("label-position"), 1)

    def on_key_entry_changed(self, *args):
        settings = self.get_settings()
        settings["key"] = self.key_entry.get_text()
        self.set_settings(settings)
        self.show()

    def on_label_position_changed(self, *args):
        settings = self.get_settings()
        settings["label-position"] = self.label_position_row.get_selected_item().key
        self.set_settings(settings)
        ## Clear
        self.set_top_label(None)
        self.set_center_label(None)
        self.set_bottom_label(None)
        # Show
        self.show()

    def on_tick(self):
        self.show()

    def show(self):
        settings = self.get_settings()
        key = settings.get("key", "%d-%m-%Y")
        label_position = settings.get("label-position", "center")

        if label_position not in ["top", "center", "bottom"]:
            return

        self.set_label(text=datetime.now().strftime(key), font_size=10, position=label_position)


class ClocksPlugin(PluginBase):
    def __init__(self):
        super().__init__()

        self.init_locale_manager()

        self.lm = self.locale_manager

        ## Register actions
        self.analog_clock_holder = ActionHolder(
            plugin_base=self,
            action_base=AnalogClock,
            action_id_suffix="AnalogClock",
            action_name=self.lm.get("actions.analog-clock.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNSUPPORTED
            }
        )
        self.add_action_holder(self.analog_clock_holder)

        self.digital_clock_holder = ActionHolder(
            plugin_base=self,
            action_base=DigitalClock,
            action_id_suffix="DigitalClock",
            action_name=self.lm.get("actions.digital-clock.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNSUPPORTED
            }
        )
        self.add_action_holder(self.digital_clock_holder)

        self.date_holder = ActionHolder(
            plugin_base=self,
            action_base=Date,
            action_id_suffix="Date",
            action_name="Date",
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.UNTESTED,
                Input.Touchscreen: ActionInputSupport.UNSUPPORTED
            }
        )
        self.add_action_holder(self.date_holder)

        # Register plugin
        self.register(
            plugin_name=self.lm.get("plugin.name"),
            github_repo="https://github.com/StreamController/Clocks",
            plugin_version="1.0.0",
            app_version="1.0.0-alpha"
        )

    def init_locale_manager(self):
        self.lm = self.locale_manager
        self.lm.set_to_os_default()

    def get_selector_icon(self) -> Gtk.Widget:
        return Gtk.Image(icon_name="preferences-system-time-symbolic")