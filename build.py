#!/usr/bin/env python3
"""handset: any newsletter becomes a playable phone page.

  python3 build.py edition.json --out out/ [--motif analog|cyberpunk|y2k-blog] [--style style.json]

Writes:
  out/index.html   the public twin, no gate (share this one)
  out/gated.html   the gated twin, an email gate in front (only when gate.enabled is true)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from html import escape
from html.parser import HTMLParser
from pathlib import Path

import handset_render as hr
from handset_render import MOTIFS, find_style, load_style, render_page, resolve_motif  # noqa: F401

CODE_RE = re.compile(r"^[A-Z0-9]{3,20}$")
EMAIL_RE = re.compile(r"^[^\s@<>\"']+@[^\s@<>\"']+\.[^\s@<>\"']{2,}$")
HTTPS_RE = re.compile(r"^https://[^\s<>\"']+$", re.I)
HTTP_RE = re.compile(r"^https?://[^\s<>\"']+$", re.I)


class EditionError(ValueError):
    """A problem with edition.json, worded for a beginner."""


# ---------- the HTML allowlist ----------

ALLOWED = {"p", "b", "strong", "i", "em", "u", "a", "ul", "ol", "li", "br", "h3", "blockquote", "code", "small", "mark"}
VOID = {"br"}
DROP_CONTENT = {"script", "style", "iframe", "object", "embed", "template", "noscript", "svg", "math", "head", "title"}


class _Clean(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.open: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in DROP_CONTENT:
            self.skip += 1
            return
        if self.skip or tag not in ALLOWED:
            return
        if tag == "a":
            href = dict(attrs).get("href") or ""
            href = href.strip()
            if not (HTTP_RE.match(href) or href.lower().startswith("mailto:")) or any(c in href for c in "<>\"'` "):
                self.out.append("<a>")
            else:
                self.out.append(f'<a href="{escape(href, quote=True)}" target="_blank" rel="noopener noreferrer">')
        else:
            self.out.append(f"<{tag}>")
        if tag not in VOID:
            self.open.append(tag)

    def handle_startendtag(self, tag, attrs):
        if tag in VOID and not self.skip:
            self.out.append(f"<{tag}>")

    def handle_endtag(self, tag):
        if tag in DROP_CONTENT:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip or tag not in ALLOWED or tag in VOID or tag not in self.open:
            return
        while self.open:
            t = self.open.pop()
            self.out.append(f"</{t}>")
            if t == tag:
                break

    def handle_data(self, data):
        if not self.skip:
            self.out.append(escape(data, quote=False))

    def result(self) -> str:
        while self.open:
            self.out.append(f"</{self.open.pop()}>")
        return "".join(self.out).strip()


def sanitize_html(raw: str) -> str:
    """Keep only plain reading tags (paragraphs, bold, italics, lists, links, quotes). Everything else is dropped:
    scripts, styles, event handlers, javascript: links, images, iframes. Plain text with no tags becomes paragraphs."""
    raw = str(raw or "")
    if "<" not in raw:
        paras = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
        return "".join(f"<p>{escape(p, quote=False)}</p>".replace("\n", "<br>") for p in paras)
    c = _Clean()
    c.feed(raw)
    c.close()
    return c.result()


# ---------- edition.json ----------

def _s(v: object, limit: int = 300) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()[:limit]


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:40] or "edition"


def load_edition(data: dict | str | Path) -> dict:
    """Read and check an edition. Returns a clean dict the renderer trusts. Raises EditionError."""
    if not isinstance(data, dict):
        path = Path(data)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise EditionError(f"Could not open {path}. Check the file name and try again. ({exc.strerror})") from exc
        except ValueError as exc:
            raise EditionError(f"{path} is not valid JSON: {exc}. A missing comma or quote is the usual cause.") from exc
    if not isinstance(data, dict):
        raise EditionError("edition.json should hold one object, starting with { and ending with }.")
    title = _s(data.get("title"), 80)
    if not title:
        raise EditionError('Your edition needs a "title".')
    sections_in = data.get("sections")
    if not isinstance(sections_in, list) or not sections_in:
        raise EditionError('Your edition needs "sections": a list of 1 to 6, each with a title and html.')
    if len(sections_in) > 6:
        raise EditionError(f"The keypad holds 6 sections and this edition has {len(sections_in)}. Merge or trim to 6.")
    sections, seen = [], set()
    for i, s in enumerate(sections_in, start=1):
        if not isinstance(s, dict):
            raise EditionError(f"Section {i} should be an object with a title and html.")
        key = _s(s.get("key") or i, 2)
        if key not in {"1", "2", "3", "4", "5", "6"}:
            raise EditionError(f'Section {i} has key "{key}". Keys are 1 to 6.')
        if key in seen:
            raise EditionError(f"Two sections use key {key}. Each key opens one section.")
        seen.add(key)
        stitle = _s(s.get("title"), 60)
        if not stitle:
            raise EditionError(f"Section {key} needs a title.")
        body = sanitize_html(s.get("html") or "")
        if not body:
            raise EditionError(f'Section {key} ("{stitle}") has no words in "html" yet.')
        label = _s(s.get("label"), 10) or stitle.split(" ")[0][:8]
        sections.append({"key": key, "title": stitle, "label": label, "html": body})
    sections.sort(key=lambda x: x["key"])

    share = data.get("share") if isinstance(data.get("share"), dict) else {}
    share_url = _s(share.get("url"), 500)
    if share_url and not HTTP_RE.match(share_url):
        raise EditionError('share.url should start with https:// (the public link to this page), or be left empty.')
    author = data.get("author") if isinstance(data.get("author"), dict) else {}
    email = _s(author.get("email"), 254)
    if email and not EMAIL_RE.match(email):
        raise EditionError(f'author.email "{email}" does not look like an email address.')
    a_url = _s(author.get("url"), 500)
    if a_url and not HTTP_RE.match(a_url):
        raise EditionError("author.url should start with https://, or be left empty.")

    gate_in = data.get("gate") if isinstance(data.get("gate"), dict) else {}
    enabled = gate_in.get("enabled") is True
    endpoint = _s(gate_in.get("endpoint"), 500)
    if enabled and not HTTPS_RE.match(endpoint):
        raise EditionError("The email gate is on, so gate.endpoint needs your form address starting with https://. "
                           "Turn the gate off with \"enabled\": false if you do not have one yet.")
    code = _s(gate_in.get("code"), 20).upper() or re.sub(r"[^A-Z0-9]", "", title.upper())[:12] or "EDITION"
    if not CODE_RE.match(code):
        code = (re.sub(r"[^A-Z0-9]", "", code) + "EDN")[:20]

    cta = _s(data.get("cta"), 40) or "Pick up the phone"
    return {
        "title": title, "issue": _s(data.get("issue"), 30), "date": _s(data.get("date"), 40),
        "brand": _s(data.get("brand"), 30) or title, "cta": cta.rstrip("."),
        "description": _s(data.get("description"), 200) or f"{title}, a phone page you can play.",
        "lang": _s(data.get("lang"), 10) if re.match(r"^[a-zA-Z-]{2,10}$", _s(data.get("lang"), 10)) else "en",
        "slug": slugify(f"{title} {_s(data.get('issue'), 30)}"),
        "sections": sections,
        "share": {"url": share_url, "text": _s(share.get("text"), 200)},
        "author": {"name": _s(author.get("name"), 60), "email": email, "url": a_url},
        "gate": {"enabled": enabled, "endpoint": endpoint if enabled else "", "code": code,
                 "headline": _s(gate_in.get("headline"), 80), "button": _s(gate_in.get("button"), 40) or cta.rstrip("."),
                 "text": _s(gate_in.get("text"), 240) or "Leave your email and the phone is yours.",
                 "fine": _s(gate_in.get("fine"), 160)},
    }


def build(edition: dict, out: Path, style: dict, motif: str) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    written = [out / "index.html"]
    written[0].write_text(render_page(edition, style, motif, gated=False), encoding="utf-8")
    gated = out / "gated.html"
    if edition["gate"]["enabled"]:
        gated.write_text(render_page(edition, style, motif, gated=True), encoding="utf-8")
        written.append(gated)
    elif gated.exists():
        gated.unlink()  # an old gated twin from an earlier build would be stale
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Turn edition.json into a playable phone page.")
    ap.add_argument("edition", type=Path, help="your edition.json")
    ap.add_argument("--out", type=Path, default=Path("out"), help="folder for the pages (default: out)")
    ap.add_argument("--motif", choices=MOTIFS, help="analog, cyberpunk or y2k-blog (default: style.json, then cyberpunk)")
    ap.add_argument("--style", type=Path, help="a style.json somewhere else")
    args = ap.parse_args(argv)
    try:
        edition = load_edition(args.edition)
    except EditionError as exc:
        print(f"Not built yet: {exc}", file=sys.stderr)
        return 2
    style = load_style(find_style(args.style))
    motif = resolve_motif(args.motif, style)
    files = build(edition, args.out, style, motif)
    print(f"Built {edition['title']} in the {motif} look, {len(edition['sections'])} sections.")
    print(f"Public page: {files[0]}")
    if len(files) > 1:
        print(f"Gated page:  {files[1]} (email gate posts to {edition['gate']['endpoint']})")
    else:
        print("No gated page: the email gate is off in edition.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
