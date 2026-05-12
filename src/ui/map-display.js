export function createMapDisplay(root) {
    let cb = null;
    return {
        mount(onSoloChange) {
            root.innerHTML = `
        <h2>Visualización del mapa</h2>
        <label style="display:flex;align-items:center;gap:8px;font-size:12px;cursor:pointer">
          <input type="checkbox" id="solo-toggle" style="margin:0">
          Solo mostrar municipio seleccionado
        </label>
      `;
            cb = root.querySelector("#solo-toggle");
            cb.addEventListener("change", () => onSoloChange(cb.checked));
        },
        setVisible(visible) {
            root.hidden = !visible;
        },
        setSolo(value) {
            if (cb && cb.checked !== value)
                cb.checked = value;
        },
    };
}
