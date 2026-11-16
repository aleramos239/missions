import { esc } from "./fmt.js";
import { md } from "./md.js";
import { sure, tell } from "./ui.js";
import { goalText, goalVal, stopsText, testMonths } from "./panel.js";

const $ = (s, r = document) => r.querySelector(s);
const WHO = { owner: "You", engine: "Tests", lead: "Lead", builder: "Builder", doubter: "Doubter", defender: "Defender", judge: "Judge" };
const cap = (s) => (s ? s[0].toUpperCase() + s.slice(1) : "");
const clock = (at) => new Date(at).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
// the fixed steps on the line: Brief, Ideas, Build and run, Argue, Verdict, Test months
const STEP_AT = { ideas: 1, build: 2, wait: 2, check: 2, stage: 1, argue: 3, verdict: 4, read: 5 };
const LABELS = ["Brief", "Ideas", "Build and run", "Argue", "Verdict", "Test months"];
const APPROVE = "Yes, start: the team may run heat maps, pick boxes by the score and read test months through the Judge";
const APPROVE_ASK = "Yes, start: the team may run heat maps and pick boxes by the score; it asks me before the test months";

const when = (at) => new Date(at).toLocaleString("en-US", { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
const opened = new Set();  // the talk rows the owner opened
const folds = new Set();   // the "The team worked" rows he opened (keyed by their first message)
const more = new Set();    // the long messages he opened with "Show more"

function row(e, m) {
  const who = WHO[e.who] || cap(String(e.who || "?"));
  const tag = e.who === "judge" ? "code" : e.who === "owner" ? (e.to ? `to ${cap(String(e.to))}` : "to everyone") : m.team[e.who] ? cap(String(m.team[e.who].model)) : "";
  const t = `<span class="t" title="${esc(when(e.at))}">${clock(e.at)}</span>`;
  const line = e.data && typeof e.data.line === "string" ? `<div class="raw">${esc(e.data.line)}</div>` : "";
  if (e.type === "talk")  // a worker's working notes: two lines, a click opens the rest (kept open across repaints)
    return `<div class="feed-row talk" data-who="${esc(who)}" data-n="${e.n}"><div class="h"><b>${esc(who)}</b><span class="tag">notes</span>${t}<details${opened.has(e.n) ? " open" : ""}><summary>${esc(e.text)}</summary></details></div></div>`;
  const body = `<div class="md${more.has(e.n) ? " more" : ""}">${md(e.text)}</div>`;
  if (who === "You")  // his own turn: a soft bubble on the right
    return `<div class="feed-row you" data-who="You" data-n="${e.n}"><div class="h"><div class="meta">${esc(tag)} · ${t}</div>${body}</div></div>`;
  return `<div class="feed-row" data-who="${esc(who)}" data-n="${e.n}"><div class="h"><b>${esc(who)}</b>${tag ? `<span class="tag">${esc(tag)}</span>` : ""}${t}${body}</div>${line}</div>`;
}
const chatOnly = (events) => events.filter((e) => e.type === "chat" && e.text);
const shown = (events) => events.filter((e) => (e.type === "chat" || e.type === "talk") && e.text);
const JUDGE_NOISE = /\bis dropped\b|\bnot started\b/;

// "For you": his own texts; what is written to him (data.to_owner, a brief question); a worker's answer to his text
// (a chat after that worker's "owner" turn); the Judge's reads (not its dropped / not-started lines); the engine's
// lines kept from the workers (stage over, errors, Homebase down). The rest is the team at work.
export function mine(events) {
  const keep = new Set(), step = {};
  for (const e of events) {
    if (e.type === "turn") { step[e.who] = e.text; continue; }
    if (e.type !== "chat" || !e.text) continue;
    const d = e.data || {};
    if (e.who === "owner" || d.to_owner || d.ask || step[e.who] === "owner"
        || (e.who === "judge" && !JUDGE_NOISE.test(e.text)) || (e.who === "engine" && e.for_workers === false)) keep.add(e.n);
    if (e.who in step) step[e.who] = null;  // one answer per "owner" turn
  }
  return keep;
}

const plural = (n) => `${n} ${n === 1 ? "message" : "messages"}`;
function feed(el, events, m, view = "") {
  const rows = shown(events);
  if (view !== "mine") {
    el.innerHTML = rows.filter((e) => !view || (WHO[e.who] || cap(String(e.who))) === view).map((e) => row(e, m)).join("");
    return clampLong(el);
  }
  const keep = mine(events);
  let html = "", run = [];
  const flush = () => {
    if (run.length) html += `<details class="mx-fold" data-fold="${run[0].n}"${folds.has(run[0].n) ? " open" : ""}><summary>The team worked · ${plural(run.length)}</summary><div class="mx-fold-in">${run.map((e) => row(e, m)).join("")}</div></details>`;
    run = [];
  };
  for (const e of rows) {
    if (keep.has(e.n)) { flush(); html += row(e, m); }
    else if (!(e.type === "talk" && e.text.trim().length < 60)) run.push(e);  // a throwaway note is left out
  }
  flush();
  el.innerHTML = html;
  clampLong(el);
}

// a message taller than the clamp gets a fade and "Show more" (only visible ones can be measured; a fold measures on open)
function clampLong(root) {
  root.querySelectorAll(".md:not(.more):not([data-c])").forEach((b) => {
    if (!b.offsetParent) return;
    b.dataset.c = "1";
    if (b.scrollHeight <= b.clientHeight + 2) return;
    b.classList.add("clamped");
    b.insertAdjacentHTML("afterend", `<button class="mx-more" type="button">Show more</button>`);
  });
}

export function renderChat(S) {
  const m = S.m, r = m.right, g = m.board.goal, b = r.best, t = m.board.tries.mission;
  $("#chatTitle").textContent = b ? `Best so far ${goalVal(g.kind, b.goal_value)}. Goal ${goalVal(g.kind, g.target)}.` : `Goal ${goalVal(g.kind, g.target)}. Nothing has scored yet.`;
  $("#chatSentence").textContent = m.sentence || "";
  const at = STEP_AT[m.step] ?? 0, done = (at / 5) * 100;
  $("#chatCap").textContent = `${m.round ? `Round ${m.round} · ${LABELS[at]} · ` : ""}Test months ${testMonths(m).toLowerCase()} · ${t} ${t === 1 ? "try" : "tries"}`;
  $("#stepRound").textContent = `Round ${m.round}`;
  $("#stepSince").textContent = "";
  const h = Math.floor(m.run_seconds / 3600), mi = Math.floor(m.run_seconds / 60) % 60;
  $("#elapsed").textContent = `${h} h ${mi} m`;
  $("#tlDone").style.width = done + "%"; $("#tlNow").style.left = done + "%";
  $("#tlLabels").innerHTML = LABELS.map((l, i) => `<span class="tl-t${i === 0 ? " at-start" : i === 5 ? " at-end" : ""}${i === at ? " strong" : ""}" style="left:${i * 20}%">${l}</span>`).join("");
  const box = $("#chatBox"), atEnd = !box.dataset.on || nearEnd(box);
  feed($("#feed"), S.events, m, $("#who").value);
  if (!box.dataset.on) { box.dataset.on = "1"; initBox(box); }
  const grew = S.events.length > (box._n ?? S.events.length); box._n = S.events.length;  // a repaint alone is not news
  if (atEnd) { box.scrollTop = box.scrollHeight; $("#newMsg").hidden = true; } else if (grew) $("#newMsg").hidden = false;
}

const nearEnd = (b) => b.scrollHeight - b.scrollTop - b.clientHeight < 40;
// his own height, as "v2:<px>": an older plain number was saved by any click in the box, not a drag, so it is ignored
const HKEY = "missions.chatH";
function initBox(box) {
  const v = localStorage.getItem(HKEY) || "", h = v.startsWith("v2:") ? parseInt(v.slice(3), 10) : NaN;
  if (h >= 240) box.style.height = h + "px";
  let h0 = 0;  // saved only when a drag changed the height
  box.addEventListener("mousedown", () => (h0 = box.offsetHeight));
  const save = () => { if (box.offsetHeight >= 240 && h0 && box.offsetHeight !== h0) { box.style.height = box.offsetHeight + "px"; localStorage.setItem(HKEY, "v2:" + box.offsetHeight); } };
  box.addEventListener("mouseup", save); box.addEventListener("touchend", save);
  box.addEventListener("scroll", () => { if (nearEnd(box)) $("#newMsg").hidden = true; });
  $("#newMsg").onclick = () => { box.scrollTop = box.scrollHeight; $("#newMsg").hidden = true; };
}

// the Lead's open question: the last ask with no owner answer after it
function openAsk(events) {
  const rows = chatOnly(events);
  for (let i = rows.length - 1; i >= 0; i--) {
    if (rows[i].who === "owner") return null;
    if (rows[i].data && rows[i].data.ask) return rows[i];
  }
  return null;
}

export function card(m, p) {
  const b = p, g = b.goal, acct = b.account;
  const list = (xs) => (xs || []).map(esc).join(" · ") || "—";
  const r = (k, v) => `<div class="acct"><span class="nm grow">${k}</span><span class="kvi">${v}</span></div>`;
  return `<h2 class="hb-sec-h">The brief</h2><div class="mx-brief">`
    + r("Goal", esc(goalText(g))) + r("Exits", esc(b.exits || "hm40")) + r("Idea", esc(b.idea)) + r("Fixed", list(b.fixed)) + r("The team may change", list(b.may_change))
    + r("Fewest trades a week", esc(b.fewest_trades_week)) + r("Account", esc(acct ? acct.name || acct.id : "—"))
    + r("The firm bans", list(b.bans)) + r("Stops at", esc(stopsText(m.limits))) + r("Test months", esc(testMonths(m)))
    + (b.notes ? r("Notes", esc(b.notes)) : "")
    + `</div><div class="mcap">Rules read off the firm's page, not confirmed.</div>`;
}

export async function renderBrief(S, api) {
  const m = S.m, el = $("#briefFeed"), asking = m.status === "briefing";
  feed(el, S.events, m);
  const ask = asking ? openAsk(S.events) : null;
  if (ask) {
    const q = document.createElement("div"); q.className = "mx-q";
    ask.data.ask.options.forEach((o) => {
      const b = document.createElement("button"); b.type = "button"; b.className = "btn btn-quiet btn-sm"; b.textContent = o; b.dataset.reply = o; q.append(b);
    });
    el.querySelector(`[data-n="${ask.n}"] .h`).append(q);
  }
  $("#v-brief .day-title").innerHTML = asking ? "New mission.<br><span>The lead is writing the brief with you. Nothing runs yet.</span>" : `The brief.<br><span>${esc(m.title)}</span>`;
  const card_ = $("#briefCard");
  card_.hidden = !m.brief;
  $("#briefCompose").hidden = !asking;
  $("#briefCap").textContent = !asking ? "The brief the team works from" : m.brief ? "Brief ready · waiting for your go" : ask ? "The lead asks · answer below or tap a reply" : "The lead is working · nothing runs yet";
  if (m.brief) {
    const key = m.id + JSON.stringify(m.brief);
    if (S.briefKey !== key) { S.briefKey = key; S.briefPage = await api(`/api/missions/${m.id}/brief`); }
    if (S.m !== m) return; // the page moved on while this loaded
    card_.innerHTML = card(m, S.briefPage) + (asking ? `<div class="foot"><button class="btn btn-default btn-sm" type="button" id="approveBtn">${m.test_months === "ask" ? APPROVE_ASK : APPROVE}</button></div>` : "");
  }
}

// "Needs you": the one question the owner must answer now (m.needs from the server), with its answer right there
export function renderNeeds(m) {
  const el = $("#needsBar"), n = m && m.needs;
  el.hidden = !n;
  if (!n) return (el.innerHTML = "");
  const key = JSON.stringify(n);
  if (el.dataset.key === key) return; // unchanged: keep the buttons (and a click in flight) as they are
  el.dataset.key = key;
  el.innerHTML = `<b>Needs you:</b> <span>${esc(n.q)}</span><div class="mx-q">${n.options.map((o) => `<button class="btn btn-default btn-sm" type="button" data-${n.kind === "read" ? "read" : "reply"}="${esc(o)}">${esc(o)}</button>`).join("")}</div>`;
}

export function init({ S, api, reload }) {
  $("#who").onchange = () => { renderChat(S); $("#chatBox").scrollTop = $("#chatBox").scrollHeight; };
  $("#briefToggle").onclick = (e) => {
    const open = $("#chatMore").hidden; $("#chatMore").hidden = !open;
    e.currentTarget.setAttribute("aria-expanded", String(open)); e.currentTarget.textContent = open ? "Hide the brief" : "Show the brief";
  };
  const toggled = (e) => {  // toggle does not bubble: caught on the way down
    const f = e.target.dataset.fold;
    if (f) { if (e.target.open) { folds.add(Number(f)); clampLong(e.target); } else folds.delete(Number(f)); return; }
    const n = Number(e.target.closest("[data-n]").dataset.n);
    if (e.target.open) opened.add(n); else opened.delete(n);
  };
  const showMore = (e) => {
    const b = e.target.closest(".mx-more"); if (!b) return;
    const body = b.previousElementSibling; more.add(Number(b.closest("[data-n]").dataset.n));
    body.classList.add("more"); body.classList.remove("clamped"); b.remove();
  };
  for (const id of ["#feed", "#briefFeed"]) { $(id).addEventListener("toggle", toggled, true); $(id).addEventListener("click", showMore); }
  const say = async (to, text, sure) => {
    const out = await api(`/api/missions/${S.id}/chat`, { method: "POST", body: { to, text, ...(sure ? { sure: true } : {}) } });
    if (out.warn) return (await sure(out.warn, { yes: "Send anyway", no: "Don't send" })) ? say(to, text, true) : false;
    if (out.n && !S.events.some((e) => e.n === out.n)) { S.events.push(out); reload(false); }
    return true;
  };
  $("#compose").onsubmit = async (e) => {
    e.preventDefault();
    const text = $("#msg").value.trim(); if (!text) return;
    try { if (await say($("#to").value, text)) $("#msg").value = ""; } catch (x) { tell(x.message); }
  };
  const answer = async (text) => {
    const err = $("#briefErr"); err.hidden = true;
    document.querySelectorAll("#briefFeed .mx-q button").forEach((b) => (b.disabled = true));
    try { await api(`/api/missions/${S.id}/brief/answer`, { method: "POST", body: { text } }); }
    catch (x) { err.textContent = x.message; err.hidden = false; }
    reload(true);
  };
  $("#briefCompose").onsubmit = (e) => { e.preventDefault(); const t = $("#briefMsg").value.trim(); if (t) { $("#briefMsg").value = ""; answer(t); } };
  $("#briefFeed").addEventListener("click", (e) => { const b = e.target.closest("[data-reply]"); if (b) answer(b.dataset.reply); });
  $("#needsBar").addEventListener("click", async (e) => {
    const b = e.target.closest("[data-reply], [data-read]"); if (!b) return;
    $("#needsBar").querySelectorAll("button").forEach((x) => (x.disabled = true));
    if (b.dataset.reply) { await answer(b.dataset.reply); $("#needsBar").dataset.key = ""; return; }
    try { await api(`/api/missions/${S.id}/read/approve`, { method: "POST", body: { said: b.dataset.read } }); }
    catch (x) { tell(x.message); $("#needsBar").dataset.key = ""; }
    reload(true);
  });
  $("#briefCard").addEventListener("click", async (e) => {
    const b = e.target.closest("#approveBtn"); if (!b) return;
    b.disabled = true;
    try { await api(`/api/missions/${S.id}/brief/approve`, { method: "POST", body: { said: b.textContent } }); S.page = "chat"; location.hash = `#/m/${S.id}/chat`; reload(true); }
    catch (x) { $("#briefErr").textContent = x.message; $("#briefErr").hidden = false; b.disabled = false; }
  });
}
