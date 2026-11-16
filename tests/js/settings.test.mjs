import test from "node:test";
import assert from "node:assert/strict";
import { changed } from "../../missions/static/js/settings.js";
import { limitsHtml } from "../../missions/static/js/new.js";

test("only the changed keys go back", () => {
  const m = { test_months: "ask", limits: { tries: { n: 20 } }, team: { lead: { model: "opus", effort: "high" } } };
  assert.deepEqual(changed(m, { test_months: "ask", limits: { tries: { n: 20 } }, team: m.team }), {});
  assert.deepEqual(changed(m, { test_months: "team", limits: { tries: { n: 40 } }, team: m.team }),
    { test_months: "team", limits: { tries: { n: 40 } } });
});

test("the limit rows show the mission's values, a value off the menu keeps its own line", () => {
  const h = limitsHtml({ tries: { n: 30 }, hours: { n: 8 } }, "ask");
  assert.match(h, /data-lim="tries"[^]*value="30" selected>30 tries/);
  assert.match(h, /mx-lim" data-lim="hours"[^]*value="8" selected/);
  assert.match(h, /mx-lim off" data-lim="usage"/);
  assert.match(h, /value="ask" selected>Ask me first/);
  assert.match(limitsHtml({ until_goal: true }), /mx-lim off" data-lim="tries"/);
});
