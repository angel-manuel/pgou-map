import { PILOTS } from "../registry";
export function createMunicipalitySelector(root) {
    const buttons = new Map();
    return {
        mount(onSelect) {
            root.innerHTML = `<h2>Municipio piloto</h2>`;
            for (const p of PILOTS) {
                const btn = document.createElement("button");
                btn.className = "muni-button";
                const badge = p.dataStatus === "stub"
                    ? `<span style="float:right;font-size:10px;color:#ffce5c;border:1px solid #ffce5c;padding:1px 5px;border-radius:3px">stub</span>`
                    : `<span style="float:right;font-size:10px;color:#52b3a4;border:1px solid #52b3a4;padding:1px 5px;border-radius:3px">real</span>`;
                btn.innerHTML = `${p.name}${badge}`;
                btn.title = p.dataNote ?? "";
                btn.addEventListener("click", () => onSelect(p));
                root.appendChild(btn);
                buttons.set(p.id, btn);
            }
        },
        setActive(id) {
            for (const [k, btn] of buttons) {
                btn.classList.toggle("active", k === id);
            }
        },
    };
}
