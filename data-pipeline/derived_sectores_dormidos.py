"""Capa derivada: sectores urbanizables sectorizados pendientes de desarrollo.

Definición operativa (ver docs/01-investigacion/06-recalificacion-municipal.md §10.2, §12):
- Filtro base: `clasificacion == "urbanizable-sectorizado"`.
- Idealmente, cruzar con estado de gestión: sin Plan Parcial aprobado o sin
  Proyecto de Urbanización ejecutado. En el MVP nos quedamos con el filtro
  base y marcamos cada feature con `verificacion_gestion = "pendiente"`.

Uso:
    python data-pipeline/derived_sectores_dormidos.py <vigente.geojson> <out.geojson>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 3:
        print("uso: derived_sectores_dormidos.py <input> <output>", file=sys.stderr)
        sys.exit(1)
    inp, outp = Path(sys.argv[1]), Path(sys.argv[2])
    fc = json.loads(inp.read_text(encoding="utf-8"))
    features = [
        {
            **f,
            "properties": {
                **f["properties"],
                "derivado": "sectores-dormidos",
                "verificacion_gestion": "pendiente",
            },
        }
        for f in fc["features"]
        if f["properties"].get("clasificacion") == "urbanizable-sectorizado"
    ]
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"derived dormidos: {len(features)} features -> {outp}")


if __name__ == "__main__":
    main()
