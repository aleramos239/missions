import { esc, statusWord } from "./fmt.js";
import { STEP_WORD } from "./panel.js";

export const PAGES = [["chat", "Chat", "mx-ico-chat"], ["run", "Running", "mx-ico-clock"], ["prog", "Progress", "mx-ico-chart"],
  ["best", "Best so far", "mx-ico-star"], ["heat", "Heat map", "mx-ico-grid"], ["pass", "Eval pass", "mx-ico-check"],
  ["tested", "Tested", "mx-ico-hist"], ["luck", "Real or luck", "mx-ico-shield"], ["set", "Settings", "mx-ico-gear"]];
const CHEV = '<svg class="sh-chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 5.5l6.5 6.5L9 18.5"/></svg>';
const DONE = ["achieved", "limit", "out_of_reach", "stopped"];

const WORD = { running: "Running", achieved: "Goal met", limit: "Limit hit" };
const TONE = { running: "ok", achieved: "ok", crashed: "bad", paused: "warn", waiting_homebase: "warn", waiting_plan: "warn", waiting_owner: "warn" };
// line 2 of a mission row: a dot, one status word, its number, and the stage while it runs
const meta = (m) => m.needs ? `<span class="mx-dot warn"></span><b class="mx-needs-w">Needs you</b> · #${m.id}` : `<span class="mx-dot ${TONE[m.status] || ""}"></span>${esc(WORD[m.status] || statusWord(m))} · #${m.id}${m.status === "running" && m.stage && m.stage[1] > 1 ? ` · stage ${m.stage[0]} of ${m.stage[1]}` : ""}`;

// the page badges: only the open mission is loaded, the others show none
function badges(m, d) {
  if (!d || d.id !== m.id) return {};
  const b = d.right.best, tr = d.board.tries.mission;
  return { chat: m.badge || "", run: STEP_WORD[d.right.doing.step] || "", best: b ? `${b.version}${b.box ? " " + b.box.split(" · ")[1] : ""}` : "", tested: `${tr} ${tr === 1 ? "try" : "tries"}` };
}

export function render(el, list, S) {
  const shut = S.shut;
  el.innerHTML = list.map((m) => {
    const open = m.id === S.id && !shut.has(m.id) || (S.open.has(m.id)), bd = badges(m, S.m);
    const pages = m.status === "briefing" ? [PAGES[0]] : PAGES;
    const dot = DONE.includes(m.status) ? (m.status === "achieved" ? " mx-done" : " mx-miss") : "";
    return `<div class="sh${open ? "" : " shut"}${m.needs ? " mx-needs-row" : ""}" data-m="${m.id}"><button class="sh-t" type="button" aria-expanded="${open}">${CHEV}<span class="mx-mt"><b title="${esc(m.title)}">${esc(m.title)}</b><small>${meta(m)}</small></span></button></div>`
      + pages.map(([v, label, ico]) => `<button class="item one${m.id === S.id && v === S.page ? " sel" : ""}" type="button" data-m="${m.id}" data-v="${v}" aria-current="${m.id === S.id && v === S.page ? "page" : "false"}"${open ? "" : " hidden"}><i class="sd ${ico}${dot}"></i><span class="it"><b>${label}</b></span><span class="ir mono">${esc(bd[v] || "")}</span></button>`).join("");
  }).join("");
  document.querySelectorAll("#side .nav").forEach((n) => {
    const on = !S.id && S.page === n.dataset.v;
    n.classList.toggle("sel", on); n.setAttribute("aria-current", on ? "page" : "false");
  });
}

export function init(el, S, go, rerender) {
  document.getElementById("side").addEventListener("click", (e) => {
    const t = e.target.closest(".sh-t");
    if (t) {
      const id = +t.closest(".sh").dataset.m, isOpen = t.getAttribute("aria-expanded") === "true";
      if (isOpen) { S.open.delete(id); S.shut.add(id); } else { S.shut.delete(id); S.open.add(id); }
      return rerender();
    }
    const b = e.target.closest("[data-v]");
    if (b) go(b.dataset.m ? `#/m/${b.dataset.m}/${b.dataset.v}` : `#/${b.dataset.v}`);
  });
}
