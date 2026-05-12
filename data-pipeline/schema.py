"""Esquema normalizado PGOU.

MIRROR EXACTO de apps/pgou-map/src/schema.ts. Si cambia uno, cambia el otro.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

Clasificacion = Literal[
    "urbano-consolidado",
    "urbano-no-consolidado",
    "urbanizable-sectorizado",
    "urbanizable-no-sectorizado",
    "no-urbanizable-comun",
    "no-urbanizable-protegido",
]

Calificacion = Literal[
    "residencial",
    "terciario",
    "industrial",
    "dotacional-publico",
    "dotacional-privado",
    "espacio-libre",
    "equipamiento",
    "mixto",
    "sin-asignar",
]

Version = Literal[
    "vigente",
    "revision-borrador",
    "revision-aprobacion-inicial",
    "revision-aprobacion-provisional",
]


@dataclass(frozen=True)
class ZonaProperties:
    municipio: str
    clasificacion: Clasificacion
    calificacion: Calificacion
    version: Version
    fuente: str
    fecha_dato: str
    ambito: Optional[str] = None
    edificabilidad_m2_m2: Optional[float] = None

    def to_dict(self) -> dict:
        d: dict = {
            "municipio": self.municipio,
            "clasificacion": self.clasificacion,
            "calificacion": self.calificacion,
            "version": self.version,
            "fuente": self.fuente,
            "fecha_dato": self.fecha_dato,
        }
        if self.ambito is not None:
            d["ambito"] = self.ambito
        if self.edificabilidad_m2_m2 is not None:
            d["edificabilidad_m2_m2"] = self.edificabilidad_m2_m2
        return d
