import { VERSION_LABEL } from "../schema";
export function createVersionSelector(root) {
    const buttons = new Map();
    const currentRoot = root;
    return {
        update(pilot, onSelect) {
            buttons.clear();
            currentRoot.innerHTML = "";
            if (!pilot || pilot.versions.length <= 1) {
                currentRoot.hidden = true;
                return;
            }
            currentRoot.hidden = false;
            currentRoot.innerHTML = `<h2>Versión PGOU</h2>`;
            for (const v of pilot.versions) {
                const btn = document.createElement("button");
                btn.className = "version-button";
                btn.textContent = VERSION_LABEL[v.version];
                btn.addEventListener("click", () => onSelect(v.version));
                currentRoot.appendChild(btn);
                buttons.set(v.version, btn);
                if (v.note) {
                    const note = document.createElement("div");
                    note.className = "notice";
                    note.textContent = v.note;
                    currentRoot.appendChild(note);
                }
            }
        },
        setActive(version) {
            for (const [k, btn] of buttons) {
                btn.classList.toggle("active", k === version);
            }
        },
    };
}
