import json
import zoneinfo

import pytz
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
from gi.repository import Gtk, Adw, Gio, GObject

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


class TimezoneRow(Adw.ComboRow):
    __gtype_name__ = "TimezoneRow"
    __gsignals__ = {
        'zone-changed': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, selected: str | None = None, fallback: str | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selected = selected
        self.fallback = fallback

        self.set_title("Timezone")
        self.set_subtitle("Select timezone")

        # Get available timezones and load them into the combo box
        self.str_list = Gtk.StringList()
        for zone in sorted(zoneinfo.available_timezones()):
            self.str_list.append(zone)
        self.set_model(self.str_list)

        self.select_active()

        self.connect("notify::selected", self.on_selected_changed)

    def select_active(self) -> None:
        if self.selected is not None:
            for i, zone in enumerate(self.str_list):
                if zone.get_string() == self.selected:
                    self.set_selected(i)
                    return
            
        if self.fallback is not None:
            for i, zone in enumerate(self.str_list):
                if zone.get_string() == self.fallback:
                    self.set_selected(i)
                    return
            
        self.set_selected(Gtk.INVALID_LIST_POSITION)


    def on_selected_changed(self, *args):
        if self.get_selected() == Gtk.INVALID_LIST_POSITION:
            self.emit("zone-changed", None) #idk how this could happen

        self.emit("zone-changed", self.str_list[self.get_selected()].get_string())
        


class TimeActionBase(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings: dict = {}

    def on_ready(self):
        self.settings = self.get_settings()
        self.show()

    def get_config_rows(self) -> list:
        self.timezone_row = TimezoneRow(
            fallback=self.plugin_base.local_timezone,
            selected=self.settings.get("timezone", None)
        )
        self.timezone_row.connect("zone-changed", self.on_timezone_changed)
        return [self.timezone_row]

    def on_timezone_changed(self, row, timezone: str):
        self.settings["timezone"] = timezone
        self.set_settings(self.settings)
        self.show()

    def get_current_time(self):
        timezone = pytz.timezone(self.settings.get("timezone", self.plugin_base.local_timezone))
        return datetime.now(timezone)


class AnalogClock(TimeActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.generator = AnalogClockGenerator(
            hour_markings_width=9,
            hour_hand_width=15,
            minute_hand_width=11,
            second_hand_width=6
        )

    def on_tick(self):
        self.show()

    def show(self):
        now = self.get_current_time()
        clock = self.generator.get_clock(
            hour=now.hour,
            minute=now.minute,
            second=now.second
        )
        self.set_media(image=clock)


class DigitalClock(TimeActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.has_configuration = True
        self.points_visible: bool = False  # Keep track of ":" status for the clock

    def get_config_rows(self) -> list:
        rows = super().get_config_rows()
        

        self.label_positions = [ItemListComboRowListItem("top", "Top"), ItemListComboRowListItem("center", "Center"), ItemListComboRowListItem("bottom", "Bottom")]
        self.label_position_row = ItemListComboRow(self.label_positions, title="Label position")

        self.twenty_four_format_switch = Adw.SwitchRow(
            title=self.plugin_base.lm.get("actions.digital-clock.twenty-four-format"),
            tooltip_text=self.plugin_base.lm.get("actions.digital-clock.twenty-four-format.tooltip")
        )

        self.show_seconds_switch = Adw.SwitchRow(
            title=self.plugin_base.lm.get("actions.digital-clock.show-seconds")
        )

        self.load_defaults()

        self.twenty_four_format_switch.connect("notify::active", self.on_twenty_four_format_switch_toggled)
        self.show_seconds_switch.connect("notify::active", self.on_show_seconds_switch_toggled)
        self.label_position_row.connect("notify::selected", self.on_label_position_changed)

        return [self.twenty_four_format_switch, self.show_seconds_switch, self.label_position_row]

        return rows + [self.twenty_four_format_switch, self.show_seconds_switch]
    
    def load_defaults(self):
        settings = self.get_settings()
        self.twenty_four_format_switch.set_active(settings.get("twenty-four-format", True))
        self.show_seconds_switch.set_active(settings.get("show-seconds", False))
        self.label_position_row.set_selected_item_by_key(settings.get("label-position"), 1)

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
        label_position = settings.get("label-position", "center")

        if label_position not in ["top", "center", "bottom"]:
            return

        seperator = " " if self.points_visible else ":"
        if settings.get("show-seconds", False):
            seperator = ":"

        now = self.get_current_time()
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

        self.set_label(label, font_size=font_size, position=label_position)

        self.points_visible = not self.points_visible


class Date(TimeActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.has_configuration = True

    def get_config_rows(self) -> list:
        rows = super().get_config_rows()
        
        self.key_entry = Adw.EntryRow(title="Date time format")
        self.label_positions = [
            ItemListComboRowListItem("top", "Top"),
            ItemListComboRowListItem("center", "Center"),
            ItemListComboRowListItem("bottom", "Bottom")
        ]
        self.label_position_row = ItemListComboRow(self.label_positions, title="Label position")

        self.load_config_values()

        self.key_entry.connect("changed", self.on_key_entry_changed)
        self.label_position_row.connect("notify::selected", self.on_label_position_changed)

        return rows + [self.key_entry, self.label_position_row]
    
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
        self.set_top_label(None)
        self.set_center_label(None)
        self.set_bottom_label(None)
        self.show()

    def on_tick(self):
        self.show()

    def show(self):
        settings = self.get_settings()
        key = settings.get("key", "%d-%m-%Y")
        label_position = settings.get("label-position", "center")

        if label_position not in ["top", "center", "bottom"]:
            return

        self.set_label(text=self.get_current_time().strftime(key), font_size=10, position=label_position)


class ClocksPlugin(PluginBase):
    def __init__(self):
        super().__init__()

        self.init_locale_manager()

        self.lm = self.locale_manager

        self.launch_backend(os.path.join(self.PATH, "backend", "backend.py"), os.path.join(self.PATH, "backend", ".venv"), open_in_terminal=False)
        self.wait_for_backend(10)
        self.local_timezone = self.backend.get_local_timezone()

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
