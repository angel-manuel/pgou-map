"""Reconcilia desajustes entre cam-municipios.geojson (fronteras OSM) e
index.json (SIT-CAM), y genera stubs para municipios sin PGOU publicado.

Acciones:
1) Renombra el-boalo-cerceda-mataelpino → slug=el-boalo, name=El Boalo
   (la SIT publica con el nombre corto). has_sit=True.
2) Para cada municipio sin datos SIT, escribe public/data/cam/<slug>/vigente.geojson
   con un único feature (la propia frontera) marcado como STUB y añade entrada
   en cam/index.json con stub=True.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOUNDARIES = ROOT / "public" / "data" / "cam-municipios.geojson"
INDEX_FILE = ROOT / "public" / "data" / "cam" / "index.json"
CAM_DIR = ROOT / "public" / "data" / "cam"

# Municipios reales sin datos en SIT-CAM (la WFS no publica VPLA para ellos)
STUB_SLUGS = ["tres-cantos", "puentes-viejas", "lozoyuela-navas-sieteiglesias"]

# (slug viejo en frontera, slug nuevo, nombre nuevo) → para que casen con SIT
RENAMES: list[tuple[str, str, str]] = [
    ("el-boalo-cerceda-mataelpino", "el-boalo", "El Boalo"),
]


def bbox_of(geom: dict) -> tuple[float, float, float, float]:
    minx = miny = float("inf")
    maxx = maxy = float("-inf")
    coords = geom["coordinates"]
    if geom["type"] == "Polygon":
        rings = [coords]
    elif geom["type"] == "MultiPolygon":
        rings = coords
    else:
        raise ValueError(f"unexpected geom type {geom['type']}")
    for poly in rings:
        for ring in poly:
            for x, y in ring:
                if x < minx: minx = x
                if x > maxx: maxx = x
                if y < miny: miny = y
                if y > maxy: maxy = y
    return (minx, miny, maxx, maxy)


def centroid_of_bbox(b: tuple[float, float, float, float]) -> tuple[float, float]:
    return ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)


def main() -> None:
    boundaries = json.loads(BOUNDARIES.read_text(encoding="utf-8"))
    index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))

    # ---- 1) Renames ----
    by_slug = {f["properties"]["slug"]: f for f in boundaries["features"]}
    for old_slug, new_slug, new_name in RENAMES:
        feat = by_slug.get(old_slug)
        if not feat:
            print(f"  skip rename {old_slug} (not in boundaries)")
            continue
        feat["properties"]["slug"] = new_slug
        feat["properties"]["name"] = new_name
        feat["properties"]["has_sit"] = True
        del by_slug[old_slug]
        by_slug[new_slug] = feat
        print(f"  renamed {old_slug} → {new_slug} (has_sit=True)")

    # ---- 2) Stubs ----
    existing_slugs_in_index = {m["slug"] for m in index["municipios"]}
    for slug in STUB_SLUGS:
        feat = by_slug.get(slug)
        if not feat:
            print(f"  skip stub {slug} (no boundary feature)")
            continue
        if slug in existing_slugs_in_index:
            print(f"  skip stub {slug} (already in SIT index)")
            continue
        name = feat["properties"]["name"]
        geom = feat["geometry"]
        bbox = bbox_of(geom)
        center = centroid_of_bbox(bbox)

        # Mark boundary as having data, even if synthetic
        feat["properties"]["has_sit"] = True

        # Write vigente.geojson: one feature, no real PGOU info, sin-asignar.
        stub_feature = {
            "type": "Feature",
            "geometry": geom,
            "properties": {
                "municipio": name,
                "ambito": f"{slug.upper()}-STUB",
                "clasificacion": "sin-asignar",
                "calificacion": "sin-asignar",
                "version": "vigente",
                "fuente": "STUB — SIT-CAM no publica capa VPLA para este municipio",
                "fecha_dato": "2026-05-12",
                "slug": slug,
            },
        }
        out = CAM_DIR / slug / "vigente.geojson"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(
                {"type": "FeatureCollection", "features": [stub_feature]},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        index["municipios"].append(
            {
                "slug": slug,
                "name": name,
                "cam_code": "STUB",
                "file": f"/data/cam/{slug}/vigente.geojson",
                "center": [center[0], center[1]],
                "bbox": list(bbox),
                "feature_count": 1,
                "documento": "STUB — SIT-CAM no publica capa VPLA",
                "stub": True,
            }
        )
        print(f"  stub {slug}: wrote {out.relative_to(ROOT)}; added index entry")

    # ---- 3) Persist ----
    BOUNDARIES.write_text(
        json.dumps(boundaries, ensure_ascii=False), encoding="utf-8"
    )
    index["count"] = len(index["municipios"])
    # Keep deterministic order
    index["municipios"].sort(key=lambda m: m["name"])
    INDEX_FILE.write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\ntotal index entries now: {index['count']}")


if __name__ == "__main__":
    main()
