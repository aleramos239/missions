import { statusWord, esc } from "./fmt.js";
import { goalText } from "./panel.js";
import * as sse from "./sse.js";
import * as side from "./side.js";
import * as panel from "./panel.js";
import * as nw from "./new.js";
import * as chat from "./chat.js";
import * as mic from "./mic.js";

const $ = (s, r = document) => r.querySelector(s);
const H = document.documentElement;
// S: what the page is showing. id = the open mission (null on New mission / Connections)
const S = { list: [], id: null, page: "new", m: null, events: [], open: new Set(), shut: new Set() };
const NARROW = 1000; // under this the right panel folds away so the three columns fit
let closeStream = null, timer = null, firstPaint = true;

export async function api(path, o = {}) {
  const r = await fetch(path, { method: o.method || "GET", headers: o.body ? { "content-type": "application/json" } : {},
    body: o.body ? JSON.stringify(o.body) : undefined });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || j.detail || `${r.status}`);
  return j;
}
const go = (h) => { if (location.hash === h) route(); else location.hash = h; };
const refreshList = async () => { S.list = await api("/api/missions"); paintSide(); };
const paintSide = () => side.render($("#sideMissions"), S.list, S);

function parse() {
  const p = location.hash.replace(/^#\/?/, "").split("/");
  if (p[0] === "m" && /^\d+$/.test(p[1])) return { id: +p[1], page: p[2] || "chat" };
  return { id: null, page: p[0] === "conn" ? "conn" : "new" };
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
  if (S.page === "conn") conn();
  $(".app-main").scrollTop = 0;
}

// a new event: show it now; anything but a chat line also means the mission changed, so ask again (once a moment)
function onEvent(e) {
  if (S.events.some((x) => x.n === e.n)) return;
  S.events.push(e);
  paint(false);
  if (e.type !== "chat" || e.who === "lead" || e.who === "judge") reload(true);
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
  $("#tbTitle").textContent = m ? m.title : S.page === "conn" ? "Connections" : "New mission";
  $("#tbSub").textContent = m ? `${statusWord(m)} · goal ${goalText(m.board.goal)}` : S.page === "conn" ? "Claude and the Lab" : "Nothing runs yet";
  panel.toolbar(m || null);
  H.classList.toggle("hb-insp-off", !m || H.dataset.inspShut === "1" || window.innerWidth < NARROW);
  if (!m) { ["pMission", "pNow", "pBrief"].forEach((i) => ($("#" + i).innerHTML = "")); return; }
  panel.render(m);
  if (v === "chat") chat.renderChat(S);
  else if (v === "brief") chat.renderBrief(S, api);
  else $("#otherTitle").innerHTML = `${(side.PAGES.find((p) => p[0] === S.page) || [, S.page])[1]}.<br><span>${esc(m.title)}</span>`;
  const last = $(v === "brief" ? "#briefFeed .feed-row:last-child" : "#feed .feed-row:last-child");
  if (last && (scroll || firstPaint)) { last.scrollIntoView({ block: "nearest" }); firstPaint = false; }
}

async function conn() {
  const rows = $("#connRows");
  try {
    const c = await api("/api/connections"), h = c.health || {};
    const row = (ok, nm, sub, val) => `<div class="acct tall"><span class="mx-mark ${ok ? "ok" : "no"}" aria-label="${ok ? "OK" : "Not working"}"></span><span class="grow"><span class="nm">${nm}</span><span class="sub">${sub}</span></span><span class="kvi">${val}</span></div>`;
    rows.innerHTML = row(!!h.claude, "Claude CLI", "on this Mac · your Claude login · no API key", h.claude ? "Found" : "Not found")
      + row(!!h.door, "The Judge's door", "fixed code that reads the Lab for the team", h.door ? "Ready" : "Missing")
      + row(!!h.chart_service, "Homebase Lab", "the tester the team uses · this Mac", h.chart_service ? "Connected" : "Not answering")
      + row(c.hunt_paused !== false, "The hunt loop", "paused while a mission runs", c.hunt_paused === null ? "Unknown" : c.hunt_paused ? "Paused" : "Running");
    $("#labPill").querySelector(".hb-m-long").textContent = h.chart_service ? "Lab connected" : "Lab not answering";
  } catch (e) { rows.innerHTML = `<div class="mx-err">${esc(e.message)}</div>`; }
}

// the toolbar
$("#hbSideBtn").onclick = () => H.classList.toggle("hb-side-off");
$("#hbInspBtn").onclick = () => { H.dataset.inspShut = H.dataset.inspShut === "1" ? "0" : "1"; paint(false); };
$("#gearBtn").onclick = $("#labPill").onclick = () => go("#/conn");
$("#openBrief").onclick = () => go(`#/m/${S.id}/brief`);
$("#pauseBtn").onclick = async (e) => {
  try { await api(`/api/missions/${S.id}/${e.currentTarget.dataset.act}`, { method: "POST" }); } catch (x) { alert(x.message); }
  reload(true);
};
$("#stopBtn").onclick = async () => {
  if (!confirm("Stop this mission? The team writes the closest honest result and ends.")) return;
  try { await api(`/api/missions/${S.id}/stop`, { method: "POST" }); } catch (x) { alert(x.message); }
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
