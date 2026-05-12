"""Recorre datos.gob.es y la API CKAN de la Comunidad de Madrid para descubrir
qué municipios de la CAM publican datasets de planeamiento descargables en
formato geoespacial (ZIP, SHP, GeoJSON, GML, KMZ).

Imprime una tabla con: municipio, dataset, formatos disponibles y URL.

Uso:
    python data-pipeline/survey_pgou_sources.py
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict

# datos.gob.es API: ?_pageSize=, _page=, keyword=
DGB_BASE = "https://datos.gob.es/apidata/catalog/dataset/keyword"
KEYWORDS = [
    "planeamiento",
    "PGOU",
    "calificacion-suelo",
    "ordenacion",
    "urbanismo",
    "suelo",
]
# Formatos geoespaciales de interés (en el campo `format._value` o `format.value`)
GEO_FMT_HINTS = ("ZIP", "SHP", "GeoJSON", "GML", "KMZ", "KML", "WFS", "WMS")

# CAM municipios → INE code (28-prefijo). El publisher de datos.gob.es para un
# Ayuntamiento es `.../Organismo/L01<INECODE>`. Necesitamos al menos los
# pilotos y un patrón para identificar otros municipios CAM.
CAM_PUBLISHER_PATTERN = re.compile(r"L0128\d{3}")


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(
        url, headers={"User-Agent": "pgou-map/0.1 (research)", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def title_es(item: dict) -> str:
    t = item.get("title", [])
    if isinstance(t, list):
        for x in t:
            if isinstance(x, dict) and x.get("_lang") == "es":
                return x.get("_value", "?")
        if t and isinstance(t[0], dict):
            return t[0].get("_value", "?")
    if isinstance(t, dict):
        return t.get("_value", "?")
    return str(t)


def publisher_id(item: dict) -> str:
    pub = item.get("publisher", {})
    if isinstance(pub, dict):
        return pub.get("_about", "") or ""
    return str(pub or "")


def distributions(item: dict) -> list[dict]:
    dis = item.get("distribution", [])
    if isinstance(dis, dict):
        return [dis]
    return [d for d in dis if isinstance(d, dict)]


def fmt_value(d: dict) -> str:
    f = d.get("format", {})
    if isinstance(f, dict):
        v = f.get("value") or f.get("_value") or ""
        return v.rsplit("/", 1)[-1] if isinstance(v, str) else ""
    return str(f)


def is_geo(d: dict) -> bool:
    v = fmt_value(d).upper()
    return any(h.upper() in v for h in GEO_FMT_HINTS)


def crawl() -> dict[str, list[dict]]:
    """Returns publisher_id → list of geo-dataset records."""
    by_pub: dict[str, list[dict]] = defaultdict(list)
    seen_ds_ids: set[str] = set()

    for kw in KEYWORDS:
        page = 0
        while True:
            url = f"{DGB_BASE}/{urllib.parse.quote(kw)}?_pageSize=50&_page={page}"
            try:
                data = fetch_json(url)
            except Exception as e:
                print(f"[crawl] {kw} page={page}: {e}", file=sys.stderr)
                break
            items = data.get("result", {}).get("items", [])
            if not items:
                break
            for it in items:
                ds_id = it.get("_about") or it.get("@id") or title_es(it)
                if ds_id in seen_ds_ids:
                    continue
                seen_ds_ids.add(ds_id)
                pub = publisher_id(it)
                if not CAM_PUBLISHER_PATTERN.search(pub):
                    continue
                geo_dists = [d for d in distributions(it) if is_geo(d)]
                if not geo_dists:
                    continue
                by_pub[pub].append(
                    {
                        "title": title_es(it),
                        "dataset_url": ds_id,
                        "formats": sorted({fmt_value(d) for d in geo_dists}),
                        "downloads": [
                            d.get("accessURL") or d.get("downloadURL") for d in geo_dists
                        ],
                    }
                )
            page += 1
            if page > 10:  # safety
                break
            time.sleep(0.2)
    return by_pub


# Mapeo INE → nombre del municipio (subset esperable; otros se imprimen con el
# código INE). 28 = código provincia Madrid; los últimos 3 dígitos son el
# municipio dentro de la provincia.
INE_NAME = {
    "079": "Madrid",
    "005": "Alcalá de Henares",
    "148": "Torrejón de Ardoz",
    "068": "Guadarrama",
    "006": "Alcobendas",
    "007": "Alcorcón",
    "058": "Fuenlabrada",
    "065": "Getafe",
    "074": "Leganés",
    "092": "Móstoles",
    "127": "San Sebastián de los Reyes",
    "159": "Las Rozas de Madrid",
    "022": "Aranjuez",
    "045": "Coslada",
    "049": "El Escorial",
    "115": "Pozuelo de Alarcón",
    "133": "Rivas-Vaciamadrid",
    "134": "Boadilla del Monte",
    "175": "Villaviciosa de Odón",
    "180": "Tres Cantos",
    "181": "Soto del Real",
    "078": "Majadahonda",
}


def pub_to_name(pub_id: str) -> tuple[str, str]:
    m = CAM_PUBLISHER_PATTERN.search(pub_id)
    if not m:
        return ("?", pub_id)
    code = m.group(0)[-3:]
    return (INE_NAME.get(code, f"(INE 28{code})"), code)


def main() -> None:
    print("[survey] crawling datos.gob.es ...")
    by_pub = crawl()
    print(f"\n[survey] {len(by_pub)} CAM municipios with geo PGOU-related datasets:\n")

    rows = []
    for pub, items in by_pub.items():
        name, code = pub_to_name(pub)
        rows.append((name, code, items))
    rows.sort(key=lambda r: r[0])

    for name, code, items in rows:
        print(f"== {name}  (INE 28{code})  ·  {len(items)} datasets ==")
        for it in items:
            print(f"   · {it['title'][:90]}")
            print(f"     formatos: {', '.join(it['formats'])}")
            for u in it["downloads"][:2]:
                if u:
                    print(f"     → {u[:140]}")
        print()


if __name__ == "__main__":
    main()
