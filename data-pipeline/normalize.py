"""Helpers para mapear nomenclaturas nativas de cada PGOU al esquema normalizado.

Cada municipio define su propia tabla de mapeo en su script de ingest, llamando
a `normalize_clasificacion` y `normalize_calificacion` con sus claves nativas.
Cuando aparece una clave desconocida, se loguea y se cae a "sin-asignar" para
que el problema se vea en el visor.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Iterable

from schema import Calificacion, Clasificacion, ZonaProperties


def normalize_clasificacion(native: str, table: Dict[str, Clasificacion]) -> Clasificacion:
    key = native.strip().lower()
    if key in table:
        return table[key]
    print(f"[normalize] clasificacion desconocida: {native!r}", file=sys.stderr)
    return "no-urbanizable-comun"


def normalize_calificacion(native: str, table: Dict[str, Calificacion]) -> Calificacion:
    key = native.strip().lower()
    if key in table:
        return table[key]
    print(f"[normalize] calificacion desconocida: {native!r}", file=sys.stderr)
    return "sin-asignar"


def write_geojson(out_path: Path, features: Iterable[dict]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fc = {"type": "FeatureCollection", "features": list(features)}
    out_path.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    print(f"[normalize] wrote {out_path} ({len(fc['features'])} features)")


def make_feature(geometry: dict, props: ZonaProperties) -> dict:
    return {"type": "Feature", "geometry": geometry, "properties": props.to_dict()}
