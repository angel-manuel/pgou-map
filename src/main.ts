import {
  CAM_CENTER,
  CAM_MUNICIPIOS_FILE,
  CAM_ZOOM,
  type Municipio,
  type DerivedLayer,
} from "./registry";
import { loadGeoJSON } from "./data";
import {
  createMap,
  installLayers,
  setActiveCamSlugs,
  setColorMode,
  setDormidos,
  setReconvertible,
  setSoloMode,
  setZones,
} from "./map";
import maplibregl from "maplibre-gl";
import { createVersionSelector } from "./ui/version-selector";
import { createLayerToggle, type LayerState } from "./ui/layer-toggle";
import { createLegend } from "./ui/legend";
import { createInfoPanel } from "./ui/info-panel";
import { createAllMunicipios } from "./ui/all-municipios";
import { createMapDisplay } from "./ui/map-display";
import type { Version } from "./schema";
import type { FeatureCollection, Feature } from "geojson";

const $ = (id: string): HTMLElement => {
  const el = document.getElementById(id);
  if (!el) throw new Error(`Missing element #${id}`);
  return el;
};

function mergeFCs(fcs: (FeatureCollection | null)[]): FeatureCollection {
  const features: Feature[] = [];
  for (const fc of fcs) {
    if (!fc) continue;
    for (const f of fc.features) features.push(f);
  }
  return { type: "FeatureCollection", features };
}

function pickVersionFile(m: Municipio, version: Version): string | null {
  const exact = m.versions.find((v) => v.version === version);
  if (exact) return exact.file;
  return m.versions[0]?.file ?? null;
}

function unionBoundsOf(municipios: Iterable<Municipio>): maplibregl.LngLatBounds | null {
  let bounds: maplibregl.LngLatBounds | null = null;
  for (const m of municipios) {
    // We don't have full bbox per Municipio in the type, so approximate from center+zoom.
    // For tighter bounds we'd read from the CAM index, but center+padding works well enough.
    const lng = m.center[0];
    const lat = m.center[1];
    const pad = m.zoom <= 11 ? 0.12 : m.zoom <= 12.5 ? 0.06 : 0.03;
    const b = new maplibregl.LngLatBounds([lng - pad, lat - pad], [lng + pad, lat + pad]);
    if (!bounds) bounds = b;
    else bounds.extend(b);
  }
  return bounds;
}

