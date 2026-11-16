import { EFFORTS, opts, readTeam, roleRow } from "./team.js";
export const ROLES = [["lead", "Lead", "plans each round, talks to you, writes the brief"],
  ["builder", "Builder", "writes the strategy, runs every test"],
  ["doubter", "Doubter", "hunts for luck, a different model on purpose"],
  ["defender", "Defender", "argues for what works, asks for the next run"]];
// name, key, value key, options [value, label], default, text when on, text when off
const LIMS = [
  ["Tries a stage", "tries", "n", [10, 20, 40, 80, 160].map((n) => [n, `${n} tries`]), 20, "then the team stops, looks at everything and the Lead picks the next stage", "no limit · the luck bar still rises each try, so more tries can't fake a pass"],
  ["Stages", "stages", "n", [1, 2, 3, 5, 8].map((n) => [n, n === 1 ? "1 stage" : `${n} stages`]), 3, "after the last stage it stops and reports the closest honest result", "one stage"],
  ["Time", "hours", "n", [[2, "2 hours"], [4, "4 hours"], [8, "8 hours"], [24, "1 day"], [72, "3 days"], [168, "1 week"]], 8, "then it stops and reports the closest honest result", "no limit · runs until the goal is reached or you press Stop"],
  ["Claude usage", "usage", "pct", [10, 25, 40, 60, 80].map((n) => [n, `${n} % of plan`]), 40, "share of your Claude plan this mission may use, then it stops", "no limit · if your plan runs out, the team waits for it to reset, then carries on"],
];
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

const rows = (root) => $$("[data-lim]", root);
const isOn = (r) => !r.classList.contains("off");
const valText = (r) => $("select", r).selectedOptions[0].textContent.replace(" of plan", " of your plan");

// the auto row, one row a limit and the test-months row, filled from a mission's limits and test_months (New mission and Settings)
export function limitsHtml(lim = null, tm = "team") {
  const set = lim && !lim.until_goal ? lim : {};
  return '<div class="srow mx-lim mx-auto"><div><div class="n">Run until the goal</div><div class="sp mono">turns every limit off · never stops to ask you · Pause and Stop still work</div></div><span></span><button class="switch" data-auto type="button" role="switch" aria-checked="true" aria-label="Run until the goal"></button></div>'
    + LIMS.map(([n, key, vk, list, def, on, off]) => {
      const cur = set[key] && set[key][vk], have = cur == null || list.some(([v]) => v === cur);
      const all = have ? list : [...list, [cur, list[1][1].replace(/^\d+/, cur)]]; // a value the menu lacks keeps its own line
      return `<div class="srow mx-lim${cur == null ? " off" : ""}" data-lim="${key}" data-vk="${vk}" data-on="${on}" data-off="${off}"><div><div class="n">${n}</div><div class="sp mono"></div></div><div><select class="hb-field" aria-label="Most ${n.toLowerCase()}">${opts(all, cur ?? def)}</select><div class="mx-nolim">No limit</div></div><button class="switch" type="button" role="switch" aria-checked="false" aria-label="Limit the ${n.toLowerCase()}"></button></div>`;
    }).join("")
    + `<div class="srow mx-lim"><div><div class="n">Test months</div><div class="sp mono" data-tmsub></div></div><select class="hb-field" data-tm aria-label="Test months">${opts([["team", "Team reads them"], ["ask", "Ask me first"]], tm)}</select><span></span></div>`;
}

export function limits(root) {
  const on = rows(root).filter(isOn);
  if (!on.length) return { until_goal: true };
  return Object.fromEntries(on.map((r) => [r.dataset.lim, { [r.dataset.vk]: +$("select", r).value }]));
}
export const testMonths = (root) => $("[data-tm]", root).value;

function paint(root, stops) {
  rows(root).forEach((r) => {
    const on = isOn(r);
    $(".switch", r).setAttribute("aria-checked", on);
    $(".sp", r).textContent = r.dataset[on ? "on" : "off"];
  });
  const team = testMonths(root) === "team", on = rows(root).filter(isOn).map(valText);
  $("[data-tmsub]", root).textContent = team
    ? "once a version clears every in-sample check · one read a version, never re-tuned after · the team hears held or broke, you see the numbers"
    : "the team waits for your word at that point, so it is not fully on its own";
  $("[data-auto]", root).setAttribute("aria-checked", !on.length && team);
  if (stops) stops.textContent = "Stops when the goal is met and all six real-or-luck checks pass, test months included"
    + (on.length ? `, or at ${on.join(", ")}, or when you press Stop.` : ", or when you press Stop. Nothing else stops it.")
    + " Heat maps run on their own: starting the mission is your word.";
}

// the switches and menus of limitsHtml; change() runs after each change
export function wireLimits(root, stops, change = () => {}) {
  const again = () => { paint(root, stops); change(); };
  rows(root).forEach((r) => {
    $(".switch", r).onclick = () => { r.classList.toggle("off"); again(); };
    $("select", r).onchange = again;
  });
  $("[data-tm]", root).onchange = again;
  $("[data-auto]", root).onclick = () => {
    const all = $("[data-auto]", root).getAttribute("aria-checked") !== "true";
    rows(root).forEach((r) => r.classList.toggle("off", all));
    if (all) $("[data-tm]", root).value = "team";
    again();
  };
  paint(root, stops);
}

export async function init({ api, go, refreshList }) {
  const defaults = await api("/api/team-defaults");
  $("#allEffort").innerHTML = '<option value="">Set every role…</option>' + opts(EFFORTS);
  $("#roles").innerHTML = ROLES.map(([k, n, d]) => roleRow([k, n], defaults, d)).join("")
    + '<div class="srow mx-role" data-who="Judge"><div><div class="n">Judge</div><div class="sp mono">fixed code, the six real-or-luck checks</div></div><span class="rs">code</span><span class="rp mono">—</span></div>';
  $("#limits").innerHTML = limitsHtml();

  $("#allEffort").onchange = (e) => {
    if (e.target.value) $$("#roles .mx-eff").forEach((s) => (s.value = e.target.value));
    e.target.value = "";
  };
  wireLimits($("#limits"), $("#stopsWhen"));

  $("#startForm").onsubmit = async (e) => {
    e.preventDefault();
    const sentence = $("#goal").value.trim(), err = $("#newErr");
    err.hidden = true;
    if (!sentence) { err.textContent = "Say the idea and the goal first."; err.hidden = false; return; }
    const team = readTeam($("#roles"));
    try {
      const m = await api("/api/missions", { method: "POST", body: { sentence, team, limits: limits($("#limits")), test_months: testMonths($("#limits")) } });
      $("#goal").value = "";
      await refreshList();
      go(`#/m/${m.id}/chat`);
    } catch (x) { err.textContent = x.message; err.hidden = false; }
  };
}
