# BPSR-AutoUltimate — Copilot Instructions

## Purpose
Real-time remote key synchronization desktop app. A group leader's keypresses are broadcast over WebSocket and simulated on all member machines via `pynput`. The primary target is gaming (e.g., synchronized `R` presses).

## Architecture
`App` (`src/app.py`) is the central wiring hub. All subsystems are connected exclusively through `EventBus` — no layer imports directly from another (except `App` and views calling `self.app.*`).

```
main.py → App → [GUI, Network, Input, Models, Config]
                  EventBus (thread-safe pub/sub glue)
```

Key directories:
- `src/gui/` — `customtkinter` views extending `BaseView`
- `src/network/` — `WSClient` (websockets, async) + `EventBus` (singleton)
- `src/input/` — `KeyHandler` facade wrapping `KeyListener` + `KeySimulator` (pynput)
- `src/models/` — Pure `@dataclass` models with `from_dict()` factories
- `src/config.py` — Singleton with dev (`.env`) and production (`_secrets.py`) modes
- `compile.py` — Full build script: generates secrets, runs PyInstaller

## Threading Model
`WSClient` runs an `asyncio` event loop in a **daemon thread**. To send from the GUI thread into that loop use `asyncio.run_coroutine_threadsafe()`. EventBus callbacks that touch GUI widgets **must** schedule via `window.after(0, lambda: ...)` — never update widgets from a background thread directly.

## Design Patterns to Follow
- **Singleton**: `EventBus` and `Config` use a `_instance` class variable and `classmethod instance()` factory.
- **Template Method**: All views extend `BaseView(ctk.CTkFrame)` and implement `_build_ui()`. Use optional `on_show()` / `on_hide()` lifecycle hooks.
- **Facade**: `KeyHandler` wraps `KeyListener` and `KeySimulator`; `App` only touches `KeyHandler`.
- **Models**: Always `@dataclass` with a `@classmethod from_dict(cls, data: dict)` factory. Nested objects (e.g., `User` inside `Group`) are deserialized inside `from_dict`.
- **EventBus**: Callbacks copy the subscriber list before iterating (deadlock prevention). New event names must be documented at the call site.

## Coding Conventions
- Every module starts with `from __future__ import annotations`.
- Avoid circular imports: use `TYPE_CHECKING` guard for type-only imports (see `base_view.py`).
- New views: subclass `BaseView`, implement `_build_ui()`, register in `App._setup_gui()`.
- New network events: add handler in `App.__init__` with `self._bus.subscribe(...)` and a matching `_on_*` private method.
- Config values are always accessed via `Config.instance()`.

## Run & Build
```powershell
# Development (requires admin for key simulation in some apps)
python main.py

# Production — set BPSR_SERVER_URL and X-API-KEY in .env first
python compile.py          # output: dist/BPSR-AutoUltimate.exe
```

`compile.py` encrypts the API key + server URL into `src/_secrets.py` (auto-deleted post-build) using PBKDF2-HMAC-SHA256 + Fernet. Never commit `_secrets.py` or `.env`.

## Environment Variables (dev)
| Variable | Default |
|---|---|
| `BPSR_SERVER_URL` | `ws://localhost:4061/bpsr/ws` |
| `X-API-KEY` | `""` |
| `BPSR_RECONNECT_DELAY` | `3.0` |
| `BPSR_MAX_RECONNECT_DELAY` | `30.0` |
| `BPSR_THEME` | `dark-blue` |

## Key WebSocket Message Types
Outbound: `auth`, `list_groups`, `create_group`, `join_group`, `leave_group`, `toggle_key_lock`, `key_press`  
Inbound: `auth_ok`, `groups_list`, `group_joined`, `group_updated`, `simulate_key`, `error`
