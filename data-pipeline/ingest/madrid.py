"""Ingesta PGOU Madrid capital (PG-97).

Fuente: Geoportal Madrid, dataset "PGOUM 97. Plano de ordenación".
URL ZIP: https://geoportal.madrid.es/fsdescargas/IDEAM_WBGEOPORTAL/PLANEAMIENTO/PG97/ORDENACION/PGOUM97_ORDENACION.zip

Capa usada: `AMBITOS` (1487 polígonos). Cada feature trae:
- TIPOAMBITO: NZ, API, APE, APR, UZP, UZI, UNP, NUC, NUP, AOE, SG.
- USO_CARACT: RE, TE, IN, DO, 99 (nulo para casi todos los NZ).
- NOMBRE / AMBITO / SUP_AMBITO.

LEEME.TXT (incluido en el ZIP) documenta esto.

El script:
1. Si no hay cache local, descarga el ZIP (~125 MB).
2. Extrae AMBITOS.shp.
3. Convierte con ogr2ogr a GeoJSON en EPSG:4326.
4. Mapea TIPOAMBITO → clasificacion y USO_CARACT → calificacion según
   las tablas TIPOAMBITO_CLAS y USO_CALIF de abajo (revisable, son la
   interpretación que se documenta).
5. Escribe public/data/madrid/vigente.geojson con el esquema normalizado.

Requiere: `ogr2ogr` (paquete `gdal-bin` en Debian/Ubuntu).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schema import Calificacion, Clasificacion, ZonaProperties  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data-pipeline" / ".cache"
ZIP_PATH = CACHE / "madrid-pgoum97.zip"
EXTRACT_DIR = CACHE / "pgoum97"
AMBITOS_SHP = EXTRACT_DIR / "AMBITOS.shp"
AMBITOS_GEOJSON = CACHE / "madrid-ambitos-4326.geojson"
OUT = ROOT / "public" / "data" / "madrid" / "vigente.geojson"

ZIP_URL = (
    "https://geoportal.madrid.es/fsdescargas/IDEAM_WBGEOPORTAL/"
    "PLANEAMIENTO/PG97/ORDENACION/PGOUM97_ORDENACION.zip"
)

# Mapeo TIPOAMBITO → clasificación del suelo (Ley 9/2001 Madrid).
# Decisiones interpretativas, revisar si se rediscute:
#  - NZ, API y APE en la trama urbana consolidada → urbano-consolidado.
#  - APR (Áreas de Planeamiento Remitido): pendientes de instrumento de
#    desarrollo → urbano-no-consolidado.
#  - UZP (Urbanizable Programado), UZI (Urbanizable Inmediato): sectorizados.
#  - UNP (Urbanizable No Programado): no sectorizados.
#  - NUC (No Urbanizable Común): no urbanizable común.
#  - NUP (No Urbanizable Protegido): no urbanizable protegido.
#  - AOE (Actuación de Ordenación Especial), SG (Sistema General): mixto /
#    casos especiales — se mantienen como urbano-no-consolidado por defecto.
TIPOAMBITO_CLAS: dict[str, Clasificacion] = {
    "NZ":  "urbano-consolidado",
    "API": "urbano-consolidado",
    "APE": "urbano-consolidado",
    "APR": "urbano-no-consolidado",
    "UZP": "urbanizable-sectorizado",
    "UZI": "urbanizable-sectorizado",
    "UNP": "urbanizable-no-sectorizado",
    "NUC": "no-urbanizable-comun",
    "NUP": "no-urbanizable-protegido",
    "AOE": "urbano-no-consolidado",
    "SG":  "urbano-consolidado",
}

USO_CALIF: dict[str | None, Calificacion] = {
    "RE": "residencial",
    "TE": "terciario",
    "IN": "industrial",
    "DO": "dotacional-publico",
    "99": "sin-asignar",
    None: "sin-asignar",
    "":  "sin-asignar",
}

FUENTE = "Geoportal Madrid — PGOUM97_ORDENACION.zip (AMBITOS), normalizado por data-pipeline/ingest/madrid.py"
FECHA_DATO = "2026-05-12"
# Tolerance Douglas-Peucker para la versión que va al navegador.
# 0.00008° ≈ 7 m. Suficiente para zoom 11-15; bajamos peso de 3.2 MB → 1.4 MB.
SIMPLIFY_TOLERANCE_DEG = 0.00008


def download_if_missing() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    if ZIP_PATH.exists() and ZIP_PATH.stat().st_size > 100_000_000:
        return
    print(f"[madrid] downloading {ZIP_URL}")
    req = urllib.request.Request(ZIP_URL, headers={"User-Agent": "pgou-map/0.1 (research)"})
    with urllib.request.urlopen(req, timeout=300) as resp, open(ZIP_PATH, "wb") as f:
        shutil.copyfileobj(resp, f)
    print(f"[madrid] saved {ZIP_PATH.stat().st_size // 1024 // 1024} MB")


def extract_if_missing() -> None:
    if AMBITOS_SHP.exists():
        return
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[madrid] extracting AMBITOS.*")
    with zipfile.ZipFile(ZIP_PATH) as z:
        for name in z.namelist():
            if name.startswith("AMBITOS."):
                z.extract(name, EXTRACT_DIR)


def reproject() -> None:
    if AMBITOS_GEOJSON.exists():
        return
    if not shutil.which("ogr2ogr"):
        raise SystemExit(
            "ogr2ogr no disponible. Instalar GDAL: `sudo apt install gdal-bin` "
            "(Debian/Ubuntu) o equivalente."
        )
    print(f"[madrid] reprojecting AMBITOS to EPSG:4326")
    subprocess.run(
        [
            "ogr2ogr",
            "-f", "GeoJSON",
            "-t_srs", "EPSG:4326",
            "-lco", "RFC7946=YES",
            str(AMBITOS_GEOJSON),
            str(AMBITOS_SHP),
        ],
        check=True,
    )


def simplify(src: Path, dst: Path) -> None:
    if not shutil.which("ogr2ogr"):
        if dst != src:
            dst.write_bytes(src.read_bytes())
        return
    subprocess.run(
        [
            "ogr2ogr",
            "-f", "GeoJSON",
            "-simplify", str(SIMPLIFY_TOLERANCE_DEG),
            "-lco", "RFC7946=YES",
            str(dst),
            str(src),
        ],
        check=True,
    )


def normalize() -> None:
    raw = json.loads(AMBITOS_GEOJSON.read_text(encoding="utf-8"))
    out_features: list[dict] = []
    unknown_tipo: set[str] = set()
    unknown_uso: set[str] = set()

    for f in raw["features"]:
        p = f.get("properties", {}) or {}
        tipo = (p.get("TIPOAMBITO") or "").strip()
        uso = p.get("USO_CARACT")
        if tipo not in TIPOAMBITO_CLAS:
            unknown_tipo.add(tipo)
        clas = TIPOAMBITO_CLAS.get(tipo, "urbano-no-consolidado")
        uso_norm = uso.strip() if isinstance(uso, str) else uso
        if uso_norm not in USO_CALIF:
            unknown_uso.add(str(uso))
        cali = USO_CALIF.get(uso_norm, "sin-asignar")

        props = ZonaProperties(
            municipio="Madrid",
            clasificacion=clas,
            calificacion=cali,
            version="vigente",
            fuente=FUENTE,
            fecha_dato=FECHA_DATO,
            ambito=p.get("AMBITO") or p.get("NOMBRE"),
        )
        # Adjuntar metadatos crudos como contexto (no parte del esquema normalizado).
        d = props.to_dict()
        d["_raw_TIPOAMBITO"] = tipo or None
        d["_raw_USO_CARACT"] = uso
        d["_raw_NOMBRE"] = p.get("NOMBRE")

        out_features.append({"type": "Feature", "geometry": f["geometry"], "properties": d})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    full_path = OUT.with_suffix(".full.geojson")
    full_path.write_text(
        json.dumps({"type": "FeatureCollection", "features": out_features}, ensure_ascii=False),
        encoding="utf-8",
    )
    simplify(full_path, OUT)
    full_path.unlink(missing_ok=True)
    print(f"[madrid] wrote {OUT}  ({len(out_features)} features, {OUT.stat().st_size // 1024} KB)")
    if unknown_tipo:
        print(f"[madrid] WARN TIPOAMBITO desconocidos: {sorted(unknown_tipo)}", file=sys.stderr)
    if unknown_uso:
        print(f"[madrid] WARN USO_CARACT desconocidos: {sorted(unknown_uso)}", file=sys.stderr)


def main() -> None:
    download_if_missing()
    extract_if_missing()
    reproject()
    normalize()


if __name__ == "__main__":
    main()
