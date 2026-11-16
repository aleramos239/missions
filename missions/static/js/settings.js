// A mission's Settings: test months, limits and team, changed with the owner's PATCH. The brief is shown, never edited here.
import { esc } from "./fmt.js";
import { title, mount, tell } from "./ui.js";
import { readTeam, roleRow } from "./team.js";
import { ROLES, limitsHtml, limits, testMonths, wireLimits } from "./new.js";
import { card } from "./chat.js";
import { api } from "./net.js";
import { render as panel } from "./panel.js";

// only the keys whose value differs from the mission's
export const changed = (m, next) => Object.fromEntries(Object.entries(next).filter(([k, v]) => JSON.stringify(v) !== JSON.stringify(m[k])));

let dirty = null, saved = null; // the mission with unsaved edits (a repaint would wipe them); the mission just saved

const page = {
  on: [],
  render(m, el) {
    if (dirty === m.id && el.querySelector("[data-set]")) return;
    dirty = null;
    return mount(el, async () => {
      const p = await api(`/api/missions/${m.id}/brief`);
      const wait = m.status === "waiting_owner" && m.pending && m.pending.read_for;
      return title("Settings.", "Change how this mission runs. The brief stays as it is.")
        + `<div data-set>`
        + `<h2 class="hb-sec-h">Team</h2><div class="slist" data-team>${ROLES.map(([k, n, d]) => roleRow([k, n], m.team, d)).join("")}</div>`
        + `<h2 class="hb-sec-h">Limits</h2><div class="slist" data-limits>${limitsHtml(m.limits, m.test_months)}</div>`
        + `<div class="mcap">Ask me first: the app stops and asks you before any version's test months are read. Team reads them: when a version passes every check and meets the goal, the Judge reads its test months once, without asking you.</div>`
        + (wait ? `<div class="mcap">${esc(m.pending.read_for)} is waiting for your yes now: press Read test months at the top. A change here counts from the next version.</div>` : "")
        + `<div class="mcap" data-stops></div>`
        + `<div class="mx-start-bar"><span class="grow" data-msg role="status">${saved === m.id ? "Saved" : ""}</span><button class="btn btn-default btn-sm" type="button" data-save disabled>Save</button></div></div>`
        + (p.goal ? card(m, p) : `<div class="mcap">No brief yet.</div>`);
    }, (el) => {
      const lim = el.querySelector("[data-limits]"), team = el.querySelector("[data-team]"), btn = el.querySelector("[data-save]"), msg = el.querySelector("[data-msg]");
      const next = () => changed(m, { limits: limits(lim), test_months: testMonths(lim), team: readTeam(team) });
      const edit = () => { saved = null; msg.textContent = ""; btn.disabled = !Object.keys(next()).length; dirty = btn.disabled ? null : m.id; };
      wireLimits(lim, el.querySelector("[data-stops]"), edit);
      team.querySelectorAll("select").forEach((s) => (s.onchange = edit));
      btn.onclick = async () => {
        const body = next();
        if (!Object.keys(body).length) return;
        btn.disabled = true;
        try {
          const r = await api(`/api/missions/${m.id}`, { method: "PATCH", body });
          Object.keys(body).forEach((k) => (m[k] = r[k]));
        } catch (e) { btn.disabled = false; return tell(e.message); }
        dirty = null; saved = m.id;
        panel(m); // the right panel's Test months figure
        page.render(m, el);
      };
    });
  },
};
export default page;
