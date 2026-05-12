import { CAM_INDEX_FILE, OVERRIDES, } from "../registry";
/** Build a default Municipio from a SIT index entry (no derived layers). */
export function pilotFromIndex(e) {
    const [minx, miny, maxx, maxy] = e.bbox;
    const span = Math.max(maxx - minx, maxy - miny);
    let zoom = 12;
    if (span > 0.18)
        zoom = 11;
    if (span > 0.35)
        zoom = 10;
    if (span < 0.05)
        zoom = 13.5;
    return {
        slug: e.slug,
        name: e.name,
        center: e.center,
        zoom,
        dataStatus: "real",
        dataNote: `SIT-CAM. ${e.feature_count} polígonos${e.documento ? ` · ${e.documento}` : ""}. Sólo clasificación, sin uso pormenorizado.`,
        versions: [{ version: "vigente", file: e.file }],
        derived: [
            // SIT data has no `calificacion`; only dormidos works derivable.
            {
                id: "sectores-dormidos",
                file: `/data/cam/${e.slug}/sectores-dormidos.geojson`,
                label: "Sectores dormidos",
            },
        ],
    };
}
export function createAllMunicipios(root) {
    const buttonsBySlug = new Map();
    let entries = [];
    let entriesBySlug = new Map();
    const listId = "all-muni-list";
    function renderList(query, onSelect) {
        const ul = root.querySelector(`#${listId}`);
        if (!ul)
            return;
        ul.innerHTML = "";
        buttonsBySlug.clear();
        const q = query.trim().toLowerCase();
        const matched = q
            ? entries.filter((e) => e.name.toLowerCase().includes(q))
            : entries;
        const stat = root.querySelector("#all-muni-stat");
        if (stat)
            stat.textContent = `${matched.length} de ${entries.length}`;
        for (const e of matched.slice(0, 250)) {
            const li = document.createElement("li");
            li.style.listStyle = "none";
            const btn = document.createElement("button");
            btn.className = "muni-button";
            btn.style.fontSize = "12px";
            btn.style.padding = "5px 8px";
            const isOverride = e.slug in OVERRIDES;
            const tag = isOverride
                ? `<span style="float:right;font-size:9px;color:#52b3a4;border:1px solid #52b3a4;padding:0 4px;border-radius:3px">+detalle</span>`
                : "";
            btn.innerHTML = `${e.name}  · ${e.feature_count}${tag}`;
            btn.title = `${e.documento ?? ""} · CAM ${e.cam_code}`;
            btn.addEventListener("click", () => {
                const m = OVERRIDES[e.slug] ?? pilotFromIndex(e);
                onSelect(m, e);
            });
            li.appendChild(btn);
            ul.appendChild(li);
            buttonsBySlug.set(e.slug, btn);
        }
    }
    return {
        async mount(onSelect) {
            root.innerHTML = `
        <h2>Municipios CAM</h2>
        <input type="search" id="all-muni-q" placeholder="Buscar municipio…"
          style="width:100%;padding:6px 8px;background:#11151c;color:inherit;border:1px solid #2a3140;border-radius:4px;font-size:12px;margin-bottom:6px">
        <div style="font-size:11px;color:#9aa3b2;margin-bottom:6px">
          <span id="all-muni-stat">cargando…</span> · fuente SIT-CAM
        </div>
        <ul id="${listId}" style="margin:0;padding:0;max-height:320px;overflow-y:auto"></ul>
      `;
            try {
                const res = await fetch(CAM_INDEX_FILE);
                const idx = (await res.json());
                entries = idx.municipios.slice().sort((a, b) => a.name.localeCompare(b.name, "es"));
                entriesBySlug = new Map(entries.map((e) => [e.slug, e]));
            }
            catch {
                const stat = root.querySelector("#all-muni-stat");
                if (stat)
                    stat.textContent = "error cargando index.json";
                return;
            }
            const input = root.querySelector("#all-muni-q");
            input.addEventListener("input", () => renderList(input.value, onSelect));
            renderList("", onSelect);
        },
        setActive(slug) {
            for (const [k, btn] of buttonsBySlug) {
                btn.classList.toggle("active", k === slug);
            }
        },
        resolveBySlug(slug) {
            if (slug in OVERRIDES)
                return OVERRIDES[slug];
            const e = entriesBySlug.get(slug);
            return e ? pilotFromIndex(e) : null;
        },
    };
}
