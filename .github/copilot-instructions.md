# BPSR-AutoUltimate — Copilot Instructions (Mobile Branch)

## Purpose
Real-time remote key synchronization **mobile** app for Android. A group leader (desktop) sends keypresses via WebSocket; the mobile client simulates screen taps at proportional coordinates using `input tap`. Built with Kivy + Buildozer.

## Architecture
`BPSRApp` (`src/app.py`) is the central wiring hub. All subsystems are connected through `EventBus` — no layer imports directly from another (except screens via `App.get_running_app()`).

```
main.py → BPSRApp (Kivy) → [GUI, Network, Input, Models, Config]
                              EventBus (thread-safe pub/sub glue)
```

Key directories:
- `src/gui/` — Kivy `Screen` subclasses + `bpsr.kv` layout
- `src/network/` — `WSClient` (websockets, async) + `EventBus` (singleton)
- `src/input/` — `TouchHandler` (Android `input tap` via subprocess)
- `src/models/` — Pure `@dataclass` models with `from_dict()` factories
- `src/config.py` — Singleton loading from env vars / `.env`
- `buildozer.spec` — Android APK build configuration

## Threading Model
`WSClient` runs an `asyncio` event loop in a **daemon thread**. EventBus callbacks that touch Kivy widgets **must** schedule via `Clock.schedule_once(callback, 0)`.

## Mobile-Specific Constraints
- Mobile users **cannot** be group leaders (no key capture capability)
- Mobile users **cannot** create groups (creation = becoming leader)
- `simulate_key` events are converted to screen taps via `TouchHandler`
- Tap positions are defined as screen ratios in `Config.tap_positions`
- Root (or Shizuku) required for Android tap simulation outside the app

## Design Patterns
- **Singleton**: `EventBus` and `Config` use `_instance` + `classmethod instance()`.
- **ScreenManager**: Kivy's built-in screen navigation (`login` → `lobby` → `group`).
- **Facade**: `TouchHandler` wraps Android-specific tap logic; `App` only touches `TouchHandler`.
- **Models**: Always `@dataclass` with `@classmethod from_dict(cls, data: dict)`.
- **EventBus**: Callbacks copy subscriber list before iterating (deadlock prevention).

## Coding Conventions
- Every module starts with `from __future__ import annotations`.
- Avoid circular imports: screens access app via `App.get_running_app()`.
- New screens: subclass `Screen`, define layout in `bpsr.kv`, register in `BPSRApp.build()`.
- New network events: subscribe in `BPSRApp._subscribe_events()`.
- Config values always via `Config.instance()`.

## Run & Build
```bash
# Development (desktop — taps are printed to console)
python main.py

# Android APK (requires Linux/WSL + Android SDK)
pip install buildozer cython
buildozer android debug
```

## Environment Variables (dev)
| Variable | Default |
|---|---|
| `BPSR_SERVER_URL` | `ws://localhost:4061/bpsr/ws` |
| `X-API-KEY` | `""` |
| `BPSR_RECONNECT_DELAY` | `3.0` |
| `BPSR_MAX_RECONNECT_DELAY` | `30.0` |

## Key WebSocket Message Types
Outbound: `auth` (with `device_type: "mobile"`), `list_groups`, `join_group`, `leave_group`
Inbound: `auth_ok`, `groups_list`, `group_joined`, `group_updated`, `simulate_key`, `kicked`, `error`
