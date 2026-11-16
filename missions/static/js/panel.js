import { esc, hm, money, pct, pts, stageText, statusWord } from "./fmt.js";

const NAMES = { lead: "Lead", builder: "Builder", doubter: "Doubter", defender: "Defender" };
const LIVE = ["running", "waiting_plan", "waiting_homebase"];
export const STEP_WORD = { ideas: "Ideas", build: "Build and run", wait: "Waiting", argue: "Argue", verdict: "Verdict", read: "Test months", check: "Code check", stage: "Stage review" };
const SHOW_RUN = [...LIVE, "paused", "waiting_owner"];
// who does what at each fixed step
export const DOING = { ideas: { lead: "planning the round" }, build: { builder: "building" }, wait: { builder: "waiting on a test" },
  argue: { doubter: "reading the results", defender: "arguing for it" }, verdict: { lead: "writing the verdict" },
  read: { lead: "waiting on the Judge" }, check: { builder: "checking the code" }, stage: { lead: "reviewing the stage" } };

export const goalVal = (kind, v) => v == null ? "none yet" : kind === "eval" || kind === "years" ? pct(v) : kind === "points" ? `${pts(v)} pts` : money(v);
export const goalText = (g) => g && g.kind ? (g.kind === "eval" ? `${pct(g.target)} pass` : g.kind === "years" ? `${pct(g.target)} win in ${(g.recent || []).join(", ")}, other years green` : goalVal(g.kind, g.target)) + (g.rule ? ` · ${g.rule}` : "") : "not set";
export function stopsText(l) {
  l = l || {};
  if (l.until_goal) return "the goal, or your Stop";
  const on = [l.tries && `${l.tries.n} tries${l.stages && l.stages.n > 1 ? ` a stage, ${l.stages.n} stages` : ""}`, l.hours && `${l.hours.n} h`, l.usage && `${l.usage.pct} % of plan`].filter(Boolean);
  return on.length ? `the goal, ${on.join(", ")}, or your Stop` : "the goal, or your Stop";
}
export const testMonths = (m) => m.test_months === "ask" ? "Ask me first" : m.reads ? `${m.reads} read` : "Sealed";
const fig = (k, v, who, tip) => `<div class="f"${who ? ` data-who="${who}"` : ""}${tip ? ` title="${tip}"` : ""}><span class="k">${k}</span><span class="v">${esc(v)}</span></div>`;

export function render(d) {
  const r = d.right, g = d.board.goal, b = r.best, t = d.pending.tries || d.board.tries;
  const lim = d.limits && d.limits.usage;
  document.getElementById("pMission").innerHTML = fig("Goal", goalText(g))
    + fig("Best so far", b ? `${goalVal(g.kind, b.goal_value)} · ${b.version}` : "none yet") + fig("Luck bar", r.luck)
    + fig(d.board.stage && d.board.stage.of > 1 ? "Stage" : "Tries", d.board.stage ? stageText(d.board.stage) : `${t.mission}`) + fig("Test months", testMonths(d))
    + fig("Used", `${pct(d.usage_used || 0)}${lim ? ` of ${lim.pct} %` : ""} week · $${(d.cost_usd || 0).toFixed(2)} · ${hm(d.run_seconds)}`, null, "Share of the weekly plan used while this mission ran. Account-wide: any other Claude use at the same time counts too.");
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
  const p = document.getElementById("pauseBtn"), b = runButton(d);
  p.textContent = b.text; p.dataset.act = b.act;
}

// the run button: Pause while live, Read test months while the engine waits for the owner's yes, else Resume
export function runButton(d) {
  if (d.status === "waiting_owner" && d.pending && d.pending.read_for) return { text: "Read test months", act: "read" };
  return LIVE.includes(d.status) ? { text: "Pause", act: "pause" } : { text: "Resume", act: "resume" };
}
