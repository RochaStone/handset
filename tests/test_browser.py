"""Headless Chrome tests: every motif at 390px wide, and the page driven like a reader would.
Skipped with a clear message when Chrome or Chromium is not installed."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import build  # noqa: E402
import handset_render as hr  # noqa: E402

SCREENS = ["menu", "1", "2", "3", "4", "5", "6", "7", "share"]


@unittest.skipUnless(hr.find_chrome(), "Chrome or Chromium is not installed, so the 390px renders were not run")
class Mobile390(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ed = build.load_edition(ROOT / "examples" / "edition.sample.json")
        cls.style = hr.load_style()

    def assertFits(self, page, screens, label):
        ok, res = hr.measure_width(page, screens, 390)
        self.assertTrue(ok, res)
        for sid, r in res.items():
            self.assertLessEqual(r["scrollWidth"], 390, f"{label} screen {sid}: {r}")
            self.assertEqual(r["over"], [], f"{label} screen {sid}")

    def test_every_motif_fits_390_on_every_screen(self):
        for m in hr.MOTIFS:
            with self.subTest(motif=m):
                self.assertFits(hr.render_page(self.ed, self.style, m), SCREENS, m)

    def test_gated_twin_fits_390(self):
        for m in hr.MOTIFS:
            with self.subTest(motif=m):
                self.assertFits(hr.render_page(self.ed, self.style, m, gated=True), ["gate"], m + " gated")

    def test_the_overflow_check_can_fail(self):
        page = hr.render_page(self.ed, self.style, "cyberpunk").replace(
            '<div class="stage">', '<div style="width:600px;height:4px"></div><div class="stage">', 1)
        ok, res = hr.measure_width(page, ["menu"], 390)
        self.assertTrue(ok, res)
        self.assertGreater(res["menu"]["scrollWidth"], 390)

    def test_reading_all_six_earns_snake(self):
        script = """
        var key = function (k) { d.querySelector('[data-key="' + k + '"]').click(); };
        key("1");  /* leaves the splash for the menu */
        var steps = [];
        ["1", "2", "3", "4", "5"].forEach(function (k) { key(k); });
        key("7");
        steps.push({ lock: d.getElementById("gameSt").textContent, gameHidden: d.getElementById("gameBox").hidden,
                     marks: Array.prototype.map.call(d.querySelectorAll("#lockList .mark"), function (m) { return m.textContent; }).join("") });
        key("6"); key("7");
        steps.push({ lock: d.getElementById("gameSt").textContent, gameHidden: d.getElementById("gameBox").hidden,
                     lockHidden: d.getElementById("lockBox").hidden });
        d.getElementById("playBtn").click();
        steps.push({ msg: d.getElementById("gameMsg").textContent });
        key("0");
        steps.push({ menuOn: d.getElementById("scr-menu").classList.contains("is-on") });
        return steps;"""
        ok, res = hr.probe_page(hr.render_page(self.ed, self.style, "cyberpunk"), script)
        self.assertTrue(ok, res)
        self.assertNotIn("error", res if isinstance(res, dict) else {}, res)
        self.assertEqual(res[0], {"lock": "LOCKED 5/6", "gameHidden": True, "marks": "xxxxx."})
        self.assertEqual(res[1], {"lock": "PLAY", "gameHidden": False, "lockHidden": True})
        self.assertIn("Steer", res[2]["msg"])
        self.assertTrue(res[3]["menuOn"])

    def test_soft_keys_walk_the_edition(self):
        script = """
        var next = d.getElementById("navNext"), back = d.getElementById("navBack"), seen = [];
        var on = function () { return d.querySelector(".screen.is-on").id; };
        w.handsetShow("menu"); seen.push(on(), back.disabled);
        next.click(); seen.push(on());
        next.click(); seen.push(on());
        back.click(); seen.push(on());
        w.handsetShow("6"); next.click(); seen.push(on());
        next.click(); seen.push(on());
        return seen;"""
        ok, res = hr.probe_page(hr.render_page(self.ed, self.style, "analog"), script)
        self.assertTrue(ok, res)
        self.assertEqual(res, ["scr-menu", True, "scr-1", "scr-2", "scr-1", "scr-7", "scr-menu"])

    def test_gated_twin_shows_the_gate_and_public_twin_does_not(self):
        script = 'return { gate: d.getElementById("gate") ? !d.getElementById("gate").hidden : null, ' \
                 'locked: d.body.classList.contains("gated") };'
        ok, gated = hr.probe_page(hr.render_page(self.ed, self.style, "y2k-blog", gated=True), script)
        self.assertTrue(ok, gated)
        self.assertEqual(gated, {"gate": True, "locked": True})
        ok, public = hr.probe_page(hr.render_page(self.ed, self.style, "y2k-blog"), script)
        self.assertTrue(ok, public)
        self.assertEqual(public, {"gate": None, "locked": False})

    def test_gate_refuses_an_unfinished_email_without_posting(self):
        script = """
        var posted = false; w.fetch = function () { posted = true; return new Promise(function () {}); };
        d.getElementById("gateEmail").value = "me@";
        d.getElementById("gateForm").dispatchEvent(new w.Event("submit", { cancelable: true }));
        return { posted: posted, msg: d.getElementById("gateMsg").textContent };"""
        ok, res = hr.probe_page(hr.render_page(self.ed, self.style, "cyberpunk", gated=True), script)
        self.assertTrue(ok, res)
        self.assertFalse(res["posted"])
        self.assertIn("unfinished", res["msg"])

    def test_gate_posts_email_and_code_then_opens(self):
        script = """
        var sent = null;
        w.fetch = function (url, opts) { sent = { url: url, body: JSON.parse(opts.body), method: opts.method };
          return Promise.resolve({ ok: true, json: function () { return Promise.resolve({ code: "abc123" }); } }); };
        d.getElementById("gateEmail").value = "reader@example.com";
        d.getElementById("gateForm").dispatchEvent(new w.Event("submit", { cancelable: true }));
        return new Promise(function (resolve) { setTimeout(function () {
          var saved = null; try { saved = w.localStorage.getItem("handset:the-pocket-post-n-01:code"); } catch (e) { saved = "blocked"; }
          resolve({ sent: sent, gateHidden: d.getElementById("gate").hidden, locked: d.body.classList.contains("gated"),
                    menuOn: d.getElementById("scr-menu").classList.contains("is-on"), saved: saved });
        }, 300); });"""
        ok, res = hr.probe_page(hr.render_page(self.ed, self.style, "cyberpunk", gated=True), script)
        self.assertTrue(ok, res)
        self.assertEqual(res["sent"], {"url": "https://example.com/api/subscribe", "method": "POST",
                                       "body": {"email": "reader@example.com", "code": "POCKET01"}})
        self.assertTrue(res["gateHidden"])
        self.assertFalse(res["locked"])
        self.assertTrue(res["menuOn"])
        self.assertIn(res["saved"], ("ABC123", "blocked"))  # srcdoc frames may block storage; the code still opens the phone

    def test_gate_failure_keeps_the_door_and_says_so(self):
        script = """
        w.fetch = function () { return Promise.resolve({ ok: false, status: 500 }); };
        d.getElementById("gateEmail").value = "reader@example.com";
        d.getElementById("gateForm").dispatchEvent(new w.Event("submit", { cancelable: true }));
        return new Promise(function (resolve) { setTimeout(function () {
          resolve({ gateHidden: d.getElementById("gate").hidden, msg: d.getElementById("gateMsg").textContent,
                    btn: d.getElementById("gateGo").disabled });
        }, 300); });"""
        ok, res = hr.probe_page(hr.render_page(self.ed, self.style, "cyberpunk", gated=True), script)
        self.assertTrue(ok, res)
        self.assertFalse(res["gateHidden"])
        self.assertIn("did not go through", res["msg"])
        self.assertIn("hello@example.com", res["msg"])
        self.assertFalse(res["btn"])

    def test_snake_moves_on_its_own_clock(self):
        script = """
        ["1", "2", "3", "4", "5", "6"].forEach(function (k) { w.handsetShow(k); });
        w.handsetShow("7");
        d.getElementById("playBtn").click();
        var cv = d.getElementById("snake"), before = cv.toDataURL();
        return new Promise(function (resolve) { setTimeout(function () {
          resolve({ moved: cv.toDataURL() !== before, running: /Steer/.test(d.getElementById("gameMsg").textContent) ||
                    /GAME OVER|HIGH SCORE/.test(d.getElementById("gameMsg").textContent) });
        }, 1500); });"""
        ok, res = hr.probe_page(hr.render_page(self.ed, self.style, "y2k-blog"), script)
        self.assertTrue(ok, res)
        self.assertTrue(res["moved"], res)


if __name__ == "__main__":
    unittest.main()
