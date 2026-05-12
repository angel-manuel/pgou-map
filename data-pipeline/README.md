# Pipeline de datos — pgou-map

Convierte cartografía urbanística heterogénea de cada municipio piloto al
esquema normalizado definido en `schema.py` (espejo de `src/schema.ts`).

## Estado

MVP en modo **stub**: `build_stubs.py` produce geometrías sintéticas pero válidas
para que el visor funcione end-to-end. Cada `ingest/<pilot>.py` documenta
la fuente real prevista y queda como `TODO` ejecutable.

## Comandos

```bash
# 1) Generar todos los stubs (estado actual del MVP)
python data-pipeline/build_stubs.py

# 2) Cuando cada ingest real esté listo, sustituir:
python data-pipeline/ingest/madrid.py
python data-pipeline/ingest/alcala.py
python data-pipeline/ingest/torrejon.py
python data-pipeline/ingest/guadarrama.py

# 3) Regenerar capas derivadas tras cada vigente.geojson
python data-pipeline/derived_sectores_dormidos.py \
    public/data/madrid/vigente.geojson \
    public/data/madrid/sectores-dormidos.geojson

python data-pipeline/derived_reconvertible.py \
    public/data/madrid/vigente.geojson \
    public/data/madrid/reconvertible.geojson
```

## Convención de mapeo

Cada ingest define dos diccionarios:

```python
CLAS_TABLE: dict[str, Clasificacion] = {...}  # claves nativas → enum normalizado
CALI_TABLE: dict[str, Calificacion] = {...}
```

y usa `normalize.normalize_clasificacion()` / `normalize.normalize_calificacion()`,
que loguean a stderr cualquier clave nativa desconocida (no rompen el build,
pero la zona queda como `sin-asignar` o `no-urbanizable-comun` y se ve en el
visor).

## Fuentes — estado actual

| Municipio | Fuente | Estado | Tamaño |
|---|---|---|---|
| Madrid capital (PG-97) | Geoportal Madrid `PGOUM97_ORDENACION.zip` → capa AMBITOS | **REAL** | 1487 features → 1.4 MB GeoJSON |
| Madrid revisión (PG 2020) | sin cartografía pública | TODO | — |
| Alcalá de Henares | sin abierto programático (probado: datos.gob.es, datos.comunidad.madrid, IDEM-CAM WFS) | TODO (stub) | — |
| Torrejón de Ardoz | sin abierto programático | TODO (stub) | — |
| Guadarrama | sin abierto programático, riesgo de PGOU sólo en PDF | TODO (stub) | — |
| CAM municipios base | OSM via Overpass API (relation 349055 + admin_level=8) | **REAL** | 179 features → 161 KB tras simplificar |

Para los pilotos en TODO, las vías más prometedoras (manuales):
- Visor SIGTRAUR (CAM): https://www.comunidad.madrid/servicios/urbanismo-medio-ambiente — descargar shapefile desde la UI Java.
- Portal de transparencia de cada Ayuntamiento (Alcalá, Torrejón, Guadarrama).
- Solicitud de acceso a información pública si las opciones anteriores fallan.

## Validación

Para Madrid (cuando el ingest real esté listo):
1. Contar zonas residenciales del GeoJSON normalizado.
2. Contrastar con cifra agregada que aporte la fuente oficial.
3. Discrepancia > 10 % → revisar tabla de mapeo y documentar aquí.
