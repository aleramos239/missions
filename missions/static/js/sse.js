// One stream a mission. Re-opens on error with after=<last n>, so no event is missed or shown twice.
export function open(mid, after, onEvent) {
  let es, last = after, dead = false, timer;
  const go = () => {
    es = new EventSource(`/api/missions/${mid}/stream?after=${last}`);
    es.onmessage = (e) => { const ev = JSON.parse(e.data); last = ev.n; onEvent(ev); };
    es.onerror = () => { es.close(); if (!dead) timer = setTimeout(go, 2000); };
  };
  go();
  return () => { dead = true; clearTimeout(timer); es.close(); };
}
