"""Rendering for handset: style.json, the three motif skins, and headless Chrome tools.

One function, render_page(), draws the same handset from the same edition in three motif families:
  analog     a printed phone manual page with the handset drawn in ink
  cyberpunk  a plum LCD with pixel type and scanlines, gold screws (the default for this tool)
  y2k-blog   the handset inside a cream OS 9 window with a blog sidebar
Motif is structure; style.json palette and fonts are colour and type, so every family re-tones.
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
STYLE_EXAMPLE = HERE / "examples" / "style.rocha-coded.json"
MOTIFS = ("analog", "cyberpunk", "y2k-blog")
DEFAULT_MOTIF = "cyberpunk"
CSS_FILES = {"analog": ["handset.css", "motif-analog.css"], "cyberpunk": ["handset.css", "motif-cyberpunk.css"],
             "y2k-blog": ["handset.css", "motif-y2k.css"]}
MOTIF_ALIASES = {"guest-check": "analog", "front-page": "analog", "magazine-scrawl": "analog",
                 "pink-paper": "analog", "rotary": "analog", "leopard": "analog", "neutral": "analog",
                 "retro-tv": "cyberpunk", "sticker-collage": "y2k-blog", "y2k": "y2k-blog", "blog": "y2k-blog"}
COLOUR = re.compile(r"^#[0-9A-Fa-f]{3,8}$")
FONT_NAME = re.compile(r"^[A-Za-z0-9 ]{1,40}$")
PALETTE_VARS = {"hero": "--ground", "wine": "--wine", "accent": "--candy", "paper_pink": "--paper",
                "paper": "--cream", "ink": "--ink", "marker": "--marker", "plum": "--plum", "gold": "--gold"}
FONT_VARS = {
    "masthead": ("--serif", 'Georgia, "Times New Roman", serif', "opsz,wght@9..144,400;9..144,900"),
    "body": ("--body", "Georgia, serif", ""),
    "label": ("--label", 'system-ui, "Helvetica Neue", Arial, sans-serif', "wght@400;800"),
    "mono": ("--mono", "ui-monospace, Menlo, Consolas, monospace", "wght@400;500"),
    "scrawl": ("--scrawl", '"Marker Felt", "Comic Sans MS", cursive', ""),
    "pixel": ("--pixel", '"Pixelify Sans", ui-monospace, monospace', ""),
}
HOUSE_PIXEL_FONT = "Silkscreen"
PIXEL_HEART = ('<svg class="pix" viewBox="0 0 7 6" width="14" height="12" aria-hidden="true" shape-rendering="crispEdges">'
               '<path fill="currentColor" d="M1 0h2v1h1V0h2v1h1v2H6v1H5v1H4v1H3V5H2V4H1V3H0V1h1z"/></svg>')
PIXEL_STAR = ('<svg class="pix" viewBox="0 0 5 5" width="12" height="12" aria-hidden="true" shape-rendering="crispEdges">'
              '<path fill="currentColor" d="M2 0h1v2h2v1H3v2H2V3H0V2h2z"/></svg>')
SPLASH_ART = ('<svg class="splash-art" viewBox="0 0 13 11" width="78" height="66" aria-hidden="true" shape-rendering="crispEdges">'
              '<path fill="currentColor" d="M2 0h3v1h1v1h1V1h1V0h3v1h1v1h1v4h-1v1h-1v1h-1v1h-1v1H8v1H5v-1H4V9H3V8H2V7H1V6H0V2h1V1h1z"/>'
              '</svg>')


def _e(s: object) -> str:
    return html.escape(str(s), quote=True)


# ---------- style.json ----------

def find_style(explicit: Path | None = None, cwd: Path | None = None, home: Path | None = None) -> Path:
    """The shared Rocha Coded fallback order: --style, ./style.json, ~/.rocha-coded/style.json, bundled example."""
    candidates = [explicit] if explicit else []
    candidates += [Path(cwd or Path.cwd()) / "style.json",
                   Path(home or Path.home()) / ".rocha-coded" / "style.json", STYLE_EXAMPLE]
    return next((Path(c) for c in candidates if c and Path(c).is_file()), STYLE_EXAMPLE)


def load_style(path: Path | None = None) -> dict:
    path = Path(path) if path else STYLE_EXAMPLE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"Could not read style file {path} ({exc}). Using the bundled example look.", file=sys.stderr)
        path = STYLE_EXAMPLE
        try:
            data = json.loads(STYLE_EXAMPLE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
    data = data if isinstance(data, dict) else {}
    if path.resolve() == STYLE_EXAMPLE.resolve():
        return {**data, "_bundled": True}  # the shared example's motif yields to this tool's default
    return inherit_style(data)


def inherit_style(user: dict) -> dict:
    """A user's style borrows ONLY missing palette and font entries from the bundled example.
    Lines, owner, handle, name, references and notes never fall back to Rocha's."""
    try:
        example = json.loads(STYLE_EXAMPLE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        example = {}
    merged = dict(user)
    for key in ("palette", "fonts"):
        mine = user.get(key) if isinstance(user.get(key), dict) else {}
        base = example.get(key) if isinstance(example.get(key), dict) else {}
        merged[key] = {**base, **{k: v for k, v in mine.items() if str(v or "").strip()}}
    return merged


def resolve_motif(requested: str | None, style: dict) -> str:
    """--motif wins, then style.json motif, then cyberpunk (this tool's default). Old names map to a family."""
    own = None if style.get("_bundled") else style.get("motif")
    raw = str(requested or own or DEFAULT_MOTIF).strip().lower()
    raw = MOTIF_ALIASES.get(raw, raw)
    return raw if raw in MOTIFS else DEFAULT_MOTIF


def style_head(style: dict) -> str:
    """Font links plus a :root block that overrides colours and fonts. Values are validated, never pasted raw."""
    palette = style.get("palette") if isinstance(style.get("palette"), dict) else {}
    fonts = dict(style.get("fonts")) if isinstance(style.get("fonts"), dict) else {}
    if not str(fonts.get("pixel") or "").strip():
        fonts["pixel"] = HOUSE_PIXEL_FONT
    css_vars, families = [], []
    for key, var in PALETTE_VARS.items():
        val = str(palette.get(key) or "").strip()
        if COLOUR.match(val):
            css_vars.append(f"{var}: {val};")
    for key, (var, fallback, axes) in FONT_VARS.items():
        fam = str(fonts.get(key) or "").strip()
        if not FONT_NAME.match(fam):
            continue
        css_vars.append(f'{var}: "{fam}", {fallback};')
        q = fam.replace(" ", "+")
        families.append(f"https://fonts.googleapis.com/css2?family={q}{':' + axes if axes else ''}&display=swap")
        if axes:  # if the family lacks those axes, the plain request still loads it
            families.append(f"https://fonts.googleapis.com/css2?family={q}&display=swap")
    links = "\n".join(f'<link rel="stylesheet" href="{_e(u)}">' for u in dict.fromkeys(families))
    return links + f"\n<style>:root {{ {' '.join(css_vars)} }}</style>"


def _line(style: dict, key: str) -> str:
    lines = style.get("lines") if isinstance(style.get("lines"), dict) else {}
    return str(lines.get(key) or "").strip()


# ---------- the page ----------

def _handset(ed: dict) -> str:
    by_key = {s["key"]: s for s in ed["sections"]}
    keys = [s["key"] for s in ed["sections"]]
    total = len(keys)
    menu, screens, lock = [], [], []
    for i, s in enumerate(ed["sections"]):
        menu.append(f'<li><button type="button" data-go="{s["key"]}"><span class="t">{s["key"]} {_e(s["title"])}</span>'
                    f'<span class="st" data-st="{s["key"]}">new</span></button></li>')
        nxt = ed["sections"][i + 1]["title"] if i + 1 < total else "Games"
        screens.append(
            f'<section class="screen" id="scr-{s["key"]}" aria-label="{_e(s["title"])}">'
            f'<h2 tabindex="-1"><span>{_e(s["title"])}</span><span class="pos">{i + 1}/{total}</span></h2>'
            f'<div class="body">{s["html"]}</div>'
            f'<p class="nextcue">NEXT <b>{_e(nxt)}</b></p></section>')
        lock.append(f'<li><span class="mark" data-lk="{s["key"]}">.</span><span>{s["key"]} {_e(s["title"])}</span></li>')
    menu.append('<li><button type="button" data-go="7"><span class="t">7 Games</span>'
                f'<span class="st" id="gameSt">LOCKED 0/{total}</span></button></li>')
    keypad = []
    for n in "123456789":
        if n in by_key:
            label = by_key[n]["label"]
            keypad.append(f'<button type="button" class="key" data-key="{n}" aria-label="{n}, {_e(by_key[n]["title"])}">'
                          f'<b>{n}</b><span>{_e(label)}</span></button>')
        elif n in "123456":
            keypad.append(f'<button type="button" class="key" data-key="{n}" disabled aria-label="{n}, empty">'
                          f'<b>{n}</b><span>&middot;</span></button>')
        elif n == "7":
            keypad.append('<button type="button" class="key key--hot" data-key="7" aria-label="7, Snake, locked">'
                          '<b>7</b><span>Snake</span></button>')
        elif n == "8":
            keypad.append('<button type="button" class="key" data-key="8" aria-label="8, share"><b>8</b><span>Share</span></button>')
        else:
            who = "Write" if ed["author"]["email"] else "Visit"
            dis = "" if (ed["author"]["email"] or ed["author"]["url"]) else " disabled"
            keypad.append(f'<button type="button" class="key" data-key="9" aria-label="9, {who.lower()} to the author"{dis}>'
                          f'<b>9</b><span>{who}</span></button>')
    keypad.append('<button type="button" class="key key--zero" data-key="0" aria-label="0, menu"><b>0</b><span>Menu</span></button>')
    meta = " · ".join(x for x in (ed["issue"], ed["date"]) if x)
    return f"""<div class="phone" id="phone">
<i class="screw tl"></i><i class="screw tr"></i><i class="screw bl"></i><i class="screw br"></i>
<div class="phone__ear"></div>
<div class="phone__brand"><span>{_e(ed["brand"])}</span><span class="leds" aria-hidden="true"><i></i><i></i></span></div>
<div class="lcd">
<div class="lcd__status"><span class="bars" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
<span class="net">{_e(ed["title"])}</span><span class="batt" aria-hidden="true"></span></div>
<div class="lcd__view" id="view" tabindex="0" role="region" aria-label="Phone screen">
<section class="screen is-on" id="scr-splash" aria-label="Starting up">{SPLASH_ART}
<p class="splash-title">{_e(ed["title"])}</p><p class="splash-meta">{_e(meta)}</p><p class="splash-go">PRESS ANY KEY</p></section>
<section class="screen" id="scr-menu" aria-label="Menu"><h2 tabindex="-1"><span>Menu</span><span class="pos">{_e(ed["issue"] or "MENU")}</span></h2>
<ul class="menu">{"".join(menu)}</ul>
<p class="menu-foot">8 share · 9 {"write to" if ed["author"]["email"] else "visit"} {_e(ed["author"]["name"] or "the author")} · 0 menu</p></section>
{"".join(screens)}
<section class="screen" id="scr-7" aria-label="Games"><h2 tabindex="-1"><span>Games</span><span class="pos">7</span></h2>
<div id="lockBox"><p class="lock-note">Snake unlocks when every section is read. Your checklist:</p>
<ul class="locklist" id="lockList">{"".join(lock)}</ul></div>
<div id="gameBox" hidden><div class="hud"><span>SCORE <b id="score">000</b></span><span>HI <b id="hi">000</b></span></div>
<canvas id="snake" width="288" height="216" aria-label="Snake. Press Play, then steer with the arrow keys."></canvas>
<button type="button" class="play-btn" id="playBtn">PLAY</button><p class="game-msg" id="gameMsg" aria-live="polite"></p></div></section>
<section class="screen" id="scr-share" aria-label="Share"><h2 tabindex="-1"><span>Share</span><span class="pos">8</span></h2>
<p class="lock-note" id="shareMsg" aria-live="polite">Copy this link and send it on:</p><p class="share-link" id="shareLink"></p></section>
</div></div>
<div class="nav"><button type="button" class="soft" id="navBack" disabled>Back</button>
<button type="button" class="soft" id="navNext">Next</button></div>
<div class="keypad" id="keypad">{"".join(keypad)}</div>
</div>"""


def _deck(ed: dict) -> str:
    n = len(ed["sections"])
    return (f'<p class="deck"><b>{_e(ed["cta"])}.</b> Press 1 to {n} to read. '
            f'Read all {n} and Snake unlocks on 7.</p>')


HINT = ('<p class="hint">Keys: 1 to 6 sections · 7 Snake · 8 share · 9 write · 0 menu. '
        'Arrow keys work too.</p>')


def _analog(ed: dict, style: dict, phone: str) -> str:
    rows = [f'<li><b>{s["key"]}</b><span><em>key {s["key"]}</em>{_e(s["title"])}</span></li>' for s in ed["sections"]]
    rows += ['<li class="hot"><b>7</b><span><em>key 7</em>Snake, earned when every section is read</span></li>',
             '<li><b>8</b><span><em>key 8</em>Share this edition with a friend</span></li>',
             f'<li><b>9</b><span><em>key 9</em>Write to {_e(ed["author"]["name"] or "the author")}</span></li>',
             '<li><b>0</b><span><em>key 0</em>Back to the menu</span></li>']
    scrawl = _line(style, "scrawl")
    meta = "<br>".join(_e(x) for x in (ed["issue"], ed["date"]) if x)
    return f"""<article class="manual">
<header class="manual__head"><p class="kicker">owner's manual · operating your edition</p>
<h1>{_e(ed["title"])}</h1><p class="meta">{meta}</p></header>
<div class="manual__body"><figure class="fig">{phone}<figcaption>Fig. 1 · the handset, front view</figcaption></figure>
<div>{_deck(ed)}<ol class="callouts">{"".join(rows)}</ol>{HINT}
{f'<p class="scrawl">{_e(scrawl)}</p>' if scrawl else ""}</div></div>
<footer class="manual__foot"><span>{_e(ed["author"]["name"])}</span><span>page 1 of 1</span></footer>
</article>"""


def _cyberpunk(ed: dict, phone: str) -> str:
    meta = "".join(f"<span>{_e(x)}</span>" for x in (ed["issue"], ed["date"]) if x)
    return f"""<header class="cp-head"><p class="prompt">handset:~$ <b>open {_e(ed["slug"])}</b><span class="cursor" aria-hidden="true"></span></p>
<h1>{_e(ed["title"])}</h1><p class="meta">{meta}</p></header>
{_deck(ed)}{phone}
<p class="cp-bar"><span>[{"#" * len(ed["sections"])}] {len(ed["sections"])} sections</span><span>7 = snake</span></p>{HINT}"""


def _y2k(ed: dict, style: dict, phone: str) -> str:
    a = ed["author"]
    guest = (f"mailto:{a['email']}?subject={quote(ed['title'])}" if a["email"] else a["url"])
    mood = _line(style, "celebrate").lower()
    reading = " · ".join(x for x in (ed["title"], ed["issue"]) if x)
    return f"""<div class="win"><div class="titlebar"><div class="btns" aria-hidden="true"><i></i><i></i><i></i></div>
<span class="title px">handset.exe</span></div>
<div class="marquee" aria-hidden="true"><span>{_e(ed["title"])} · {_e(ed["issue"])} · {_e(ed["cta"].lower())} · press 1 to {len(ed["sections"])}</span></div>
<div class="winbody"><main class="post"><h1>{_e(ed["title"])}</h1>{_deck(ed)}{phone}{HINT}</main>
<aside class="side">
<section><h3 class="px">about me</h3><p>{_e(a["name"] or "the author")}</p></section>
<section><h3 class="px">currently reading</h3><p>{_e(reading)}</p></section>
<section><h3 class="px">mood</h3><p>✧ {_e(mood)}</p></section>
<section class="counter"><h3 class="px">hit counter</h3><p>you are visitor no.<br><b>000,777</b></p></section>
<section><h3 class="px">guestbook</h3><p>{PIXEL_HEART} {f'<a href="{_e(guest)}">sign my guestbook</a>' if guest else "sign my guestbook"}</p></section>
<p class="sparkle">{PIXEL_STAR}{PIXEL_HEART}{PIXEL_STAR}</p>
<p class="updated">last updated {_e(ed["date"] or ed["issue"])}</p>
</aside></div></div>"""


def _gate(ed: dict) -> str:
    g = ed["gate"]
    fine = f'<p class="gate-fine">{_e(g["fine"])}</p>' if g["fine"] else ""
    return f"""<div id="gate" role="dialog" aria-modal="true" aria-labelledby="gateTitle" hidden>
<div class="gate-card"><p class="kicker">{_e(" · ".join(x for x in (ed["issue"], ed["date"]) if x))}</p>
<h2 id="gateTitle">{_e(g["headline"] or ed["title"])}</h2><p>{_e(g["text"])}</p>
<form id="gateForm" novalidate><label for="gateEmail">Your email</label>
<input id="gateEmail" name="email" type="email" autocomplete="email" inputmode="email" required>
<button class="gate-go" id="gateGo" type="submit">{_e(g["button"])}</button>
<p class="gate-msg" id="gateMsg" aria-live="polite"></p></form>{fine}</div></div>"""


def _config_json(ed: dict, gated: bool) -> str:
    cfg = {"slug": ed["slug"], "title": ed["title"], "keys": [s["key"] for s in ed["sections"]],
           "sections": [{"key": s["key"], "title": s["title"]} for s in ed["sections"]],
           "share": {"url": ed["share"]["url"], "text": ed["share"]["text"]},
           "author": {"name": ed["author"]["name"], "email": ed["author"]["email"], "url": ed["author"]["url"]},
           "gate": ({"enabled": True, "endpoint": ed["gate"]["endpoint"], "code": ed["gate"]["code"]}
                    if gated else {"enabled": False})}
    # safe inside <script>: no "</" and no HTML comment openers can close or confuse the tag
    return json.dumps(cfg, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def render_page(ed: dict, style: dict | None = None, motif: str = DEFAULT_MOTIF, gated: bool = False) -> str:
    """The one render path. `ed` is a validated edition (see build.load_edition)."""
    style = style if style is not None else load_style()
    motif = resolve_motif(motif, style)
    css = "\n".join((ASSETS / f).read_text(encoding="utf-8") for f in CSS_FILES[motif])
    js = (ASSETS / "logic.js").read_text(encoding="utf-8") + "\n" + (ASSETS / "handset.js").read_text(encoding="utf-8")
    phone = _handset(ed)
    if motif == "analog":
        inner = _analog(ed, style, phone)
    elif motif == "y2k-blog":
        inner = _y2k(ed, style, phone)
    else:
        inner = _cyberpunk(ed, phone)
    robots = '<meta name="robots" content="noindex">' if gated else ""
    return f"""<!doctype html>
<html lang="{_e(ed["lang"])}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{_e(ed["title"])}{" · " + _e(ed["issue"]) if ed["issue"] else ""}</title>
<meta name="description" content="{_e(ed["description"])}">{robots}
<meta name="color-scheme" content="light">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<style>{css}</style>
{style_head(style)}
</head>
<body class="m-{motif}{" has-gate" if gated else ""}">
<div class="stage">{inner}</div>
{_gate(ed) if gated else ""}
<script type="application/json" id="handset-config">{_config_json(ed, gated)}</script>
<script>{js}</script>
</body></html>
"""


# ---------- headless Chrome ----------

def find_chrome() -> str | None:
    env = os.environ.get("CHROME_PATH")
    if env and Path(env).exists():
        return env
    for cmd in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "microsoft-edge"):
        p = shutil.which(cmd)
        if p:
            return p
    for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/Applications/Chromium.app/Contents/MacOS/Chromium",
              "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"):
        if Path(p).exists():
            return p
    return None


