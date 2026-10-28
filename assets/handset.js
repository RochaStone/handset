/* handset page: screens, keypad, soft keys, share, the email gate and the earned Snake.
   Reads its settings from <script type="application/json" id="handset-config">. Needs HandsetLogic. */
(function () {
  "use strict";
  var L = window.HandsetLogic;
  var cfgEl = document.getElementById("handset-config");
  if (!L || !cfgEl) { return; }
  var cfg;
  try { cfg = JSON.parse(cfgEl.textContent); }
  catch (err) { cfg = null; }
  if (!cfg) { return; }

  var KEYS = cfg.keys;                        // section keys in order, e.g. ["1","2","3","4","5","6"]
  var NS = "handset:" + cfg.slug + ":";       // storage namespace, one per edition
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var touch = (window.matchMedia && window.matchMedia("(hover: none) and (pointer: coarse)").matches) ||
              ("ontouchstart" in window);

  function store(key, val) {
    try { window.localStorage.setItem(NS + key, val); return true; }
    catch (err) { return false; }           // private mode or blocked storage: progress lasts this visit
  }
  function recall(key) {
    try { return window.localStorage.getItem(NS + key); }
    catch (err) { return null; }
  }

  var view = document.getElementById("view");
  var navBack = document.getElementById("navBack");
  var navNext = document.getElementById("navNext");
  var menuButtons = Array.prototype.slice.call(document.querySelectorAll("#scr-menu .menu button"));
  var current = "splash";
  var cursor = 0;
  var read = L.parseRead(recall("read"));

  /* ---------- the earned Snake: the lock, the checklist, the menu status ---------- */
  function paintLock() {
    var open = L.isUnlocked(read, KEYS);
    var st = document.getElementById("gameSt");
    if (st) { st.textContent = L.lockLabel(read, KEYS); }
    L.checklist(read, cfg.sections).forEach(function (row) {
      var m = document.querySelector('#lockList [data-lk="' + row.key + '"]');
      if (m) { m.textContent = row.mark; }
    });
    KEYS.forEach(function (k) {
      var s = document.querySelector('#scr-menu [data-st="' + k + '"]');
      if (s) { s.textContent = read[k] ? "read" : "new"; }
    });
    document.getElementById("lockBox").hidden = open;
    document.getElementById("gameBox").hidden = !open;
    var key7 = document.querySelector('[data-key="7"]');
    if (key7) { key7.setAttribute("aria-label", open ? "7, Snake, ready to play" : "7, Snake, locked"); }
  }

  function paintMenu() {
    menuButtons.forEach(function (b, i) { b.setAttribute("aria-current", i === cursor ? "true" : "false"); });
  }

  function show(id, focusIt) {
    var next = document.getElementById("scr-" + id);
    if (!next) { return; }
    Array.prototype.forEach.call(view.querySelectorAll(".screen"), function (s) { s.classList.remove("is-on"); });
    next.classList.add("is-on");
    if (current === "7" && id !== "7") { stopGame(); }
    current = id;
    view.scrollTop = 0;
    if (KEYS.indexOf(id) !== -1 && !read[id]) {
      read = L.markRead(read, id, KEYS);
      store("read", JSON.stringify(read));
    }
    navBack.disabled = id === "splash" || id === "menu";
    navNext.disabled = id === "splash";
    navNext.textContent = id === "menu" ? "Open" : "Next";
    paintLock();
    if (id === "menu") { paintMenu(); }
    if (focusIt !== false) {
      var h = next.querySelector("h2");
      if (h) { h.focus({ preventScroll: true }); }
    }
  }
  window.handsetShow = function (id) { show(String(id), false); };  // used by the 390px layout test

  function moveCursor(delta) {
    cursor = (cursor + delta + menuButtons.length) % menuButtons.length;
    paintMenu();
    menuButtons[cursor].focus({ preventScroll: true });
  }

  menuButtons.forEach(function (b, i) {
    b.addEventListener("click", function () { cursor = i; show(b.getAttribute("data-go")); });
  });
  navBack.addEventListener("click", function () { show(L.prevScreen(current, KEYS)); });
  navNext.addEventListener("click", function () {
    if (current === "menu") { show(menuButtons[cursor].getAttribute("data-go")); return; }
    show(L.nextScreen(current, KEYS));
  });

  /* ---------- 8: share the public link, never the reader's ?c= link ---------- */
  var shareMsg = document.getElementById("shareMsg");
  var shareLink = document.getElementById("shareLink");
  function share() {
    var url = L.shareUrl(cfg.share.url, window.location.href);
    var text = cfg.share.text || cfg.title;
    show("share");
    shareLink.textContent = url;
    if (navigator.share) {
      shareMsg.textContent = "Choose where to send it.";
      navigator.share({ title: cfg.title, text: text, url: url }).then(function () {
        shareMsg.textContent = "Sent. Thank you for passing it on.";
      }, function () {
        shareMsg.textContent = "No problem. The link is below if you want it.";
      });
      return;
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(function () {
        shareMsg.textContent = "Link copied. Paste it anywhere.";
      }, function () {
        shareMsg.textContent = "Copy this link and send it on:";
      });
      return;
    }
    shareMsg.textContent = "Copy this link and send it on:";
  }

  /* ---------- 9: the author ---------- */
  function author() {
    if (cfg.author.email) {
      window.location.href = "mailto:" + cfg.author.email + "?subject=" + encodeURIComponent(cfg.title);
    } else if (cfg.author.url) {
      window.open(cfg.author.url, "_blank", "noopener");
    }
  }

  /* ---------- keypad and keyboard ---------- */
  function press(k) {
    if (current === "splash") { show("menu"); return; }
    if (playing() && /^[2468]$/.test(k)) { turn(k); return; }
    var a = L.keyAction(k, KEYS);
    if (a.action === "open") { show(a.target); }
    else if (a.action === "share") { share(); }
    else if (a.action === "author") { author(); }
  }

  document.getElementById("keypad").addEventListener("click", function (e) {
    var btn = e.target.closest("[data-key]");
    if (btn && !btn.disabled) { press(btn.getAttribute("data-key")); }
  });

  document.addEventListener("keydown", function (e) {
    if (document.body.classList.contains("gated")) { return; }   // the gate form owns the keyboard
    var t = e.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA")) { return; }
    var k = e.key;
    if (current === "splash") { show("menu"); e.preventDefault(); return; }
    if (playing()) {
      var steer = { ArrowUp: "2", ArrowDown: "8", ArrowLeft: "4", ArrowRight: "6" }[k];
      if (steer) { turn(steer); e.preventDefault(); return; }
    }
    if (current === "menu" && (k === "ArrowDown" || k === "ArrowUp")) {
      moveCursor(k === "ArrowDown" ? 1 : -1); e.preventDefault(); return;
    }
    if (k === "ArrowRight") { navNext.click(); e.preventDefault(); return; }
    if (k === "ArrowLeft") { if (!navBack.disabled) { navBack.click(); } e.preventDefault(); return; }
    if (k === "Escape") { show("menu"); e.preventDefault(); return; }
    if (k === "Enter" && current === "menu") { navNext.click(); e.preventDefault(); return; }
    if (k === "Enter" && current === "7" && L.isUnlocked(read, KEYS)) { startGame(); e.preventDefault(); return; }
    if (/^[0-9]$/.test(k)) { press(k); }
  });

  /* ---------- the email gate (gated twin only) ---------- */
  var gate = document.getElementById("gate");
  if (gate) {
    var state = L.gateState({ enabled: cfg.gate.enabled, search: window.location.search, saved: recall("code") });
    if (state.open) {
      if (state.code) { store("code", state.code); }
      gate.hidden = true;
    } else {
      gate.hidden = false;
      document.body.classList.add("gated");
      var form = document.getElementById("gateForm");
      var input = document.getElementById("gateEmail");
      var btn = document.getElementById("gateGo");
      var msg = document.getElementById("gateMsg");
      var label = btn.textContent;
      window.setTimeout(function () { input.focus(); }, 50);
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        var email = input.value;
        if (!L.validEmail(email)) { msg.textContent = "That email looks unfinished. Check it and try again."; input.focus(); return; }
        btn.disabled = true;
        btn.textContent = "One moment...";
        msg.textContent = "";
        window.fetch(cfg.gate.endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(L.gatePayload(email, cfg.gate.code))
        }).then(function (res) {
          if (!res.ok) { throw new Error("status " + res.status); }
          return res.json().then(function (d) { return d; }, function () { return null; });
        }).then(function (data) {
          var code = L.codeFromReply(data, cfg.gate.code);
          store("code", code);
          try { window.history.replaceState({}, "", window.location.pathname + "?c=" + encodeURIComponent(code)); }
          catch (err) { msg.textContent = ""; }   // file:// pages cannot rewrite the address; the code is saved anyway
          gate.hidden = true;
          document.body.classList.remove("gated");
          show("menu");
        }).catch(function () {
          btn.disabled = false;
          btn.textContent = label;
          msg.textContent = cfg.author.email
            ? "That did not go through. Try again in a minute, or write to " + cfg.author.email + "."
            : "That did not go through. Try again in a minute.";
        });
      });
    }
  }

  /* ================= SNAKE ================= */
  var CELL = 12, COLS = 24, ROWS = 18;
  var cv = document.getElementById("snake");
  var ctx = cv.getContext("2d");
  var scoreEl = document.getElementById("score");
  var hiEl = document.getElementById("hi");
  var gameMsg = document.getElementById("gameMsg");
  var playBtn = document.getElementById("playBtn");
  var SAY_START = touch ? "Tap Play, then swipe to steer." : "Press Play, then steer with the arrow keys or 2 4 6 8.";
  var SAY_AGAIN = touch ? "Tap Play to go again." : "Press Play to go again.";
  var HEART = [[0,1,0,0,1,0],[1,1,1,1,1,1],[1,1,1,1,1,1],[0,1,1,1,1,0],[0,0,1,1,0,0],[0,0,0,0,0,0]];
  var snake, dir, nextDir, apple, score = 0, timer = null, alive = false, tick = 190;
  var hi = parseInt(recall("hi") || "0", 10) || 0;

  function pad(n) { return ("00" + n).slice(-3); }
  function colour(name, fallback) {
    var v = window.getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v || fallback;
  }
  function playing() { return current === "7" && alive; }

  function placeApple() {
    var free = [];
    for (var x = 0; x < COLS; x++) {
      for (var y = 0; y < ROWS; y++) {
        var hit = snake.some(function (s) { return s.x === x && s.y === y; });
        if (!hit) { free.push({ x: x, y: y }); }
      }
    }
    apple = free.length ? free[Math.floor(Math.random() * free.length)] : { x: 0, y: 0 };
  }

  function reset() {
    snake = [{ x: 8, y: 9 }, { x: 7, y: 9 }, { x: 6, y: 9 }];
    dir = { x: 1, y: 0 };
    nextDir = dir;
    score = 0;
    scoreEl.textContent = pad(score);
    placeApple();
    draw();
  }

  function draw() {
    var bg = colour("--game-bg", "#FFF7F4"), fg = colour("--game-ink", "#3B1230"), heart = colour("--game-apple", "#C2246E");
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, cv.width, cv.height);
    ctx.fillStyle = fg;
    snake.forEach(function (s, i) {
      ctx.fillRect(s.x * CELL + 1, s.y * CELL + 1, CELL - 2, CELL - 2);
      if (i === 0) {
        ctx.fillStyle = bg;
        ctx.fillRect(s.x * CELL + 4, s.y * CELL + 4, CELL - 8, CELL - 8);
        ctx.fillStyle = fg;
      }
    });
    ctx.fillStyle = heart;
    var px = CELL / 6;
    for (var r = 0; r < 6; r++) {
      for (var c = 0; c < 6; c++) {
        if (HEART[r][c]) { ctx.fillRect(apple.x * CELL + c * px, apple.y * CELL + r * px + 1, px, px); }
      }
    }
  }

  function step() {
    dir = nextDir;
    var head = { x: snake[0].x + dir.x, y: snake[0].y + dir.y };
    var crash = head.x < 0 || head.y < 0 || head.x >= COLS || head.y >= ROWS ||
                snake.some(function (s) { return s.x === head.x && s.y === head.y; });
    if (crash) { over(); return; }
    snake.unshift(head);
    if (head.x === apple.x && head.y === apple.y) {
      score += 10;
      scoreEl.textContent = pad(score);
      placeApple();
      if (tick > 130) { tick -= 5; window.clearInterval(timer); timer = window.setInterval(step, tick); }
    } else {
      snake.pop();
    }
    draw();
  }

  function over() {
    stopGame();
    if (score > hi) {
      hi = score;
      hiEl.textContent = pad(hi);
      store("hi", String(hi));
      gameMsg.textContent = "NEW HIGH SCORE " + pad(score) + ". " + SAY_AGAIN;
    } else {
      gameMsg.textContent = "GAME OVER. SCORE " + pad(score) + ". " + SAY_AGAIN;
    }
  }

  function stopGame() {
    window.clearInterval(timer);
    timer = null;
    alive = false;
  }

  function startGame() {
    if (!L.isUnlocked(read, KEYS)) { show("7"); return; }
    if (current !== "7") { show("7"); }
    stopGame();
    reset();
    alive = true;
    tick = 190;
    gameMsg.textContent = touch ? "Swipe to steer." : "Steer with the arrow keys or 2 4 6 8.";
    timer = window.setInterval(step, tick);
  }

  function turn(k) {
    if (!alive) { return; }
    var d = { "2": { x: 0, y: -1 }, "8": { x: 0, y: 1 }, "4": { x: -1, y: 0 }, "6": { x: 1, y: 0 } }[k];
    if (!d || (d.x === -dir.x && d.y === -dir.y)) { return; }   // no instant reverse
    nextDir = d;
  }

  /* Swipe anywhere on the screen to steer, only while playing, so swipes still scroll every other screen. */
  var tx = 0, ty = 0;
  function swipeStart(e) { tx = e.changedTouches[0].clientX; ty = e.changedTouches[0].clientY; }
  function swipeEnd(e) {
    var dx = e.changedTouches[0].clientX - tx, dy = e.changedTouches[0].clientY - ty;
    if (Math.abs(dx) < 16 && Math.abs(dy) < 16) { return; }
    if (Math.abs(dx) > Math.abs(dy)) { turn(dx > 0 ? "6" : "4"); } else { turn(dy > 0 ? "8" : "2"); }
  }
  view.addEventListener("touchstart", function (e) { if (playing()) { swipeStart(e); } }, { passive: true });
  view.addEventListener("touchend", function (e) { if (playing()) { swipeEnd(e); } }, { passive: true });
  playBtn.addEventListener("click", startGame);
  cv.addEventListener("click", function () { if (!alive) { startGame(); } });

  hiEl.textContent = pad(hi);
  gameMsg.textContent = SAY_START;
  reset();

  /* ---------- start: a deep link (#menu, #3, #games), else the splash then the menu ---------- */
  var deep = L.screenFromHash(window.location.hash, KEYS);
  paintLock();
  if (deep) { show(deep, false); }
  else if (reduced) { show("menu", false); }
  else { window.setTimeout(function () { if (current === "splash") { show("menu", false); } }, 2400); }
}());
