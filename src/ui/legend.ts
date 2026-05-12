import {
  CALIFICACION,
  CALIFICACION_COLOR,
  CALIFICACION_LABEL,
  CLASIFICACION,
  CLASIFICACION_COLOR,
  CLASIFICACION_LABEL,
} from "../schema";
import type { ColorMode } from "../map";

export interface Legend {
  update(mode: ColorMode, derivedActive: { dormidos: boolean; reconvertible: boolean }): void;
  hide(): void;
}

export function createLegend(root: HTMLElement): Legend {
  return {
    update(mode, derived) {
      root.hidden = false;
      const entries =
        mode === "clasificacion"
          ? CLASIFICACION.map((c) => ({ color: CLASIFICACION_COLOR[c], label: CLASIFICACION_LABEL[c] }))
          : CALIFICACION.map((c) => ({ color: CALIFICACION_COLOR[c], label: CALIFICACION_LABEL[c] }));

      root.innerHTML = `<h2>Leyenda</h2>`;
      for (const e of entries) {
        const row = document.createElement("div");
        row.className = "legend-row";
        row.innerHTML = `<span class="legend-swatch" style="background:${e.color}"></span><span>${e.label}</span>`;
        root.appendChild(row);
      }

      if (derived.dormidos) {
        const row = document.createElement("div");
        row.className = "legend-row";
        row.innerHTML = `<span class="legend-swatch" style="background:transparent;border:2px solid #ffce5c"></span><span>Sectores dormidos (borde)</span>`;
        root.appendChild(row);
      }
      if (derived.reconvertible) {
        const row = document.createElement("div");
        row.className = "legend-row";
        row.innerHTML = `<span class="legend-swatch" style="background:transparent;border:2px solid #ff6b9d"></span><span>Reconvertible (borde)</span>`;
        root.appendChild(row);
      }
    },
    hide() {
      root.hidden = true;
      root.innerHTML = "";
    },
  };
}
