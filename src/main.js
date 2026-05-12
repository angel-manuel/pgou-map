import { CAM_CENTER, CAM_MUNICIPIOS_FILE, CAM_ZOOM, } from "./registry";
import { loadGeoJSON } from "./data";
import { createMap, installLayers, setActiveCamSlug, setColorMode, setDormidos, setReconvertible, setSoloMode, setZones, } from "./map";
import { createVersionSelector } from "./ui/version-selector";
import { createLayerToggle } from "./ui/layer-toggle";
import { createLegend } from "./ui/legend";
import { createInfoPanel } from "./ui/info-panel";
import { createAllMunicipios } from "./ui/all-municipios";
import { createMapDisplay } from "./ui/map-display";
const $ = (id) => {
    const el = document.getElementById(id);
    if (!el)
        throw new Error(`Missing element #${id}`);
    return el;
};
async function main() {
    const map = createMap($("map"), CAM_CENTER, CAM_ZOOM);
    await new Promise((resolve) => map.on("load", () => resolve()));
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
    let active = null;
    let activeVersion = "vigente";
    let soloMode = false;
    let layerState = {
        colorMode: "clasificacion",
        dormidos: false,
        reconvertible: false,
    };
    async function applyVersion(m, version) {
        const entry = m.versions.find((v) => v.version === version);
        if (!entry)
            return;
        const fc = await loadGeoJSON(entry.file);
        setZones(map, fc);
        if (!fc && entry.note) {
            infoPanel.show({
                municipio: m.name,
                ambito: "(sin datos)",
                version,
                fuente: entry.note,
            });
        }
    }
    async function applyDerived(m, state) {
        const dormidosEntry = m.derived.find((d) => d.id === "sectores-dormidos");
        const reconvEntry = m.derived.find((d) => d.id === "reconvertible");
        const dormidosFC = state.dormidos && dormidosEntry ? await loadGeoJSON(dormidosEntry.file) : null;
        const reconvFC = state.reconvertible && reconvEntry ? await loadGeoJSON(reconvEntry.file) : null;
        setDormidos(map, dormidosFC, state.dormidos);
        setReconvertible(map, reconvFC, state.reconvertible);
    }
    function refreshUI() {
        allMunis.setActive(active?.slug ?? null);
        setActiveCamSlug(map, active?.slug ?? null);
        setSoloMode(map, soloMode && active ? active.slug : null);
        mapDisplay.setVisible(!!active);
        mapDisplay.setSolo(soloMode);
        verSel.update(active, async (v) => {
            activeVersion = v;
            verSel.setActive(v);
            if (active)
                await applyVersion(active, v);
        });
        verSel.setActive(activeVersion);
        layerToggle.update(active, layerState, async (next) => {
            const colorChanged = next.colorMode !== layerState.colorMode;
            layerState = next;
            if (colorChanged)
                setColorMode(map, layerState.colorMode);
            if (active)
                await applyDerived(active, layerState);
            refreshUI();
        });
        if (active) {
            legend.update(layerState.colorMode, {
                dormidos: layerState.dormidos,
                reconvertible: layerState.reconvertible,
            });
        }
        else {
            legend.hide();
        }
    }
    async function activate(m) {
        active = m;
        activeVersion = m.versions[0].version;
        layerState = { colorMode: "clasificacion", dormidos: false, reconvertible: false };
        setColorMode(map, layerState.colorMode);
        map.flyTo({ center: m.center, zoom: m.zoom, duration: 800 });
        await applyVersion(m, activeVersion);
        await applyDerived(m, layerState);
        refreshUI();
    }
    await allMunis.mount((m) => void activate(m));
    mapDisplay.mount((solo) => {
        soloMode = solo;
        setSoloMode(map, soloMode && active ? active.slug : null);
    });
    map.on("click", "zones-fill", (e) => {
        const feat = e.features?.[0];
        if (!feat)
            return;
        infoPanel.show(feat.properties);
    });
    map.on("mouseenter", "zones-fill", () => (map.getCanvas().style.cursor = "pointer"));
    map.on("mouseleave", "zones-fill", () => (map.getCanvas().style.cursor = ""));
    // Click on any municipio outline activates it.
    map.on("click", "cam-fill", (e) => {
        const feat = e.features?.[0];
        const slug = feat?.properties?.slug;
        if (!slug)
            return;
        const m = allMunis.resolveBySlug(slug);
        if (m)
            void activate(m);
    });
    map.on("mouseenter", "cam-fill", () => (map.getCanvas().style.cursor = "pointer"));
    map.on("mouseleave", "cam-fill", () => (map.getCanvas().style.cursor = ""));
    refreshUI();
}
void main();
