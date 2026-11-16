import { statusWord, canDelete, deleteAsk } from "./fmt.js";
import { goalText } from "./panel.js";
import * as sse from "./sse.js";
import * as side from "./side.js";
import * as panel from "./panel.js";
import * as nw from "./new.js";
import * as chat from "./chat.js";
import * as mic from "./mic.js";
import { api } from "./net.js";
import { sure, tell } from "./ui.js";
import running from "./running.js";
import progress from "./progress.js";
import best from "./best.js";
import heat from "./heat.js";
import evalpass from "./evalpass.js";
import tested from "./tested.js";
import luck from "./luck.js";
import conn from "./conn.js";
import home from "./home.js";

const $ = (s, r = document) => r.querySelector(s);
const H = document.documentElement;
// S: what the page is showing. id = the open mission (null on New mission / Connections)
const S = { list: [], id: null, page: "new", m: null, events: [], open: new Set(), shut: new Set() };
const NARROW = 1000; // under this the right panel folds away so the three columns fit
let closeStream = null, timer = null, firstPaint = true;

const go = (h) => { if (location.hash === h) route(); else location.hash = h; };
const refreshList = async () => { S.list = await api("/api/missions"); paintSide(); };
const paintSide = () => side.render($("#sideMissions"), S.list, S);

