"""Ingesta PGOU Guadarrama.

Estado actual: PENDIENTE. Usar stubs (`build_stubs.py`).

Notas operativas (de `docs/01-investigacion/06-recalificacion-municipal.md`):
- Municipio pequeño, PGOU posiblemente antiguo y/o solo en formato PDF.
- Si la cartografía digital no está disponible, dejar el municipio como
  "datos pendientes" en lugar de digitalizar a mano de baja calidad.

Fuentes a integrar:
- SIGTRAUR (CAM).
- Ayuntamiento de Guadarrama → sede electrónica / transparencia.

Salida: apps/pgou-map/public/data/guadarrama/vigente.geojson
"""
from __future__ import annotations

import sys


def main() -> None:
    print("ingest/guadarrama.py: pendiente — ver build_stubs.py.", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
