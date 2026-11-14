import test from "node:test";
import assert from "node:assert/strict";
import * as f from "../../missions/static/js/fmt.js";

test("numbers keep their sign", () => {
  assert.equal(f.money(-1234.5), "−$1,235");
  assert.equal(f.money(1234.5), "+$1,235");
  assert.equal(f.money(0), "$0");
  assert.equal(f.pct(0.41), "41 %");
  assert.equal(f.pts(4.1), "+4.1");
  assert.equal(f.pts(-0.25), "−0.3");
  assert.equal(f.rr(1.5), "1:1.5");
  assert.equal(f.box(20, 14), "20 · #14");
  assert.equal(f.luck(3.5, 7, 3.1), "needs 3.5 after 7 tries; has 3.1");
  assert.equal(f.luck(3.5, 1, null), "needs 3.5 after 1 try; has none");
  assert.equal(f.ago(125), "2 min");
  assert.equal(f.ago(30), "30 s");
  assert.equal(f.ago(7200), "2 h");
});

test("sidebar words", () => {
  assert.equal(f.statusWord({ status: "running", round: 3 }), "Round 3");
  assert.equal(f.statusWord({ status: "queued", round: 0 }), "Next");
  assert.equal(f.statusWord({ status: "achieved" }), "Reached");
  assert.equal(f.statusWord({ status: "limit" }), "Not reached");
  assert.equal(f.statusWord({ status: "out_of_reach" }), "Out of reach");
  assert.equal(f.statusWord({ status: "stopped" }), "Stopped");
  assert.equal(f.statusWord({ status: "waiting_homebase", round: 2 }), "Waiting for Homebase");
  assert.equal(f.statusWord({ status: "paused", round: 2 }), "Paused");
  assert.equal(f.statusWord({ status: "crashed", round: 2 }), "Error");
});

test("missing and zero values", () => {
  for (const g of [f.money, f.pct, f.pts, f.rr]) for (const v of [NaN, null, undefined, Infinity, -Infinity]) assert.equal(g(v), "—");
  assert.equal(f.money(-0.4), "$0");
  assert.equal(f.money(-0), "$0");
  assert.equal(f.money(1234567.89), "+$1,234,568");
  assert.equal(f.pct(0), "0 %");
  assert.equal(f.pct(-0.001), "0 %");
  assert.equal(f.pts(0), "0.0");
  assert.equal(f.pts(-0.04), "0.0");
});

test("dec keeps its sign, hm reads hours and minutes", () => {
  assert.equal(f.dec(-0.456, 2), "−0.46");
  assert.equal(f.dec(1.2, 2), "+1.20");
  assert.equal(f.dec(0, 2), "0.00");
  assert.equal(f.dec(null), "—");
  assert.equal(f.hm(4200), "1 h 10 min");
  assert.equal(f.hm(600), "10 min");
});

test("plain numbers", () => {
  assert.equal(f.plain(1234.5, 1), "1,234.5");
  assert.equal(f.plain(null), "—");
  assert.equal(f.plain(3.4, 1), "3.4");
});
