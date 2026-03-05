"""Keyboard input handling — capture & simulate keys via pynput.

Uses the Strategy pattern so key mappings are easily extensible.
"""
from __future__ import annotations

from typing import Dict, Optional, Set

from pynput import keyboard
from pynput.keyboard import Controller, Key, KeyCode

from src.network.event_bus import EventBus


# ---------------------------------------------------------------------------
# Key mapping — extend this dict to support more keys in the future
# ---------------------------------------------------------------------------

KEY_MAP: Dict[str, Key | KeyCode | str] = {
    "r": KeyCode.from_char("r"),
    # Example future keys:
    # "space": Key.space,
    # "e": KeyCode.from_char("e"),
}

# Special keys that trigger actions (not simulated, just captured)
TOGGLE_KEY = Key.f9  # F9 toggles key lock


# ---------------------------------------------------------------------------
# Key Simulator — receives "simulate_key" events and presses keys
# ---------------------------------------------------------------------------

class KeySimulator:
    """Simulates key presses on the local machine."""

    def __init__(self) -> None:
        self._controller = Controller()
        self._enabled = True

    def simulate(self, key_name: str) -> None:
        """Press and release a key by name."""
        if not self._enabled:
            return
        target = KEY_MAP.get(key_name.lower())
        if target is None:
            return
        try:
            self._controller.press(target)
            self._controller.release(target)
        except Exception as exc:
            print(f"[KeySimulator] Failed to simulate '{key_name}': {exc}")

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled


# ---------------------------------------------------------------------------
# Key Listener — captures global key events
# ---------------------------------------------------------------------------

class KeyListener:
    """Listens for global key presses and emits events.

    When the user is a leader and key lock is active:
      - F9 → toggles key lock (emits 'local_toggle_key_lock')
      - R (or mapped key) → emits 'local_key_press'
    """

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self._bus = event_bus or EventBus.instance()
        self._listener: Optional[keyboard.Listener] = None
        self._is_leader = False
        self._locked_keys: Set[str] = set()

    def start(self) -> None:
        """Start the global key listener in a background thread."""
        if self._listener is not None:
            return
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        """Stop the global key listener."""
        if self._listener:
            self._listener.stop()
            self._listener = None

    def set_leader(self, is_leader: bool) -> None:
        """Update whether the local user is the group leader."""
        self._is_leader = is_leader

    def set_locked_keys(self, keys: Set[str]) -> None:
        """Update which keys are currently locked (for leader capture)."""
        self._locked_keys = keys

    def _on_press(self, key: Key | KeyCode | None) -> None:
        if key is None:
            return

        # F9 toggle — only for leader
        if key == TOGGLE_KEY and self._is_leader:
            self._bus.emit("local_toggle_key_lock", "r")
            return

        # Leader key press — send to server for broadcast
        if self._is_leader:
            key_name = self._resolve_key_name(key)
            if key_name and key_name in self._locked_keys:
                self._bus.emit("local_key_press", key_name)

    def _on_release(self, key: Key | KeyCode | None) -> None:
        # We don't need to handle key releases for this application.
        pass

    @staticmethod
    def _resolve_key_name(key: Key | KeyCode | None) -> Optional[str]:
        """Convert a pynput key object to our string key name."""
        if isinstance(key, KeyCode) and key.char:
            char = key.char.lower()
            if char in KEY_MAP:
                return char
        elif isinstance(key, Key):
            for name, mapped in KEY_MAP.items():
                if key == mapped:
                    return name
        return None


# ---------------------------------------------------------------------------
# KeyHandler — facade that wires listener + simulator + event bus
# ---------------------------------------------------------------------------

class KeyHandler:
    """High-level facade combining KeyListener and KeySimulator.

    Listens for EventBus events and orchestrates key I/O.
    """

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self._bus = event_bus or EventBus.instance()
        self.listener = KeyListener(self._bus)
        self.simulator = KeySimulator()
        self._active = False

        # Subscribe to network events
        self._bus.subscribe("simulate_key", self._on_simulate_key)

    def start(self) -> None:
        """Activate key handling."""
        if self._active:
            return
        self._active = True
        self.listener.start()

    def stop(self) -> None:
        """Deactivate key handling."""
        self._active = False
        self.listener.stop()

    def set_leader(self, is_leader: bool) -> None:
        self.listener.set_leader(is_leader)

    def update_locks(self, key_locks: Dict[str, bool]) -> None:
        """Update locked keys from a group_update."""
        locked = {k for k, v in key_locks.items() if v}
        self.listener.set_locked_keys(locked)

    def _on_simulate_key(self, key_name: str) -> None:
        """Called when the server tells us to simulate a key press."""
        if self._active:
            self.simulator.simulate(key_name)

    def cleanup(self) -> None:
        """Unsubscribe and stop."""
        self.stop()
        self._bus.unsubscribe("simulate_key", self._on_simulate_key)
