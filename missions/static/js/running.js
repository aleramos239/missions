import { esc, pct, ago, hm, plain } from "./fmt.js";
import { api } from "./net.js";
import { DOING } from "./panel.js";
import { editing, readTeam, roleRow, wire } from "./team.js";
import { turnStats, whyWords } from "./turns.js";
import { title, sec, group, acct, mount, tell } from "./ui.js";

const NAMES = { lead: "Lead", builder: "Builder", doubter: "Doubter", defender: "Defender" };

function usageLine(u, m) {
  const f = u.five_hour && u.five_hour.used, w = u.seven_day && u.seven_day.used;
  if (f == null && w == null) return "not measured yet";
  const used = w != null && m.usage_start != null ? Math.round((w - m.usage_start) * 100) : null, of = m.limits && m.limits.usage;
  return [f != null && `5-hour ${pct(f)}`, w != null && `week ${pct(w)}`,
    used != null && `this mission used ${used}${of ? ` of ${of.pct}` : ""} points`].filter(Boolean).join(", ");
}

export default {
  on: ["step", "progress", "status", "turn"],
  render(m, el) {
    if (editing(el)) return;  // a repaint would reset the select the owner has open
    return mount(el, async () => {
      const [r, c, refused, events] = await Promise.all([api(`/api/missions/${m.id}/running`), api("/api/connections"), api(`/api/missions/${m.id}/refused`), api(`/api/missions/${m.id}/events`)]);
      const all = await api("/api/missions").catch(() => []);
      const now = Date.now() / 1000, live = ["running", "waiting_homebase"].includes(m.status);
      const workers = r.workers.map((w) => {
        const doing = live && (DOING[w.state] || {})[w.role];
        return { role: w.role, doing, state: !doing ? "Ready" : /^waiting/.test(doing) ? "Waiting" : "Working",
          min: doing && w.since ? ago(now - Date.parse(w.since) / 1000) : "—" };
      });
      const busy = workers.filter((w) => w.state === "Working").length, sl = r.slots;
      const team = `<div class="slist" id="teamRows">${workers.map((w) => roleRow([w.role, NAMES[w.role]], m.team, esc(`${w.state}${w.min !== "—" ? ` ${w.min}` : ""} · ${w.doing || "idle"}`))).join("")}`
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
      const num = (v) => (typeof v === "number" ? v : 0), sum = (k) => all.reduce((a, x) => a + num(x[k]), 0);
      const usage = all.length ? group([...all].sort((a, b) => b.id - a.id).map((x) => acct({ nm: `${x.title} #${x.id}`, sub: String(x.status).replace(/_/g, " "),
        val: `${typeof x.usage_used === "number" ? pct(x.usage_used) : "—"} wk · $${num(x.cost_usd).toFixed(2)} · ${hm(num(x.run_seconds))}` }))
        .concat(acct({ nm: "Total", val: `${pct(sum("usage_used"))} wk · $${sum("cost_usd").toFixed(2)} · ${hm(sum("run_seconds"))}` }))) : `<div class="mcap">No missions yet.</div>`;
      const ts = turnStats(events), who = (w) => NAMES[w] || String(w), usd = (v) => `$${plain(v, 2)}`;
      const turns = ts.last.length ? group(ts.totals.map((x) => acct({ nm: who(x.who), val: `${x.turns} ${x.turns === 1 ? "turn" : "turns"} · ${hm(x.secs)} · ${usd(x.cost)}` }))
        .concat(ts.last.map((e) => {
          const d = e.data, tools = Array.isArray(d.tools) ? d.tools : [];
          return acct({ nm: `${who(e.who)} · ${e.text}`, mark: d.ok === false ? "no" : undefined, val: `${ago(d.secs || 0)} · ${usd(d.cost)}`,
            sub: [`${new Date(e.at).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })} · ${tools.length} tool ${tools.length === 1 ? "call" : "calls"}`]
              .concat(d.ok === false ? [whyWords(d.why)] : []) })
            .replace('<div class="acct', `<div title="${esc(tools.join(", ") || "no tool calls")}" class="acct`);
        }))) : `<div class="mcap">No turn yet.</div>`;
      return title(`${busy} of 4 working.`, r.jobs.length ? `${r.jobs.length} test${r.jobs.length === 1 ? "" : "s"} running on this Mac.` : "No test is running.")
        + sec("Team", team) + sec("Tests", tests) + sec("Turns", turns, "Each role's totals, then the last 30 turns, newest first. Hold the pointer on a turn for its tool calls.") + sec("Machines", mach) + sec("Usage", usage, "Week share is the part of the Claude week each mission used.") + sec("Refused tool calls", ref, "Calls the team made that the Judge's door turned down.");
    }, (el) => {
      const rows = el.querySelector("#teamRows");
      if (rows) wire(rows, null, async () => {  // the whole team goes back; the engine reads it before its next turn
        try { m.team = await api(`/api/missions/${m.id}`, { method: "PATCH", body: { team: readTeam(rows) } }).then((x) => x.team); } catch (e) { tell(e.message); }
      });
      const sw = el.querySelector("#huntSw");
      if (sw) sw.onclick = async () => {
        const on = sw.getAttribute("aria-checked") !== "true";
        try { await api("/api/hunt", { method: "POST", body: { pause: on } }); sw.setAttribute("aria-checked", on); } catch (e) { tell(e.message); }
      };
    });
  },
};
