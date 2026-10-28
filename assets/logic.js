/* handset logic: pure functions only, no DOM. The page inlines this file and the tests import it.
   Screens are strings: "splash", "menu", "1".."6" (sections), "7" (games), "share". */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) { module.exports = api; }
  else { root.HandsetLogic = api; }
}(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var CODE_RE = /^[A-Z0-9]{3,20}$/;
  var EMAIL_RE = /^[^\s@<>"']+@[^\s@<>"']+\.[^\s@<>"']{2,}$/;

  /* How many of the edition's section keys have been read. */
  function readCount(read, keys) {
    var n = 0;
    for (var i = 0; i < keys.length; i++) { if (read && read[keys[i]] === true) { n++; } }
    return n;
  }

  /* Snake is earned: every section in the edition read, and at least one section exists. */
  function isUnlocked(read, keys) {
    return keys.length > 0 && readCount(read, keys) === keys.length;
  }

  /* Opening a section marks it read. Returns a new object; never mutates the old one.
     Only real section keys count, so opening the menu or the games screen marks nothing. */
  function markRead(read, key, keys) {
    var next = {};
    var k;
    for (k in read) { if (Object.prototype.hasOwnProperty.call(read, k)) { next[k] = read[k]; } }
    if (keys.indexOf(String(key)) !== -1) { next[String(key)] = true; }
    return next;
  }

  /* The x-mark checklist on the games screen: one row per section, "x" read or "." not yet. */
  function checklist(read, sections) {
    return sections.map(function (s) {
      return { key: s.key, title: s.title, mark: read && read[s.key] === true ? "x" : "." };
    });
  }

  /* The status line next to Games on the menu. */
  function lockLabel(read, keys) {
    return isUnlocked(read, keys) ? "PLAY" : "LOCKED " + readCount(read, keys) + "/" + keys.length;
  }

  /* Parse stored progress safely. Anything odd becomes an empty record. */
  function parseRead(raw) {
    if (!raw) { return {}; }
    try {
      var v = JSON.parse(raw);
      if (!v || typeof v !== "object" || Array.isArray(v)) { return {}; }
      var out = {};
      for (var k in v) { if (/^[1-6]$/.test(k) && v[k] === true) { out[k] = true; } }
      return out;
    } catch (err) {
      return {};
    }
  }

  /* NEXT and BACK walk one road through the edition: sections in order, then games, then the menu. */
  function nextScreen(current, keys) {
    if (current === "splash" || current === "share") { return "menu"; }
    if (current === "menu") { return keys.length ? keys[0] : "7"; }
    if (current === "7") { return "menu"; }
    var i = keys.indexOf(current);
    if (i === -1) { return "menu"; }
    return i + 1 < keys.length ? keys[i + 1] : "7";
  }

  function prevScreen(current, keys) {
    if (current === "splash" || current === "menu" || current === "share") { return "menu"; }
    if (current === "7") { return keys.length ? keys[keys.length - 1] : "menu"; }
    var i = keys.indexOf(current);
    return i > 0 ? keys[i - 1] : "menu";
  }

  /* What each keypad key does. Returns {action, target}. Keys 1..6 with no section do nothing. */
  function keyAction(k, keys) {
    k = String(k);
    if (/^[1-6]$/.test(k)) { return keys.indexOf(k) !== -1 ? { action: "open", target: k } : { action: "none" }; }
    if (k === "7") { return { action: "open", target: "7" }; }
    if (k === "8") { return { action: "share" }; }
    if (k === "9") { return { action: "author" }; }
    if (k === "0") { return { action: "open", target: "menu" }; }
    return { action: "none" };
  }

  /* A deep link: #menu, #games, #share or #1..#6 (only sections that exist). */
  function screenFromHash(hash, keys) {
    var h = String(hash || "").replace(/^#/, "").toLowerCase();
    if (h === "menu") { return "menu"; }
    if (h === "games" || h === "7") { return "7"; }
    if (h === "share") { return "share"; }
    if (keys.indexOf(h) !== -1) { return h; }
    return null;
  }

  function normaliseCode(raw) {
    var c = String(raw || "").trim().toUpperCase();
    return CODE_RE.test(c) ? c : null;
  }

  /* The email gate. A well-formed ?c=CODE in the link, or a code already saved on this device,
     opens it. Without the gate (the public twin) it is always open. */
  function gateState(opts) {
    if (!opts || !opts.enabled) { return { open: true, code: null, via: "off" }; }
    var fromUrl = null;
    var m = /[?&]c=([^&#]*)/.exec(String(opts.search || ""));
    if (m) {
      try { fromUrl = normaliseCode(decodeURIComponent(m[1].replace(/\+/g, " "))); }
      catch (err) { fromUrl = null; }
    }
    if (fromUrl) { return { open: true, code: fromUrl, via: "url" }; }
    var saved = normaliseCode(opts.saved);
    if (saved) { return { open: true, code: saved, via: "saved" }; }
    return { open: false, code: null, via: "none" };
  }

  function validEmail(email) {
    var e = String(email || "").trim();
    return e.length <= 254 && EMAIL_RE.test(e);
  }

  /* What the gate sends to the endpoint. */
  function gatePayload(email, code) {
    return { email: String(email || "").trim(), code: normaliseCode(code) || "" };
  }

  /* The code to remember after a good reply: the server's own code if it sent one, else the edition code. */
  function codeFromReply(data, fallback) {
    var fromServer = data && typeof data === "object" ? normaliseCode(data.code) : null;
    return fromServer || normaliseCode(fallback) || "OPEN";
  }

  /* The link SHARE hands on: the configured public link, else this page with no ?c= and no #hash,
     so every friend meets the front door. */
  function shareUrl(configured, href) {
    var c = String(configured || "").trim();
    if (/^https?:\/\//i.test(c)) { return c; }
    return String(href || "").split("#")[0].split("?")[0];
  }

  return {
    CODE_RE: CODE_RE, readCount: readCount, isUnlocked: isUnlocked, markRead: markRead,
    checklist: checklist, lockLabel: lockLabel, parseRead: parseRead, nextScreen: nextScreen,
    prevScreen: prevScreen, keyAction: keyAction, screenFromHash: screenFromHash,
    normaliseCode: normaliseCode, gateState: gateState, validEmail: validEmail,
    gatePayload: gatePayload, codeFromReply: codeFromReply, shareUrl: shareUrl
  };
}));
