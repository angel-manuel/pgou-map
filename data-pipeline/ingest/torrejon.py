"""Ingesta PGOU Torrejón de Ardoz.

Estado actual: PENDIENTE. Usar stubs (`build_stubs.py`).

Fuentes a integrar:
- SIGTRAUR (CAM) → capas urbanísticas Torrejón.
- Datos abiertos del Ayuntamiento de Torrejón si exponen GIS.

Salida: apps/pgou-map/public/data/torrejon/vigente.geojson
"""
from __future__ import annotations

import sys


def main() -> None:
    print("ingest/torrejon.py: pendiente — ver build_stubs.py.", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
