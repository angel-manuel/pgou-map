"""Ingesta PGOU Alcalá de Henares.

Estado actual: PENDIENTE. Usar stubs (`build_stubs.py`).

Fuentes a integrar:
- Visor urbanístico municipal de Alcalá de Henares.
- SIGTRAUR (Sistema de Información Geográfica Territorial y Urbanística de la
  Región de Madrid) — `comunidad.madrid` → buscar capas WFS/WMS por municipio.

Mapear nomenclaturas con `normalize.py` y producir:
- apps/pgou-map/public/data/alcala/vigente.geojson
"""
from __future__ import annotations

import sys


def main() -> None:
    print("ingest/alcala.py: pendiente — ver build_stubs.py.", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
