// The engine's "turn" rows (one a worker turn) for the Running page: totals a role, and the newest 30.
const n = (v) => (typeof v === "number" && Number.isFinite(v) ? v : 0);
const WHY = { timeout: "ran out of time", plan: "hit the Claude plan limit; it waits, then tries again",
  "too many tool calls": "made too many tool calls" };

export const whyWords = (w) => {
  const s = !w ? "failed, no reason given" : WHY[w] || (w.startsWith("crash: ") ? `crashed: ${w.slice(7)}` : w);
  return s.length > 200 ? s.slice(0, 199) + "…" : s;
};

export function turnStats(events) {
  const rows = events.filter((e) => e.type === "turn" && e.data), by = {};
  for (const e of rows) {
    const r = (by[e.who] ||= { who: e.who, turns: 0, secs: 0, cost: 0 });
    r.turns++; r.secs += n(e.data.secs); r.cost += n(e.data.cost);
  }
  return { totals: Object.values(by), last: rows.slice(-30).reverse() };
}
