// Small pieces every result page shares. Every server string goes through esc before it is markup.
import { esc } from "./fmt.js";

export const title = (a, b) => `<h1 class="day-title">${esc(a)}<br><span>${esc(b)}</span></h1>`;
export const sec = (h, body, cap) => `<div class="sec"><h2>${esc(h)}</h2>${body}${cap ? `<div class="mcap">${esc(cap)}</div>` : ""}</div>`;
export const group = (rows) => `<div class="agroup">${rows.join("")}</div>`;
export const cls = (v) => (typeof v === "number" && v > 0 ? "pos" : typeof v === "number" && v < 0 ? "neg" : "");
const MARK = { ok: "Pass", no: "Fail", lock: "Sealed" };
// one row: name, optional sub line, value (green or red only for money: pass c), optional mark (ok / no / lock), optional tag
export function acct({ nm, sub, val, c = "", mark, tag, on }) {
  return `<div class="acct${sub ? " tall" : ""}">${mark ? `<span class="mx-mark ${mark}" aria-label="${MARK[mark]}"></span>` : on === undefined ? "" : `<span class="dot ${on ? "on" : "off"}"></span>`}`
    + `<span class="grow"><span class="nm">${esc(nm)}${tag ? `<span class="tag">${esc(tag)}</span>` : ""}</span>${sub ? `<span class="sub">${[].concat(sub).map(esc).join("<br>")}</span>` : ""}</span>`
    + `${val === undefined ? "" : `<span class="kvi ${c}">${esc(val)}</span>`}</div>`;
}
export const err = (e) => `<div class="mx-err">${esc(e.message || e)}</div>`;

// Paint html into el once its data is here. A newer paint of the same el wins; a failure shows its words.
export async function mount(el, build, bind) {
  const t = (el._t = (el._t || 0) + 1);
  let html;
  try { html = await build(); } catch (e) { html = err(e); bind = null; }
  if (t !== el._t) return;
  el.innerHTML = html;
  if (bind) bind(el);
}

// the box the owner last clicked on the heat map: the Eval pass page follows it
export const shared = { id: null, name: null, box: null };
export const mine = (m) => m.versions.filter((v) => v.box_label || v.state === "running");
export const bestOf = (m) => (m.versions.find((v) => v.version === m.board.best) || m.versions[m.versions.length - 1] || {}).name;

// In-page dialogs: the Mac app's web view gives window.confirm / alert no panel. Escape = the first (safe) button.
function ask(text, btns) {
  return new Promise((done) => {
    const d = document.createElement("div"); d.className = "mx-warn"; d.setAttribute("role", "dialog"); d.setAttribute("aria-modal", "true");
    d.innerHTML = `<div><p>${esc(text)}</p><div class="row">${btns.map((b, i) => `<button class="btn ${i === btns.length - 1 && btns.length > 1 ? "btn-default" : "btn-outline"} btn-sm" type="button" data-r="${btns.length > 1 ? i : 1}">${esc(b)}</button>`).join("")}</div></div>`;
    d.onclick = (e) => { const b = e.target.closest("[data-r]"); if (b) { d.remove(); done(b.dataset.r === "1"); } };
    d.onkeydown = (e) => { if (e.key === "Escape") { d.remove(); done(false); } };
    document.body.append(d); d.querySelector("button").focus();
  });
}
export const sure = (text, { yes = "OK", no = "Cancel" } = {}) => ask(text, [no, yes]);
export const tell = (text) => ask(text, ["OK"]);
