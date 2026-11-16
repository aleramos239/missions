import { api } from "./net.js";
import { goalVal } from "./panel.js";
import { title, sec, group, acct, mount } from "./ui.js";

const LIVE = ["running", "reading"];

export default {
  on: ["status", "step", "progress"],
  render(m, el) {
    return mount(el, async () => {
      const list = await api(`/api/missions/${m.id}/tested`), g = m.board.goal;
      const heard = Object.fromEntries(m.board.versions.map((v) => [v.version, v.heard]));
      const prog = Object.fromEntries(m.versions.map((v) => [v.version, v.progress]));
      const run = list.filter((v) => LIVE.includes(v.state));
      const done = list.filter((v) => !LIVE.includes(v.state)).sort((a, b) => (b.goal_value ?? -Infinity) - (a.goal_value ?? -Infinity));
      const row = (v) => {
        const h = heard[v.version], dead = ["dropped", "spent"].includes(v.state);
        const sub = v.frozen ? `Frozen: test months ${h && h.held ? "held" : "broke"}${h && h.line ? " · " + h.line : ""}${h && h.close != null ? (h.close ? ", close" : ", far") : ""}`
          : dead ? `Dropped: ${v.why || "no reason on file"}` : v.state === "reading" ? "Waiting on the test months" : "";
        return acct({ nm: `${v.version}${v.box ? " · " + v.box : ""}`, tag: v.version === m.board.best ? "Best" : "", sub, on: !dead && !v.frozen, mark: v.frozen ? "lock" : undefined,
          val: v.goal_value == null ? "—" : goalVal(g.kind, v.goal_value) });
      };
      const runRow = (v) => { const p = prog[v.version]; return acct({ nm: v.version, on: true, sub: p ? `in-sample table · box ${p[0]} of ${p[1]}` : "in-sample table", val: "—" }); };
      const cb = m.unbuilt || [];
      return title(`${list.length} ${list.length === 1 ? "try" : "tries"}.`, "Every version and its picked box. Best first.")
        + (run.length ? sec("Running", group(run.map(runRow))) : "")
        + sec("Done", done.length ? group(done.map(row)) : `<div class="mcap">Nothing finished yet.</div>`, "A hollow dot is dropped, with the reason. A lock is a version whose test months were read: never run or tuned again.")
        + (cb.length ? sec("Could not be built", group(cb.map((c) => acct({ nm: c.idea, sub: `${c.family} · round ${c.round} · ${c.why}`, val: "—" }))), "Ideas that could not be built or started; each row says why. A new block is yours to add.") : "");
    });
  },
};
