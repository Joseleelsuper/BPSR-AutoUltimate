"""Application controller — orchestrates GUI, network, and input layers.

Follows an MVC-like pattern:
  - Views (gui/) handle presentation
  - WSClient (network/) handles communication
  - KeyHandler (input/) handles keyboard I/O
  - App wires them together via the EventBus
"""

from __future__ import annotations

from typing import Optional

import customtkinter as ctk

from src.config import CONFIG
from src.gui.group_view import GroupView
from src.gui.lobby_view import LobbyView
from src.gui.login_view import LoginView
from src.input.key_handler import KeyHandler
from src.network.event_bus import EventBus
from src.network.ws_client import WSClient


class App:
    """Main application controller."""

    def __init__(self) -> None:
        # Core components
        self.event_bus = EventBus.instance()
        self.ws_client = WSClient(self.event_bus)
        self.key_handler = KeyHandler(self.event_bus)

        # Window
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme(CONFIG.theme)

        self.window = ctk.CTk()
        self.window.title(CONFIG.app_title)
        self.window.geometry(CONFIG.app_geometry)
        self.window.minsize(700, 450)
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

        # Views
        self._current_view: Optional[ctk.CTkFrame] = None
        self._login_view = LoginView(self.window, self)
        self._lobby_view = LobbyView(self.window, self)
        self._group_view = GroupView(self.window, self)

        # State
        self.username: Optional[str] = None
        self._in_group = False

        # Subscribe to events
        self._subscribe_events()

        # Start on login
        self._show_view(self._login_view)

    # -- Navigation --

    def _show_view(self, view) -> None:
        if self._current_view:
            self._current_view.on_hide() # pyright: ignore[reportAttributeAccessIssue]
            self._current_view.pack_forget()
        self._current_view = view
        view.pack(fill="both", expand=True)
        view.on_show()

    def _safe_show(self, view) -> None:
        """Schedule a view switch on the GUI thread."""
        self.window.after(0, lambda: self._show_view(view))

    # -- Actions (called from views) --

    def do_login(self, username: str) -> None:
        """Connect to the server with the given username."""
        self.username = username
        self.ws_client.connect(username)

    # -- Event handlers (called from background threads via EventBus) --

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
        bus.subscribe("key_lock_toggled", self._on_key_lock_toggled)
        bus.subscribe("leader_changed", self._on_leader_changed)
        bus.subscribe("kicked", self._on_kicked)
        bus.subscribe("server_error", self._on_server_error)

        # Local input events
        bus.subscribe("local_toggle_key_lock", self._on_local_toggle)
        bus.subscribe("local_key_press", self._on_local_key_press)

    def _on_connected(self, connection_id: str, username: str) -> None:
        self.key_handler.start()
        self._safe_show(self._lobby_view)

    def _on_disconnected(self) -> None:
        self._in_group = False
        self.key_handler.stop()
        self.window.after(0, lambda: self._handle_disconnect())

    def _handle_disconnect(self) -> None:
        # If we're not intentionally closing, go back to login
        if self._current_view != self._login_view:
            self._show_view(self._login_view)
            self._login_view.show_error("Desconectado del servidor")

    def _on_connection_error(self, message: str) -> None:
        self.window.after(0, lambda: self._handle_conn_error(message))

    def _handle_conn_error(self, message: str) -> None:
        if self._current_view == self._login_view:
            self._login_view.show_error(f"Error de conexión: {message}")
        elif self._current_view == self._lobby_view:
            self._lobby_view.show_error(message)

    def _on_groups_list(self, groups: list) -> None:
        self.window.after(0, lambda: self._lobby_view.update_groups(groups))

    def _on_group_entered(self, group_data: dict) -> None:
        # Called when user creates or joins a group
        self._in_group = True
        self.window.after(0, lambda: self._enter_group(group_data))

    def _enter_group(self, group_data: dict) -> None:
        self._show_view(self._group_view)
        self._group_view.update_group(group_data)

    def _on_group_update(self, data: dict) -> None:
        if self._in_group:
            self.window.after(0, lambda: self._group_view.update_group(data))

    def _on_group_left(self) -> None:
        self._in_group = False
        self.key_handler.set_leader(False)
        self.key_handler.update_locks({})
        self._safe_show(self._lobby_view)

    def _on_key_lock_toggled(self, key: str, locked: bool) -> None:
        # This is handled via group_update which follows key_lock_toggled
        pass

    def _on_leader_changed(self, new_leader_id: str, new_leader_username: str) -> None:
        # Will be reflected in the next group_update
        pass

    def _on_kicked(self, reason: str) -> None:
        self._in_group = False
        self.key_handler.set_leader(False)
        self.key_handler.update_locks({})
        self._safe_show(self._lobby_view)
        self.window.after(
            100,
            lambda: self._lobby_view.show_error(
                f"Has sido expulsado del grupo ({reason})"
            ),
        )

    def _on_server_error(self, message: str) -> None:
        self.window.after(0, lambda: self._handle_server_error(message))

    def _handle_server_error(self, message: str) -> None:
        if self._current_view == self._lobby_view:
            self._lobby_view.show_error(message)
        elif self._current_view == self._group_view:
            self._group_view.show_error(message)
        elif self._current_view == self._login_view:
            self._login_view.show_error(message)

    # Local key input events
    def _on_local_toggle(self, key: str) -> None:
        self.ws_client.toggle_key_lock(key)

    def _on_local_key_press(self, key: str) -> None:
        self.ws_client.press_key(key)

    # -- Lifecycle --

    def _on_close(self) -> None:
        """Clean shutdown."""
        self.key_handler.cleanup()
        self.ws_client.disconnect()
        self.window.destroy()

    def run(self) -> None:
        """Start the application main loop."""
        self.window.mainloop()
