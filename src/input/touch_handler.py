"""Touch simulation for Android.

When the server sends a ``simulate_key`` event the handler converts the key
name into screen-tap coordinates using the ratios defined in ``Config`` and
executes an ``input tap`` command on the device.

Resolution scaling:
    Reference position for key "r" → (1680, 940) on a 2400×1080 screen.
    Ratios: x=0.7, y≈0.8704.
    On any device the tap is placed at (width*x_ratio, height*y_ratio),
    adapting automatically to phones *and* tablets.

Requirements (Android):
    • Rooted device  → ``su -c "input tap X Y"``
    • Non-rooted     → ``input tap X Y`` (only works on some ROMs / via Shizuku)
"""

from __future__ import annotations

import subprocess
from typing import Optional

from kivy.utils import platform

from src.config import CONFIG
from src.network.event_bus import EventBus


def _get_screen_resolution() -> tuple[int, int]:
    """Return the real screen resolution in physical pixels."""
    if platform == "android":
        try:
            from jnius import autoclass  # type: ignore[import-untyped]

            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            DisplayMetrics = autoclass("android.util.DisplayMetrics")
            metrics = DisplayMetrics()
            PythonActivity.mActivity.getWindowManager().getDefaultDisplay().getRealMetrics(
                metrics
            )
            return metrics.widthPixels, metrics.heightPixels
        except Exception:
            pass

    # Fallback for desktop testing — use Kivy's window size.
    from kivy.core.window import Window  # noqa: E402

    return int(Window.width), int(Window.height)


class TouchHandler:
    """Converts ``simulate_key`` events into Android screen taps."""

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self._bus = event_bus or EventBus.instance()
        self._active = False
        self._bus.subscribe("simulate_key", self._on_simulate_key)

    def start(self) -> None:
        self._active = True

    def stop(self) -> None:
        self._active = False

    def _on_simulate_key(self, key_name: str) -> None:
        if not self._active:
            return

        position = CONFIG.tap_positions.get(key_name)
        if position is None:
            return

        x_ratio, y_ratio = position
        screen_w, screen_h = _get_screen_resolution()
        tap_x = int(screen_w * x_ratio)
        tap_y = int(screen_h * y_ratio)
        self._perform_tap(tap_x, tap_y)

    @staticmethod
    def _perform_tap(x: int, y: int) -> None:
        """Execute a tap at the given pixel coordinates."""
        if platform == "android":
            try:
                subprocess.Popen(
                    ["su", "-c", f"input tap {x} {y}"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except FileNotFoundError:
                try:
                    subprocess.Popen(
                        ["input", "tap", str(x), str(y)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except Exception:
                    pass
            except Exception:
                pass
        else:
            print(f"[TouchHandler] Would tap at ({x}, {y})")

    def cleanup(self) -> None:
        self.stop()
        self._bus.unsubscribe("simulate_key", self._on_simulate_key)
