"""Kivy screens for BPSR AutoUltimate mobile."""

from __future__ import annotations

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput

from src.models.group import Group


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class LoginScreen(Screen):
    error_text = StringProperty("")
    status_text = StringProperty("")

    def on_submit(self) -> None:
        username = self.ids.username_input.text.strip()
        if not username:
            self.error_text = "El nombre no puede estar vacío"
            return
        if len(username) > 30:
            self.error_text = "Máximo 30 caracteres"
            return

        self.error_text = ""
        self.status_text = "Conectando..."
        self.ids.login_btn.disabled = True
        App.get_running_app().do_login(username)

    def show_error(self, message: str) -> None:
        self.error_text = message
        self.status_text = ""
        self.ids.login_btn.disabled = False

    def on_enter(self) -> None:
        self.error_text = ""
        self.status_text = ""
        self.ids.login_btn.disabled = False


# ---------------------------------------------------------------------------
# Group card (used inside LobbyScreen)
# ---------------------------------------------------------------------------


class GroupCard(BoxLayout):
    group_name = StringProperty("")
    member_info = StringProperty("")
    has_password = BooleanProperty(False)

    def __init__(self, group: Group, on_join, **kwargs) -> None:  # noqa: ANN001
        super().__init__(**kwargs)
        self.group = group
        self._on_join = on_join
        self.group_name = ("\U0001f512 " if group.has_password else "") + group.name
        self.member_info = f"{group.member_count} miembro(s)"

    def join(self) -> None:
        self._on_join(self.group)


# ---------------------------------------------------------------------------
# Lobby
# ---------------------------------------------------------------------------


class LobbyScreen(Screen):
    status_text = StringProperty("Conectado")

    def on_enter(self) -> None:
        app = App.get_running_app()
        self.ids.user_label.text = f"\U0001f464 {app.username or ''}"
        app.ws_client.request_groups()

    def update_groups(self, groups_data: list[dict]) -> None:
        groups = [Group.from_dict(g) for g in groups_data]
        container = self.ids.groups_container
        container.clear_widgets()

        if not groups:
            lbl = Label(
                text="No hay grupos aún.\nUn usuario de escritorio debe crear uno.",
                font_size=sp(14),
                color=(0.69, 0.69, 0.69, 1),
                size_hint_y=None,
                height=dp(80),
                halign="center",
            )
            lbl.bind(size=lbl.setter("text_size"))
            container.add_widget(lbl)
            return

        for group in groups:
            card = GroupCard(group, on_join=self._on_join_group)
            container.add_widget(card)

    def _on_join_group(self, group: Group) -> None:
        if group.has_password:
            self._show_password_dialog(group)
        else:
            App.get_running_app().ws_client.join_group(group.id)

    def _show_password_dialog(self, group: Group) -> None:
        content = BoxLayout(
            orientation="vertical", padding=dp(16), spacing=dp(12)
        )
        pwd_input = TextInput(
            hint_text="Contraseña",
            password=True,
            multiline=False,
            size_hint_y=None,
            height=dp(44),
            font_size=sp(15),
        )
        content.add_widget(pwd_input)

        popup = Popup(
            title=f'Contraseña para "{group.name}"',
            content=content,
            size_hint=(0.85, 0.3),
            auto_dismiss=True,
        )

        btn = Button(
            text="Unirse",
            size_hint_y=None,
            height=dp(44),
            font_size=sp(15),
            background_normal="",
            background_color=(0.098, 0.463, 0.824, 1),
            color=(1, 1, 1, 1),
        )

        def _submit(_instance):  # noqa: ANN001
            pwd = pwd_input.text.strip()
            popup.dismiss()
            App.get_running_app().ws_client.join_group(group.id, pwd)

        btn.bind(on_release=_submit)
        content.add_widget(btn)
        popup.open()

    def show_error(self, message: str) -> None:
        self.status_text = f"\u274c {message}"
        Clock.schedule_once(
            lambda _dt: setattr(self, "status_text", "Conectado"), 4
        )


# ---------------------------------------------------------------------------
# Group
# ---------------------------------------------------------------------------


class GroupScreen(Screen):
    group_name_text = StringProperty("Grupo")
    role_text = StringProperty("")
    status_text = StringProperty("")

    def __init__(self, **kwargs) -> None:  # noqa: ANN003
        super().__init__(**kwargs)
        self._current_group: Group | None = None

    def update_group(self, group_data: dict) -> None:
        self._current_group = Group.from_dict(group_data)
        app = App.get_running_app()
        conn_id = app.ws_client.connection_id
        is_leader = self._current_group.leader_id == conn_id

        self.group_name_text = self._current_group.name
        self.role_text = (
            "\U0001f451 Líder" if is_leader else "\U0001f4f1 Miembro (móvil)"
        )

        self._render_members()
        self._render_locks()

    def _render_members(self) -> None:
        container = self.ids.members_container
        container.clear_widgets()

        if not self._current_group:
            return

        for member in self._current_group.members:
            is_leader = member.role == "leader"
            device = (
                "\U0001f4f1" if member.device_type == "mobile" else "\U0001f4bb"
            )
            icon = "\U0001f451" if is_leader else device
            text = f"  {icon}  {member.username}"

            lbl = Label(
                text=text,
                font_size=sp(14),
                color=(1, 1, 1, 1),
                size_hint_y=None,
                height=dp(40),
                halign="left",
                bold=is_leader,
            )
            lbl.bind(size=lbl.setter("text_size"))
            container.add_widget(lbl)

    def _render_locks(self) -> None:
        container = self.ids.locks_container
        container.clear_widgets()

        if not self._current_group:
            return

        for key, locked in self._current_group.key_locks.items():
            state_text = "\U0001f7e2 ACTIVO" if locked else "\u26aa Inactivo"
            color = (0.267, 0.8, 0.4, 1) if locked else (0.69, 0.69, 0.69, 1)

            lbl = Label(
                text=f"Tecla [{key.upper()}]: {state_text}",
                font_size=sp(14),
                color=color,
                size_hint_y=None,
                height=dp(36),
                halign="left",
            )
            lbl.bind(size=lbl.setter("text_size"))
            container.add_widget(lbl)

    def on_leave_group(self) -> None:
        App.get_running_app().ws_client.leave_group()

    def show_error(self, message: str) -> None:
        self.status_text = f"\u274c {message}"
        Clock.schedule_once(
            lambda _dt: setattr(self, "status_text", ""), 4
        )
