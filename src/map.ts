import maplibregl, { Map, StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import {
  CALIFICACION,
  CALIFICACION_COLOR,
  CLASIFICACION,
  CLASIFICACION_COLOR,
} from "./schema";
import { EMPTY_FC } from "./data";
import type { FeatureCollection } from "geojson";

const STYLE: StyleSpecification = {
  version: 8,
  glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors",
      maxzoom: 19,
    },
  },
  layers: [
    {
      id: "osm",
      type: "raster",
      source: "osm",
      paint: { "raster-opacity": 0.55, "raster-saturation": -0.4 },
    },
  ],
};

export type ColorMode = "clasificacion" | "calificacion";

export function createMap(container: HTMLElement, center: [number, number], zoom: number): Map {
  return new maplibregl.Map({
    container,
    style: STYLE,
    center,
    zoom,
    attributionControl: { compact: true },
  });
}

const SRC_CAM = "cam-municipios";
const SRC_ZONES = "zones";
const SRC_DORMIDOS = "dormidos";
const SRC_RECONV = "reconvertible";

const LYR_CAM_FILL = "cam-fill";
const LYR_CAM_LINE = "cam-line";
const LYR_ZONES_FILL = "zones-fill";
const LYR_ZONES_LINE = "zones-line";
const LYR_DORMIDOS = "dormidos-outline";
const LYR_RECONV = "reconvertible-outline";

function buildClassFillColor(): maplibregl.DataDrivenPropertyValueSpecification<string> {
  const expr: (string | string[])[] = ["match", ["get", "clasificacion"]];
  for (const c of CLASIFICACION) {
    expr.push(c, CLASIFICACION_COLOR[c]);
  }
  expr.push("#666c78");
  return expr as unknown as maplibregl.DataDrivenPropertyValueSpecification<string>;
}

function buildCalifFillColor(): maplibregl.DataDrivenPropertyValueSpecification<string> {
  const expr: (string | string[])[] = ["match", ["get", "calificacion"]];
  for (const c of CALIFICACION) {
    expr.push(c, CALIFICACION_COLOR[c]);
  }
  expr.push("#666c78");
  return expr as unknown as maplibregl.DataDrivenPropertyValueSpecification<string>;
}

export function installLayers(map: Map, camMunicipios: FeatureCollection): void {
  map.addSource(SRC_CAM, { type: "geojson", data: camMunicipios });
  map.addSource(SRC_ZONES, { type: "geojson", data: EMPTY_FC });
  map.addSource(SRC_DORMIDOS, { type: "geojson", data: EMPTY_FC });
  map.addSource(SRC_RECONV, { type: "geojson", data: EMPTY_FC });

  map.addLayer({
    id: LYR_CAM_FILL,
    type: "fill",
    source: SRC_CAM,
    paint: {
      "fill-color": [
        "case",
        ["==", ["get", "slug"], ["literal", ""]],
        "#6ea8fe",
        "#3a4252",
      ],
      "fill-opacity": [
        "case",
        ["==", ["get", "slug"], ["literal", ""]],
        0.22,
        0.06,
      ],
    },
  });
  map.addLayer({
    id: LYR_CAM_LINE,
    type: "line",
    source: SRC_CAM,
    paint: {
      "line-color": [
        "case",
        ["==", ["get", "slug"], ["literal", ""]],
        "#6ea8fe",
        "#5a6275",
      ],
      "line-width": [
        "case",
        ["==", ["get", "slug"], ["literal", ""]],
        1.4,
        0.4,
      ],
    },
  });

  map.addLayer({
    id: LYR_ZONES_FILL,
    type: "fill",
    source: SRC_ZONES,
    paint: {
      "fill-color": buildClassFillColor(),
      "fill-opacity": 0.55,
    },
    layout: { visibility: "none" },
  });
  map.addLayer({
    id: LYR_ZONES_LINE,
    type: "line",
    source: SRC_ZONES,
    paint: { "line-color": "rgba(0,0,0,0.35)", "line-width": 0.4 },
    layout: { visibility: "none" },
  });

  map.addLayer({
    id: LYR_DORMIDOS,
    type: "line",
    source: SRC_DORMIDOS,
    paint: { "line-color": "#ffce5c", "line-width": 2.2 },
    layout: { visibility: "none" },
  });
  map.addLayer({
    id: LYR_RECONV,
    type: "line",
    source: SRC_RECONV,
    paint: { "line-color": "#ff6b9d", "line-width": 2.2 },
    layout: { visibility: "none" },
  });
}

export function setZones(map: Map, fc: FeatureCollection | null): void {
  const src = map.getSource(SRC_ZONES) as maplibregl.GeoJSONSource | undefined;
  src?.setData(fc ?? EMPTY_FC);
  const visible = !!fc && fc.features.length > 0;
  map.setLayoutProperty(LYR_ZONES_FILL, "visibility", visible ? "visible" : "none");
  map.setLayoutProperty(LYR_ZONES_LINE, "visibility", visible ? "visible" : "none");
}

export function setDormidos(map: Map, fc: FeatureCollection | null, visible: boolean): void {
  const src = map.getSource(SRC_DORMIDOS) as maplibregl.GeoJSONSource | undefined;
  src?.setData(fc ?? EMPTY_FC);
  map.setLayoutProperty(LYR_DORMIDOS, "visibility", visible && fc ? "visible" : "none");
}

export function setReconvertible(map: Map, fc: FeatureCollection | null, visible: boolean): void {
  const src = map.getSource(SRC_RECONV) as maplibregl.GeoJSONSource | undefined;
  src?.setData(fc ?? EMPTY_FC);
  map.setLayoutProperty(LYR_RECONV, "visibility", visible && fc ? "visible" : "none");
}

export function setColorMode(map: Map, mode: ColorMode): void {
  const color =
    mode === "clasificacion" ? buildClassFillColor() : buildCalifFillColor();
  map.setPaintProperty(LYR_ZONES_FILL, "fill-color", color);
}

/**
 * Highlight the active municipio outline. Pass null to clear.
 * Doesn't hide the others — for that, use `setSoloMode`.
 */
export function setActiveCamSlug(map: Map, slug: string | null): void {
  const s = slug ?? "__none__";
  map.setPaintProperty(LYR_CAM_FILL, "fill-color", [
    "case", ["==", ["get", "slug"], s], "#6ea8fe", "#3a4252",
  ]);
  map.setPaintProperty(LYR_CAM_FILL, "fill-opacity", [
    "case", ["==", ["get", "slug"], s], 0.22, 0.06,
  ]);
  map.setPaintProperty(LYR_CAM_LINE, "line-color", [
    "case", ["==", ["get", "slug"], s], "#6ea8fe", "#5a6275",
  ]);
  map.setPaintProperty(LYR_CAM_LINE, "line-width", [
    "case", ["==", ["get", "slug"], s], 1.4, 0.4,
  ]);
}

/**
 * Solo mode: when true with a slug, hide all CAM outlines except the active one.
 * When false (or slug null), show every municipio.
 */
export function setSoloMode(map: Map, slug: string | null): void {
  if (!slug) {
    map.setFilter(LYR_CAM_FILL, null);
    map.setFilter(LYR_CAM_LINE, null);
    return;
  }
  const filter: maplibregl.FilterSpecification = ["==", ["get", "slug"], slug];
  map.setFilter(LYR_CAM_FILL, filter);
  map.setFilter(LYR_CAM_LINE, filter);
}

export { LYR_ZONES_FILL, LYR_CAM_FILL };
