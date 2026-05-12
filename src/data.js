const cache = new Map();
export async function loadGeoJSON(url) {
    if (cache.has(url))
        return cache.get(url);
    try {
        const res = await fetch(url);
        if (!res.ok) {
            cache.set(url, null);
            return null;
        }
        const data = (await res.json());
        cache.set(url, data);
        return data;
    }
    catch {
        cache.set(url, null);
        return null;
    }
}
export const EMPTY_FC = { type: "FeatureCollection", features: [] };
