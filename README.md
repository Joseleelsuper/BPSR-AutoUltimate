# BPSR-AutoUltimate

Aplicación de escritorio para sincronización remota de teclas en tiempo real. Las pulsaciones del líder de un grupo se transmiten por WebSocket y se simulan en los equipos de todos los miembros mediante `pynput`. El uso principal es el gaming (p. ej., pulsaciones de `R` sincronizadas).

## Contacto

Podéis encontrarme en Discord como Joseleelsuper, dentro de la [Guild HusaresAlados](https://discord.gg/rY9mt4Gn8d).

## Visibilidad

| Componente | Visibilidad | Motivo |
|---|---|---|
| Código del cliente (`src/`, `main.py`, `requirements.txt`) | **Público** | Abierto para inspección y contribución |
| Código del servidor | **Privado** | Alojado y mantenido por separado |
| `compile.py` | **Privado** | Contiene la lógica de cifrado de la API key usada para autenticarse con el servidor. Hacerlo público permitiría hacer ingeniería inversa del esquema de protección |

> El cliente se conecta al servidor usando una API key cifrada en tiempo de compilación. El script de compilación (`compile.py`) gestiona ese cifrado y, por tanto, se mantiene privado para evitar el análisis del mecanismo de protección.

## Arquitectura

```
main.py → App → [GUI, Network, Input, Models, Config]
                  EventBus (cola pub/sub thread-safe)
```

- `src/gui/` — Vistas con `customtkinter`
- `src/network/` — Cliente WebSocket + EventBus
- `src/input/` — Escucha y simulación de teclas (`pynput`)
- `src/models/` — Modelos de datos puros (`@dataclass`)
- `src/config.py` — Configuración singleton (dev `.env` / producción `_secrets.py`)

## Requisitos

```
pip install -r requirements.txt
```

## Ejecución (desarrollo)

```powershell
python main.py
```

En algunos sistemas puede requerir permisos de administrador para la simulación de teclas.

### Variables de entorno

| Variable | Por defecto |
|---|---|
| `BPSR_SERVER_URL` | `ws://localhost:4061/bpsr/ws` |
| `X-API-KEY` | `""` |
| `BPSR_RECONNECT_DELAY` | `3.0` |
| `BPSR_MAX_RECONNECT_DELAY` | `30.0` |
| `BPSR_THEME` | `dark-blue` |

## Licencia

Ver [LICENSE](LICENSE).
