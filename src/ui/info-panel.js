import { CALIFICACION_LABEL, CLASIFICACION_LABEL, VERSION_LABEL, } from "../schema";
function row(label, value) {
    if (value == null || value === "")
        return "";
    return `<div class="info-row"><span>${label}</span><span>${value}</span></div>`;
}
export function createInfoPanel(root) {
    return {
        show(props) {
            const clas = props.clasificacion;
            const cali = props.calificacion;
            const ver = props.version;
            const edi = typeof props.edificabilidad_m2_m2 === "number"
                ? props.edificabilidad_m2_m2.toFixed(2)
                : undefined;
            const fuente = props.fuente;
            const isStub = typeof fuente === "string" && fuente.startsWith("STUB");
            root.hidden = false;
            root.innerHTML = `
        <h2>Zona</h2>
        ${isStub ? `<div class="notice" style="color:#ffce5c;margin-bottom:8px">⚠ Datos sintéticos (placeholder). PGOU real no publicado en abierto para este municipio.</div>` : ""}
        ${row("Municipio", props.municipio)}
        ${row("Ámbito", props.ambito)}
        ${row("Clasificación", clas ? CLASIFICACION_LABEL[clas] : undefined)}
        ${row("Calificación", cali ? CALIFICACION_LABEL[cali] : undefined)}
        ${row("Edif. (m²/m²)", edi)}
        ${row("Versión", ver ? VERSION_LABEL[ver] : undefined)}
        ${row("Fuente", fuente)}
        ${row("Fecha dato", props.fecha_dato)}
      `;
        },
        hide() {
            root.hidden = true;
            root.innerHTML = "";
        },
    };
}
