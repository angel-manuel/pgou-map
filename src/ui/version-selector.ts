import type { Municipio } from "../registry";
import { VERSION_LABEL, type Version } from "../schema";

export interface VersionSelector {
  update(m: Municipio | null, onSelect: (v: Version) => void): void;
  setActive(version: Version): void;
}

export function createVersionSelector(root: HTMLElement): VersionSelector {
  const buttons = new Map<string, HTMLButtonElement>();
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
