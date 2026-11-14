import { esc, money, pct, pts, plain, luck as luckWords } from "./fmt.js";
import { api } from "./net.js";
import { title, sec, group, acct, cls, mount, bestOf } from "./ui.js";

const st = { id: null, name: null };
const LABEL = { boxes: "60 % of the boxes make money", trades: "200+ in-sample trades", luck: "Beats the luck bar",
  years: "4 of 6 years green, no year over half", "worse fills": "Still makes money with worse fills", "test months": "Test months, same direction" };
const T = /^\s*t\s+(-?\d+(?:\.\d+)?)/;
const MARK = (ok) => (ok === true ? "ok" : ok === false ? "no" : "lock");

// the Doubter's and Defender's words about one charge of one version, from the saved chat
function words(events, version, charge) {
  const pre = `${version} · ${charge}:`;
  return ["doubter", "defender"].map((who) => {
    const e = events.filter((x) => x.who === who && typeof x.text === "string" && x.text.startsWith(pre)).pop();
    return e ? `${who === "doubter" ? "Doubter" : "Defender"}: ${e.text.slice(pre.length).trim()}` : null;
  }).filter(Boolean);
}

const page = {
  on: ["chat", "status"],
  render(m, el) {
    if (st.id !== m.id) Object.assign(st, { id: m.id, name: null });
    const vs = m.versions.filter((v) => v.gate);
    if (!vs.some((v) => v.name === st.name)) st.name = (vs.find((v) => v.heard) || vs.find((v) => v.name === bestOf(m)) || vs[0] || {}).name;
    return mount(el, async () => {
      if (!st.name) return title("Real or luck.", "No version has been checked yet.");
      const v = m.versions.find((x) => x.name === st.name);
      const [d, events] = await Promise.all([api(`/api/missions/${m.id}/luck?name=${encodeURIComponent(st.name)}`), api(`/api/missions/${m.id}/events`)]);
      const lines = (d.gate && d.gate.lines) || [], tr = d.tries || m.board.tries, h = d.heard, y = d.yours;
      const lk = lines.find((x) => x.line === "luck"), t = lk && T.exec(String(lk.said || ""));
      const six = [...lines.filter((x) => x.line !== "test months"), { line: "test months", ok: h ? !!h.held : null, said: h ? (h.held ? "held" : "broke") : "sealed" }];
      const ok = six.filter((x) => x.ok === true).length, no = six.filter((x) => x.ok === false).length, sealed = six.length - ok - no;
      let ins = null;
      if (y && y.box != null) { try { ins = (await api(`/api/missions/${m.id}/box?name=${encodeURIComponent(st.name)}&box=${encodeURIComponent(y.box)}`)).row; } catch (_) { /* the in-sample number is a nicety */ } }
      const months = Array.isArray(y && y.blocks) ? y.blocks : null;
      const six_ = group(six.map((x) => acct({ nm: LABEL[x.line] || x.line, mark: MARK(x.ok), sub: x.line === "test months" && !h ? "" : x.said, val: x.line === "test months" && !h ? "sealed" : undefined })));
      const heard = h ? group([
        acct({ nm: "Test months", mark: h.held ? "ok" : "no", val: h.held ? "Held" : "Broke" }),
        ...(h.held ? [] : [acct({ nm: "Which line", mark: "no", val: h.line || "—" }), acct({ nm: "How far", mark: "no", val: h.close == null ? "—" : h.close ? "Close" : "Far" })]),
        acct({ nm: v.version, mark: "lock", val: "Frozen · never run or tuned again" })]) : `<div class="mcap">Not read yet.</div>`;
      const yours = y && y.trades != null ? group([
        acct({ nm: "Net, test months", val: money(y.net), c: cls(y.net) }),
        acct({ nm: "Trades", val: `${plain(y.trades)}${months ? ` · ${months.length} months` : ""}` }),
        acct({ nm: "Hit the full target", val: ins && ins.breakeven != null ? `${pct(y.win_rate)} against ${pct(ins.breakeven)} needed` : pct(y.win_rate) }),
        acct({ nm: "Points over", val: `${pts(y.points_over)}${ins ? ` · in-sample ${pts(ins.points_over)}` : ""}` }),
        ...(months ? [acct({ nm: "Months that made money", val: `${months.filter((b) => b.net > 0).length} of ${months.length}` })] : [])]) : `<div class="mcap">Nothing to show: the test months were not read.</div>`;
      const charges = (d.gate && d.gate.charges || []).map((c) => acct({ nm: c.charge, sub: [`Judge: ${c.why}`, ...words(events, v.version, c.charge)], val: c.held ? "Stands" : "Broke", mark: c.held ? "ok" : "no" }));
      const pick = `<div class="mx-sech"><h2 class="hb-sec-h">Version</h2><select class="hb-field" id="lkVer" aria-label="Version">${vs.map((x) => `<option value="${esc(x.name)}"${x.name === st.name ? " selected" : ""}>${esc(x.version)} · ${esc(x.box_label || "")}</option>`).join("")}</select></div>`;
      return title(`${ok} pass, ${no} fail, ${sealed} sealed.`, `${v.version}, box ${(v.box_label || "").split(" · ")[1] || "—"}. All six must pass before it counts.`)
        + pick + sec("The six checks", six_, "Sealed until a version passes the first five. Then one read, never re-tuned after.")
        + `<div class="mcap">${esc(luckWords(tr.needed_t, tr.mission, t ? +t[1] : null))}</div>`
        + sec(`What the team heard · ${v.version}'s test months`, heard, "All the Judge tells the workers: held or broke, which line, close or far. No dollars, %, months or trades.")
        + sec(`What you see · ${v.version}'s test months`, yours, "Only on your screen: the workers cannot open these numbers.")
        + sec("The five charges", group(charges), "Judge's result first, then the Doubter's and the Defender's words.");
    }, (el) => { el.querySelector("#lkVer").onchange = (e) => { st.name = e.target.value; page.render(m, el); }; });
  },
};
export default page;
