// Model and effort pickers shared by the new-mission form, Connections (defaults) and a mission's Team section.
export const MODELS = [["opus", "Opus 5.5"], ["fable", "Fable 5.2"], ["sonnet", "Sonnet 5.5"], ["haiku", "Haiku 5.5"]];
export const EFFORTS = [["low", "Low"], ["medium", "Medium"], ["high", "High"], ["xhigh", "Extra high"], ["max", "Max"]];
export const COST = { fable: "Fable: the most expensive, it uses your plan fastest", opus: "Opus: expensive, second to Fable",
  sonnet: "Sonnet: mid price, a good everyday worker", haiku: "Haiku: the cheapest, fastest, least thorough" };
export const costLine = (model) => COST[model] || "";
export const opts = (list, sel) => list.map(([v, l]) => `<option value="${v}"${v === sel ? " selected" : ""}>${l}</option>`).join("");
export const readTeam = (root) => Object.fromEntries([...root.querySelectorAll("[data-role]")].map((r) => {
  const [m, f] = r.querySelectorAll("select");
  return [r.dataset.role, { model: m.value, effort: f.value }];
}));
// one row a role: name + sub line, model select, effort select. sub is the text under the name.
export function roleRow([k, n], team, sub) {
  const t = team[k] || {};
  return `<div class="srow mx-role" data-who="${n}" data-role="${k}"><div><div class="n">${n}</div><div class="sp mono">${sub}</div></div>`
    + `<select class="hb-field" aria-label="${n} model">${opts(MODELS, t.model)}</select><select class="hb-field mx-eff" aria-label="${n} effort">${opts(EFFORTS, t.effort)}</select></div>`;
}
// after any select changes: sub(role, model) sets the line under the name, onChange(role, team entry) may save
export function wire(root, sub, onChange) {
  root.querySelectorAll("[data-role]").forEach((r) => r.querySelectorAll("select").forEach((s) => (s.onchange = () => {
    const [m, f] = r.querySelectorAll("select");
    if (sub) r.querySelector(".sp").textContent = sub(r.dataset.role, m.value);
    if (onChange) onChange(r.dataset.role, { model: m.value, effort: f.value });
  })));
}
// true while the owner has a select of the team rows focused: a repaint would reset it
export const editing = (root) => !!root && !!root.querySelector("#teamRows select:focus");
