# BPSR-AutoUltimate

Real-time remote key synchronization desktop app. A group leader's keypresses are broadcast over WebSocket and simulated on all member machines via `pynput`. The primary target is gaming (e.g., synchronized `R` presses).

## Visibility

| Component | Visibility | Reason |
|---|---|---|
| Client code (`src/`, `main.py`, `requirements.txt`) | **Public** | Open for inspection and contribution |
| Server code | **Private** | Hosted and maintained separately |
| `compile.py` | **Private** | Contains the encryption logic for the API key used to authenticate against the server. Making it public would allow reverse-engineering the key protection scheme |

> The client connects to the server using an API key that is encrypted at build time. The compilation script (`compile.py`) handles that encryption and is therefore kept private to prevent analysis of the protection mechanism.

## Architecture

```
main.py → App → [GUI, Network, Input, Models, Config]
                  EventBus (thread-safe pub/sub glue)
```

- `src/gui/` — `customtkinter` views
- `src/network/` — WebSocket client + EventBus
- `src/input/` — Key listener and simulator (`pynput`)
- `src/models/` — Pure dataclass models
- `src/config.py` — Singleton configuration (dev `.env` / production `_secrets.py`)

## Requirements

```
pip install -r requirements.txt
```

## Running (development)

```powershell
python main.py
```

Requires admin privileges on some systems for key simulation.

### Environment variables

| Variable | Default |
|---|---|
| `BPSR_SERVER_URL` | `ws://localhost:4061/bpsr/ws` |
| `X-API-KEY` | `""` |
| `BPSR_RECONNECT_DELAY` | `3.0` |
| `BPSR_MAX_RECONNECT_DELAY` | `30.0` |
| `BPSR_THEME` | `dark-blue` |

## License

See [LICENSE](LICENSE).
