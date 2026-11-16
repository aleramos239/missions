import { esc, money, pct, pts, statusWord } from "./fmt.js";

const NAMES = { lead: "Lead", builder: "Builder", doubter: "Doubter", defender: "Defender" };
const LIVE = ["running", "waiting_plan", "waiting_homebase"];
export const STEP_WORD = { ideas: "Ideas", build: "Build and run", wait: "Waiting", argue: "Argue", verdict: "Verdict", read: "Test months" };
const SHOW_RUN = [...LIVE, "paused", "waiting_owner"];
// who does what at each fixed step
export const DOING = { ideas: { lead: "planning the round" }, build: { builder: "building" }, wait: { builder: "waiting on a test" },
  argue: { doubter: "reading the results", defender: "arguing for it" }, verdict: { lead: "writing the verdict" },
  read: { lead: "waiting on the Judge" } };

export const goalVal = (kind, v) => v == null ? "none yet" : kind === "eval" || kind === "years" ? pct(v) : kind === "points" ? `${pts(v)} pts` : money(v);
export const goalText = (g) => g && g.kind ? (g.kind === "eval" ? `${pct(g.target)} pass` : g.kind === "years" ? `${pct(g.target)} win in ${(g.recent || []).join(", ")}, other years green` : goalVal(g.kind, g.target)) + (g.rule ? ` · ${g.rule}` : "") : "not set";
export function stopsText(l) {
  l = l || {};
  if (l.until_goal) return "the goal, or your Stop";
  const on = [l.tries && `${l.tries.n} tries`, l.hours && `${l.hours.n} h`, l.usage && `${l.usage.pct} % of plan`].filter(Boolean);
  return on.length ? `the goal, ${on.join(", ")}, or your Stop` : "the goal, or your Stop";
}
export const testMonths = (m) => m.test_months === "ask" ? "Ask me first" : m.reads ? `${m.reads} read` : "Sealed";
const fig = (k, v, who) => `<div class="f"${who ? ` data-who="${who}"` : ""}><span class="k">${k}</span><span class="v">${esc(v)}</span></div>`;

export function render(d) {
  const r = d.right, g = d.board.goal, b = r.best, t = d.pending.tries || d.board.tries;
  document.getElementById("pMission").innerHTML = fig("Goal", goalText(g))
    + fig("Best so far", b ? `${goalVal(g.kind, b.goal_value)} · ${b.version}` : "none yet") + fig("Luck bar", r.luck)
    + fig("Tries", `${t.mission}${d.limits && d.limits.tries ? ` of ${d.limits.tries.n}` : ""}`) + fig("Test months", testMonths(d));
  const live = SHOW_RUN.includes(d.status), step = (DOING[d.step] || {});
  document.getElementById("pNow").innerHTML = Object.entries(NAMES).map(([k, n]) =>
    fig(n, !live ? statusWord(d) : step[k] || "idle", n)).join("") + fig("Judge", live && d.step === "wait" ? "running the table" : "idle", "Judge");
  const br = d.brief;
  document.getElementById("pBrief").innerHTML = br ? fig("Idea", br.idea) + fig("Trades", `${br.fewest_trades_week}+ a week`)
    + fig("Stops at", stopsText(d.limits)) : fig("Brief", "Not written yet");
}

// the toolbar: title, bulb and word, chip, Pause / Resume, Stop
export function toolbar(d) {
  const run = document.getElementById("tbRun");
  run.hidden = !d || !SHOW_RUN.includes(d.status);
  if (run.hidden) return;
  const live = LIVE.includes(d.status);
  document.getElementById("tbBulb").className = "bulb " + (d.status === "running" ? "ok" : "warn");
  document.getElementById("tbWord").textContent = d.status === "running" ? "Working" : statusWord(d);
  const chip = d.step ? `${STEP_WORD[d.step] || "Working"} · round ${d.round}` : `round ${d.round}`;
  document.getElementById("tbChip").textContent = chip; document.getElementById("tbChipS").textContent = `round ${d.round}`;
  const p = document.getElementById("pauseBtn");
  p.textContent = live ? "Pause" : "Resume"; p.dataset.act = live ? "pause" : "resume";
}
