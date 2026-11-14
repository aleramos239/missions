export async function api(path, o = {}) {
  const r = await fetch(path, { method: o.method || "GET", headers: o.body ? { "content-type": "application/json" } : {},
    body: o.body ? JSON.stringify(o.body) : undefined });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || j.detail || `${r.status}`);
  return j;
}
