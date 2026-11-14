import { esc, money, pct, pts, rr, dec, plain, MINUS } from "./fmt.js";
import { api } from "./net.js";
import { numRows, mcRows, yearRows, settings, MC_CAP } from "./best.js";
import { title, sec, mount, mine, bestOf, shared } from "./ui.js";

const TARGETS = [0.5, 0.75, 1, 1.5, 2];
const METRICS = [["net", "Net"], ["over", "Points over"], ["hit", "Full target"], ["pf", "Profit factor"], ["sh", "Sharpe"]];
const st = { id: null, name: null, value: null, k: "net", box: null }; // what the owner has picked on this page

// a dollar amount with its sign always shown; the $ sits in a span the narrow layout hides
const cash = (v) => (typeof v === "number" && Number.isFinite(v) ? `${v < 0 ? MINUS : v > 0 ? "+" : ""}<span class="mx-cur">$</span>${Math.abs(Math.round(v)).toLocaleString("en-US")}` : "—");
const show = {
  net: (r) => cash(r.net), over: (r) => esc(pts(r.points_over)), hit: (r) => esc(pct(r.win_rate)),
  pf: (r) => (plain(r.pf, 2)), sh: (r) => esc(dec(r.sharpe, 2)),
};
const at = (r) => [Math.floor((r.cell - 1) / 5), (r.cell - 1) % 5];

function grid(t, rows) {
  const nrow = t.cells / 5, pk = rows.find((r) => r.box === t.pick), pp = pk && at(pk);
  const max = Math.max(1, ...rows.map((r) => Math.abs(r.net)));
  const label = (i) => (rows.find((r) => at(r)[0] === i) || {}).stop || "";
  let h = `<thead><tr><th class="mx-rh"></th>${TARGETS.map((x) => `<th>${esc(rr(x))}</th>`).join("")}</tr></thead><tbody>`;
  for (let i = 0; i < nrow; i++) {
    h += `<tr><th class="mx-rh" scope="row">${esc(label(i))}</th>`;
    for (let j = 0; j < 5; j++) {
      const r = rows.find((x) => x.cell === i * 5 + j + 1);
      if (!r) { h += "<td></td>"; continue; }
      const near = pp && !(i === pp[0] && j === pp[1]) && Math.abs(i - pp[0]) <= 1 && Math.abs(j - pp[1]) <= 1;
      h += `<td class="${r.net > 0 ? "up" : r.net < 0 ? "dn" : ""}${r.box === t.pick ? " pk" : near ? " nb" : ""}${r.box === st.box ? " mx-sel" : ""}" style="--s:${Math.round(10 + 55 * Math.abs(r.net) / max)}%">`
        + `<button type="button" data-box="${esc(r.box)}" aria-label="Box ${r.cell}">${show[st.k](r)}<small>#${r.cell}</small></button></td>`;
    }
    h += "</tr>";
  }
  return h + "</tbody>";
}

const page = {
  on: ["status", "step"],
  render(m, el) {
    if (st.id !== m.id) Object.assign(st, { id: m.id, name: null, value: null, box: null });
    const versions = mine(m).filter((v) => v.box);
    if (!versions.some((v) => v.name === st.name)) { st.name = versions.some((v) => v.name === bestOf(m)) ? bestOf(m) : (versions[0] || {}).name; st.value = st.box = null; }
    return mount(el, async () => {
      if (!st.name) return title("Heat map.", "No version has a table yet.");
      const t = await api(`/api/missions/${m.id}/table?name=${encodeURIComponent(st.name)}`);
      const pk = t.rows.find((r) => r.box === t.pick);
      if (!t.values.includes(st.value)) st.value = pk ? pk.value : t.values[0];
      if (!t.rows.some((r) => r.box === st.box && r.value === st.value)) st.box = pk && pk.value === st.value ? pk.box : null;
      const rows = t.rows.filter((r) => r.value === st.value);
      Object.assign(shared, { id: m.id, name: st.name, box: st.box ?? t.pick });
      const avgN = rows.reduce((a, r) => a + r.net, 0) / (rows.length || 1), avgO = rows.reduce((a, r) => a + (r.points_over || 0), 0) / (rows.length || 1);
      const sel = rows.find((r) => r.box === st.box);
      let detail = "";
      if (sel) {
        const { mc } = await api(`/api/missions/${m.id}/box?name=${encodeURIComponent(st.name)}&box=${encodeURIComponent(sel.box)}`);
        detail = sec(`Box #${sel.cell}${sel.box === t.pick ? " · the pick" : ""}`, numRows(sel), `${settings(sel)} · in-sample months only · $1,000 risk a trade`)
          + sec("By year", yearRows(sel)) + sec(`Monte Carlo · box #${sel.cell}`, mcRows(mc), MC_CAP);
      }
      const seg = (list, cur, attr) => list.map(([k, l]) => `<button type="button" class="${k === cur ? "sel" : ""}" ${attr}="${esc(k)}" aria-pressed="${k === cur}">${esc(l)}</button>`).join("");
      return title(`Heat map · ${st.name}`, t.pick ? `Green boxes made money, red lost; the deeper, the more. #${pk.cell} is the pick: every box touching it makes money.` : `No box is picked: ${t.why_no_pick || "none qualifies"}.`)
        + `<div class="mx-sech"><h2 class="hb-sec-h">Stop down, target across</h2><select class="hb-field" id="hmVer" aria-label="Version">${versions.map((v) => `<option value="${esc(v.name)}"${v.name === st.name ? " selected" : ""}>${esc(v.version)} · ${esc(v.box_label)}</option>`).join("")}</select></div>`
        + (t.values.length > 1 ? `<div class="seg mx-hmseg" id="hmVal" role="group" aria-label="Main setting">${seg(t.values.map((x) => [x, `Setting ${x}`]), st.value, "data-v")}</div>` : "")
        + `<div class="seg mx-hmseg" id="hmSeg" role="group" aria-label="Number in each box">${seg(METRICS, st.k, "data-k")}</div>`
        + `<div class="mx-hmwrap"><table class="mx-hm" aria-label="Heat map, ${rows.length} boxes">${grid(t, rows)}</table></div>`
        + `<div class="mcap">Average of all ${rows.length} boxes: ${esc(money(avgN))} net, ${esc(pts(avgO))} points over · ${rows.filter((r) => r.net > 0).length} of ${rows.length} make money · judged on the average, never the best box</div>`
        + detail;
    }, (el) => {
      const again = () => page.render(m, el);
      el.querySelector("#hmVer").onchange = (e) => { st.name = e.target.value; again(); };
      const val = el.querySelector("#hmVal");
      if (val) val.onclick = (e) => { const b = e.target.closest("button"); if (b) { st.value = +b.dataset.v; st.box = null; again(); } };
      el.querySelector("#hmSeg").onclick = (e) => { const b = e.target.closest("button"); if (b) { st.k = b.dataset.k; again(); } };
      el.querySelector(".mx-hm").onclick = (e) => { const b = e.target.closest("button[data-box]"); if (b) { st.box = isNaN(b.dataset.box) ? b.dataset.box : +b.dataset.box; again(); } };
    });
  },
};
export default page;
