"""Smoke tests for handset. Run from the repo root: python3 -m unittest discover -s tests -v"""
from __future__ import annotations

import copy
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import build  # noqa: E402
import handset_render as hr  # noqa: E402

SAMPLE = ROOT / "examples" / "edition.sample.json"


def sample() -> dict:
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


class LogicInNode(unittest.TestCase):
    """The unlock and gate logic is plain JavaScript; Node's own test runner checks it."""

    def test_node_logic_suite(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is not installed, so the logic tests in tests/logic.test.mjs were not run")
        out = subprocess.run([node, "--test", "tests/logic.test.mjs"], cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertRegex(out.stdout, r"pass \d+")
        self.assertRegex(out.stdout, r"fail 0")


class Edition(unittest.TestCase):
    def test_sample_loads(self):
        ed = build.load_edition(SAMPLE)
        self.assertEqual(ed["title"], "The Pocket Post")
        self.assertEqual([s["key"] for s in ed["sections"]], list("123456"))
        self.assertTrue(ed["gate"]["enabled"])
        self.assertEqual(ed["gate"]["code"], "POCKET01")

    def assertRefused(self, data, words):
        with self.assertRaises(build.EditionError) as cm:
            build.load_edition(data)
        self.assertIn(words, str(cm.exception))

    def test_needs_title_and_sections(self):
        d = sample(); d["title"] = ""
        self.assertRefused(d, "title")
        d = sample(); d["sections"] = []
        self.assertRefused(d, "sections")

    def test_at_most_six_sections(self):
        d = sample(); d["sections"].append({"title": "Seven", "html": "<p>x</p>"})
        self.assertRefused(d, "6 sections")

    def test_keys_are_one_to_six_and_unique(self):
        d = sample(); d["sections"][1]["key"] = "1"
        self.assertRefused(d, "Two sections use key 1")
        d = sample(); d["sections"][0]["key"] = "7"
        self.assertRefused(d, "Keys are 1 to 6")

    def test_gate_on_needs_https_endpoint(self):
        d = sample(); d["gate"]["endpoint"] = "http://example.com/x"
        self.assertRefused(d, "https://")
        d = sample(); d["gate"]["enabled"] = False; d["gate"]["endpoint"] = ""
        self.assertFalse(build.load_edition(d)["gate"]["enabled"])

    def test_bad_links_and_email_refused(self):
        d = sample(); d["share"]["url"] = "javascript:alert(1)"
        self.assertRefused(d, "share.url")
        d = sample(); d["author"]["email"] = "not an email"
        self.assertRefused(d, "author.email")

    def test_fewer_sections_and_missing_keys(self):
        d = sample(); d["sections"] = [{"title": "Only", "html": "Plain words.\n\nTwo paragraphs."}]
        ed = build.load_edition(d)
        self.assertEqual(ed["sections"][0]["key"], "1")
        self.assertEqual(ed["sections"][0]["html"], "<p>Plain words.</p><p>Two paragraphs.</p>")
        page = hr.render_page(ed, hr.load_style(), "cyberpunk")
        self.assertIn('data-key="2" disabled', page)
        self.assertIn("LOCKED 0/1", page)


class Sanitiser(unittest.TestCase):
    def test_keeps_reading_tags(self):
        s = build.sanitize_html('<p>Hi <b>you</b> <i>there</i></p><ul><li>one</li></ul><a href="https://x.test/a?b=1">x</a>')
        self.assertIn("<b>you</b>", s)
        self.assertIn("<li>one</li>", s)
        self.assertIn('href="https://x.test/a?b=1"', s)
        self.assertIn('rel="noopener noreferrer"', s)

    def test_drops_scripts_handlers_and_bad_links(self):
        s = build.sanitize_html('<p onclick="x()">a</p><script>alert(1)</script><style>p{}</style>'
                                '<img src=x onerror=alert(1)><a href="javascript:alert(1)">b</a>'
                                '<iframe src="https://evil.test"></iframe><svg><script>1</script></svg>')
        self.assertNotIn("onclick", s)
        self.assertNotIn("alert", s)
        self.assertNotIn("<img", s)
        self.assertNotIn("javascript", s)
        self.assertNotIn("iframe", s)
        self.assertNotIn("<style", s)
        self.assertIn("<p>a</p>", s)
        self.assertIn("<a>b</a>", s)

    def test_escapes_text_and_closes_tags(self):
        s = build.sanitize_html("<p>1 < 2 & <b>bold")
        self.assertEqual(s, "<p>1 &lt; 2 &amp; <b>bold</b></p>")

    def test_titles_are_escaped_in_the_page(self):
        d = sample(); d["sections"][0]["title"] = '<img src=x onerror="alert(1)">'
        d["title"] = "A </script><script>alert(2)</script>"
        page = hr.render_page(build.load_edition(d), hr.load_style(), "cyberpunk", gated=True)
        self.assertNotIn('<img src=x', page)
        self.assertEqual(page.count("<script>"), 1)  # only the page's own script tag


class Motifs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ed = build.load_edition(SAMPLE)
        cls.style = hr.load_style()
        cls.pages = {m: hr.render_page(cls.ed, cls.style, m) for m in hr.MOTIFS}

    def test_each_motif_has_its_signature(self):
        self.assertIn("owner's manual", self.pages["analog"])
        self.assertIn("Fig. 1", self.pages["analog"])
        self.assertIn("handset:~$", self.pages["cyberpunk"])
        self.assertIn('class="cursor"', self.pages["cyberpunk"])
        self.assertIn("handset.exe", self.pages["y2k-blog"])
        self.assertIn("000,777", self.pages["y2k-blog"])
        self.assertIn("sign my guestbook", self.pages["y2k-blog"])
        for m, page in self.pages.items():
            self.assertIn(f'class="m-{m}', page)

    def test_same_handset_in_every_motif(self):
        for page in self.pages.values():
            for s in self.ed["sections"]:
                self.assertIn(f'id="scr-{s["key"]}"', page)
                self.assertIn(f'data-key="{s["key"]}"', page)
            for k in "7890":
                self.assertIn(f'data-key="{k}"', page)
            for part in ('id="scr-splash"', 'id="scr-menu"', 'id="scr-7"', 'id="lockList"', 'id="snake"',
                         'id="navBack"', 'id="navNext"', 'id="scr-share"'):
                self.assertIn(part, page)

    def test_cta_names_the_experience(self):
        for page in self.pages.values():
            self.assertIn("Pick up the phone", page)

    def test_default_motif_is_cyberpunk_and_choice_order(self):
        self.assertEqual(hr.resolve_motif(None, self.style), "cyberpunk")
        self.assertEqual(hr.resolve_motif("analog", self.style), "analog")
        self.assertEqual(hr.resolve_motif(None, {"motif": "y2k-blog"}), "y2k-blog")
        self.assertEqual(hr.resolve_motif(None, {"motif": "retro-tv"}), "cyberpunk")
        self.assertEqual(hr.resolve_motif(None, {"motif": "guest-check"}), "analog")
        self.assertEqual(hr.resolve_motif(None, {"motif": "nonsense"}), "cyberpunk")

    def test_no_glow_anywhere(self):
        for f in (ROOT / "assets").glob("*.css"):
            css = f.read_text(encoding="utf-8")
            self.assertNotIn("text-shadow", css, f.name)
            self.assertNotRegex(css, r"box-shadow:[^;]*\d+px\s+\d+px\s+[1-9]\d*px", f.name)  # no blurred shadows
            self.assertNotRegex(css, r"filter:\s*drop-shadow|blur\(", f.name)

    def test_page_is_self_contained_apart_from_fonts(self):
        for page in self.pages.values():
            self.assertNotRegex(page, r'<script[^>]+src=')
            for url in re.findall(r'(?:href|src)="(https?://[^"]+)"', page):
                self.assertTrue(url.startswith(("https://fonts.googleapis.com", "https://fonts.gstatic.com",
                                                "https://example.com")), url)


class Twins(unittest.TestCase):
    def test_public_twin_has_no_gate_and_no_endpoint(self):
        ed = build.load_edition(SAMPLE)
        page = hr.render_page(ed, hr.load_style(), "cyberpunk", gated=False)
        self.assertNotIn('id="gate"', page)
        self.assertNotIn("example.com/api/subscribe", page)
        self.assertIn('"gate": {"enabled": false}', page)

    def test_gated_twin_has_the_gate(self):
        ed = build.load_edition(SAMPLE)
        page = hr.render_page(ed, hr.load_style(), "cyberpunk", gated=True)
        self.assertIn('id="gate"', page)
        self.assertIn('id="gateForm"', page)
        self.assertIn('"endpoint": "https://example.com/api/subscribe"', page)
        self.assertIn('"code": "POCKET01"', page)
        self.assertIn('name="robots" content="noindex"', page)
        self.assertIn(">Pick up the phone</button>", page)

    def test_config_json_cannot_close_the_script(self):
        d = sample(); d["share"]["text"] = "</script><b>x</b>"
        page = hr.render_page(build.load_edition(d), hr.load_style(), "cyberpunk")
        cfg = re.search(r'<script type="application/json" id="handset-config">(.*?)</script>', page, re.S).group(1)
        self.assertNotIn("<", cfg)
        self.assertEqual(json.loads(cfg)["share"]["text"], "</script><b>x</b>")


class StyleFile(unittest.TestCase):
    def test_fallback_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cwd, home = tmp / "work", tmp / "home"
            (home / ".rocha-coded").mkdir(parents=True)
            cwd.mkdir()
            self.assertEqual(hr.find_style(None, cwd, home), hr.STYLE_EXAMPLE)
            (home / ".rocha-coded" / "style.json").write_text("{}")
            self.assertEqual(hr.find_style(None, cwd, home), home / ".rocha-coded" / "style.json")
            (cwd / "style.json").write_text("{}")
            self.assertEqual(hr.find_style(None, cwd, home), cwd / "style.json")
            explicit = tmp / "mine.json"; explicit.write_text("{}")
            self.assertEqual(hr.find_style(explicit, cwd, home), explicit)

    def test_user_style_inherits_only_palette_and_fonts(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "style.json"
            p.write_text(json.dumps({"palette": {"hero": "#112233", "accent": ""}, "fonts": {"masthead": "Bodoni Moda"},
                                     "motif": "y2k-blog"}))
            st = hr.load_style(p)
        example = json.loads(hr.STYLE_EXAMPLE.read_text())
        self.assertEqual(st["palette"]["hero"], "#112233")
        self.assertEqual(st["palette"]["accent"], example["palette"]["accent"])  # borrowed
        self.assertEqual(st["fonts"]["masthead"], "Bodoni Moda")
        self.assertEqual(st["fonts"]["mono"], example["fonts"]["mono"])  # borrowed
        for key in ("lines", "owner", "handle", "name", "references", "notes"):
            self.assertNotIn(key, st)  # never borrowed
        self.assertEqual(hr.resolve_motif(None, st), "y2k-blog")  # her own motif wins

    def test_her_lines_never_leak_into_a_user_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "style.json"
            p.write_text(json.dumps({"palette": {"hero": "#112233"}}))
            st = hr.load_style(p)
        ed = build.load_edition(SAMPLE)
        example = json.loads(hr.STYLE_EXAMPLE.read_text())
        for m in hr.MOTIFS:
            page = hr.render_page(ed, st, m)
            for line in example["lines"].values():
                self.assertNotIn(line, page, m)
                self.assertNotIn(line.lower(), page, m)
            self.assertIn("--ground: #112233;", page)

    def test_bundled_example_lines_show_only_with_the_bundled_style(self):
        ed = build.load_edition(SAMPLE)
        self.assertIn("build your founder world", hr.render_page(ed, hr.load_style(), "analog"))

    def test_bad_values_are_not_injected(self):
        st = {"palette": {"hero": "red;}</style><script>alert(1)</script>", "ink": "#123456"},
              "fonts": {"masthead": "x\"};@import url(evil)", "label": "Inter"}}
        head = hr.style_head(st)
        self.assertNotIn("alert", head)
        self.assertNotIn("evil", head)
        self.assertIn("--ink: #123456;", head)
        self.assertIn("family=Inter", head)
        self.assertIn("family=Silkscreen", head)

    def test_bundled_examples_share_keys(self):
        a = json.loads(hr.STYLE_EXAMPLE.read_text())
        b = json.loads((ROOT / "style.example.json").read_text())
        self.assertEqual(set(a), set(b))
        for k in ("palette", "fonts", "lines"):
            self.assertEqual(set(a[k]), set(b[k]), k)


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = build.main([str(a) for a in args])
        return code, out.getvalue(), err.getvalue()

    def test_writes_public_and_gated_twins(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = self.run_cli(SAMPLE, "--out", tmp, "--motif", "analog")
            self.assertEqual(code, 0)
            self.assertTrue((Path(tmp) / "index.html").is_file())
            self.assertTrue((Path(tmp) / "gated.html").is_file())
            self.assertIn("analog look", out)
            self.assertIn("m-analog", (Path(tmp) / "gated.html").read_text())

    def test_gate_off_writes_no_gated_twin_and_clears_an_old_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.run_cli(SAMPLE, "--out", tmp)
            d = sample(); d["gate"]["enabled"] = False
            e = tmp / "e.json"; e.write_text(json.dumps(d))
            code, out, _ = self.run_cli(e, "--out", tmp)
            self.assertEqual(code, 0)
            self.assertFalse((tmp / "gated.html").exists())
            self.assertIn("No gated page", out)

    def test_friendly_error_for_broken_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            e = Path(tmp) / "e.json"; e.write_text('{"title": "x",}')
            code, _, err = self.run_cli(e, "--out", tmp)
            self.assertEqual(code, 2)
            self.assertIn("not valid JSON", err)

    def test_no_em_dashes_or_banned_words_in_shipped_text(self):
        for f in [*ROOT.glob("*.md"), *ROOT.glob("*.py"), *(ROOT / "assets").glob("*"), SAMPLE, *ROOT.glob("tests/*")]:
            if not f.is_file():
                continue
            text = f.read_text(encoding="utf-8")
            self.assertNotIn(chr(0x2014), text, f.name)
            prose = text.lower().replace('"simply" or "just"', "")  # the rule itself, quoted in SKILL.md
            self.assertNotRegex(prose, r"\bsimply\b|\bjust\b", f.name)


if __name__ == "__main__":
    unittest.main()
