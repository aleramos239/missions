import { esc, money, pct, pts, rr, dec, plain } from "./fmt.js";
import { api } from "./net.js";
import { goalVal, goalText } from "./panel.js";
import { title, sec, group, acct, cls, mount, bestOf } from "./ui.js";

const usd0 = (v) => (typeof v === "number" ? `$${Math.abs(Math.round(v)).toLocaleString("en-US")}` : "—");

// the settings in RR, points and dollars
export const settings = (r) => `${rr(r.target_r)}, ${r.stop_pts}-pt stop (${r.stop}) · main setting ${r.value}`;

// By year, then combined: year, trades, full-target points over, net
export function yearRows(r) {
  const ys = (r.years || []).map(([y, n, o, net]) => acct({ nm: String(y), val: `${plain(n)} trades · ${pts(o)} · ${money(net)}`, c: cls(net) }));
  return group([...ys, acct({ nm: "All", val: `${plain(r.trades)} trades · ${pts(r.points_over)} · ${money(r.net)}`, c: cls(r.net) })]);
}

export function numRows(r) {
  return group([
    acct({ nm: "Net, in-sample months", val: money(r.net), c: cls(r.net) }),
    acct({ nm: "Full target", val: `${pct(r.win_rate)} against ${pct(r.breakeven)} needed`, sub: `${pts(r.points_over)} points over` }),
    acct({ nm: "Trades", val: `${plain(r.per_week, 1)} a week · ${plain(r.trades)} in all` }),
    acct({ nm: "Dollars a trade", val: money(r.usd_trade), c: cls(r.usd_trade) }),
    acct({ nm: "Profit factor", val: plain(r.pf, 2) }),
    acct({ nm: "Sharpe", val: dec(r.sharpe, 2) })]);
}

export function mcRows(mc) {
  if (!mc) return `<div class="mcap">No Monte Carlo yet.</div>`;
  return group([
    acct({ nm: "Worst drawdown", val: `${usd0(mc.worst_drawdown.typical)} typical · ${usd0(mc.worst_drawdown.one_in_20)} in 1 of 20` }),
    acct({ nm: "Longest losing streak", val: `${plain(mc.losing_streak.typical)} typical · ${plain(mc.losing_streak.one_in_20)} in 1 of 20 trades` }),
    acct({ nm: "Net in the 1-in-20 case", val: money(mc.net_one_in_20), c: cls(mc.net_one_in_20) }),
    acct({ nm: "Paths below $0", val: mc.below_zero_pct == null ? mc.below_zero_said || "—" : `${plain(mc.below_zero_pct, 1)} %` })]);
}
export const MC_CAP = "Luck alone: the same days drawn again 2,000 times. Shown only, never blocks.";

export default {
  on: ["status", "step"],
  render(m, el) {
    return mount(el, async () => {
      const name = bestOf(m), v = m.versions.find((x) => x.name === name), g = m.board.goal;
      if (!v || !v.box || !m.board.best) return title("No best yet.", "No version has a picked box so far.");
      const { row: r, mc } = await api(`/api/missions/${m.id}/box?name=${encodeURIComponent(v.name)}&box=${encodeURIComponent(v.box)}`);
      if (!r) return title(`${v.version} · ${v.box_label}`, "This box is not in the table.");
      const bv = m.board.versions.find((x) => x.version === v.version);
      return title(`${v.version} · ${v.box_label}`, settings(r))
        + `<p class="sd-state"><b>${esc(goalVal(g.kind, bv.goal_value))}</b> against the goal of ${esc(goalText(g))}. Full target ${esc(pct(r.win_rate))} against ${esc(pct(r.breakeven))} needed: ${esc(pts(r.points_over))} points over.</p>`
        + `<p class="sd-note">${esc(plain(r.per_week, 1))} trades a week · ${esc(money(r.usd_trade))} a trade at $1,000 risk · in-sample months only.</p>`
        + sec("The numbers", numRows(r)) + sec("Monte Carlo", mcRows(mc), MC_CAP)
        + sec("By year", yearRows(r), "Trades, points over the full-target rate, net: each year, then combined.");
    });
  },
};
