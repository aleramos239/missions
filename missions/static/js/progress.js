import { esc, pct, hm } from "./fmt.js";
import { goalVal, goalText } from "./panel.js";
import { title, sec, group, acct, mount } from "./ui.js";

// one point per version in order: its picked box's in-sample goal value, the best so far (a step), the goal (dashed)
function chart(vs, g) {
  const val = (v) => (g.kind === "eval" ? v * 100 : v);
  const top = Math.max(val(g.target), ...vs.map((v) => val(v.goal_value ?? 0)), 1) * 1.2, W = 110, H = 60;
  const X = (i) => 5 + (vs.length < 2 ? 50 : i * (W - 10) / (vs.length - 1)), Y = (v) => H - (val(v) / top) * H;
  let best = -Infinity, step = "";
  vs.forEach((v, i) => { if (v.goal_value != null) { best = Math.max(best, v.goal_value); step += `${step ? " " : ""}${X(i)},${Y(best)}`; } });
  const yl = [[top, goalVal(g.kind, g.kind === "eval" ? top / 100 : top)], [val(g.target), goalVal(g.kind, g.target)], [0, goalVal(g.kind, 0)]];
  const svg = `<line class="eq-grid" x1="0" y1="${H / 2}" x2="${W}" y2="${H / 2}"/><line class="eq-zero" x1="0" y1="${H}" x2="${W}" y2="${H}"/>`
    + `<line class="eq-line3" x1="0" y1="${Y(g.target)}" x2="${W}" y2="${Y(g.target)}"/>`
    + vs.map((v, i) => (v.goal_value == null ? "" : `<path class="mx-try" d="M${X(i)} ${Y(v.goal_value)}h0"/>`)).join("")
    + (step ? `<polyline class="eq-line" points="${step}"/>` : "");
  const ys = yl.map(([v, t]) => `<span class="eq-y" style="top:${(100 - (v / top) * 100).toFixed(1)}%">${esc(t)}</span>`).join("");
  const xs = vs.length ? [0, Math.floor((vs.length - 1) / 2), vs.length - 1].filter((v, i, a) => a.indexOf(v) === i).map((i) => `<span>${esc(vs[i].version)}</span>`).join("") : "";
  return `<div class="eq"><div class="lb"><span>${esc(g.kind === "eval" ? "Pass %" : "Goal value")} of each try's picked box</span></div>`
    + `<div class="eq-plot">${ys}<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-label="Goal value by version">${svg}</svg></div>`
    + `<div class="eq-x">${xs}</div><div class="mx-key"><span><i></i>best so far</span><span><i class="l3"></i>goal ${esc(goalText(g))}</span></div></div>`;
}

export default {
  on: ["status", "step"],
  render(m, el) {
    return mount(el, async () => {
      const b = m.board, g = b.goal, r = m.right, vs = b.versions.filter((v) => !["dropped", "spent"].includes(v.state) || v.goal_value != null);
      const scored = vs.filter((v) => v.goal_value != null).length;
      const lim = m.limits || {};
      const rows = group([
        acct({ nm: "Best so far", val: r.best ? `${goalVal(g.kind, r.best.goal_value)} · ${r.best.version}` : "none yet" }),
        acct({ nm: "Luck bar", val: r.luck }),
        acct({ nm: "Goal", val: goalText(g) }),
        acct({ nm: "Tries used", val: `${b.tries.mission}${lim.tries ? ` of ${lim.tries.n}` : ""}` }),
        acct({ nm: "Time used", val: `${hm(m.run_seconds)}${lim.hours ? ` of ${lim.hours.n} h` : ""}` })]);
      const head = r.best ? `${goalVal(g.kind, r.best.goal_value)} of ${goalVal(g.kind, g.target)}.` : "Nothing scored yet.";
      return title(head, r.best ? `Best so far: ${r.best.version}${r.best.box ? ", box " + r.best.box.split(" · ")[1] : ""}. ${scored} ${scored === 1 ? "try" : "tries"} scored.` : "The first table is still running.")
        + chart(vs, g) + `<h2 class="hb-sec-h">Where it stands</h2>` + rows
        + `<div class="mcap">A try under the luck bar could be luck from trying many versions: the bar rises with every try.</div>`;
    });
  },
};
