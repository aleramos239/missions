import test from "node:test";
import assert from "node:assert/strict";
import { md } from "../../missions/static/js/md.js";

test("html is escaped before markdown", () => {
  assert.equal(md('<script>alert("x")</script>'), "<p>&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;</p>");
  assert.equal(md("**<b>hi</b>**"), "<p><strong>&lt;b&gt;hi&lt;/b&gt;</strong></p>");
  assert.equal(md("`<img src=x onerror=1>`"), "<p><code>&lt;img src=x onerror=1&gt;</code></p>");
});

test("bold, italic, code", () => {
  assert.equal(md("**Base:** the *agree* rule, `off_min` 5"), "<p><strong>Base:</strong> the <em>agree</em> rule, <code>off_min</code> 5</p>");
  assert.equal(md("2 * 3 * 4 and g_side_with"), "<p>2 * 3 * 4 and g_side_with</p>");
});

test("paragraphs and line breaks", () => {
  assert.equal(md("one\ntwo\n\nthree"), "<p>one<br>two</p><p>three</p>");
});

test("lists, one nesting level", () => {
  assert.equal(md("- a\n- b\n  - b1\n- c"), "<ul><li>a</li><li>b<ul><li>b1</li></ul></li><li>c</li></ul>");
  assert.equal(md("Tried:\n1. v01\n2. v02"), "<p>Tried:</p><ol><li>v01</li><li>v02</li></ol>");
  assert.equal(md("* star item"), "<ul><li>star item</li></ul>");
});

test("headings and tables", () => {
  assert.equal(md("## What next"), "<h4>What next</h4>");
  assert.equal(md("| Box | Net |\n|---|---:|\n| #30 | $7,270 |"),
    '<div class="md-tw"><table><thead><tr><th>Box</th><th>Net</th></tr></thead><tbody><tr><td>#30</td><td>$7,270</td></tr></tbody></table></div>');
});
