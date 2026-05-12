export function createLayerToggle(root) {
    return {
        update(pilot, state, onChange) {
            root.innerHTML = "";
            if (!pilot) {
                root.hidden = true;
                return;
            }
            root.hidden = false;
            root.innerHTML = `<h2>Capas</h2>`;
            const modes = [
                { id: "clasificacion", label: "Color por clasificación" },
                { id: "calificacion", label: "Color por calificación" },
            ];
            for (const m of modes) {
                const btn = document.createElement("button");
                btn.className = "layer-button";
                btn.textContent = m.label;
                if (state.colorMode === m.id)
                    btn.classList.add("active");
                btn.addEventListener("click", () => onChange({ ...state, colorMode: m.id }));
                root.appendChild(btn);
            }
            const sep = document.createElement("div");
            sep.style.height = "8px";
            root.appendChild(sep);
            for (const derived of pilot.derived) {
                const btn = document.createElement("button");
                btn.className = "layer-button";
                const isOn = derived.id === "sectores-dormidos" ? state.dormidos : state.reconvertible;
                btn.textContent = (isOn ? "✓ " : "○ ") + derived.label;
                if (isOn)
                    btn.classList.add("active");
                btn.addEventListener("click", () => {
                    if (derived.id === "sectores-dormidos") {
                        onChange({ ...state, dormidos: !state.dormidos });
                    }
                    else {
                        onChange({ ...state, reconvertible: !state.reconvertible });
                    }
                });
                root.appendChild(btn);
            }
        },
    };
}
