"""Lobby view — list groups, create, and join."""

from __future__ import annotations

from typing import List, Optional

import customtkinter as ctk

from src.gui.base_view import BaseView
from src.models.group import Group


class _GroupCard(ctk.CTkFrame):
    """A single row representing a group in the lobby list."""

    def __init__(self, master, group: Group, on_join, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.group = group
        self.grid_columnconfigure(1, weight=1)

        lock_icon = "🔒 " if group.has_password else ""

        name_label = ctk.CTkLabel(
            self,
            text=f"{lock_icon}{group.name}",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        name_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(8, 0))

        info = ctk.CTkLabel(
            self,
            text=f"{group.member_count} miembro(s)",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
            anchor="w",
        )
        info.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8))

        join_btn = ctk.CTkButton(
            self,
            text="+ Unirse",
            width=90,
            height=30,
            font=ctk.CTkFont(size=12),
            command=lambda: on_join(group),
        )
        join_btn.grid(row=0, column=2, rowspan=2, padx=12, pady=8)


class _CreateGroupDialog(ctk.CTkToplevel):
    """Modal dialog to create a new group."""

    def __init__(self, master, on_create, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.title("Crear Grupo")
        self.geometry("350x250")
        self.resizable(False, False)
        self.grab_set()

        self._on_create = on_create

        ctk.CTkLabel(self, text="Nombre del grupo", font=ctk.CTkFont(size=14)).pack(
            pady=(20, 4)
        )
        self._name_entry = ctk.CTkEntry(self, width=260, placeholder_text="Mi grupo")
        self._name_entry.pack(pady=(0, 12))

        ctk.CTkLabel(
            self, text="Contraseña (opcional)", font=ctk.CTkFont(size=14)
        ).pack(pady=(0, 4))
        self._pwd_entry = ctk.CTkEntry(
            self, width=260, placeholder_text="Dejar vacío = sin contraseña", show="•"
        )
        self._pwd_entry.pack(pady=(0, 16))

        self._error_label = ctk.CTkLabel(
            self, text="", text_color="#ff6b6b", font=ctk.CTkFont(size=11)
        )
        self._error_label.pack()

        ctk.CTkButton(
            self,
            text="Crear",
            width=260,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._submit,
        ).pack(pady=(8, 0))

        self._name_entry.focus()
        self._name_entry.bind("<Return>", lambda _: self._submit())

    def _submit(self) -> None:
        name = self._name_entry.get().strip()
        if not name:
            self._error_label.configure(text="El nombre no puede estar vacío")
            return
        if len(name) > 50:
            self._error_label.configure(text="Máximo 50 caracteres")
            return
        pwd = self._pwd_entry.get().strip() or None
        self._on_create(name, pwd)
        self.destroy()


class _PasswordDialog(ctk.CTkToplevel):
    """Modal dialog to enter a group password."""

    def __init__(self, master, group_name: str, on_submit, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.title("Contraseña requerida")
        self.geometry("320x180")
        self.resizable(False, False)
        self.grab_set()

        self._on_submit = on_submit

        ctk.CTkLabel(
            self, text=f"Grupo: {group_name}", font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(20, 4))
        ctk.CTkLabel(
            self, text="Introduce la contraseña", font=ctk.CTkFont(size=12)
        ).pack(pady=(0, 8))

        self._pwd_entry = ctk.CTkEntry(self, width=240, show="•")
        self._pwd_entry.pack(pady=(0, 12))
        self._pwd_entry.focus()
        self._pwd_entry.bind("<Return>", lambda _: self._submit())

        ctk.CTkButton(self, text="Unirse", width=240, command=self._submit).pack()

    def _submit(self) -> None:
        pwd = self._pwd_entry.get().strip()
        self._on_submit(pwd)
        self.destroy()


class LobbyView(BaseView):
    """Lists available groups and allows creating or joining one."""

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        header.grid_columnconfigure(1, weight=1)

        title = ctk.CTkLabel(
            header,
            text="Grupos disponibles",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        self._user_label = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
        )
        self._user_label.grid(row=0, column=1, sticky="e", padx=(0, 8))

        self._create_btn = ctk.CTkButton(
            header,
            text="+ Crear Grupo",
            width=130,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_create_group,
        )
        self._create_btn.grid(row=0, column=2, sticky="e")

        # Scrollable group list
        self._scroll = ctk.CTkScrollableFrame(self)
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 8))
        self._scroll.grid_columnconfigure(0, weight=1)

        self._empty_label = ctk.CTkLabel(
            self._scroll,
            text="No hay grupos aún. ¡Crea el primero!",
            font=ctk.CTkFont(size=13),
            text_color="gray55",
        )

        # Status bar
        self._status = ctk.CTkLabel(
            self,
            text="Conectado",
            font=ctk.CTkFont(size=11),
            text_color="gray50",
        )
        self._status.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 8))

        self._groups: List[Group] = []

    def on_show(self) -> None:
        username = self.app.username or ""
        self._user_label.configure(text=f"👤 {username}")
        self.app.ws_client.request_groups()

    def update_groups(self, groups_data: List[dict]) -> None:
        """Called with the latest groups list from the server."""
        self._groups = [Group.from_dict(g) for g in groups_data]
        self._render_groups()

    def _render_groups(self) -> None:
        # Clear existing cards
        for widget in self._scroll.winfo_children():
            widget.destroy()

        if not self._groups:
            self._empty_label = ctk.CTkLabel(
                self._scroll,
                text="No hay grupos aún. ¡Crea el primero!",
                font=ctk.CTkFont(size=13),
                text_color="gray55",
            )
            self._empty_label.grid(row=0, column=0, pady=40)
            return

        for i, group in enumerate(self._groups):
            card = _GroupCard(
                self._scroll,
                group,
                on_join=self._on_join_group,
                corner_radius=8,
            )
            card.grid(row=i, column=0, sticky="ew", pady=4)

    def _on_create_group(self) -> None:
        _CreateGroupDialog(self, on_create=self._do_create)

    def _do_create(self, name: str, password: Optional[str]) -> None:
        self.app.ws_client.create_group(name, password)

    def _on_join_group(self, group: Group) -> None:
        if group.has_password:
            _PasswordDialog(
                self,
                group.name,
                on_submit=lambda pwd: self.app.ws_client.join_group(group.id, pwd),
            )
        else:
            self.app.ws_client.join_group(group.id)

    def show_error(self, message: str) -> None:
        self._status.configure(text=f"❌ {message}", text_color="#ff6b6b")
        self.after(
            4000, lambda: self._status.configure(text="Conectado", text_color="gray50")
        )
