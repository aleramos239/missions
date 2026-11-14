// One press-to-start, press-to-stop mic a typing box. Hidden where the browser has no speech.
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
let rec = null, act = null;

function stop() {
  if (rec) { const r = rec; rec = null; try { r.stop(); } catch (_) {} }
  if (!act) return;
  const { btn, field, ph } = act; act = null;
  btn.classList.remove("rec"); btn.setAttribute("aria-pressed", "false");
  btn.title = btn.ariaLabel = "Speak instead of typing";
  field.placeholder = ph; field.focus();
}

export function init() {
  document.querySelectorAll(".mx-mic").forEach((btn) => {
    if (!SR) { btn.hidden = true; return; }
    btn.onclick = () => {
      const again = act && act.btn === btn; stop(); if (again) return;
      const field = document.getElementById(btn.dataset.for);
      act = { btn, field, ph: field.placeholder };
      btn.classList.add("rec"); btn.setAttribute("aria-pressed", "true"); btn.title = btn.ariaLabel = "Stop recording";
      field.placeholder = "Listening…";
      const base = field.value.trim() ? field.value.trim() + " " : "";
      rec = new SR(); rec.continuous = true; rec.interimResults = true; rec.lang = "en-US";
      rec.onresult = (e) => { field.value = base + [...e.results].map((r) => r[0].transcript).join("").trim(); };
      rec.onerror = stop;
      rec.onend = () => { if (rec) stop(); };
      try { rec.start(); } catch (_) { stop(); }
    };
  });
  document.querySelectorAll("form").forEach((f) => f.addEventListener("submit", stop, true));
}
