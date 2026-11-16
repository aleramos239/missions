// A small markdown renderer for the team chat. The text is HTML-escaped FIRST; only the tags below are ever made.
// Paragraphs, line breaks, **bold**, *italic*, `code`, -/*/1. lists (one nesting level), #-### headings, pipe tables,
// ``` code blocks, --- rules. No links, no images, no raw HTML.
import { esc } from "./fmt.js";

const LI = /^(\s*)([-*+]|\d{1,3}[.)])\s+(.*)$/;
const HEAD = /^(#{1,3})\s+(.*)$/;
const SEP = /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/;
const FENCE = /^\s*```/;
const RULE = /^\s*(-{3,}|\*{3,})\s*$/;
const isTable = (L, i) => L[i].includes("|") && i + 1 < L.length && L[i + 1].includes("|") && SEP.test(L[i + 1]);
const starts = (L, i) => HEAD.test(L[i]) || LI.test(L[i]) || FENCE.test(L[i]) || RULE.test(L[i]) || isTable(L, i);

export function inline(s) {
  const code = [];
  return s
    .replace(/`([^`\n]+)`/g, (_, c) => `\u0000${code.push(c) - 1}\u0000`)
    .replace(/\*\*(?=\S)(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*\w])\*(?=[^\s*])([^*\n]+?)\*(?![*\w])/g, "$1<em>$2</em>")
    .replace(/\u0000(\d+)\u0000/g, (_, n) => `<code>${code[n]}</code>`);
}

function list(L, i) {
  const m0 = L[i].match(LI), base = m0[1].length, ol = /\d/.test(m0[2]), items = [];
  for (; i < L.length; i++) {
    const m = L[i].match(LI);
    if (m && m[1].length > base && items.length) {
      const it = items[items.length - 1]; it.sub.push(m[3]); it.subOl ??= /\d/.test(m[2]);
    } else if (m) {
      if (/\d/.test(m[2]) !== ol) break;
      items.push({ t: m[3], sub: [] });
    } else if (L[i].trim() && /^\s/.test(L[i]) && items.length) {  // a wrapped line of the item above
      const it = items[items.length - 1];
      if (it.sub.length) it.sub[it.sub.length - 1] += " " + L[i].trim(); else it.t += " " + L[i].trim();
    } else break;
  }
  const tag = ol ? "ol" : "ul", start = ol && parseInt(m0[2], 10) > 1 ? ` start="${parseInt(m0[2], 10)}"` : "";
  const sub = (it) => it.sub.length ? `<${it.subOl ? "ol" : "ul"}>${it.sub.map((s) => `<li>${inline(s)}</li>`).join("")}</${it.subOl ? "ol" : "ul"}>` : "";
  return [`<${tag}${start}>${items.map((it) => `<li>${inline(it.t)}${sub(it)}</li>`).join("")}</${tag}>`, i];
}

function table(L, i) {
  const cells = (l) => l.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => inline(c.trim()));
  const head = cells(L[i]), rows = [];
  for (i += 2; i < L.length && L[i].includes("|") && L[i].trim(); i++) rows.push(cells(L[i]));
  const tr = (r, t) => `<tr>${r.map((c) => `<${t}>${c}</${t}>`).join("")}</tr>`;
  return [`<div class="md-tw"><table><thead>${tr(head, "th")}</thead><tbody>${rows.map((r) => tr(r, "td")).join("")}</tbody></table></div>`, i];
}

export function md(src) {
  const L = esc(src).replace(/\r\n?/g, "\n").split("\n"), out = [];
  let i = 0;
  while (i < L.length) {
    const l = L[i];
    if (!l.trim()) { i++; continue; }
    let h, r;
    if (FENCE.test(l)) {
      const body = [];
      for (i++; i < L.length && !FENCE.test(L[i]); i++) body.push(L[i]);
      out.push(`<pre><code>${body.join("\n")}</code></pre>`); i++;
    } else if ((h = l.match(HEAD))) { out.push(`<h4>${inline(h[2])}</h4>`); i++; }
    else if (RULE.test(l)) { out.push("<hr>"); i++; }
    else if (isTable(L, i)) { [r, i] = table(L, i); out.push(r); }
    else if (LI.test(l)) { [r, i] = list(L, i); out.push(r); }
    else {
      const p = [];
      for (; i < L.length && L[i].trim() && !(p.length && starts(L, i)); i++) p.push(inline(L[i].trim()));
      out.push(`<p>${p.join("<br>")}</p>`);
    }
  }
  return out.join("");
}