def _chrome(args: list[str], timeout: int = 90) -> tuple[bool, str]:
    chrome = find_chrome()
    if not chrome:
        return False, "No Chrome or Chromium found. The HTML pages are ready; install Chrome or set CHROME_PATH for pictures."
    with tempfile.TemporaryDirectory() as profile:
        cmd = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
               "--no-default-browser-check", f"--user-data-dir={profile}", "--force-device-scale-factor=1", *args]
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            cmd.insert(1, "--no-sandbox")
        try:
            out = subprocess.run(cmd, capture_output=True, timeout=timeout, check=False, text=True)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, f"Chrome could not run ({exc})."
    return True, out.stdout


def png_size(path: Path) -> tuple[int, int]:
    with Path(path).open("rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    return struct.unpack(">II", head[16:24])


def render_png(page: Path, png: Path, width: int, height: int, budget_ms: int = 6000, hash_: str = "") -> tuple[bool, str]:
    ok, msg = _chrome([f"--window-size={width},{height}", f"--virtual-time-budget={budget_ms}",
                       f"--screenshot={png}", Path(page).resolve().as_uri() + (f"#{hash_}" if hash_ else "")])
    if not ok:
        return False, msg
    if not Path(png).exists():
        return False, "Chrome ran but wrote no PNG."
    w, h = png_size(png)
    return True, f"{png} ({w}x{h})"


PROBE_HARNESS = """<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0">
<iframe id="f" style="border:0;width:%(w)dpx;height:844px"></iframe><pre id="out">pending</pre>
<script>
var f = document.getElementById("f");
f.srcdoc = %(page)s;
f.onload = function () { setTimeout(run, 400); };
function overflow(d, w) {
  var bad = [];
  Array.prototype.forEach.call(d.querySelectorAll("body *"), function (el) {
    var r = el.getBoundingClientRect();
    if (r.width && (r.right > w + 1 || r.left < -1) && !el.closest(".marquee") && !el.closest("[hidden]"))
      bad.push((el.id ? "#" + el.id : el.tagName.toLowerCase() + "." + el.className) + " " + Math.round(r.left) + ".." + Math.round(r.right));
  });
  return bad.slice(0, 5);
}
function run() {
  var w = f.contentWindow, d = f.contentDocument, res;
  var done = function (v) { document.getElementById("out").textContent = JSON.stringify(v); };
  try { res = (function (w, d, W) { %(script)s })(w, d, %(w)d); }
  catch (err) { res = { error: String(err) }; }
  if (res && typeof res.then === "function") { res.then(done, function (err) { done({ error: String(err) }); }); }
  else { done(res); }
}
</script></body></html>"""


def probe_page(page_html: str, script: str, width: int = 390) -> tuple[bool, dict | str]:
    """Load a page in a frame of `width` px in headless Chrome and run `script` (a JS function body that gets
    w, d, W and returns a JSON-able value or a Promise of one; `overflow(d, W)` lists elements wider than the frame).
    A frame is used because headless Chrome on macOS will not size a window under 500px."""
    with tempfile.TemporaryDirectory() as tmp:
        harness = Path(tmp) / "probe.html"
        harness.write_text(PROBE_HARNESS % {"w": width, "page": json.dumps(page_html).replace("</", "<\\/"),
                                            "script": script}, encoding="utf-8")
        ok, out = _chrome(["--virtual-time-budget=8000", "--dump-dom", harness.as_uri()], timeout=120)
    if not ok:
        return False, out
    m = re.search(r'<pre id="out">(.*?)</pre>', out, re.S)
    if not m or m.group(1) == "pending":
        return False, "The probe page did not finish."
    return True, json.loads(html.unescape(m.group(1)))


def measure_width(page_html: str, screens: list[str], width: int = 390) -> tuple[bool, dict | str]:
    """Open each screen in a `width` px frame and report how wide the page got and anything sticking out."""
    script = ("var res = {}; %s.forEach(function (id) { if (id !== 'gate' && w.handsetShow) w.handsetShow(id);"
              " res[id] = { scrollWidth: d.documentElement.scrollWidth, over: overflow(d, W) }; }); return res;"
              % json.dumps(screens))
    return probe_page(page_html, script, width)
