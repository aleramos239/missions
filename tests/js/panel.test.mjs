import test from "node:test";
import assert from "node:assert/strict";
import { runButton } from "../../missions/static/js/panel.js";

test("the run button asks to read test months only while the engine waits for that yes", () => {
  assert.deepEqual(runButton({ status: "waiting_owner", pending: { read_for: "m3_v02" } }), { text: "Read test months", act: "read" });
  assert.deepEqual(runButton({ status: "waiting_owner", pending: {} }), { text: "Resume", act: "resume" });
  assert.deepEqual(runButton({ status: "running", pending: { read_for: "m3_v02" } }), { text: "Pause", act: "pause" });
  assert.deepEqual(runButton({ status: "paused" }), { text: "Resume", act: "resume" });
});
