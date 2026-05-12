import {
  CALIFICACION_LABEL,
  CLASIFICACION_LABEL,
  VERSION_LABEL,
  type Calificacion,
  type Clasificacion,
  type Version,
} from "../schema";

interface RawProps {
  municipio?: unknown;
  ambito?: unknown;
  clasificacion?: unknown;
  calificacion?: unknown;
  edificabilidad_m2_m2?: unknown;
  version?: unknown;
  fuente?: unknown;
  fecha_dato?: unknown;
}

export interface InfoPanel {
  show(props: RawProps): void;
  hide(): void;
}

function row(label: string, value: string | undefined | null): string {
  if (value == null || value === "") return "";
  return `<div class="info-row"><span>${label}</span><span>${value}</span></div>`;
}

export function createInfoPanel(root: HTMLElement): InfoPanel {
  return {
    show(props) {
      const clas = props.clasificacion as Clasificacion | undefined;
      const cali = props.calificacion as Calificacion | undefined;
      const ver = props.version as Version | undefined;
      const edi = typeof props.edificabilidad_m2_m2 === "number"
        ? props.edificabilidad_m2_m2.toFixed(2)
        : undefined;
      const fuente = props.fuente as string | undefined;
      const isStub = typeof fuente === "string" && fuente.startsWith("STUB");

      root.hidden = false;
      root.innerHTML = `
        <h2>Zona</h2>
        ${isStub ? `<div class="notice" style="color:#ffce5c;margin-bottom:8px">⚠ Datos sintéticos (placeholder). PGOU real no publicado en abierto para este municipio.</div>` : ""}
        ${row("Municipio", props.municipio as string | undefined)}
        ${row("Ámbito", props.ambito as string | undefined)}
        ${row("Clasificación", clas ? CLASIFICACION_LABEL[clas] : undefined)}
        ${row("Calificación", cali ? CALIFICACION_LABEL[cali] : undefined)}
        ${row("Edif. (m²/m²)", edi)}
        ${row("Versión", ver ? VERSION_LABEL[ver] : undefined)}
        ${row("Fuente", fuente)}
        ${row("Fecha dato", props.fecha_dato as string | undefined)}
      `;
    },
    hide() {
      root.hidden = true;
      root.innerHTML = "";
    },
  };
}
