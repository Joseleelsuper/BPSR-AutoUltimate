"""Login view — asks for a username before connecting."""

from __future__ import annotations

import customtkinter as ctk

from src.gui.base_view import BaseView


class LoginView(BaseView):
    """First screen: enter a username to identify yourself."""

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Center container
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.grid(row=0, column=0)

        title = ctk.CTkLabel(
            container,
            text="BPSR AutoUltimate",
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        title.pack(pady=(0, 8))

        subtitle = ctk.CTkLabel(
            container,
            text="Introduce nombre de usuario",
            font=ctk.CTkFont(size=15),
            text_color="gray70",
        )
        subtitle.pack(pady=(0, 20))

        self._entry = ctk.CTkEntry(
            container,
            placeholder_text="Username",
            width=280,
            height=40,
            font=ctk.CTkFont(size=14),
        )
        self._entry.pack(pady=(0, 16))
        self._entry.bind("<Return>", lambda _e: self._on_submit())

        self._btn = ctk.CTkButton(
            container,
            text="Entrar",
            width=280,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._on_submit,
        )
        self._btn.pack(pady=(0, 8))

        self._error_label = ctk.CTkLabel(
            container,
            text="",
            text_color="#ff6b6b",
            font=ctk.CTkFont(size=12),
        )
        self._error_label.pack()

        self._status_label = ctk.CTkLabel(
            container,
            text="",
            text_color="gray60",
            font=ctk.CTkFont(size=11),
        )
        self._status_label.pack(pady=(8, 0))

    def on_show(self) -> None:
        self._entry.focus()
        self._error_label.configure(text="")
        self._status_label.configure(text="")
        self._btn.configure(state="normal")

    def _on_submit(self) -> None:
        username = self._entry.get().strip()
        if not username:
            self._error_label.configure(text="El nombre no puede estar vacío")
            return
        if len(username) > 30:
            self._error_label.configure(text="Máximo 30 caracteres")
            return

        self._error_label.configure(text="")
        self._status_label.configure(text="Conectando...")
        self._btn.configure(state="disabled")
        self.app.do_login(username)

    def show_error(self, message: str) -> None:
        self._error_label.configure(text=message)
        self._status_label.configure(text="")
        self._btn.configure(state="normal")
