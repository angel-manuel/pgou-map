import {
  CAM_INDEX_FILE,
  OVERRIDES,
  type CamIndexEntry,
  type Municipio,
} from "../registry";

interface CamIndex {
  count: number;
  source: string;
  municipios: CamIndexEntry[];
}

export interface AllMunicipios {
  mount(onSelectionChange: (selected: Map<string, Municipio>) => void): Promise<void>;
  setSelection(slugs: Iterable<string>, anchor?: string | null): void;
  toggleSlug(slug: string): void;
  resolveBySlug(slug: string): Municipio | null;
  getSelection(): Map<string, Municipio>;
}

/** Build a default Municipio from a SIT index entry (no derived layers). */
export function pilotFromIndex(e: CamIndexEntry): Municipio {
  const [minx, miny, maxx, maxy] = e.bbox;
  const span = Math.max(maxx - minx, maxy - miny);
  let zoom = 12;
  if (span > 0.18) zoom = 11;
  if (span > 0.35) zoom = 10;
  if (span < 0.05) zoom = 13.5;
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

export function createAllMunicipios(root: HTMLElement): AllMunicipios {
  const buttonsBySlug = new Map<string, HTMLButtonElement>();
  let entries: CamIndexEntry[] = [];
  let entriesBySlug = new Map<string, CamIndexEntry>();
  let renderedOrder: string[] = []; // slugs currently shown in the list
  const selection = new Map<string, Municipio>();
  let anchorSlug: string | null = null;
  let onChange: ((sel: Map<string, Municipio>) => void) | null = null;
  const listId = "all-muni-list";

  function resolve(slug: string): Municipio | null {
    if (slug in OVERRIDES) return OVERRIDES[slug];
    const e = entriesBySlug.get(slug);
    return e ? pilotFromIndex(e) : null;
  }

  function emit(): void {
    onChange?.(selection);
  }

  function syncButtonsActive(): void {
    for (const [k, btn] of buttonsBySlug) {
      btn.classList.toggle("active", selection.has(k));
    }
    updateStat();
  }

  function updateStat(): void {
    const stat = root.querySelector("#all-muni-stat") as HTMLElement | null;
    if (!stat) return;
    const totalShown = renderedOrder.length;
    const selCount = selection.size;
    stat.textContent =
      selCount > 0
        ? `${selCount} sel. · ${totalShown} de ${entries.length}`
        : `${totalShown} de ${entries.length}`;
  }

  function selectOne(slug: string): void {
    selection.clear();
    const m = resolve(slug);
    if (m) selection.set(slug, m);
    anchorSlug = slug;
    syncButtonsActive();
    emit();
  }

  function toggle(slug: string): void {
    if (selection.has(slug)) {
      selection.delete(slug);
    } else {
      const m = resolve(slug);
      if (m) selection.set(slug, m);
    }
    anchorSlug = slug;
    syncButtonsActive();
    emit();
  }

  function selectRangeTo(slug: string): void {
    if (!anchorSlug || !renderedOrder.includes(anchorSlug)) {
      // No anchor in current view → behave like a toggle.
      toggle(slug);
      return;
    }
    const a = renderedOrder.indexOf(anchorSlug);
    const b = renderedOrder.indexOf(slug);
    if (a === -1 || b === -1) {
      toggle(slug);
      return;
    }
    const [lo, hi] = a <= b ? [a, b] : [b, a];
    for (let i = lo; i <= hi; i++) {
      const s = renderedOrder[i];
      if (!selection.has(s)) {
        const m = resolve(s);
        if (m) selection.set(s, m);
      }
    }
    // anchor stays the same — standard range-extend behavior
    syncButtonsActive();
    emit();
  }

  function selectAllVisible(): void {
    for (const s of renderedOrder) {
      if (!selection.has(s)) {
        const m = resolve(s);
        if (m) selection.set(s, m);
      }
    }
    syncButtonsActive();
    emit();
  }

  function clearSelection(): void {
    if (selection.size === 0) return;
    selection.clear();
    anchorSlug = null;
    syncButtonsActive();
    emit();
  }

  function renderList(query: string): void {
    const ul = root.querySelector(`#${listId}`) as HTMLUListElement | null;
    if (!ul) return;
    ul.innerHTML = "";
    buttonsBySlug.clear();
    const q = query.trim().toLowerCase();
    const matched = q
      ? entries.filter((e) => e.name.toLowerCase().includes(q))
      : entries;
    renderedOrder = matched.slice(0, 250).map((e) => e.slug);
    for (const e of matched.slice(0, 250)) {
      const li = document.createElement("li");
      li.style.listStyle = "none";
      const btn = document.createElement("button");
      btn.className = "muni-button";
      btn.style.fontSize = "12px";
      btn.style.padding = "5px 8px";
      btn.setAttribute("data-slug", e.slug);
      const isOverride = e.slug in OVERRIDES;
      const tag = isOverride
        ? `<span style="float:right;font-size:9px;color:#52b3a4;border:1px solid #52b3a4;padding:0 4px;border-radius:3px">+detalle</span>`
        : "";
      btn.innerHTML = `${e.name}  · ${e.feature_count}${tag}`;
      btn.title = `${e.documento ?? ""} · CAM ${e.cam_code}`;
      btn.addEventListener("click", (ev) => {
        const me = ev as MouseEvent;
        if (me.shiftKey) {
          selectRangeTo(e.slug);
        } else if (me.ctrlKey || me.metaKey) {
          toggle(e.slug);
        } else {
          selectOne(e.slug);
        }
      });
      li.appendChild(btn);
      ul.appendChild(li);
      buttonsBySlug.set(e.slug, btn);
    }
    syncButtonsActive();
  }

  return {
    async mount(onSelectionChange) {
      onChange = onSelectionChange;
      root.innerHTML = `
        <h2>Municipios CAM</h2>
        <input type="search" id="all-muni-q" placeholder="Buscar municipio…"
          style="width:100%;padding:6px 8px;background:#11151c;color:inherit;border:1px solid #2a3140;border-radius:4px;font-size:12px;margin-bottom:6px">
        <div style="display:flex;gap:6px;margin-bottom:6px">
          <button type="button" id="all-muni-select-all" class="mini-button">Todos</button>
          <button type="button" id="all-muni-clear" class="mini-button">Ninguno</button>
        </div>
        <div style="font-size:11px;color:#9aa3b2;margin-bottom:6px">
          <span id="all-muni-stat">cargando…</span> · fuente SIT-CAM
        </div>
        <div style="font-size:10px;color:#6a7286;margin-bottom:6px;line-height:1.4">
          Clic = uno · Ctrl/⌘+clic = añadir/quitar · Mayús+clic = rango · Ctrl/⌘+A = todos los visibles
        </div>
        <ul id="${listId}" style="margin:0;padding:0;max-height:320px;overflow-y:auto"></ul>
      `;
      try {
        const res = await fetch(CAM_INDEX_FILE);
        const idx = (await res.json()) as CamIndex;
        entries = idx.municipios.slice().sort((a, b) => a.name.localeCompare(b.name, "es"));
        entriesBySlug = new Map(entries.map((e) => [e.slug, e]));
      } catch {
        const stat = root.querySelector("#all-muni-stat");
        if (stat) stat.textContent = "error cargando index.json";
        return;
      }
      const input = root.querySelector("#all-muni-q") as HTMLInputElement;
      input.addEventListener("input", () => renderList(input.value));
      const selAllBtn = root.querySelector("#all-muni-select-all") as HTMLButtonElement;
      const clearBtn = root.querySelector("#all-muni-clear") as HTMLButtonElement;
      selAllBtn.addEventListener("click", () => selectAllVisible());
      clearBtn.addEventListener("click", () => clearSelection());

      // Ctrl/Cmd+A while typing in the search input (or button focused inside this section)
      // selects all currently visible.
      root.addEventListener("keydown", (ev) => {
        const ke = ev as KeyboardEvent;
        if ((ke.ctrlKey || ke.metaKey) && ke.key.toLowerCase() === "a") {
          ke.preventDefault();
          selectAllVisible();
        }
      });

      renderList("");
    },
    setSelection(slugs, anchor) {
      selection.clear();
      for (const s of slugs) {
        const m = resolve(s);
        if (m) selection.set(s, m);
      }
      if (anchor !== undefined) anchorSlug = anchor;
      syncButtonsActive();
      emit();
    },
    toggleSlug(slug) {
      toggle(slug);
    },
    resolveBySlug(slug) {
      return resolve(slug);
    },
    getSelection() {
      return selection;
    },
  };
}
