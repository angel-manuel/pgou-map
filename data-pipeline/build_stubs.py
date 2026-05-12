"""Genera datos stub deterministas para que el visor renderice end-to-end sin
descargar nada. Reemplazar cada salida por la ingesta real conforme se vayan
construyendo los scripts `ingest/<municipio>.py`.

Genera:
- public/data/cam-municipios.geojson  (CAM outline + 4 pilot polygons)
- public/data/<pilot>/vigente.geojson (rejilla 5x5 de zonas)
- public/data/madrid/revision.geojson (rejilla 5x5 con algunos cambios)
- public/data/<pilot>/sectores-dormidos.geojson  (filtro derivado)
- public/data/<pilot>/reconvertible.geojson      (filtro derivado)

Marca todas las features con fuente="STUB" para que sea obvio en la UI.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from schema import Calificacion, Clasificacion, ZonaProperties

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public" / "data"

# Centros aproximados de los 4 pilotos. lon, lat.
PILOTS: dict[str, tuple[str, float, float, float]] = {
    # id: (nombre, lon, lat, half_size_deg)
    "madrid": ("Madrid", -3.7038, 40.4168, 0.18),
    "alcala": ("Alcalá de Henares", -3.366, 40.482, 0.07),
    "torrejon": ("Torrejón de Ardoz", -3.4796, 40.4555, 0.05),
    "guadarrama": ("Guadarrama", -4.09, 40.673, 0.05),
}

CLASES: list[Clasificacion] = [
    "urbano-consolidado",
    "urbano-no-consolidado",
    "urbanizable-sectorizado",
    "urbanizable-no-sectorizado",
    "no-urbanizable-comun",
    "no-urbanizable-protegido",
]

USOS: list[Calificacion] = [
    "residencial",
    "terciario",
    "industrial",
    "dotacional-publico",
    "dotacional-privado",
    "espacio-libre",
    "equipamiento",
    "mixto",
]


def rect(lon: float, lat: float, half: float) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [lon - half, lat - half],
                [lon + half, lat - half],
                [lon + half, lat + half],
                [lon - half, lat + half],
                [lon - half, lat - half],
            ]
        ],
    }


def grid_cells(lon: float, lat: float, half: float, n: int) -> list[tuple[int, int, dict]]:
    step = (2 * half) / n
    out: list[tuple[int, int, dict]] = []
    for i in range(n):
        for j in range(n):
            x0 = lon - half + i * step
            y0 = lat - half + j * step
            poly = {
                "type": "Polygon",
                "coordinates": [
                    [
                        [x0, y0],
                        [x0 + step, y0],
                        [x0 + step, y0 + step],
                        [x0, y0 + step],
                        [x0, y0],
                    ]
                ],
            }
            out.append((i, j, poly))
    return out


def make_zones(
    pilot_id: str,
    pilot_name: str,
    lon: float,
    lat: float,
    half: float,
    *,
    version: str,
    seed: int,
    fuente: str,
) -> list[dict]:
    rng = random.Random(seed)
    features = []
    for i, j, geom in grid_cells(lon, lat, half, n=8):
        # Distribución plausible: centro denso urbano, periferia urbanizable, fuera no urbanizable
        center_dist = max(abs(i - 3.5), abs(j - 3.5))
        if center_dist <= 1.5:
            clas: Clasificacion = "urbano-consolidado"
            cali: Calificacion = rng.choice(
                ["residencial", "residencial", "terciario", "mixto", "dotacional-publico"]
            )
        elif center_dist <= 2.5:
            clas = rng.choice(["urbano-no-consolidado", "urbanizable-sectorizado"])
            cali = rng.choice(["residencial", "industrial", "dotacional-privado", "terciario"])
        elif center_dist <= 3.2:
            clas = "urbanizable-no-sectorizado"
            cali = rng.choice(["residencial", "industrial", "sin-asignar"])
        else:
            clas = rng.choice(["no-urbanizable-comun", "no-urbanizable-protegido"])
            cali = "espacio-libre"

        props = ZonaProperties(
            municipio=pilot_name,
            clasificacion=clas,
            calificacion=cali,
            version=version,  # type: ignore[arg-type]
            fuente=fuente,
            fecha_dato="2026-05-12",
            ambito=f"{pilot_id.upper()}-{i}-{j}",
            edificabilidad_m2_m2=round(rng.uniform(0.3, 2.5), 2)
            if clas.startswith("urban") else None,
        )
        features.append({"type": "Feature", "geometry": geom, "properties": props.to_dict()})
    return features


def write_fc(path: Path, features: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  wrote {path.relative_to(ROOT)}  ({len(features)} features)")


def build_cam_base() -> None:
    """CAM outline + 4 pilot rectangles. id field marks pilots."""
    # Rough CAM bbox
    cam_geom = rect(-3.65, 40.55, 0.85)
    features = [
        {
            "type": "Feature",
            "geometry": cam_geom,
            "properties": {"id": "cam-outline", "name": "Comunidad de Madrid (stub)"},
        }
    ]
    for pid, (name, lon, lat, half) in PILOTS.items():
        features.append(
            {
                "type": "Feature",
                "geometry": rect(lon, lat, half),
                "properties": {"id": pid, "name": name},
            }
        )
    write_fc(PUBLIC / "cam-municipios.geojson", features)


def build_pilot(pilot_id: str) -> None:
    name, lon, lat, half = PILOTS[pilot_id]
    print(f"[{pilot_id}] {name}")

    vigente = make_zones(
        pilot_id, name, lon, lat, half,
        version="vigente",
        seed=hash(pilot_id) & 0xFFFF,
        fuente="STUB (build_stubs.py) — sustituir con ingesta real",
    )
    write_fc(PUBLIC / pilot_id / "vigente.geojson", vigente)

    if pilot_id == "madrid":
        # Stub de una revisión con cambios: ~20% de zonas reclasificadas
        revision = make_zones(
            pilot_id, name, lon, lat, half,
            version="revision-borrador",
            seed=(hash(pilot_id) ^ 0xBADC0DE) & 0xFFFF,
            fuente="STUB (revisión simulada) — el PG 2020 real no tiene cartografía pública aún",
        )
        write_fc(PUBLIC / pilot_id / "revision.geojson", revision)

    # Derivados a partir de la versión vigente
    dormidos = [
        f for f in vigente
        if f["properties"]["clasificacion"] == "urbanizable-sectorizado"
    ]
    for f in dormidos:
        f["properties"] = {**f["properties"], "derivado": "sectores-dormidos"}
    write_fc(PUBLIC / pilot_id / "sectores-dormidos.geojson", dormidos)

    reconv = [
        f for f in vigente
        if f["properties"]["clasificacion"] == "urbano-consolidado"
        and f["properties"]["calificacion"] in ("terciario", "dotacional-privado")
    ]
    for f in reconv:
        f["properties"] = {**f["properties"], "derivado": "reconvertible"}
    write_fc(PUBLIC / pilot_id / "reconvertible.geojson", reconv)


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    build_cam_base()
    for pid in PILOTS:
        build_pilot(pid)
    print("\nStubs generados. Reemplazar progresivamente con ingest/<pilot>.py reales.")


if __name__ == "__main__":
    main()
