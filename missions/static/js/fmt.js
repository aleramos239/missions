// Plain-word formatting. The minus is U+2212; a sign is never dropped.
export const MINUS = "−";
const ok = (v) => typeof v === "number" && Number.isFinite(v);
const DASH = "—";
// a value that rounds to zero carries no sign; a missing or non-finite value is a dash
const sign = (v, d) => (Number(Math.abs(v).toFixed(d)) === 0 ? "" : v < 0 ? MINUS : "+");
const num = (v, d = 0) => Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });

export const money = (v) => (ok(v) ? `${sign(v, 0)}$${num(v)}` : DASH);
export const pct = (v) => (ok(v) ? `${Math.round(v * 100) || 0} %` : DASH);
export const pts = (v) => (ok(v) ? `${sign(v, 1)}${num(v, 1)}` : DASH);
export const rr = (v) => (ok(v) ? `1:${v}` : DASH);
export const box = (stop, n) => `${stop} · #${n}`;
export const luck = (needed, tries, has) =>
  `needs ${needed} after ${tries} ${tries === 1 ? "try" : "tries"}; has ${has ?? "none"}`;
export const ago = (s) => (s < 60 ? `${Math.round(s)} s` : s < 3600 ? `${Math.floor(s / 60)} min` : s < 86400 ? `${Math.floor(s / 3600)} h` : `${Math.floor(s / 86400)} d`);

const WORDS = { queued: "Next", ready: "Next", achieved: "Reached", limit: "Not reached", out_of_reach: "Out of reach",
  stopped: "Stopped", briefing: "Brief", paused: "Paused", crashed: "Error", waiting_homebase: "Waiting for Homebase",
  waiting_plan: "Waiting for the plan", waiting_owner: "Needs you" };
export const statusWord = (m) => WORDS[m.status] || (m.round ? `Round ${m.round}` : "Next");
export const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
// a signed number with d decimals (Sharpe as Homebase gives it); an hours-and-minutes length of time
export const dec = (v, d = 2) => (ok(v) ? `${sign(v, d)}${num(v, d)}` : DASH);
export const hm = (s) => (ok(s) ? (s < 3600 ? `${Math.round(s / 60)} min` : `${Math.floor(s / 3600)} h ${Math.round((s % 3600) / 60)} min`) : DASH);
