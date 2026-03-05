"""Group view — shows members, key-lock states, leader controls."""

from __future__ import annotations

import customtkinter as ctk

from src.gui.base_view import BaseView
from src.models.group import Group


class GroupView(BaseView):
    """View shown once a user has joined (or created) a group."""

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Header ---
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        header.grid_columnconfigure(1, weight=1)

        self._group_name_label = ctk.CTkLabel(
            header,
            text="Grupo",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self._group_name_label.grid(row=0, column=0, sticky="w")

        self._role_label = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
        )
        self._role_label.grid(row=0, column=1, sticky="w", padx=12)

        self._leave_btn = ctk.CTkButton(
            header,
            text="Salir del grupo",
            width=130,
            fg_color="#cc4444",
            hover_color="#aa3333",
            font=ctk.CTkFont(size=13),
            command=self._on_leave,
        )
        self._leave_btn.grid(row=0, column=2, sticky="e")

        # --- Body ---
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 8))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=0)
        body.grid_rowconfigure(0, weight=1)

        # Members list
        members_frame = ctk.CTkFrame(body)
        members_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        members_frame.grid_columnconfigure(0, weight=1)
        members_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            members_frame,
            text="Miembros",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 4))

        self._members_scroll = ctk.CTkScrollableFrame(members_frame)
        self._members_scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self._members_scroll.grid_columnconfigure(0, weight=1)

        # Side panel — key locks & controls
        side = ctk.CTkFrame(body, width=220)
        side.grid(row=0, column=1, sticky="nsew")
        side.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            side,
            text="Estado de teclas",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))

        self._locks_frame = ctk.CTkFrame(side, fg_color="transparent")
        self._locks_frame.grid(row=1, column=0, sticky="ew", padx=12)
        self._locks_frame.grid_columnconfigure(0, weight=1)

        # Leader-only controls
        self._leader_frame = ctk.CTkFrame(side, fg_color="transparent")
        self._leader_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(16, 8))

        self._leader_info = ctk.CTkLabel(
            self._leader_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray55",
            wraplength=200,
            justify="left",
        )
        self._leader_info.pack(anchor="w")

        # --- Bottom status ---
        self._status = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray50",
        )
        self._status.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 8))

        # State
        self._current_group: Group | None = None
        self._is_leader = False

    def on_show(self) -> None:
        # When this view is shown, we should already have the latest group data from the server.
        pass

    def update_group(self, group_data: dict) -> None:
        """Update the view with fresh group data from the server."""
        self._current_group = Group.from_dict(group_data)
        conn_id = self.app.ws_client.connection_id
        self._is_leader = self._current_group.leader_id == conn_id

        self._group_name_label.configure(text=self._current_group.name)
        role_text = "👑 Líder" if self._is_leader else "👤 Miembro"
        self._role_label.configure(text=role_text)

        # Update key handler state
        self.app.key_handler.set_leader(self._is_leader)
        self.app.key_handler.update_locks(self._current_group.key_locks)

        self._render_members()
        self._render_locks()
        self._render_leader_info()

    def _render_members(self) -> None:
        for w in self._members_scroll.winfo_children():
            w.destroy()

        if not self._current_group:
            return

        for i, member in enumerate(self._current_group.members):
            is_leader = member.role == "leader"
            icon = "👑" if is_leader else "👤"
            text = f"  {icon}  {member.username}"

            row_frame = ctk.CTkFrame(self._members_scroll, fg_color="transparent")
            row_frame.grid(row=i, column=0, sticky="ew", pady=2)
            row_frame.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                row_frame,
                text=text,
                font=ctk.CTkFont(size=13, weight="bold" if is_leader else "normal"),
                anchor="w",
            ).grid(row=0, column=0, sticky="w")

            # Leader can ban/transfer to members (not themselves)
            if (
                self._is_leader
                and not is_leader
                and member.connection_id != self.app.ws_client.connection_id
            ):
                ctk.CTkButton(
                    row_frame,
                    text="Ban",
                    width=50,
                    height=24,
                    fg_color="#cc4444",
                    hover_color="#aa3333",
                    font=ctk.CTkFont(size=11),
                    command=lambda u=member.username: self._on_ban(u),
                ).grid(row=0, column=1, padx=(4, 10))

                ctk.CTkButton(
                    row_frame,
                    text="👑",
                    width=36,
                    height=24,
                    fg_color="#b8860b",
                    hover_color="#8b6508",
                    font=ctk.CTkFont(size=11),
                    command=lambda u=member.username: self._on_transfer_leader(u),
                ).grid(row=0, column=2, padx=(0, 4))

    def _render_locks(self) -> None:
        for w in self._locks_frame.winfo_children():
            w.destroy()

        if not self._current_group:
            return

        for i, (key, locked) in enumerate(self._current_group.key_locks.items()):
            state_text = "🟢 ACTIVO" if locked else "⚪ Inactivo"
            state_color = "#44cc66" if locked else "gray55"

            row = ctk.CTkFrame(self._locks_frame, fg_color="transparent")
            row.grid(row=i, column=0, sticky="ew", pady=4)
            row.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                row,
                text=f"Tecla [{key.upper()}]",
                font=ctk.CTkFont(size=13, weight="bold"),
            ).grid(row=0, column=0, sticky="w")

            ctk.CTkLabel(
                row,
                text=state_text,
                font=ctk.CTkFont(size=12),
                text_color=state_color,
            ).grid(row=0, column=1, sticky="e")

    def _render_leader_info(self) -> None:
        if self._is_leader:
            self._leader_info.configure(
                text=(
                    "🎮 Controles de líder:\n"
                    "• F9 — Activar/desactivar bloqueo de tecla R\n"
                    "• R — Pulsar R en todos los miembros\n"
                    "  (solo cuando el bloqueo está activo)"
                )
            )
            self._status.configure(text="Eres el líder del grupo")
        else:
            self._leader_info.configure(text="Esperando instrucciones del líder...")
            self._status.configure(text="Conectado al grupo")

    def _on_leave(self) -> None:
        self.app.ws_client.leave_group()

    def _on_ban(self, username: str) -> None:
        self.app.ws_client.ban_user(username)

    def _on_transfer_leader(self, username: str) -> None:
        self.app.ws_client.transfer_leader(username)

    def show_error(self, message: str) -> None:
        self._status.configure(text=f"❌ {message}", text_color="#ff6b6b")
        self.after(4000, lambda: self._status.configure(text="", text_color="gray50"))
