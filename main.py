"""Punto de entrada de BPSR AutoUltimate (versión móvil).

Requiere Kivy para la interfaz gráfica.
Para compilar para Android, usar Buildozer (ver buildozer.spec).
"""

from __future__ import annotations

from src.app import BPSRApp


def main():
    BPSRApp().run()


if __name__ == "__main__":
    main()
