import { esc } from "./fmt.js";
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

function row(e, m) {
  const who = WHO[e.who] || cap(String(e.who || "?"));
  const tag = e.who === "judge" ? "code" : e.who === "owner" ? (e.to ? `to ${cap(String(e.to))}` : "") : m.team[e.who] ? cap(String(m.team[e.who].model)) : "";
  const line = e.data && typeof e.data.line === "string" ? `<div class="raw">${esc(e.data.line)}</div>` : "";
  return `<div class="feed-row${who === "You" ? " you" : ""}" data-who="${esc(who)}" data-n="${e.n}"><span class="t">${clock(e.at)}</span><div class="h"><b>${esc(who)}</b>${tag ? `<span class="tag">${esc(tag)}</span>` : ""}<p>${esc(e.text)}</p></div>${line}</div>`;
}
const chatOnly = (events) => events.filter((e) => e.type === "chat" && e.text);

function feed(el, events, m) {
  el.innerHTML = chatOnly(events).map((e) => row(e, m)).join("");
}

export function renderChat(S) {
  const m = S.m, r = m.right, g = m.board.goal, b = r.best, t = m.board.tries.mission;
  $("#chatTitle").innerHTML = `${b ? `Best so far ${goalVal(g.kind, b.goal_value)}. Goal ${goalVal(g.kind, g.target)}.` : `Goal ${goalVal(g.kind, g.target)}. Nothing has scored yet.`}<br><span>${esc(m.sentence)}</span>`;
  $("#chatCap").textContent = `Test months ${testMonths(m).toLowerCase()} · ${t} ${t === 1 ? "try" : "tries"} · the bar rises with every try`;
  $("#stepRound").textContent = `Round ${m.round}`;
  $("#stepSince").textContent = "";
  const h = Math.floor(m.run_seconds / 3600), mi = Math.floor(m.run_seconds / 60) % 60;
  $("#elapsed").textContent = `${h} h ${mi} m`;
  const at = STEP_AT[m.step] ?? 0, done = (at / 5) * 100;
  $("#tlDone").style.width = done + "%"; $("#tlNow").style.left = done + "%";
  $("#tlLabels").innerHTML = LABELS.map((l, i) => `<span class="tl-t${i === 0 ? " at-start" : i === 5 ? " at-end" : ""}${i === at ? " strong" : ""}" style="left:${i * 20}%">${l}</span>`).join("");
  feed($("#feed"), S.events, m);
  filter();
}

function filter() {
  const v = $("#who").value;
  document.querySelectorAll("#feed .feed-row").forEach((r) => (r.hidden = !!v && r.dataset.who !== v));
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

function card(m, p) {
  const b = p, g = b.goal, acct = b.account;
  const list = (xs) => (xs || []).map(esc).join(" · ") || "—";
  const r = (k, v) => `<div class="acct"><span class="nm grow">${k}</span><span class="kvi">${v}</span></div>`;
  return `<h2 class="hb-sec-h">The brief</h2><div class="mx-brief">`
    + r("Goal", esc(goalText(g))) + r("Idea", esc(b.idea)) + r("Fixed", list(b.fixed)) + r("The team may change", list(b.may_change))
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

export function init({ S, api, reload }) {
  $("#who").onchange = filter;
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
  $("#briefCard").addEventListener("click", async (e) => {
    const b = e.target.closest("#approveBtn"); if (!b) return;
    b.disabled = true;
    try { await api(`/api/missions/${S.id}/brief/approve`, { method: "POST", body: { said: b.textContent } }); S.page = "chat"; location.hash = `#/m/${S.id}/chat`; reload(true); }
    catch (x) { $("#briefErr").textContent = x.message; $("#briefErr").hidden = false; b.disabled = false; }
  });
}
