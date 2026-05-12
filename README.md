# pgou-map

Visor interno (proyecto-e) del planeamiento urbanístico de la Comunidad de
Madrid. Mapa de los 179 municipios, con zonificación PGOU y capas derivadas
para los **municipios piloto**:

- Madrid capital
- Alcalá de Henares
- Torrejón de Ardoz
- Guadarrama

Diseñado como herramienta de análisis interno para informar el programa, no
como visor público de campaña. Base conceptual en
[`docs/01-investigacion/06-recalificacion-municipal.md`](../../docs/01-investigacion/06-recalificacion-municipal.md)
y [`08-control-autonomico-del-pgou.md`](../../docs/01-investigacion/08-control-autonomico-del-pgou.md).

## Estado de los datos

| Capa | Cobertura | Datos | Fuente |
|---|---|---|---|
| Overview CAM (límites administrativos) | 179 municipios | **REAL** | OSM via Overpass (`fetch_cam_boundaries.py`) — 161 KB simplificado |
| **Planeamiento — clasificación del suelo** | **176 municipios CAM** | **REAL** | SIT-CAM WFS `UsoDelSuelo:VPLA_V_CLASIFICACION` (`fetch_sit_cam.py`) — 13 540 polígonos, 20 MB total, un GeoJSON por municipio bajo `/data/cam/<slug>/` + `index.json` |
| Madrid capital — calificación (uso pormenorizado) | 1 municipio | **REAL** | Geoportal Madrid PGOUM-97 AMBITOS (`ingest/madrid.py`) — 1487 ámbitos con `USO_CARACT` (residencial / terciario / industrial / dotacional). Más detallado que el SIT |
| Madrid — revisión (Plan General 2020) | — | sin datos | Cartografía no pública |
| Derivados — sectores dormidos | 176 municipios | derivado | `derived_sectores_dormidos.py` filtra `clasificacion=urbanizable-sectorizado` |
| Derivados — reconvertible (terciario/dotacional-privado a residencial) | sólo Madrid | derivado | Requiere `calificacion`; sólo disponible en la fuente Geoportal Madrid. Para el resto la capa SIT no expone uso pormenorizado |

3 códigos CAM (077/098/103/105/139/142) no devolvieron features en el WFS;
posibles municipios sin PGOU publicado en el sistema. Ver `index.json` para la
lista exacta de 176 cubiertos.

## Carga dinámica

- Overview CAM (161 KB) se carga al arrancar para que el mapa sea navegable.
- **Cada municipio carga sus capas (vigente, sectores-dormidos, reconvertible) sólo cuando lo seleccionas**. El módulo `src/data.ts` mantiene caché en memoria para no refetchar al volver al mismo municipio.

## Funcionalidades

- Mapa CAM con **los 180 contornos municipales** visibles y clicables. Click sobre cualquier municipio carga su PGOU.
- Sidebar con buscador de los 176 municipios con datos SIT-CAM (filtro por nombre).
- Toggle **"Solo mostrar municipio seleccionado"** que oculta los otros 178 contornos.
- Selector de versión PGOU (aparece cuando hay > 1 versión; actualmente Madrid).
- Cambio de color entre **clasificación del suelo** y **calificación / uso pormenorizado**.
- Toggle de capas derivadas: **sectores dormidos** y **terciario/dotacional reconvertible** (este último sólo para Madrid, único municipio con uso pormenorizado).
- Click en una zona → ficha detalle con municipio, ámbito, clasificación, calificación, edificabilidad, versión, fuente y fecha del dato.

## Stack

- Vite + TypeScript (estricto), sin framework UI.
- MapLibre GL JS con tile raster OSM.
- GeoJSON estático servido desde `public/data/`.
- Pipeline Python (sin dependencias externas en el modo stub).

## Cómo arrancar

