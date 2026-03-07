# BPSR AutoUltimate — Versión Móvil (Android)

Aplicación de sincronización remota de pulsaciones en tiempo real para dispositivos Android.
El líder del grupo (desde escritorio) pulsa una tecla y todos los miembros móviles reciben un toque en pantalla en la posición configurada.

## Arquitectura

```
main.py → BPSRApp (Kivy)
  ├── EventBus      (pub/sub thread-safe)
  ├── WSClient      (WebSocket en hilo background con asyncio)
  ├── TouchHandler   (simula toques en Android)
  └── ScreenManager
        ├── LoginScreen
        ├── LobbyScreen
        └── GroupScreen
```

### Diferencias con la versión de escritorio

| Aspecto | Escritorio | Móvil |
|---|---|---|
| GUI | customtkinter | Kivy |
| Entrada | pynput (teclado) | TouchHandler (input tap) |
| Rol | Puede ser líder o miembro | **Solo miembro** |
| Acción al recibir `simulate_key` | Pulsa tecla | Toque en pantalla |
| Compilación | PyInstaller (.exe) | Buildozer (.apk) |

## Posición de toque

Cuando el líder pulsa **R**, el móvil ejecuta un toque en la posición calculada como proporción de la resolución:

| Tecla | Referencia (2400×1080) | Ratio X | Ratio Y |
|---|---|---|---|
| R | (1680, 940) | 0.700 | 0.870 |

En cualquier dispositivo la posición se escala automáticamente:
```
tap_x = ancho_pantalla × 0.700
tap_y = alto_pantalla  × 0.870
```

## Requisitos del dispositivo

- **Android 7.0+** (API 24)
- **Root** recomendado para simulación de toques fuera de la app
  - Con root: `su -c "input tap X Y"`
  - Sin root: funciona en algunos ROMs o con Shizuku

## Desarrollo

### Requisitos
```bash
pip install -r requirements.txt
```

### Variables de entorno (.env)
| Variable | Default |
|---|---|
| `BPSR_SERVER_URL` | `ws://localhost:4061/bpsr/ws` |
| `X-API-KEY` | `""` |
| `BPSR_RECONNECT_DELAY` | `3.0` |
| `BPSR_MAX_RECONNECT_DELAY` | `30.0` |

### Ejecutar en escritorio (testing)
```bash
python main.py
```
Los toques se imprimirán por consola en lugar de ejecutarse.

### Compilar APK para Android

#### Dependencias del sistema (Ubuntu/WSL)
```bash
sudo apt-get install -y \
    unzip \
    autoconf automake libtool pkg-config \
    libffi-dev \
    ccache \
    git zip
```

#### Herramientas Python
```bash
pip install buildozer cython
```

#### Android SDK — cmdline-tools
Buildozer necesita `sdkmanager` en la ruta legacy. Descarga las *command-line tools* y crea el enlace simbólico:
```bash
cd ~/.buildozer/android/platform/android-sdk
wget "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip" -O cmdline-tools.zip
unzip cmdline-tools.zip && rm cmdline-tools.zip
mkdir -p cmdline-tools/latest
mv cmdline-tools/bin cmdline-tools/latest/bin
mv cmdline-tools/lib cmdline-tools/latest/lib
mkdir -p tools/bin
ln -sf ~/.buildozer/android/platform/android-sdk/cmdline-tools/latest/bin/sdkmanager tools/bin/sdkmanager
yes | ~/.buildozer/android/platform/android-sdk/cmdline-tools/latest/bin/sdkmanager --licenses
```

> **Rendimiento en WSL**: construir desde `/mnt/c/` es muy lento por el overhead del sistema de archivos.
> Se recomienda copiar el proyecto al filesystem nativo de WSL (`~/BPSR-AutoUltimate`) y compilar desde allí.

#### Compilar
```bash
# Generar APK de debug
buildozer android debug

# El APK se genera en bin/
```

## Protocolo WebSocket

### Autenticación
El cliente móvil envía `device_type: "mobile"` durante la autenticación HMAC:
```json
{ "type": "auth", "hmac": "<HMAC-SHA256>", "username": "Jugador1", "device_type": "mobile" }
```

### Restricciones para dispositivos móviles
- No pueden **crear** grupos (requiere ser líder)
- No pueden **ser promovidos** a líder
- Si el líder se desconecta y no quedan usuarios de escritorio, el grupo se destruye
- Reciben `simulate_key` que se convierte en un toque en pantalla

### Mensajes soportados
| Dirección | Tipo | Descripción |
|---|---|---|
| → Servidor | `list_groups` | Listar grupos disponibles |
| → Servidor | `join_group` | Unirse a un grupo |
| → Servidor | `leave_group` | Salir del grupo |
| ← Servidor | `auth_ok` | Autenticación exitosa |
| ← Servidor | `groups_list` | Lista de grupos |
| ← Servidor | `group_joined` | Confirmación de unión |
| ← Servidor | `group_update` | Actualización del grupo |
| ← Servidor | `simulate_key` | Orden de simular toque |
| ← Servidor | `kicked` | Expulsado del grupo |
| ← Servidor | `error` | Error del servidor |

## Estructura de archivos

```
main.py                 # Punto de entrada
buildozer.spec          # Config de compilación Android
requirements.txt        # Dependencias Python
src/
  app.py                # BPSRApp (Kivy App)
  config.py             # Config singleton
  gui/
    bpsr.kv             # Layouts Kivy
    screens.py          # LoginScreen, LobbyScreen, GroupScreen
  input/
    touch_handler.py    # Simulación de toques Android
  models/
    group.py            # Dataclasses User, Group
  network/
    event_bus.py        # EventBus singleton thread-safe
    ws_client.py        # WebSocket client con device_type: "mobile"
```

## Licencia

MIT — ver [LICENSE](LICENSE).
