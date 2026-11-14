import { esc } from "./fmt.js";
import { api } from "./net.js";
import { acct, sec, group, mount } from "./ui.js";

const row = ({ ok, nm, sub, val }) => acct({ nm, sub, val, mark: ok ? "ok" : "no" });

export default {
  on: ["status"],
  render(_m, el) {
    return mount(el, async () => {
      const c = await api("/api/connections"), h = c.health || {}, s = c.settings || {};
      document.querySelector("#labPill .hb-m-long").textContent = h.chart_service ? "Lab connected" : "Lab not answering";
      const claude = group([
        row({ ok: !!h.claude, nm: "Claude CLI", sub: s.claude ? `set path: ${s.claude}` : "found on this Mac by itself · your Claude login · no API key", val: h.claude ? `Version ${h.claude}` : "Not found" }),
        `<div class="acct tall"><span class="grow"><span class="nm">Path to claude</span><span class="sub">leave empty to find it by itself</span></span><input class="hb-field" id="cPath" value="${esc(s.claude || "")}" aria-label="Path to claude" placeholder="/path/to/claude"><button class="btn btn-outline btn-sm" id="cPathSave" type="button">Save</button></div>`]);
      const lab = group([
        row({ ok: !!h.chart_service, nm: "Homebase chart service", sub: "the Lab the team tests in · this Mac", val: h.chart_service ? "Up" : "Down" }),
        row({ ok: !!h.door, nm: "The Judge's door", sub: "fixed code that reads the Lab for the team", val: h.door ? "Up" : "Down" }),
        acct({ nm: "Desk, accounts, orders", sub: "the connector has no order tools; this app never touches an account", val: "Never" })]);
      const ntfy = group([
        `<div class="acct tall"><span class="grow"><span class="nm">ntfy topic</span><span class="sub">sends 'Mission 7: goal reached' to ntfy.sh; no numbers or names</span></span><input class="hb-field" id="cNtfy" value="${esc(s.ntfy_topic || "")}" aria-label="ntfy topic" placeholder="a topic only you know"><button class="btn btn-outline btn-sm" id="cNtfySave" type="button">Save</button></div>`]);
      return sec("Claude", claude) + sec("The Lab", lab) + sec("Alerts", ntfy, "") + `<div class="mcap">The trading server is never used. Missions runs nothing there.</div>`;
    }, (el) => {
      const save = (btn, input, key) => (el.querySelector(btn).onclick = async () => {
        try { await api("/api/connections", { method: "POST", body: { [key]: el.querySelector(input).value.trim() } }); el.querySelector(btn).textContent = "Saved"; } catch (e) { alert(e.message); }
      });
      save("#cPathSave", "#cPath", "claude");
      save("#cNtfySave", "#cNtfy", "ntfy_topic");
    });
  },
};
