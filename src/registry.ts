import type { Version } from "./schema";

export interface DerivedLayer {
  id: "sectores-dormidos" | "reconvertible";
  file: string;
  label: string;
}

export type DataStatus = "real" | "stub";

/**
 * Selectable municipality — derived either from a manual override (currently
 * just Madrid, which has a richer fuente than the SIT-CAM WFS) or generated on
 * the fly from a SIT index entry via {@link pilotFromIndex}.
 */
export interface Municipio {
  slug: string;
  name: string;
  center: [number, number];
  zoom: number;
  dataStatus: DataStatus;
  dataNote?: string;
  versions: { version: Version; file: string; note?: string }[];
  derived: DerivedLayer[];
}

/**
 * Manual overrides: when the user picks one of these slugs, we use this entry
 * instead of generating a default from the SIT index. Madrid is the only one
 * because the Geoportal-Madrid PGOUM-97 dataset has uso pormenorizado that the
 * SIT WFS lacks.
 */
export const OVERRIDES: Record<string, Municipio> = {
  madrid: {
    slug: "madrid",
    name: "Madrid",
    center: [-3.7038, 40.4168],
    zoom: 10.5,
    dataStatus: "real",
    dataNote: "PGOUM-97 (Geoportal Madrid). 1487 ámbitos con uso pormenorizado.",
    versions: [
      { version: "vigente", file: "/data/madrid/vigente.geojson" },
      {
        version: "revision-borrador",
        file: "/data/madrid/revision.geojson",
        note: "Plan General 2020 en trámite — cartografía pública no disponible",
      },
    ],
    derived: [
      { id: "sectores-dormidos", file: "/data/madrid/sectores-dormidos.geojson", label: "Sectores dormidos" },
      { id: "reconvertible", file: "/data/madrid/reconvertible.geojson", label: "Terciario/dotacional reconvertible" },
    ],
  },
};

export const CAM_MUNICIPIOS_FILE = "/data/cam-municipios.geojson";
export const CAM_CENTER: [number, number] = [-3.65, 40.55];
export const CAM_ZOOM = 8.2;

export const CAM_INDEX_FILE = "/data/cam/index.json";

export interface CamIndexEntry {
  slug: string;
  name: string;
  cam_code: string;
  file: string;
  center: [number, number];
  bbox: [number, number, number, number];
  feature_count: number;
  documento: string | null;
}
