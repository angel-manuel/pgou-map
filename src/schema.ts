export const CLASIFICACION = [
  "urbano-consolidado",
  "urbano-no-consolidado",
  "urbanizable-sectorizado",
  "urbanizable-no-sectorizado",
  "no-urbanizable-comun",
  "no-urbanizable-protegido",
] as const;
export type Clasificacion = (typeof CLASIFICACION)[number];

export const CALIFICACION = [
  "residencial",
  "terciario",
  "industrial",
  "dotacional-publico",
  "dotacional-privado",
  "espacio-libre",
  "equipamiento",
  "mixto",
  "sin-asignar",
] as const;
export type Calificacion = (typeof CALIFICACION)[number];

export const VERSION = [
  "vigente",
  "revision-borrador",
  "revision-aprobacion-inicial",
  "revision-aprobacion-provisional",
] as const;
export type Version = (typeof VERSION)[number];

export interface ZonaProperties {
  municipio: string;
  ambito?: string;
  clasificacion: Clasificacion;
  calificacion: Calificacion;
  edificabilidad_m2_m2?: number;
  version: Version;
  fuente: string;
  fecha_dato: string;
}

export const CLASIFICACION_COLOR: Record<Clasificacion, string> = {
  "urbano-consolidado": "#588157",
  "urbano-no-consolidado": "#a3b18a",
  "urbanizable-sectorizado": "#e8df9d",
  "urbanizable-no-sectorizado": "#d4c66a",
  "no-urbanizable-comun": "#e0a07a",
  "no-urbanizable-protegido": "#c97b63",
};

export const CALIFICACION_COLOR: Record<Calificacion, string> = {
  residencial: "#c97b63",
  terciario: "#6ea8fe",
  industrial: "#9b5cb0",
  "dotacional-publico": "#52b3a4",
  "dotacional-privado": "#7fc1b8",
  "espacio-libre": "#a3b18a",
  equipamiento: "#e0a07a",
  mixto: "#d4c66a",
  "sin-asignar": "#666c78",
};

export const CLASIFICACION_LABEL: Record<Clasificacion, string> = {
  "urbano-consolidado": "Urbano consolidado",
  "urbano-no-consolidado": "Urbano no consolidado",
  "urbanizable-sectorizado": "Urbanizable sectorizado",
  "urbanizable-no-sectorizado": "Urbanizable no sectorizado",
  "no-urbanizable-comun": "No urbanizable común",
  "no-urbanizable-protegido": "No urbanizable protegido",
};

export const CALIFICACION_LABEL: Record<Calificacion, string> = {
  residencial: "Residencial",
  terciario: "Terciario",
  industrial: "Industrial",
  "dotacional-publico": "Dotacional público",
  "dotacional-privado": "Dotacional privado",
  "espacio-libre": "Espacio libre",
  equipamiento: "Equipamiento",
  mixto: "Mixto",
  "sin-asignar": "Sin asignar",
};

export const VERSION_LABEL: Record<Version, string> = {
  vigente: "Vigente",
  "revision-borrador": "Revisión (borrador)",
  "revision-aprobacion-inicial": "Revisión (aprobación inicial)",
  "revision-aprobacion-provisional": "Revisión (aprobación provisional)",
};