```bash
cd apps/pgou-map
npm install

# Pipeline de datos (idempotente, cache en data-pipeline/.cache/):
python3 data-pipeline/fetch_cam_boundaries.py   # CAM 179 — OSM (overview)
python3 data-pipeline/fetch_sit_cam.py          # SIT-CAM 176 — clasificación real para todos
python3 data-pipeline/ingest/madrid.py          # Madrid PGOUM-97 — Geoportal Madrid (más detalle)
python3 data-pipeline/derived_sectores_dormidos.py public/data/madrid/vigente.geojson public/data/madrid/sectores-dormidos.geojson
python3 data-pipeline/derived_reconvertible.py    public/data/madrid/vigente.geojson public/data/madrid/reconvertible.geojson
# Regenerar derivados para los otros pilotos cuando se reingestan:
for slug in alcala-de-henares torrejon-de-ardoz guadarrama; do
  python3 data-pipeline/derived_sectores_dormidos.py public/data/cam/$slug/vigente.geojson public/data/cam/$slug/sectores-dormidos.geojson
  python3 data-pipeline/derived_reconvertible.py    public/data/cam/$slug/vigente.geojson public/data/cam/$slug/reconvertible.geojson
done

npm run dev                            # http://localhost:5173
```

Requisitos pipeline: **GDAL/ogr2ogr** (Debian/Ubuntu: `sudo apt install gdal-bin`).

Para producción:

```bash
npm run build
npm run preview
```

## Verificación manual (golden path)

1. Carga inicial: rectángulo CAM, 4 pilotos resaltados en azul.
2. Click en un piloto en la barra lateral (o sobre el rectángulo en el mapa)
   → el mapa centra y aparece la zonificación.
3. Para Madrid: el selector de versión "Vigente / Revisión (borrador)" cambia
   la capa renderizada.
4. Toggle "Sectores dormidos" → contornos amarillos sobre las zonas
   `urbanizable-sectorizado`.
5. Toggle "Terciario/dotacional reconvertible" → contornos magenta sobre
   las zonas `urbano-consolidado` con uso `terciario` o `dotacional-privado`.
6. Click en una zona → panel "Zona" con todos los campos.
7. Cambiar entre los 4 pilotos repite el flujo limpiamente.

## Estructura

```
apps/pgou-map/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── src/
│   ├── main.ts                       # bootstrap
│   ├── map.ts                        # MapLibre + capas
│   ├── data.ts                       # carga de GeoJSON (con cache)
│   ├── schema.ts                     # enums normalizados + colores/etiquetas
│   ├── registry.ts                   # catálogo de pilotos y rutas a sus datos
│   ├── styles.css
│   └── ui/
│       ├── municipality-selector.ts
│       ├── version-selector.ts       # visible si > 1 versión
│       ├── layer-toggle.ts           # color mode + capas derivadas
│       ├── legend.ts                 # leyenda dinámica
│       └── info-panel.ts             # ficha de zona
├── public/data/                      # GeoJSON (stub, regenerable)
└── data-pipeline/
    ├── README.md
    ├── schema.py                     # espejo de src/schema.ts
    ├── normalize.py                  # helpers de mapeo categoría nativa → enum
    ├── build_stubs.py                # genera datos stub deterministas
    ├── derived_sectores_dormidos.py  # filtro derivado
    ├── derived_reconvertible.py      # filtro derivado
    └── ingest/                       # TODO: implementaciones reales por piloto
        ├── madrid.py
        ├── alcala.py
        ├── torrejon.py
        └── guadarrama.py
```

## Hoja de ruta (post-MVP)

1. **Sustituir stubs por datos reales**, empezando por Madrid (Geoportal Madrid).
2. **Base CAM real**: descargar límites administrativos IDEM-CAM o INE.
3. **Validación cruzada**: contar zonas residenciales del GeoJSON normalizado
   contra cifras agregadas de la fuente oficial; documentar discrepancias en
   `data-pipeline/README.md`.
4. **Métrica de "sectores dormidos" mejor que el filtro base**: cruzar con
   estado de gestión (Plan Parcial aprobado / Proyecto de Urbanización
   ejecutado) cuando haya esa información.
5. Si llega a publicarse: revisar términos de uso de cada fuente y añadir
   atribución por capa.
