"""Descarga límites administrativos de los 179 municipios de la CAM desde OSM
vía Overpass API y los convierte a GeoJSON simplificado para el overview.

- `data-pipeline/.cache/cam-municipios-full.geojson`: detalle completo (~1.5 MB).
- `public/data/cam-municipios.geojson`: versión simplificada que se envía al
  navegador en el arranque (~160 KB). Requiere `ogr2ogr` (GDAL).

Los IDs de los pilotos (`madrid`, `alcala`, `torrejon`, `guadarrama`) se
asignan al matchear el `name:es` del relation con la lista PILOT_MATCH.
El resto de municipios llevan id `osm-<relation_id>` y name del relation.

Uso:
    python data-pipeline/fetch_cam_boundaries.py

Mirror Overpass por defecto: kumi.systems. La principal (overpass-api.de)
suele timeout-ear con este payload.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import urllib.request
import urllib.parse
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "public" / "data" / "cam-municipios.geojson"
CACHE = ROOT / "data-pipeline" / ".cache" / "cam-osm.json"
FULL_CACHE = ROOT / "data-pipeline" / ".cache" / "cam-municipios-full.geojson"
# Index produced by `fetch_sit_cam.py`; used here to match OSM relations with
# the SIT slug so the visor can resolve clicks → PGOU data without name guesses.
SIT_INDEX = ROOT / "public" / "data" / "cam" / "index.json"

# Douglas-Peucker tolerance in degrees for the overview file shipped to the
# browser. ~0.002° ≈ 200 m at this latitude — enough detail to recognise each
# municipio at zoom 8-10 while keeping the file small (~160 KB for 180 features).
SIMPLIFY_TOLERANCE = 0.002

OVERPASS_MIRRORS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
]
QUERY = """
[out:json][timeout:600];
rel(349055);
map_to_area->.cam;
relation["admin_level"="8"]["boundary"="administrative"](area.cam);
out geom;
"""

def _slugify(s: str) -> str:
    """Same algorithm as fetch_sit_cam.py:slugify — keep them in sync."""
    n = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    out = []
    for c in n.lower():
        out.append(c if c.isalnum() else "-")
    return "".join(out).strip("-") or "sin-nombre"


def _load_sit_slugs() -> dict[str, str]:
    """Return {slug → display_name} from SIT index.json if available."""
    if not SIT_INDEX.exists():
        return {}
    data = json.loads(SIT_INDEX.read_text(encoding="utf-8"))
    return {m["slug"]: m["name"] for m in data.get("municipios", [])}


def fetch_overpass() -> dict:
    if CACHE.exists():
        print(f"[overpass] using cache: {CACHE.relative_to(ROOT)}")
        return json.loads(CACHE.read_text(encoding="utf-8"))
    data = urllib.parse.urlencode({"data": QUERY}).encode("utf-8")
    last_err: Exception | None = None
    for url in OVERPASS_MIRRORS:
        print(f"[overpass] trying {url} ...")
        req = urllib.request.Request(
            url, data=data, headers={"User-Agent": "pgou-map/0.1 (research)"}
        )
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                raw = resp.read().decode("utf-8")
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(raw, encoding="utf-8")
            return json.loads(raw)
        except Exception as e:
            print(f"[overpass]   failed: {e}")
            last_err = e
            continue
    raise RuntimeError(f"all overpass mirrors failed; last error: {last_err}")




def stitch_rings(ways: list[list[tuple[float, float]]]) -> list[list[tuple[float, float]]]:
    """Stitch open way segments into closed rings by endpoint matching."""
    segs = [list(w) for w in ways if len(w) >= 2]
    rings: list[list[tuple[float, float]]] = []
    while segs:
        cur = segs.pop(0)
        progress = True
        while progress and cur[0] != cur[-1]:
            progress = False
            for i, s in enumerate(segs):
                if s[0] == cur[-1]:
                    cur.extend(s[1:])
                    segs.pop(i); progress = True; break
                if s[-1] == cur[-1]:
                    cur.extend(reversed(s[:-1])); segs.pop(i); progress = True; break
                if s[-1] == cur[0]:
                    cur = s[:-1] + cur; segs.pop(i); progress = True; break
                if s[0] == cur[0]:
                    cur = list(reversed(s))[:-1] + cur; segs.pop(i); progress = True; break
        if cur[0] == cur[-1] and len(cur) >= 4:
            rings.append(cur)
        # else: dropped — open ring (likely missing data from the bounding query)
    return rings


def ring_area(ring: list[tuple[float, float]]) -> float:
    """Signed area (shoelace). Positive = CCW. Used only for sizing/ordering."""
    a = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        a += x1 * y2 - x2 * y1
    return a / 2.0


def relation_to_geometry(rel: dict) -> dict | None:
    outers = [
        [(p["lon"], p["lat"]) for p in m["geometry"]]
        for m in rel.get("members", [])
        if m.get("type") == "way" and m.get("role") == "outer" and m.get("geometry")
    ]
    if not outers:
        return None
    rings = stitch_rings(outers)
    if not rings:
        return None
    # Order rings by absolute area (biggest first) so MapLibre renders correctly.
    rings.sort(key=lambda r: abs(ring_area(r)), reverse=True)
    polygons = [[list(map(list, r))] for r in rings]  # each ring its own polygon (no inners)
    if len(polygons) == 1:
        return {"type": "Polygon", "coordinates": polygons[0]}
    return {"type": "MultiPolygon", "coordinates": polygons}


def main() -> None:
    raw = fetch_overpass()
    elements = raw.get("elements", [])
    print(f"[overpass] received {len(elements)} relations")

    sit_slugs = _load_sit_slugs()
    sit_by_slug = set(sit_slugs.keys())

    features = []
    skipped = 0
    unmatched_osm: list[str] = []
    for rel in elements:
        tags = rel.get("tags", {})
        name = tags.get("name") or tags.get("name:es") or "?"
        geom = relation_to_geometry(rel)
        if geom is None:
            skipped += 1
            continue
        # Slug aligned with the SIT-CAM index; matches when OSM and SIT agree.
        slug = _slugify(name)
        has_sit = slug in sit_by_slug
        if not has_sit:
            unmatched_osm.append(name)
        features.append(
            {
                "type": "Feature",
                "geometry": geom,
                "properties": {
                    "slug": slug,
                    "name": name,
                    "has_sit": has_sit,
                    "osm_relation": rel.get("id"),
                    "ine_code": tags.get("ine:municipio"),
                },
            }
        )

    print(f"[overpass] features built: {len(features)} (skipped {skipped})")
    matched = sum(1 for f in features if f["properties"]["has_sit"])
    print(f"[overpass] matched to SIT index by slug: {matched}/{len(features)}")
    if unmatched_osm:
        print(f"[overpass] {len(unmatched_osm)} OSM names without SIT match (first 10):")
        for n in unmatched_osm[:10]:
            print(f"           - {n}")

    FULL_CACHE.parent.mkdir(parents=True, exist_ok=True)
    FULL_CACHE.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[overpass] wrote {FULL_CACHE.relative_to(ROOT)}  ({FULL_CACHE.stat().st_size // 1024} KB)")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("ogr2ogr"):
        subprocess.run(
            [
                "ogr2ogr",
                "-f", "GeoJSON",
                "-simplify", str(SIMPLIFY_TOLERANCE),
                "-lco", "RFC7946=YES",
                str(OUT),
                str(FULL_CACHE),
            ],
            check=True,
        )
        print(f"[simplify] wrote {OUT.relative_to(ROOT)}  ({OUT.stat().st_size // 1024} KB, tol {SIMPLIFY_TOLERANCE}°)")
    else:
        # Sin GDAL: enviamos el detalle completo. Avisa por stderr.
        OUT.write_text(FULL_CACHE.read_text(encoding="utf-8"), encoding="utf-8")
        print(
            f"[simplify] ogr2ogr no disponible, copia sin simplificar a {OUT.relative_to(ROOT)}",
            )


if __name__ == "__main__":
    main()
