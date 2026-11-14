import { esc, statusWord } from "./fmt.js";

export const PAGES = [["chat", "Chat", "mx-ico-chat"], ["run", "Running", "mx-ico-clock"], ["prog", "Progress", "mx-ico-chart"],
  ["best", "Best so far", "mx-ico-star"], ["heat", "Heat map", "mx-ico-grid"], ["pass", "Eval pass", "mx-ico-check"],
  ["tested", "Tested", "mx-ico-hist"], ["luck", "Real or luck", "mx-ico-shield"]];
const CHEV = '<svg class="sh-chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 5.5l6.5 6.5L9 18.5"/></svg>';
const DONE = ["achieved", "limit", "out_of_reach", "stopped"];

// the page badges: only the open mission is loaded, the others show none
function badges(m, d) {
  if (!d || d.id !== m.id) return {};
  const b = d.right.best, tr = d.board.tries.mission;
  return { chat: m.badge || "", run: d.right.doing.step || "", best: b ? `${b.version}${b.box ? " " + b.box.split(" · ")[1] : ""}` : "", tested: `${tr} ${tr === 1 ? "try" : "tries"}` };
}

export function render(el, list, S) {
  const shut = S.shut;
  el.innerHTML = list.map((m) => {
    const open = m.id === S.id && !shut.has(m.id) || (S.open.has(m.id)), bd = badges(m, S.m);
    const pages = m.status === "briefing" ? [PAGES[0]] : PAGES;
    const dot = DONE.includes(m.status) ? (m.status === "achieved" ? " mx-done" : " mx-miss") : "";
    return `<div class="sh${open ? "" : " shut"}" data-m="${m.id}"><button class="sh-t" type="button" aria-expanded="${open}">${CHEV}<span>${esc(m.title)}</span><i>${esc(statusWord(m))}</i></button></div>`
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