async function main(): Promise<void> {
  const map = createMap($("map"), CAM_CENTER, CAM_ZOOM);

  await new Promise<void>((resolve) => map.on("load", () => resolve()));

  const camMunicipios = (await loadGeoJSON(CAM_MUNICIPIOS_FILE)) ?? {
    type: "FeatureCollection",
    features: [],
  };
  installLayers(map, camMunicipios);

  const allMunis = createAllMunicipios($("all-municipios"));
  const mapDisplay = createMapDisplay($("map-display"));
  const verSel = createVersionSelector($("version-selector"));
  const layerToggle = createLayerToggle($("layer-toggle"));
  const legend = createLegend($("legend"));
  const infoPanel = createInfoPanel($("info-panel"));

  let selected: Map<string, Municipio> = new Map();
  let activeVersion: Version = "vigente";
  let soloMode = false;
  let layerState: LayerState = {
    colorMode: "clasificacion",
    dormidos: false,
    reconvertible: false,
  };

  /**
   * Context municipio for the side panels (version selector, layer toggle).
   * With one selected: that one. With many: the last-added or first by order.
   */
  function contextMunicipio(): Municipio | null {
    if (selected.size === 0) return null;
    // Use the last entry as "focus" so version/layer toggles follow recent intent.
    let last: Municipio | null = null;
    for (const m of selected.values()) last = m;
    return last;
  }

  function unionDerived(): DerivedLayer[] {
    const seen = new Map<DerivedLayer["id"], DerivedLayer>();
    for (const m of selected.values()) {
      for (const d of m.derived) {
        if (!seen.has(d.id)) seen.set(d.id, d);
      }
    }
    return [...seen.values()];
  }

  async function applyZones(): Promise<void> {
    if (selected.size === 0) {
      setZones(map, null);
      return;
    }
    const fcs = await Promise.all(
      [...selected.values()].map(async (m) => {
        const file = pickVersionFile(m, activeVersion);
        if (!file) return null;
        return loadGeoJSON(file);
      }),
    );
    setZones(map, mergeFCs(fcs));
  }

  async function applyDerived(): Promise<void> {
    const dormidosFiles: (FeatureCollection | null)[] = [];
    const reconvFiles: (FeatureCollection | null)[] = [];
    if (layerState.dormidos || layerState.reconvertible) {
      await Promise.all(
        [...selected.values()].map(async (m) => {
          if (layerState.dormidos) {
            const d = m.derived.find((x) => x.id === "sectores-dormidos");
            if (d) dormidosFiles.push(await loadGeoJSON(d.file));
          }
          if (layerState.reconvertible) {
            const r = m.derived.find((x) => x.id === "reconvertible");
            if (r) reconvFiles.push(await loadGeoJSON(r.file));
          }
        }),
      );
    }
    setDormidos(map, layerState.dormidos ? mergeFCs(dormidosFiles) : null, layerState.dormidos);
    setReconvertible(
      map,
      layerState.reconvertible ? mergeFCs(reconvFiles) : null,
      layerState.reconvertible,
    );
  }

  function refreshUI(): void {
    const slugSet = new Set(selected.keys());
    setActiveCamSlugs(map, slugSet);
    setSoloMode(map, soloMode && slugSet.size > 0 ? slugSet : null);

    const ctx = contextMunicipio();
    const isMulti = selected.size > 1;

    mapDisplay.setVisible(selected.size > 0);
    mapDisplay.setSolo(soloMode);

    // Version selector: only meaningful when a single municipio is selected.
    if (isMulti) {
      verSel.update(null, () => {});
    } else {
      verSel.update(ctx, async (v) => {
        activeVersion = v;
        verSel.setActive(v);
        await applyZones();
      });
      verSel.setActive(activeVersion);
    }

    // Layer toggle: build a virtual "context" exposing the UNION of derived layers
    // across all selected municipios.
    const virtualForLayers: Municipio | null = ctx
      ? { ...ctx, derived: unionDerived() }
      : null;
    layerToggle.update(virtualForLayers, layerState, async (next) => {
      const colorChanged = next.colorMode !== layerState.colorMode;
      layerState = next;
      if (colorChanged) setColorMode(map, layerState.colorMode);
      await applyDerived();
      refreshUI();
    });

    if (selected.size > 0) {
      legend.update(layerState.colorMode, {
        dormidos: layerState.dormidos,
        reconvertible: layerState.reconvertible,
      });
    } else {
      legend.hide();
    }
  }

  async function onSelectionChanged(newSelected: Map<string, Municipio>): Promise<void> {
    const prevSize = selected.size;
    selected = new Map(newSelected);

    // When going from 0 → ≥1, reset per-context state.
    if (prevSize === 0 && selected.size > 0) {
      activeVersion = "vigente";
      layerState = { colorMode: "clasificacion", dormidos: false, reconvertible: false };
      setColorMode(map, layerState.colorMode);
    }
    // When >1 selected, version-selector is hidden; force vigente.
    if (selected.size > 1 && activeVersion !== "vigente") {
      activeVersion = "vigente";
    }

    // Fit bounds when selection changes and is non-empty.
    if (selected.size > 0) {
      const bounds = unionBoundsOf(selected.values());
      if (bounds) {
        if (selected.size === 1) {
          const m = selected.values().next().value as Municipio;
          map.flyTo({ center: m.center, zoom: m.zoom, duration: 600 });
        } else {
          map.fitBounds(bounds, { padding: 60, duration: 600, maxZoom: 11.5 });
        }
      }
    }

    await applyZones();
    await applyDerived();
    refreshUI();
  }

  await allMunis.mount((sel) => void onSelectionChanged(sel));

  mapDisplay.mount((solo) => {
    soloMode = solo;
    const slugSet = new Set(selected.keys());
    setSoloMode(map, soloMode && slugSet.size > 0 ? slugSet : null);
  });

  map.on("click", "zones-fill", (e) => {
    const feat = e.features?.[0];
    if (!feat) return;
    infoPanel.show(feat.properties as Record<string, unknown>);
  });
  map.on("mouseenter", "zones-fill", () => (map.getCanvas().style.cursor = "pointer"));
  map.on("mouseleave", "zones-fill", () => (map.getCanvas().style.cursor = ""));

  // Click on any municipio outline activates it.
  // Plain click → replace selection. Ctrl/Cmd/Shift → toggle.
  map.on("click", "cam-fill", (e) => {
    const feat = e.features?.[0];
    const slug = feat?.properties?.slug as string | undefined;
    if (!slug) return;
    const oe = e.originalEvent as MouseEvent;
    const additive = oe.ctrlKey || oe.metaKey || oe.shiftKey;
    if (additive) {
      allMunis.toggleSlug(slug);
    } else {
      allMunis.setSelection([slug], slug);
    }
  });
  map.on("mouseenter", "cam-fill", () => (map.getCanvas().style.cursor = "pointer"));
  map.on("mouseleave", "cam-fill", () => (map.getCanvas().style.cursor = ""));

  refreshUI();
}

void main();
