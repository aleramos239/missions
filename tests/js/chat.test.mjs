import test from "node:test";
import assert from "node:assert/strict";
import { mine } from "../../missions/static/js/chat.js";

test("For you keeps his texts, what is written to him and the reads; the team's work folds", () => {
  const ev = [
    { n: 1, type: "chat", who: "builder", text: "idea", for_workers: false },
    { n: 2, type: "chat", who: "owner", to: "lead", text: "hows it going", for_workers: true },
    { n: 3, type: "chat", who: "doubter", text: "argue", for_workers: true },
    { n: 4, type: "turn", who: "lead", text: "owner" },
    { n: 5, type: "chat", who: "lead", text: "the answer", for_workers: true },
    { n: 6, type: "chat", who: "lead", text: "later orders", for_workers: true },
    { n: 7, type: "chat", who: "judge", text: "m4_v01 is dropped: under 2 a week.", for_workers: true },
    { n: 8, type: "chat", who: "judge", text: "m4_v04, box 10 · #30. Lines passed: 5 of 5.", for_workers: true },
    { n: 9, type: "chat", who: "lead", text: "two sentences", data: { to_owner: true }, for_workers: false },
    { n: 10, type: "chat", who: "engine", text: "Stage 1 is over.", for_workers: false },
    { n: 11, type: "chat", who: "engine", text: "Closed for this mission: x", for_workers: true },
  ];
  assert.deepEqual([...mine(ev)], [2, 5, 8, 9, 10]);
});