function parse() {
  const p = location.hash.replace(/^#\/?/, "").split("/");
  if (p[0] === "m" && /^\d+$/.test(p[1])) return { id: +p[1], page: p[2] || "chat" };
  return { id: null, page: p[0] === "conn" || p[0] === "home" ? p[0] : "new" };
}

let seq = 0;
async function route() {
  const me = ++seq, r = parse();
  if (r.id !== S.id) {
    if (closeStream) closeStream();
    closeStream = null; S.m = null; S.events = []; S.briefKey = null;
  }
  S.id = r.id; S.page = r.page;
  if (S.id && !(S.m && S.m.id === S.id)) { // not loaded yet (or an older route's fetch was dropped): fetch it
    const id = S.id;
    let m, events;
    try {
      [m, events] = await Promise.all([api(`/api/missions/${id}`), api(`/api/missions/${id}/events`)]);
    } catch (e) { if (me === seq) { S.id = null; S.page = "new"; go("#/new"); } return; }
    if (me !== seq) return; // a newer route started: it owns the page now
    S.m = m; S.events = events;
    if (closeStream) closeStream();
    closeStream = sse.open(id, events.length ? events[events.length - 1].n : 0, onEvent);
  }
  paint();
  if (!S.id && (S.page === "conn" || S.page === "home")) show(S.page === "conn" ? conn : home, $(S.page === "conn" ? "#connBody" : "#homeBody"));
  else if (view() === "other") showPage(true);
  $(".app-main").scrollTop = 0;
}

// a new event: show it now; anything but a chat line also means the mission changed, so ask again (once a moment)
function onEvent(e) {
  if (S.events.some((x) => x.n === e.n)) return;
  S.events.push(e);
  paint(false);
  if (e.type !== "chat" || e.who === "lead" || e.who === "judge") reload(true);
  const pg = PAGE[S.page];
  if (view() === "other" && pg && pg.on.includes(e.type)) showPage();
}

// the result pages: each is { on: event types it redraws for, render(mission, el) }
const PAGE = { run: running, prog: progress, best, heat, pass: evalpass, tested, luck };
const show = (pg, el, m = null) => { el.dataset.pg = S.page; return pg.render(m, el); };
function showPage(fresh = false) {
  const pg = PAGE[S.page], el = $("#v-other");
  if (!pg || !S.m) return;
  if (fresh || el.dataset.pg !== S.page) el.innerHTML = "";
  show(pg, el, S.m);
}

// reload(true): fetch the mission and the sidebar again; reload(false): just repaint
export function reload(fetchAgain = true) {
  if (!fetchAgain) return paint(false);
  clearTimeout(timer);
  timer = setTimeout(async () => {
    if (!S.id) return;
    const id = S.id;
    try {
      const [m, list] = await Promise.all([api(`/api/missions/${id}`), api("/api/missions")]);
      if (S.id !== id) return;
      S.m = m; S.list = list;
      if (m.status === "briefing" && S.page === "chat") S.page = "chat";
      paint(false);
      if (view() === "other") showPage();
    } catch (_) { /* the next event asks again */ }
  }, 250);
}

function view() {
  if (!S.id) return S.page;
  if (S.page === "brief" || (S.page === "chat" && S.m && S.m.status === "briefing")) return "brief";
  return S.page === "chat" ? "chat" : "other";
}

function paint(scroll = true) {
  paintSide();
  if (S.id && !S.m) return; // still loading: keep what is shown
  const v = view();
  document.querySelectorAll(".view").forEach((s) => (s.hidden = s.id !== "v-" + v));
  const m = S.id && S.m;
  $("#tbTitle").textContent = m ? m.title : S.page === "conn" ? "Connections" : S.page === "home" ? "Missions" : "New mission";
  $("#tbSub").textContent = m ? `${statusWord(m)} · goal ${goalText(m.board.goal)}` : S.page === "conn" ? "Claude and the Lab" : S.page === "home" ? "Every mission" : "Nothing runs yet";
  panel.toolbar(m || null);
  const del = $("#delBtn"); del.hidden = !m || !canDelete(m); del.title = "Delete this mission";  // hidden while busy: the toolbar has no room at 800 px
  H.classList.toggle("hb-insp-off", !m || H.dataset.inspShut === "1" || window.innerWidth < NARROW);
  if (!m) { ["pMission", "pNow", "pBrief"].forEach((i) => ($("#" + i).innerHTML = "")); return; }
  panel.render(m);
  if (v === "chat") chat.renderChat(S);
  else if (v === "brief") chat.renderBrief(S, api);
  const last = v === "chat" ? null : $("#briefFeed .feed-row:last-child");
  if (last && (scroll || firstPaint)) { last.scrollIntoView({ block: "nearest" }); firstPaint = false; }
}

// the toolbar
$("#hbSideBtn").onclick = () => H.classList.toggle("hb-side-off");
$("#hbInspBtn").onclick = () => { H.dataset.inspShut = H.dataset.inspShut === "1" ? "0" : "1"; paint(false); };
$("#gearBtn").onclick = $("#labPill").onclick = () => go("#/conn");
$("#openBrief").onclick = () => go(`#/m/${S.id}/brief`);
$("#pauseBtn").onclick = async (e) => {
  try { await api(`/api/missions/${S.id}/${e.currentTarget.dataset.act}`, { method: "POST" }); } catch (x) { tell(x.message); }
  reload(true);
};
$("#delBtn").onclick = async () => {
  if (!(await sure(deleteAsk(S.id), { yes: "Delete", no: "Keep" }))) return;
  try { await api(`/api/missions/${S.id}`, { method: "DELETE" }); } catch (x) { return tell(x.message); }
  location.hash = "#/home"; location.reload();
};
$("#stopBtn").onclick = async () => {
  if (!(await sure("Stop this mission? The team writes the closest honest result and ends.", { yes: "Stop", no: "Keep running" }))) return;
  try { await api(`/api/missions/${S.id}/stop`, { method: "POST" }); } catch (x) { tell(x.message); }
  reload(true);
};

side.init($("#sideMissions"), S, go, paintSide);
nw.init({ api, go, refreshList });
chat.init({ S, api, reload });
mic.init();
window.addEventListener("hashchange", route);
window.addEventListener("resize", () => paint(false));
setInterval(() => refreshList().catch(() => {}), 15000);

refreshList().then(() => {
  if (!location.hash) location.hash = S.list.length ? `#/m/${S.list[0].id}/chat` : "#/new";
  else route();
});
