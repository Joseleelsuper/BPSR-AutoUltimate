"""

Punto de entrada de BPSR AutoUltimate.

Nota: para simular teclas en aplicaciones que corren como administrador
(algunos juegos), ejecuta este script manualmente como administrador.
Para uso normal no se necesitan privilegios elevados.

"""

from __future__ import annotations

from src.app import App


def main():
    app = App()
    app.run()


if __name__ == "__main__":
    main()
