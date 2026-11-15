import { EFFORTS, opts, readTeam, roleRow } from "./team.js";
const ROLES = [["lead", "Lead", "plans each round, talks to you, writes the brief"],
  ["builder", "Builder", "writes the strategy, runs every test"],
  ["doubter", "Doubter", "hunts for luck, a different model on purpose"],
  ["defender", "Defender", "argues for what works, asks for the next run"]];
// name, key, value key, options [value, label], default, text when on, text when off
const LIMS = [
  ["Tries", "tries", "n", [10, 20, 40, 80, 160].map((n) => [n, `${n} tries`]), 40, "then it stops and reports the closest honest result", "no limit · the luck bar still rises each try, so more tries can't fake a pass"],
  ["Time", "hours", "n", [[2, "2 hours"], [4, "4 hours"], [8, "8 hours"], [24, "1 day"], [72, "3 days"], [168, "1 week"]], 8, "then it stops and reports the closest honest result", "no limit · runs until the goal is reached or you press Stop"],
  ["Claude usage", "usage", "pct", [10, 25, 40, 60, 80].map((n) => [n, `${n} % of plan`]), 40, "share of your Claude plan this mission may use, then it stops", "no limit · if your plan runs out, the team waits for it to reset, then carries on"],
];
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

const rows = () => $$("#limits [data-lim]");
const isOn = (r) => !r.classList.contains("off");
const valText = (r) => $("select", r).selectedOptions[0].textContent.replace(" of plan", " of your plan");

export function limits() {
  const on = rows().filter(isOn);
  if (!on.length) return { until_goal: true };
  return Object.fromEntries(on.map((r) => [r.dataset.lim, { [r.dataset.vk]: +$("select", r).value }]));
}
export const testMonths = () => $("#tmSel").value;

function paint() {
  rows().forEach((r) => {
    const on = isOn(r);
    $(".switch", r).setAttribute("aria-checked", on);
    $(".sp", r).textContent = r.dataset[on ? "on" : "off"];
  });
  const team = testMonths() === "team", on = rows().filter(isOn).map(valText);
  $("#tmSub").textContent = team
    ? "once a version clears every in-sample check · one read a version, never re-tuned after · the team hears held or broke, you see the numbers"
    : "the team waits for your word at that point, so it is not fully on its own";
  $("#autoSw").setAttribute("aria-checked", !on.length && team);
  $("#stopsWhen").textContent = "Stops when the goal is met and all six real-or-luck checks pass, test months included"
    + (on.length ? `, or at ${on.join(", ")}, or when you press Stop.` : ", or when you press Stop. Nothing else stops it.")
    + " Heat maps run on their own: starting the mission is your word.";
}

export async function init({ api, go, refreshList }) {
  const defaults = await api("/api/team-defaults");
  $("#allEffort").innerHTML = '<option value="">Set every role…</option>' + opts(EFFORTS);
  $("#roles").innerHTML = ROLES.map(([k, n, d]) => roleRow([k, n], defaults, d)).join("")
    + '<div class="srow mx-role" data-who="Judge"><div><div class="n">Judge</div><div class="sp mono">fixed code, the six real-or-luck checks</div></div><span class="rs">code</span><span class="rp mono">—</span></div>';
  $("#limits").innerHTML = '<div class="srow mx-lim mx-auto"><div><div class="n">Run until the goal</div><div class="sp mono">turns every limit off · never stops to ask you · Pause and Stop still work</div></div><span></span><button id="autoSw" class="switch" type="button" role="switch" aria-checked="true" aria-label="Run until the goal"></button></div>'
    + LIMS.map(([n, key, vk, list, def, on, off]) => `<div class="srow mx-lim off" data-lim="${key}" data-vk="${vk}" data-on="${on}" data-off="${off}"><div><div class="n">${n}</div><div class="sp mono"></div></div><div><select class="hb-field" aria-label="Most ${n.toLowerCase()}">${opts(list, def)}</select><div class="mx-nolim">No limit</div></div><button class="switch" type="button" role="switch" aria-checked="false" aria-label="Limit the ${n.toLowerCase()}"></button></div>`).join("")
    + '<div class="srow mx-lim" id="tmRow"><div><div class="n">Test months</div><div class="sp mono" id="tmSub"></div></div><select class="hb-field" id="tmSel" aria-label="Test months"><option value="team" selected>Team reads them</option><option value="ask">Ask me first</option></select><span></span></div>';

  $("#allEffort").onchange = (e) => {
    if (e.target.value) $$("#roles .mx-eff").forEach((s) => (s.value = e.target.value));
    e.target.value = "";
  };
  rows().forEach((r) => {
    $(".switch", r).onclick = () => { r.classList.toggle("off"); paint(); };
    $("select", r).onchange = paint;
  });
  $("#tmSel").onchange = paint;
  $("#autoSw").onclick = () => {
    const all = $("#autoSw").getAttribute("aria-checked") !== "true";
    rows().forEach((r) => r.classList.toggle("off", all));
    if (all) $("#tmSel").value = "team";
    paint();
  };
  paint();

  $("#startForm").onsubmit = async (e) => {
    e.preventDefault();
    const sentence = $("#goal").value.trim(), err = $("#newErr");
    err.hidden = true;
    if (!sentence) { err.textContent = "Say the idea and the goal first."; err.hidden = false; return; }
    const team = readTeam($("#roles"));
    try {
      const m = await api("/api/missions", { method: "POST", body: { sentence, team, limits: limits(), test_months: testMonths() } });
      $("#goal").value = "";
      await refreshList();
      go(`#/m/${m.id}/chat`);
    } catch (x) { err.textContent = x.message; err.hidden = false; }
  };
}
