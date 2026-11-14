// Plain-word formatting. The minus is U+2212; a sign is never dropped.
const MINUS = "−";
const sign = (v) => (v < 0 ? MINUS : "+");
const num = (v, d = 0) => Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });

export const money = (v) => `${sign(v)}$${num(v)}`;
export const pct = (v) => `${Math.round(v * 100)} %`;
export const pts = (v) => `${sign(v)}${num(v, 1)}`;
export const rr = (v) => `1:${v}`;
export const box = (stop, n) => `${stop} · #${n}`;
export const luck = (needed, tries, has) =>
  `needs ${needed} after ${tries} ${tries === 1 ? "try" : "tries"}; has ${has ?? "none"}`;
export const ago = (s) => (s < 60 ? `${Math.round(s)} s` : s < 3600 ? `${Math.floor(s / 60)} min` : s < 86400 ? `${Math.floor(s / 3600)} h` : `${Math.floor(s / 86400)} d`);

const WORDS = { queued: "Next", ready: "Next", achieved: "Reached", limit: "Not reached", out_of_reach: "Out of reach",
  stopped: "Stopped", briefing: "Brief", paused: "Paused", crashed: "Error", waiting_homebase: "Waiting for Homebase",
  waiting_plan: "Waiting for the plan", waiting_owner: "Needs you" };
export const statusWord = (m) => WORDS[m.status] || (m.round ? `Round ${m.round}` : "Next");
export const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
