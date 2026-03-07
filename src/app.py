"""Application controller — orchestrates GUI, network, and input layers.

Mobile version: uses Kivy + ScreenManager instead of customtkinter.
Touch simulation replaces keyboard I/O; mobile users are always members.
"""

from __future__ import annotations

from typing import Optional

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager

from src.config import CONFIG  # noqa: F401 – ensure config is loaded
from src.gui.screens import GroupScreen, LobbyScreen, LoginScreen
from src.input.touch_handler import TouchHandler
from src.network.event_bus import EventBus
from src.network.ws_client import WSClient


class BPSRApp(App):
    """Main Kivy application for the mobile client."""

    def build(self) -> ScreenManager:
        self.title = "BPSR AutoUltimate"
        Builder.load_file("src/gui/bpsr.kv")

        # Core subsystems
        self.event_bus = EventBus.instance()
        self.ws_client = WSClient(self.event_bus)
        self.touch_handler = TouchHandler(self.event_bus)

        # State
        self.username: Optional[str] = None
        self._in_group = False

        # Screens
        self.sm = ScreenManager()
        self.login_screen = LoginScreen(name="login")
        self.lobby_screen = LobbyScreen(name="lobby")
        self.group_screen = GroupScreen(name="group")

        self.sm.add_widget(self.login_screen)
        self.sm.add_widget(self.lobby_screen)
        self.sm.add_widget(self.group_screen)

        self._subscribe_events()
        return self.sm

    # -- Actions (called from views) --

    def do_login(self, username: str) -> None:
        self.username = username
        self.ws_client.connect(username)

    # -- Event subscriptions --

    def _subscribe_events(self) -> None:
        bus = self.event_bus
        bus.subscribe("connected", self._on_connected)
        bus.subscribe("disconnected", self._on_disconnected)
        bus.subscribe("connection_error", self._on_connection_error)
        bus.subscribe("groups_list", self._on_groups_list)
        bus.subscribe("group_joined", self._on_group_entered)
        bus.subscribe("group_created", self._on_group_entered)
        bus.subscribe("group_update", self._on_group_update)
        bus.subscribe("group_left", self._on_group_left)
        bus.subscribe("kicked", self._on_kicked)
        bus.subscribe("server_error", self._on_server_error)

    # -- Event handlers (called from background thread → schedule on main) --

    def _on_connected(self, connection_id: str, username: str) -> None:
        self.touch_handler.start()
        Clock.schedule_once(lambda _dt: setattr(self.sm, "current", "lobby"), 0)

    def _on_disconnected(self) -> None:
        self._in_group = False
        self.touch_handler.stop()

        def _handle(_dt):  # noqa: ANN001
            if self.sm.current != "login":
                self.sm.current = "login"
                self.login_screen.show_error("Desconectado del servidor")

        Clock.schedule_once(_handle, 0)

    def _on_connection_error(self, message: str) -> None:
        def _handle(_dt):  # noqa: ANN001
            if self.sm.current == "login":
                self.login_screen.show_error(f"Error de conexión: {message}")
            elif self.sm.current == "lobby":
                self.lobby_screen.show_error(message)

        Clock.schedule_once(_handle, 0)

    def _on_groups_list(self, groups: list) -> None:
        Clock.schedule_once(lambda _dt: self.lobby_screen.update_groups(groups), 0)

    def _on_group_entered(self, group_data: dict) -> None:
        self._in_group = True

        def _handle(_dt):  # noqa: ANN001
            self.sm.current = "group"
            self.group_screen.update_group(group_data)

        Clock.schedule_once(_handle, 0)

    def _on_group_update(self, data: dict) -> None:
        if self._in_group:
            Clock.schedule_once(lambda _dt: self.group_screen.update_group(data), 0)

    def _on_group_left(self) -> None:
        self._in_group = False
        Clock.schedule_once(lambda _dt: setattr(self.sm, "current", "lobby"), 0)

    def _on_kicked(self, reason: str) -> None:
        self._in_group = False

        def _handle(_dt):  # noqa: ANN001
            self.sm.current = "lobby"
            self.lobby_screen.show_error(
                f"Has sido expulsado del grupo ({reason})"
            )

        Clock.schedule_once(_handle, 0)

    def _on_server_error(self, code: str, message: str) -> None:
        def _handle(_dt):  # noqa: ANN001
            current = self.sm.current
            if current == "lobby":
                self.lobby_screen.show_error(message)
            elif current == "group":
                self.group_screen.show_error(message)
            elif current == "login":
                self.login_screen.show_error(message)

        Clock.schedule_once(_handle, 0)

    # -- Lifecycle --

    def on_stop(self) -> None:
        self.touch_handler.cleanup()
        self.ws_client.disconnect()
