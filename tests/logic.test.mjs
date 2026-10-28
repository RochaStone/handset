// Pure-function tests for assets/logic.js. Run: node --test tests/logic.test.mjs (Node 18+, no installs).
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const L = require("../assets/logic.js");
const SIX = ["1", "2", "3", "4", "5", "6"];

test("snake stays locked until every section is read", () => {
  let read = {};
  for (const k of SIX.slice(0, 5)) {
    read = L.markRead(read, k, SIX);
    assert.equal(L.isUnlocked(read, SIX), false);
  }
  assert.equal(L.readCount(read, SIX), 5);
  assert.equal(L.lockLabel(read, SIX), "LOCKED 5/6");
  read = L.markRead(read, "6", SIX);
  assert.equal(L.isUnlocked(read, SIX), true);
  assert.equal(L.lockLabel(read, SIX), "PLAY");
});

test("reading order does not matter and re-reading does not double count", () => {
  let read = {};
  for (const k of ["6", "2", "2", "4", "1", "3", "5", "1"]) read = L.markRead(read, k, SIX);
  assert.equal(L.readCount(read, SIX), 6);
  assert.equal(L.isUnlocked(read, SIX), true);
});

test("menu, games and share screens never count as read", () => {
  let read = {};
  for (const k of ["menu", "7", "share", "splash", "0", "8"]) read = L.markRead(read, k, SIX);
  assert.deepEqual(read, {});
});

test("markRead never mutates the old record", () => {
  const before = { "1": true };
  const after = L.markRead(before, "2", SIX);
  assert.deepEqual(before, { "1": true });
  assert.deepEqual(after, { "1": true, "2": true });
});

test("an edition with three sections unlocks after three", () => {
  const keys = ["1", "2", "3"];
  let read = {};
  for (const k of keys) read = L.markRead(read, k, keys);
  assert.equal(L.isUnlocked(read, keys), true);
  assert.equal(L.lockLabel(read, keys), "PLAY");
  assert.equal(L.isUnlocked({}, []), false);
});

test("stale progress for a section that no longer exists does not unlock", () => {
  const keys = ["1", "2", "3"];
  const read = { "1": true, "2": true, "5": true };
  assert.equal(L.isUnlocked(read, keys), false);
});

test("the x-mark checklist marks read sections with x and the rest with a dot", () => {
  const rows = L.checklist({ "1": true, "3": true }, [
    { key: "1", title: "A" }, { key: "2", title: "B" }, { key: "3", title: "C" }]);
  assert.deepEqual(rows.map((r) => r.mark), ["x", ".", "x"]);
});

test("stored progress is parsed safely", () => {
  assert.deepEqual(L.parseRead('{"1":true,"2":false,"9":true,"x":true}'), { "1": true });
  assert.deepEqual(L.parseRead("not json"), {});
  assert.deepEqual(L.parseRead("[1,2]"), {});
  assert.deepEqual(L.parseRead(null), {});
});

test("NEXT and BACK walk sections, then games, then the menu", () => {
  assert.equal(L.nextScreen("splash", SIX), "menu");
  assert.equal(L.nextScreen("menu", SIX), "1");
  assert.equal(L.nextScreen("3", SIX), "4");
  assert.equal(L.nextScreen("6", SIX), "7");
  assert.equal(L.nextScreen("7", SIX), "menu");
  assert.equal(L.prevScreen("1", SIX), "menu");
  assert.equal(L.prevScreen("4", SIX), "3");
  assert.equal(L.prevScreen("7", SIX), "6");
  assert.equal(L.prevScreen("share", SIX), "menu");
});

test("keypad: 1-6 open sections that exist, 7 games, 8 share, 9 author, 0 menu", () => {
  const keys = ["1", "2", "3"];
  assert.deepEqual(L.keyAction("2", keys), { action: "open", target: "2" });
  assert.deepEqual(L.keyAction("5", keys), { action: "none" });
  assert.deepEqual(L.keyAction("7", keys), { action: "open", target: "7" });
  assert.deepEqual(L.keyAction("8", keys), { action: "share" });
  assert.deepEqual(L.keyAction("9", keys), { action: "author" });
  assert.deepEqual(L.keyAction("0", keys), { action: "open", target: "menu" });
});

test("deep links open only real screens", () => {
  assert.equal(L.screenFromHash("#menu", SIX), "menu");
  assert.equal(L.screenFromHash("#3", SIX), "3");
  assert.equal(L.screenFromHash("#games", SIX), "7");
  assert.equal(L.screenFromHash("#5", ["1", "2"]), null);
  assert.equal(L.screenFromHash("#<script>", SIX), null);
});

test("gate off (the public twin) is always open", () => {
  assert.deepEqual(L.gateState({ enabled: false, search: "", saved: null }), { open: true, code: null, via: "off" });
});

test("gate on with no code stays closed", () => {
  assert.equal(L.gateState({ enabled: true, search: "", saved: null }).open, false);
  assert.equal(L.gateState({ enabled: true, search: "?utm=x", saved: "" }).open, false);
});

test("a ?c=CODE bypass opens the gate and is normalised to upper case", () => {
  assert.deepEqual(L.gateState({ enabled: true, search: "?c=pocket01", saved: null }),
    { open: true, code: "POCKET01", via: "url" });
  assert.equal(L.gateState({ enabled: true, search: "?utm=a&c=ABC&x=1", saved: null }).code, "ABC");
});

test("a malformed ?c= does not open the gate", () => {
  for (const s of ["?c=", "?c=ab", "?c=%3Cscript%3E", "?c=" + "A".repeat(21), "?c=%E0%A4%A", "?c=AB-CD"]) {
    assert.equal(L.gateState({ enabled: true, search: s, saved: null }).open, false, s);
  }
});

test("a code saved on this device opens the gate on return visits", () => {
  assert.deepEqual(L.gateState({ enabled: true, search: "", saved: "POCKET01" }),
    { open: true, code: "POCKET01", via: "saved" });
  assert.equal(L.gateState({ enabled: true, search: "", saved: "<bad>" }).open, false);
});

test("the gate posts {email, code}", () => {
  assert.deepEqual(L.gatePayload("  me@example.com ", "pocket01"), { email: "me@example.com", code: "POCKET01" });
  assert.deepEqual(L.gatePayload("me@example.com", null), { email: "me@example.com", code: "" });
});

test("email check catches unfinished addresses", () => {
  assert.equal(L.validEmail("me@example.com"), true);
  for (const e of ["", "me", "me@", "me@example", "me @example.com", "<a>@b.co"]) assert.equal(L.validEmail(e), false, e);
});

test("after signing up, the server's own code wins, else the edition code", () => {
  assert.equal(L.codeFromReply({ code: "abc123" }, "POCKET01"), "ABC123");
  assert.equal(L.codeFromReply(null, "POCKET01"), "POCKET01");
  assert.equal(L.codeFromReply({ code: "<x>" }, "POCKET01"), "POCKET01");
  assert.equal(L.codeFromReply(null, ""), "OPEN");
});

test("share hands on the public link, never the reader's ?c= link", () => {
  assert.equal(L.shareUrl("https://example.com/post", "https://x.test/p?c=ME#7"), "https://example.com/post");
  assert.equal(L.shareUrl("", "https://x.test/p/gated.html?c=ME#7"), "https://x.test/p/gated.html");
  assert.equal(L.shareUrl("javascript:alert(1)", "https://x.test/p"), "https://x.test/p");
});
