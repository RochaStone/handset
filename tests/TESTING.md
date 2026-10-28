# Testing

Everything below was run on 28 Oct 2026, on macOS with Python 3.12.8, Node 25.9.0 and Google Chrome 156.

## 1. The phone's rules, in Node
```sh
node --test tests/logic.test.mjs
```
Result: **20 tests, all pass.** `assets/logic.js` holds the rules as pure functions, with no page code. The tests cover:
- Snake stays locked until every section is read, in any order. Re-reading never double counts. The menu, games and share screens never count as read. Stale progress for a section that no longer exists does not unlock. An edition with three sections unlocks after three.
- the x-mark checklist (`x` read, `.` not yet) and the menu label (`LOCKED 5/6`, then `PLAY`)
- stored progress that is broken or odd is read as empty
- NEXT and BACK: menu, sections in order, Games, menu
- what each key does, including 1 to 6 doing nothing when that section does not exist
- deep links (`#menu`, `#3`, `#games`) open only real screens
- the gate: off in the public twin; closed with no code; a `?c=CODE` link opens it (upper-cased); malformed codes (too short, too long, symbols, broken encoding, `<script>`) do not; a code saved on the device opens it on return
- what the gate sends, `{email, code}`; the email check; the server's own code wins over the edition code after sign-up
- SHARE hands on the configured public link, else the page address with no `?c=` and no `#`, and never a `javascript:` link

`package.json` pins plain CommonJS for this folder, so the tests also run inside a home folder whose own `package.json` says `"type": "module"` (this machine has one; the tests failed before that pin).

## 2. Everything else, in Python and headless Chrome
```sh
python3 -m unittest discover -s tests -v
```
Result: **41 tests, all OK** (the Node suite above runs again as one of them). They cover:
- **edition.json:** the sample loads; refused with a plain-words reason: no title, no sections, more than 6, keys outside 1 to 6, two sections on one key, a gate with no `https://` address, a `javascript:` share link, a broken email, broken JSON. Fewer sections work and their keys show disabled.
- **the cleaner:** paragraphs, bold, italics, lists, quotes and `https`/`mailto` links stay; scripts, styles, `onclick`, images, iframes, SVG and `javascript:` links go; stray `<` and `&` are escaped; unclosed tags are closed. Titles cannot inject HTML. The settings block inside the page cannot close its own script tag.
- **three motifs from one function:** analog (owner's manual, Fig. 1), cyberpunk (`handset:~$` prompt, block cursor), y2k-blog (`handset.exe`, hit counter `000,777`, sign my guestbook); every motif carries the same screens and keys; "Pick up the phone" in all three; cyberpunk is the default, `--motif` wins, then her own style.json, and old motif names map to a family; no text shadow, blur or glow in any stylesheet; no outside scripts.
- **twins:** the public twin has no gate and no trace of the sign-up address; the gated twin has the gate, the address, the code and a noindex tag.
- **style.json:** the fallback order (`--style`, `./style.json`, `~/.rocha-coded/style.json`, bundled); a user's file borrows only missing colours and fonts, never lines, owner, handle, name, references or notes; with a user's file none of Rocha's lines appear in any motif; bad colour and font values are not injected; both bundled style files share the same keys.
- **the command line:** writes `index.html` and `gated.html`; with the gate off, writes no gated twin and removes an old one; no em dashes, "simply" or "just" in shipped text.
- **headless Chrome, 390px wide:** each motif, every screen (menu, sections 1 to 6, Games, Share), and the gated twin's gate, loaded in a 390px frame. Page width stays 390 and no element sticks out. A canary adds a 600px block and the check catches it, so the check can fail.
- **headless Chrome, driven like a reader:** pressing 1 to 5 then 7 shows `LOCKED 5/6` and the checklist `xxxxx.`; pressing 6 then 7 shows `PLAY` and the game; Play starts it; 0 returns to the menu. The soft keys walk menu, 1, 2, back to 1, 6 to Games, Games to menu. The gated twin shows the gate and the public one does not. An unfinished email is refused without sending. With a stand-in server that says OK and returns a code, the page sends `POST {"email": "reader@example.com", "code": "POCKET01"}` to the address and opens the phone on the menu. With a stand-in server that fails, the gate stays, the button comes back and the message names the author's email. Snake's canvas changes on its own clock after Play.

## 3. By eye
`python3 scripts/make-readme-images.py` rendered the three motifs at 1080x1350 (deep-linked to the menu, and the hero to section 2) and the triptych at 1620x720. Each was opened and checked: nothing cut off, no glow.
Fixes made on the way: a screenshot caught the y2k screen mid-fade (images now deep-link so nothing animates at capture), the cyberpunk scanlines were too heavy over the pink menu row (softened), and the y2k marquee showed one stray word in still images (it now starts mid-scroll).
All three motifs and the gate card were also rendered side by side at 390x844 and checked by eye.

## 4. Security gate
```sh
./scripts/security-check.sh
```
Result: 9 passed, 0 failed, **SAFE TO PUBLISH**.

## Not tested
- **A real sign-up address.** The gate was tested against stand-in servers inside the browser, not a live email platform. Whether her platform accepts JSON and allows requests from her site (CORS) depends on that platform.
- **The share sheet on a real phone.** The share code path (`navigator.share`, then copy to clipboard, then show the link) is code-reviewed, not run on a device.
- **Swipe steering on a real touch screen.** Keyboard and keypad steering share the same turn function; swipes were not run on a device.
- **The `?c=` link and the saved code in a real browser tab.** Those rules are tested as pure functions; the test frames use `srcdoc`, which has no address bar.
- **Claude Cowork** upload of the zip, and Windows.
- **Without Node or Chrome.** Those tests skip with a message saying what was not run; the skip branch is code-reviewed.
