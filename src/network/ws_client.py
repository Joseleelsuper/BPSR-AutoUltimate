"""WebSocket client — runs its own asyncio loop in a background thread.

All public methods are thread-safe and can be called from the GUI thread.
Events are emitted via the EventBus so the GUI can react.

Events emitted:
    connected          (connection_id: str, username: str)
    disconnected       ()
    connection_error   (message: str)
    groups_list        (groups: list[dict])
    group_created      (group: dict)
    group_joined       (group: dict)
    group_update       (group: dict)
    group_left         ()
    key_lock_toggled   (key: str, locked: bool)
    simulate_key       (key: str)
    leader_changed     (new_leader_id: str, new_leader_username: str)
    kicked             (reason: str)
    server_error       (code: str, message: str)

Messages sent:
    transfer_leader    { type, target_username }
"""

from __future__ import annotations

import asyncio
import json
import threading
from typing import Any, Dict, Optional

import websockets
import websockets.exceptions

from src.config import CONFIG
from src.network.event_bus import EventBus


class WSClient:
    """Manages a persistent WebSocket connection in a background thread."""

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self._bus = event_bus or EventBus.instance()
        self._ws: Optional[Any] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._connection_id: Optional[str] = None
        self._username: Optional[str] = None
        self._reconnect = False

    # -- Properties --

    @property
    def connected(self) -> bool:
        return self._ws is not None and self._running

    @property
    def connection_id(self) -> Optional[str]:
        return self._connection_id

    @property
    def username(self) -> Optional[str]:
        return self._username

    # -- Public API (called from GUI thread) --

    def connect(self, username: str, *, reconnect: bool = True) -> None:
        """Start the background connection loop."""
        if self._running:
            return
        self._username = username
        self._reconnect = reconnect
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="ws-client"
        )
        self._thread.start()

    def disconnect(self) -> None:
        """Gracefully shut down the connection."""
        self._running = False
        self._reconnect = False
        if self._loop and self._ws:
            asyncio.run_coroutine_threadsafe(self._close_ws(), self._loop)

    def send(self, data: dict) -> None:
        """Queue a message for sending (thread-safe)."""
        if self._loop and self._ws:
            asyncio.run_coroutine_threadsafe(self._send(data), self._loop)

    # Convenience methods

    def request_groups(self) -> None:
        self.send({"type": "list_groups"})

    def create_group(self, name: str, password: Optional[str] = None) -> None:
        msg: Dict[str, Any] = {"type": "create_group", "name": name}
        if password:
            msg["password"] = password
        self.send(msg)

    def join_group(self, group_id: str, password: Optional[str] = None) -> None:
        msg: Dict[str, Any] = {"type": "join_group", "group_id": group_id}
        if password:
            msg["password"] = password
        self.send(msg)

    def leave_group(self) -> None:
        self.send({"type": "leave_group"})

    def toggle_key_lock(self, key: str = "r") -> None:
        self.send({"type": "toggle_key_lock", "key": key})

    def press_key(self, key: str = "r") -> None:
        self.send({"type": "key_press", "key": key})

    def ban_user(self, username: str) -> None:
        self.send({"type": "ban_user", "username": username})

    def transfer_leader(self, username: str) -> None:
        self.send({"type": "transfer_leader", "target_username": username})

    def unban_user(self, username: str) -> None:
        self.send({"type": "unban_user", "username": username})

    # -- Internals --

    def _run_loop(self) -> None:
        """Background thread: create an event loop and run the connection."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connection_loop())
        finally:
            self._loop.close()
            self._loop = None

    async def _connection_loop(self) -> None:
        """Connect, authenticate, and listen. Reconnect on failure."""
        delay = CONFIG.reconnect_delay

        while self._running:
            try:
                async with websockets.connect(
                    CONFIG.server_url,
                    max_size=2**20,
                    close_timeout=5,
                ) as ws:
                    self._ws = ws
                    delay = CONFIG.reconnect_delay  # Reset backoff on success
                    await self._authenticate_and_listen(ws)
            except websockets.exceptions.ConnectionClosed:
                pass
            except (
                OSError,
                websockets.exceptions.WebSocketException,
            ) as exc:
                self._bus.emit("connection_error", str(exc))
            except Exception as exc:
                self._bus.emit("connection_error", f"Unexpected: {exc}")
            finally:
                self._ws = None
                self._connection_id = None
                self._bus.emit("disconnected")

            if not self._running or not self._reconnect:
                break

            # Exponential backoff
            await asyncio.sleep(delay)
            delay = min(delay * 1.5, CONFIG.max_reconnect_delay)

    async def _authenticate_and_listen(self, ws: Any) -> None:
        """Authenticate with the server and listen for messages."""
        auth_msg = {
            "type": "auth",
            "api_key": CONFIG.api_key,
            "username": self._username,
        }
        await ws.send(json.dumps(auth_msg))

        # Wait for auth_ok or error
        raw = await ws.recv()
        resp = json.loads(raw)

        if resp.get("type") == "error":
            self._bus.emit("connection_error", resp.get("message", "Auth failed"))
            self._running = False
            return

        if resp.get("type") == "auth_ok":
            self._connection_id = resp.get("connection_id")
            self._bus.emit("connected", self._connection_id, self._username)

        # Message loop
        async for raw_msg in ws:
            if not self._running:
                break
            try:
                msg = json.loads(raw_msg)
            except json.JSONDecodeError:
                continue
            self._handle_message(msg)

    async def _send(self, data: dict) -> None:
        if self._ws:
            try:
                await self._ws.send(json.dumps(data))
            except Exception:
                pass

    async def _close_ws(self) -> None:
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass

    def _handle_message(self, msg: dict) -> None:
        """Route incoming server messages to EventBus events."""
        msg_type = msg.get("type")
        if not msg_type:
            return

        if msg_type == "groups_list":
            self._bus.emit("groups_list", msg.get("groups", []))

        elif msg_type == "group_created":
            self._bus.emit("group_created", msg.get("group", msg))

        elif msg_type == "group_joined":
            self._bus.emit("group_joined", msg.get("group", msg))

        elif msg_type == "group_update":
            self._bus.emit("group_update", msg)

        elif msg_type == "group_left":
            self._bus.emit("group_left")

        elif msg_type == "key_lock_toggled":
            self._bus.emit("key_lock_toggled", msg.get("key"), msg.get("locked"))

        elif msg_type == "simulate_key":
            self._bus.emit("simulate_key", msg.get("key"))

        elif msg_type == "leader_changed":
            self._bus.emit(
                "leader_changed",
                msg.get("new_leader_id"),
                msg.get("new_leader_username"),
            )

        elif msg_type == "kicked":
            self._bus.emit("kicked", msg.get("reason", ""))

        elif msg_type == "error":
            self._bus.emit("server_error", msg.get("code", ""), msg.get("message", ""))

        else:
            # Unknown message — ignore gracefully
            pass
