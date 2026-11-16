import { pct, statusWord, canDelete, deleteAsk } from "./fmt.js";
import { api } from "./net.js";
import { goalVal } from "./panel.js";
import { title, group, acct, mount, sure, tell } from "./ui.js";

// the result line: what the mission ended with, else its best so far
function line(d) {
  const r = d.result, b = d.right.best;
  if (r) return `${r.version}${r.box ? " · " + r.box : ""}`;
  return b ? `best ${b.version}: ${goalVal(d.board.goal.kind, b.goal_value)}` : "no result yet";
}

export default {
  on: ["status"],
  render(_m, el) {
    return mount(el, async () => {
      const list = await api("/api/missions");
      const ds = await Promise.all(list.map((x) => api(`/api/missions/${x.id}`).catch(() => null)));
      const rows = ds.filter(Boolean).map((d) => acct({ nm: d.title, sub: line(d), val: `${statusWord(d)} · ${pct(d.usage_used || 0)} wk · $${d.cost_usd.toFixed(2)}` }).replace('class="acct', `data-m="${d.id}" role="link" tabindex="0" class="acct`)
        .replace(/<\/div>$/, `<button type="button" class="btn btn-outline btn-sm mx-del" data-del="${d.id}"${canDelete(d) ? "" : ' disabled title="Stop it first"'}>Delete</button></div>`));
      return title("Missions.", list.length ? "Each with its status, its cost and where it stands." : "None yet.")
        + (rows.length ? `<div class="sec">${group(rows)}</div>` : "");
    }, (el) => {
      const open = (t) => { const r = t.closest("[data-m]"); if (r) location.hash = `#/m/${r.dataset.m}/chat`; };
      el.onclick = async (e) => {
        const b = e.target.closest("[data-del]");
        if (!b) return open(e.target);
        if (!(await sure(deleteAsk(b.dataset.del), { yes: "Delete", no: "Keep" }))) return;
        try { await api(`/api/missions/${b.dataset.del}`, { method: "DELETE" }); } catch (x) { return tell(x.message); }
        location.reload();
      };
      el.onkeydown = (e) => { if (e.key === "Enter") open(e.target); };
    });
  },
};
