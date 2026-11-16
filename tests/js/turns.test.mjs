import test from "node:test";
import assert from "node:assert/strict";
import { turnStats, whyWords } from "../../missions/static/js/turns.js";

test("turn rows add up a role and the newest come first", () => {
  const ev = [
    { n: 1, type: "chat", who: "lead", text: "hi" },
    { n: 2, type: "turn", who: "lead", text: "ideas", data: { secs: 60, cost: 0.5, tools: [], ok: true } },
    { n: 3, type: "talk", who: "lead", text: "notes", data: { step: "ideas" } },
    { n: 4, type: "turn", who: "lead", text: "verdict", data: { secs: 30, cost: 0.25, tools: ["trades"], ok: false, why: "timeout" } },
    { n: 5, type: "turn", who: "builder", text: "build", data: { secs: null, cost: 1, tools: [] } },
  ];
  const s = turnStats(ev);
  assert.deepEqual(s.totals, [{ who: "lead", turns: 2, secs: 90, cost: 0.75 }, { who: "builder", turns: 1, secs: 0, cost: 1 }]);
  assert.deepEqual(s.last.map((e) => e.n), [5, 4, 2]);
  const many = Array.from({ length: 40 }, (_, i) => ({ n: i, type: "turn", who: "lead", data: {} }));
  assert.equal(turnStats(many).last.length, 30);
  assert.equal(turnStats(many).last[0].n, 39);
});

test("a failed turn's reason reads in plain words", () => {
  assert.equal(whyWords("timeout"), "ran out of time");
  assert.equal(whyWords("crash: no result: boom"), "crashed: no result: boom");
  assert.equal(whyWords(null), "failed, no reason given");
  assert.equal(whyWords("crash: " + "x".repeat(500)).length, 200);
});
