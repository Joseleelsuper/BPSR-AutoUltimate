"""Base view class — Template Method pattern for customtkinter frames."""

from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from src.app import App


class BaseView(ctk.CTkFrame):
    """Abstract base for all application views.

    Subclasses must implement `_build_ui()` which is called once during init.
    Optionally override `on_show()` / `on_hide()` for lifecycle hooks.
    """

    def __init__(self, master: ctk.CTk, app: "App", **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.app = app
        self._build_ui()

    def _build_ui(self) -> None:
        raise NotImplementedError

    def on_show(self) -> None:
        """Called when this view becomes active."""
        pass

    def on_hide(self) -> None:
        """Called when this view is about to be replaced."""
        pass
