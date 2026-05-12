import type { FeatureCollection } from "geojson";

const cache = new Map<string, FeatureCollection | null>();

export async function loadGeoJSON(url: string): Promise<FeatureCollection | null> {
  if (cache.has(url)) return cache.get(url)!;
  try {
    const res = await fetch(url);
    if (!res.ok) {
      cache.set(url, null);
      return null;
    }
    const data = (await res.json()) as FeatureCollection;
    cache.set(url, data);
    return data;
  } catch {
    cache.set(url, null);
    return null;
  }
}

export const EMPTY_FC: FeatureCollection = { type: "FeatureCollection", features: [] };
