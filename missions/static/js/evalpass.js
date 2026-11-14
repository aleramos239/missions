import { esc, pct, plain as num } from "./fmt.js";
import { api } from "./net.js";
import { title, sec, group, acct, mount, bestOf, shared } from "./ui.js";

const st = { id: null, rule: null, timer: null };
const key = (r) => String(r).split("@")[0].replace(/[-_]/g, "");
// the size flag in words, never blank
const size = (s) => (s && typeof s === "object" ? Object.entries(s).map(([k, v]) => `${k.replace(/_/g, " ")} ${typeof v === "object" ? JSON.stringify(v) : v}`).join(" · ") || "see the note" : s == null || s === "" ? "see the note" : String(s));
const firm = (o) => { const f = String(o.rule).split(/[-_@]/)[0]; return f.charAt(0).toUpperCase() + f.slice(1); };

const page = {
  on: ["status"],
  render(m, el) {
    clearTimeout(st.timer);
    if (st.id !== m.id) Object.assign(st, { id: m.id, rule: null });
    return mount(el, async () => {
      const name = shared.id === m.id && shared.name ? shared.name : bestOf(m), v = m.versions.find((x) => x.name === name);
      const box = shared.id === m.id && shared.name === name && shared.box != null ? shared.box : v && v.box;
      if (!v || box == null) return title("Eval pass.", "No version has a picked box yet.");
      const head = title(`Eval pass · ${v.version}${v.box_label ? " · " + v.box_label.split(" · ")[1] : ""}`, "Chance this box passes an eval within 10 trading days, on the in-sample months, with worse fills.");
      const res = await api(`/api/missions/${m.id}/odds?name=${encodeURIComponent(name)}&box=${encodeURIComponent(box)}`);
      if (res.working) {
        st.timer = setTimeout(() => { if (el.dataset.pg === "pass") page.render(m, el); }, 5000);
        return head + `<div class="mcap">Working it out (a few minutes). This page fills in by itself.</div>`;
      }
      const list = res.odds || [], skipped = (res.skipped || []).map((s) => `<div class="mcap">${esc(s.rule)}: not checked: ${esc(s.why)}</div>`).join("");
      if (!list.length) return head + `<div class="mcap">No open account to check.</div>` + skipped;
      const goalKey = m.board.goal.rule ? key(m.board.goal.rule) : null;
      let o = list.find((x) => x.rule === st.rule) || list.find((x) => goalKey && key(x.rule) === goalKey) || list[0];
      st.rule = o.rule; st.list = list;
      const firms = [...new Set(list.map(firm))], mine = list.filter((x) => firm(x) === firm(o));
      const picks = `<div class="slist"><div class="srow mx-pick"><div><div class="n">Firm</div></div><select class="hb-field" id="pFirm" aria-label="Firm">${firms.map((f) => `<option${f === firm(o) ? " selected" : ""}>${esc(f)}</option>`).join("")}</select></div>`
        + `<div class="srow mx-pick"><div><div class="n">Eval</div></div><select class="hb-field" id="pEval" aria-label="Eval">${mine.map((x) => `<option value="${esc(x.rule)}"${x === o ? " selected" : ""}>${esc(x.account)}</option>`).join("")}</select></div></div>`;
      const rows = group([
        acct({ nm: "Passes within 10 trading days", sub: "Live is worse: fills are never this kind.", val: pct(o.pass_p) }),
        acct({ nm: "Busts first", val: pct(o.bust_p) }),
        acct({ nm: "Days to pass", sub: "the middle of the passes", val: o.days_to_pass == null ? "—" : `${o.days_to_pass} days` }),
        ...(o.worst_case_pass_p != null ? [acct({ nm: "Careful pass %", sub: "this account trails the intraday high: every winner takes its low before its high", val: pct(o.worst_case_pass_p) })] : []),
        ...(o.size != null || o.caveat ? [acct({ nm: "Contract size", sub: o.caveat || "", val: size(o.size) })] : [])]);
      const rules = group([
        acct({ nm: "Risk a trade", val: `$${o.risk.toLocaleString("en-US")}` }),
        acct({ nm: "Trades counted", val: `${num(o.trades)}${o.unsized ? ` · ${o.unsized} too small to size` : ""}` }),
        ...(o.bans || []).map((b) => acct({ nm: "Banned", mark: "no", sub: b })),
        ...(o.bans && o.bans.length ? [] : [acct({ nm: "Bans", val: "none on file" })])]);
      const all = `<div class="agroup" id="pAll">${list.map((x) => `<div class="acct" role="button" tabindex="0" data-rule="${esc(x.rule)}" aria-pressed="${x === o}"><span class="nm grow">${esc(x.account)}</span><span class="kvi">${esc(pct(x.pass_p))}</span></div>`).join("")}</div>`;
      return head + `<h2 class="hb-sec-h">Check it on</h2>` + picks + sec("The odds", rows)
        + sec("The rules", rules, o.confirmed === false ? "Rules read off the firm's page, not confirmed." : "Rules read off the firm's page.")
        + skipped + sec("Every eval, this box", all, "Best first · the bold one is checked above · click another to check it · follows the box you click on the heat map.");
    }, (el) => {
      const pick = (rule) => { st.rule = rule; page.render(m, el); };
      el.querySelector("#pFirm") && (el.querySelector("#pFirm").onchange = (e) => pick((st.list.find((x) => firm(x) === e.target.value) || {}).rule));
      el.querySelector("#pEval") && (el.querySelector("#pEval").onchange = (e) => pick(e.target.value));
      const all = el.querySelector("#pAll");
      const go = (t) => { const r = t.closest("[data-rule]"); if (r) pick(r.dataset.rule); };
      if (all) { all.onclick = (e) => go(e.target); all.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(e.target); } }; }
    });
  },
};
export default page;
