import { esc, pct, ago, hm } from "./fmt.js";
import { api } from "./net.js";
import { DOING } from "./panel.js";
import { title, sec, group, acct, mount } from "./ui.js";

const NAMES = { lead: "Lead", builder: "Builder", doubter: "Doubter", defender: "Defender" };
const MODEL = { opus: "Opus", fable: "Fable", sonnet: "Sonnet", haiku: "Haiku" };

function usageLine(u, m) {
  const f = u.five_hour && u.five_hour.used, w = u.seven_day && u.seven_day.used;
  if (f == null && w == null) return "not measured yet";
  const used = w != null && m.usage_start != null ? Math.round((w - m.usage_start) * 100) : null, of = m.limits && m.limits.usage;
  return [f != null && `5-hour ${pct(f)}`, w != null && `week ${pct(w)}`,
    used != null && `this mission used ${used}${of ? ` of ${of.pct}` : ""} points`].filter(Boolean).join(", ");
}

export default {
  on: ["step", "progress", "status"],
  render(m, el) {
    return mount(el, async () => {
      const [r, c, refused] = await Promise.all([api(`/api/missions/${m.id}/running`), api("/api/connections"), api(`/api/missions/${m.id}/refused`)]);
      const now = Date.now() / 1000, live = ["running", "waiting_homebase"].includes(m.status);
      const workers = r.workers.map((w) => {
        const doing = live && (DOING[w.state] || {})[w.role];
        return { role: w.role, doing, state: !doing ? "Ready" : /^waiting/.test(doing) ? "Waiting" : "Working",
          min: doing && w.since ? ago(now - Date.parse(w.since) / 1000) : "—" };
      });
      const busy = workers.filter((w) => w.state === "Working").length, sl = r.slots;
      const tag = (role) => MODEL[(m.team[role] || {}).model] || "";
      const team = `<div class="slist">${workers.map((w) => `<div class="srow mx-norm" data-who="${NAMES[w.role]}"><div><div class="n">${NAMES[w.role]}<span class="tag">${esc(tag(w.role))}</span></div><div class="sp mono">${esc(w.doing || "idle")}</div></div><div class="rs">${w.state}</div><div class="rp mono">${esc(w.min)}</div></div>`).join("")}`
        + `<div class="srow mx-norm" data-who="Judge"><div><div class="n">Judge<span class="tag">code</span></div><div class="sp mono">Scores every test the moment it ends</div></div><div class="rs">Ready</div><div class="rp mono">—</div></div></div>`;
      const tests = r.jobs.length ? `<div class="slist">${r.jobs.map((j) => {
        const [d, t] = j.progress || [0, 0];
        return `<div class="srow mx-norm"><div><div class="n">${esc(j.name)} · in-sample table<span class="tag">Running</span></div></div><div class="rs"><span class="tl-track"><i class="tl-done" style="width:${t ? Math.round(d / t * 100) : 0}%"></i></span></div><div class="rp mono">${j.progress ? `${d} of ${t}` : "—"}</div></div>`;
      }).join("")}</div>` : `<div class="mcap">No table is running.</div>`;
      const mac = sl.off ? "tests are switched off" : `${sl.running} of ${sl.cap} slots busy`;
      const paused = c.hunt_paused;
      const mach = group([
        acct({ nm: "This Mac", sub: sl.off ? mac : `tests run here · ${mac}`, val: sl.off ? "Off" : `${sl.running} of ${sl.cap}` }),
        acct({ nm: "Claude usage", sub: usageLine(r.usage, m) }),
        acct({ nm: "Cost and run time", val: `$${r.cost_usd.toFixed(2)} · ${hm(r.run_seconds)}` }),
        `<div class="acct tall"><span class="grow"><span class="nm">Pause the hunt loop</span><span class="sub">${paused === null ? "the steering note cannot be read" : "so it does not compete for the slots"}</span></span><button class="switch" id="huntSw" type="button" role="switch" aria-checked="${paused === true}" aria-label="Pause the hunt loop"${paused === null ? " disabled" : ""}></button></div>`]);
      const ref = refused.length ? group(refused.map((x) => acct({ nm: x.tool, sub: x.why, val: new Date(x.at).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) }))) : `<div class="mcap">Nothing refused.</div>`;
      return title(`${busy} of 4 working.`, r.jobs.length ? `${r.jobs.length} test${r.jobs.length === 1 ? "" : "s"} running on this Mac.` : "No test is running.")
        + sec("Team", team) + sec("Tests", tests) + sec("Machines", mach) + sec("Refused tool calls", ref, "Calls the team made that the Judge's door turned down.");
    }, (el) => {
      const sw = el.querySelector("#huntSw");
      if (sw) sw.onclick = async () => {
        const on = sw.getAttribute("aria-checked") !== "true";
        try { await api("/api/hunt", { method: "POST", body: { pause: on } }); sw.setAttribute("aria-checked", on); } catch (e) { alert(e.message); }
      };
    });
  },
};
