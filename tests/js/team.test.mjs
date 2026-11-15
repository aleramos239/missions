import test from "node:test";
import assert from "node:assert/strict";
import * as t from "../../missions/static/js/team.js";

test("cost lines rank Fable, Opus, Sonnet, Haiku", () => {
  assert.match(t.costLine("fable"), /most expensive/);
  assert.match(t.costLine("haiku"), /cheapest/);
  assert.equal(t.costLine("nope"), "");
});

test("a role row selects the team's model and effort", () => {
  const h = t.roleRow(["doubter", "Doubter"], { doubter: { model: "sonnet", effort: "medium" } }, "x");
  assert.match(h, /data-role="doubter"/);
  assert.match(h, /value="sonnet" selected/);
  assert.match(h, /value="medium" selected/);
});
