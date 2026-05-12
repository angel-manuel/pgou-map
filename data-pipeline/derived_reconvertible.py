"""Capa derivada: suelo urbano consolidado con uso terciario o dotacional
privado — palanca de reconversión a residencial post-Ley 4/2024.

Definición operativa (ver docs/01-investigacion/06-recalificacion-municipal.md §2.3, §8):
- Filtro: `clasificacion == "urbano-consolidado"` AND
          `calificacion ∈ {"terciario", "dotacional-privado"}`.

Uso:
    python data-pipeline/derived_reconvertible.py <vigente.geojson> <out.geojson>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RECONVERTIBLE_USOS = {"terciario", "dotacional-privado"}


def main() -> None:
    if len(sys.argv) != 3:
        print("uso: derived_reconvertible.py <input> <output>", file=sys.stderr)
        sys.exit(1)
    inp, outp = Path(sys.argv[1]), Path(sys.argv[2])
    fc = json.loads(inp.read_text(encoding="utf-8"))
    features = [
        {**f, "properties": {**f["properties"], "derivado": "reconvertible"}}
        for f in fc["features"]
        if f["properties"].get("clasificacion") == "urbano-consolidado"
        and f["properties"].get("calificacion") in RECONVERTIBLE_USOS
    ]
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"derived reconvertible: {len(features)} features -> {outp}")


if __name__ == "__main__":
    main()
