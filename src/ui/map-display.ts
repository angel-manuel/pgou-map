export interface MapDisplay {
  mount(onSoloChange: (solo: boolean) => void): void;
  setVisible(visible: boolean): void;
  setSolo(value: boolean): void;
}

export function createMapDisplay(root: HTMLElement): MapDisplay {
  let cb: HTMLInputElement | null = null;

  return {
    mount(onSoloChange) {
      root.innerHTML = `
        <h2>Visualización del mapa</h2>
        <label style="display:flex;align-items:center;gap:8px;font-size:12px;cursor:pointer">
          <input type="checkbox" id="solo-toggle" style="margin:0">
          Solo mostrar municipios seleccionados
        </label>
      `;
      cb = root.querySelector("#solo-toggle") as HTMLInputElement;
      cb.addEventListener("change", () => onSoloChange(cb!.checked));
    },
    setVisible(visible) {
      root.hidden = !visible;
    },
    setSolo(value) {
      if (cb && cb.checked !== value) cb.checked = value;
    },
  };
}
