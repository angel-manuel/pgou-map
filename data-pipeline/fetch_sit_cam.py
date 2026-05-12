"""Ingesta de la clasificación del suelo de TODOS los municipios de la CAM
desde el WFS del SIT (Sistema de Información Territorial — IDEM Madrid).

Endpoint: https://idem.comunidad.madrid/geosrvg/ows
Layer:    UsoDelSuelo:VPLA_V_CLASIFICACION
Cobertura: los 179 municipios de la Comunidad de Madrid.

Salida:
- public/data/cam/<slug>/vigente.geojson  (uno por municipio)
- public/data/cam/index.json              (lista con metadatos para la UI)

Mapeo CD_SIGLAS → esquema normalizado (`schema.py`):

| CD_SIGLAS         | clasificación              | calificación        |
|-------------------|----------------------------|---------------------|
| SU                | urbano-consolidado         | sin-asignar         |
| SUC               | urbano-consolidado         | sin-asignar         |
| SUNC              | urbano-no-consolidado      | sin-asignar         |
| SUBS / SUBS_A     | urbanizable-sectorizado    | sin-asignar         |
| SUBNS / SUBNS_A   | urbanizable-no-sectorizado | sin-asignar         |
| SNUC / SNU        | no-urbanizable-comun       | sin-asignar         |
| SNUP / SNUP_A     | no-urbanizable-protegido   | sin-asignar         |
| SG                | urbano-consolidado         | equipamiento        |
| SD (Sin Datos)    | no-urbanizable-comun       | sin-asignar         |

Notas:
- Los siglas con sufijo "_INCORP" / "_A" se tratan igual que la base
  (incorporado / aplazado son matices de gestión, no de clasificación).
- "SG" (Sistemas Generales) no es una clasificación stricto sensu — son
  infraestructuras que cruzan distintas clases. Lo asignamos a
  urbano-consolidado + calificación equipamiento como la mejor aproximación.

Uso:
    python data-pipeline/fetch_sit_cam.py            # todos
    python data-pipeline/fetch_sit_cam.py 005 068    # selección por CD_MUNICIPIO

Requiere `ogr2ogr` para simplificar los polígonos.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from schema import Calificacion, Clasificacion, ZonaProperties  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data-pipeline" / ".cache"
OUT_DIR = ROOT / "public" / "data" / "cam"
RAW_CACHE = CACHE / "sit-vpla-classification.geojson"

WFS_URL = "https://idem.comunidad.madrid/geosrvg/ows"
TYPE_NAME = "UsoDelSuelo:VPLA_V_CLASIFICACION"
PAGE_SIZE = 5000  # WFS 1.0 default may cap; we paginate

SIMPLIFY_DEG = 0.00008  # ~7 m

SIGLAS_TO_CLAS: dict[str, Clasificacion] = {
    "SU":     "urbano-consolidado",
    "SUC":    "urbano-consolidado",
    "SUNC":   "urbano-no-consolidado",
    "SUBS":   "urbanizable-sectorizado",
    "SUBNS":  "urbanizable-no-sectorizado",
    "SNU":    "no-urbanizable-comun",
    "SNUC":   "no-urbanizable-comun",
    "SNUP":   "no-urbanizable-protegido",
    "SG":     "urbano-consolidado",
    "SD":     "no-urbanizable-comun",
}
SIGLAS_TO_CALI: dict[str, Calificacion] = {
    "SG": "equipamiento",
}
FUENTE = (
    "SIT-CAM WFS — UsoDelSuelo:VPLA_V_CLASIFICACION "
    "(https://idem.comunidad.madrid/geosrvg/ows)"
)


def slugify(s: str) -> str:
    if not s:
        return "sin-nombre"
    n = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-") or "sin-nombre"


# Artículos y preposiciones que deben quedar en minúscula salvo si abren el nombre.
SPANISH_LOWER = {"de", "del", "la", "las", "el", "los", "y", "en"}
# Topónimos donde "El" forma parte del nombre propio aunque no esté al inicio.
PROPER_EL = {"El Escorial"}


def title_es(s: str) -> str:
    """Title-case respetando minúsculas de artículos y preposiciones castellanos."""
    if not s:
        return s
    parts = s.lower().split()
    out: list[str] = []
    for i, p in enumerate(parts):
        if i > 0 and p in SPANISH_LOWER:
            out.append(p)
        else:
            out.append("-".join(seg.capitalize() for seg in p.split("-")))
    result = " ".join(out)
    for proper in PROPER_EL:
        result = result.replace(f"de el {proper.split()[1].lower()}", f"de {proper}")
        result = result.replace(f"de el {proper.split()[1].capitalize()}", f"de {proper}")
    return result


def normalize_siglas(raw: str | None) -> tuple[Clasificacion, Calificacion]:
    if not raw:
        return ("no-urbanizable-comun", "sin-asignar")
    s = raw.strip().upper()
    # Trim suffixes like "_A" (aplazado), "_INCORP", "_INCORPORADO"
    base = re.sub(r"_(?:A|INCORP(?:ORADO)?)$", "", s)
    clas = SIGLAS_TO_CLAS.get(base, "no-urbanizable-comun")
    cali = SIGLAS_TO_CALI.get(base, "sin-asignar")
    return (clas, cali)


def fetch_one(code: str) -> list[dict]:
    """One WFS call per municipio (server doesn't support startIndex)."""
    params = {
        "service": "WFS",
        "version": "1.0.0",
        "request": "GetFeature",
        "typeName": TYPE_NAME,
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "cql_filter": f"CD_MUNICIPIO='{code}'",
        "maxFeatures": "20000",  # any single municipio fits well below this
    }
    url = f"{WFS_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "pgou-map/0.1 (research)"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        body = resp.read().decode("utf-8")
    if not body.lstrip().startswith("{"):
        raise RuntimeError(f"non-JSON response for {code}: {body[:200]}")
    return json.loads(body).get("features", [])


def fetch_bulk(filter_codes: list[str] | None) -> dict:
    """Per-municipio loop. Caches the merged result for fast re-runs."""
    if RAW_CACHE.exists() and filter_codes is None:
        print(f"[wfs] cache hit: {RAW_CACHE.relative_to(ROOT)}")
        return json.loads(RAW_CACHE.read_text(encoding="utf-8"))

    codes = filter_codes if filter_codes else [f"{i:03d}" for i in range(1, 201)]
    all_feats: list[dict] = []
    hits = 0
    for code in codes:
        try:
            feats = fetch_one(code)
        except Exception as e:
            print(f"[wfs] {code}: ERR {e}", file=sys.stderr)
            continue
        if feats:
            hits += 1
            ds_name = (feats[0].get("properties") or {}).get("DS_MUNICIPIO", "?")
            print(f"[wfs] {code} {ds_name[:30]:30s}  features={len(feats)}")
        all_feats.extend(feats)

    print(f"[wfs] municipios hit: {hits} / {len(codes)} probed; total features={len(all_feats)}")
    fc = {"type": "FeatureCollection", "features": all_feats}
    if filter_codes is None:
        CACHE.mkdir(parents=True, exist_ok=True)
        RAW_CACHE.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
        print(f"[wfs] cached → {RAW_CACHE.relative_to(ROOT)}")
    return fc


def round_coords(geom: dict, decimals: int = 6) -> dict:
    """In-place round coordinates to reduce file size. ~10 cm at 6 decimals."""
    def _r(node):
        if isinstance(node, list):
            if node and isinstance(node[0], (int, float)):
                return [round(v, decimals) for v in node]
            return [_r(x) for x in node]
        return node
    geom = dict(geom)
    geom["coordinates"] = _r(geom["coordinates"])
    return geom


def write_municipio(slug: str, code: str, name: str, features: list[dict]) -> Path:
    out_dir = OUT_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "vigente.geojson"

    out_features = []
    for f in features:
        p = f.get("properties", {}) or {}
        siglas = p.get("CD_SIGLAS")
        clas, cali = normalize_siglas(siglas)

        props = ZonaProperties(
            municipio=name,
            clasificacion=clas,
            calificacion=cali,
            version="vigente",
            fuente=FUENTE,
            fecha_dato="2026-05-12",
            ambito=p.get("CD_REUR") or p.get("CD_SIGLAS"),
        )
        d = props.to_dict()
        d["_raw_CD_SIGLAS"] = siglas
        d["_raw_DS_CLASIF_GEN"] = p.get("DS_CLASIF_GEN")
        d["_raw_DS_CLASIF_DET"] = p.get("DS_CLASIF_DET")
        d["_raw_DS_DOCU"] = p.get("DS_DOCU")
        d["_raw_DS_LEY"] = p.get("DS_LEY")
        d["_raw_FC_AC"] = p.get("FC_AC")
        d["_raw_NM_AREA_M2"] = p.get("NM_AREA")
        d["_cam_code"] = code

        geom = f.get("geometry")
        if not geom:
            continue
        out_features.append({"type": "Feature", "geometry": round_coords(geom), "properties": d})

    full = out_dir / "vigente.full.geojson"
    full.write_text(
        json.dumps({"type": "FeatureCollection", "features": out_features}, ensure_ascii=False),
        encoding="utf-8",
    )

    if shutil.which("ogr2ogr"):
        subprocess.run(
            [
                "ogr2ogr",
                "-f", "GeoJSON",
                "-simplify", str(SIMPLIFY_DEG),
                "-lco", "RFC7946=YES",
                str(out_path),
                str(full),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        full.unlink(missing_ok=True)
    else:
        full.replace(out_path)
    return out_path


def bbox(features: list[dict]) -> tuple[float, float, float, float]:
    minx = miny = float("inf")
    maxx = maxy = float("-inf")
    def visit(node):
        nonlocal minx, miny, maxx, maxy
        if isinstance(node, list) and node and isinstance(node[0], (int, float)):
            x, y = node[0], node[1]
            if x < minx: minx = x
            if y < miny: miny = y
            if x > maxx: maxx = x
            if y > maxy: maxy = y
        elif isinstance(node, list):
            for x in node:
                visit(x)
    for f in features:
        if f.get("geometry"):
            visit(f["geometry"].get("coordinates"))
    return (minx, miny, maxx, maxy)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    arg_codes = [a.zfill(3) for a in sys.argv[1:] if a.isdigit()] or None

    raw = fetch_bulk(arg_codes)
    features = raw["features"]
    print(f"[wfs] total features: {len(features)}")

    # Group by municipio
    by_muni: dict[str, list[dict]] = defaultdict(list)
    names: dict[str, str] = {}
    for f in features:
        p = f.get("properties") or {}
        code = (p.get("CD_MUNICIPIO") or "").zfill(3)
        if not code:
            continue
        by_muni[code].append(f)
        if code not in names and p.get("DS_MUNICIPIO"):
            names[code] = title_es(p["DS_MUNICIPIO"])

    print(f"[wfs] distinct municipios: {len(by_muni)}")

    index_entries = []
    for code in sorted(by_muni):
        feats = by_muni[code]
        name = names.get(code, f"(CD={code})")
        slug = slugify(name)
        # Avoid slug collisions defensively
        if any(e["slug"] == slug for e in index_entries):
            slug = f"{slug}-{code}"

        out_path = write_municipio(slug, code, name, feats)
        bx = bbox(feats)
        cx = (bx[0] + bx[2]) / 2
        cy = (bx[1] + bx[3]) / 2
        sig_counts = Counter(
            (f["properties"] or {}).get("CD_SIGLAS") for f in feats
        )
        clas_counts = Counter(
            normalize_siglas((f["properties"] or {}).get("CD_SIGLAS"))[0]
            for f in feats
        )

        index_entries.append({
            "slug": slug,
            "name": name,
            "cam_code": code,
            "file": f"/data/cam/{slug}/vigente.geojson",
            "center": [round(cx, 4), round(cy, 4)],
            "bbox": [round(v, 4) for v in bx],
            "feature_count": len(feats),
            "bytes": out_path.stat().st_size,
            "documento": (feats[0]["properties"] or {}).get("DS_DOCU"),
            "ley": (feats[0]["properties"] or {}).get("DS_LEY"),
            "siglas_counts": dict(sig_counts.most_common()),
            "clasificacion_counts": dict(clas_counts.most_common()),
        })

    index_path = OUT_DIR / "index.json"
    index_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-12",
                "source": FUENTE,
                "count": len(index_entries),
                "municipios": index_entries,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    total_bytes = sum(e["bytes"] for e in index_entries)
    print(
        f"[wfs] wrote {len(index_entries)} municipios "
        f"({total_bytes // 1024} KB total)  → {index_path.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
