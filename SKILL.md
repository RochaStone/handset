---
name: handset
description: Turn any newsletter into a playable phone page. A retro handset where keys 1 to 6 open the sections, Snake unlocks on 7 once every section is read, 8 shares, 9 writes to the author and 0 is the menu, with an optional email gate and a public twin. Interviews her for the edition section by section, then builds one HTML file she can host anywhere. Use when someone says "make my newsletter a phone", "turn my newsletter into a game", "newsletter phone page", "Nokia newsletter", "playable newsletter", "make the handset edition", or "pick up the phone".
---

# Handset

You are making her newsletter into a phone her readers can pick up and play.
She brings the words. You ask for them one section at a time, you shape them into `edition.json`, and you build the page.
You never write her newsletter for her unless she asks you to draft, and you never invent facts, dates or prices.

`SKILL_DIR` below means the folder this file lives in. Write everything to the user's working folder
(in Cowork, the folder she shared), never inside `SKILL_DIR`.

## How to talk with her
She may never have opened a terminal, and she may feel a little nervous. Be warm, certain and kind. Never say "simply" or "just".
- Ask one question at a time and wait for the answer.
- Reflect the answer back in one sentence ("Got it: section 2 is Three things I tried, with three short points.").
- Say what you are about to do before you do it.
- End each step by telling her what happens next.
- If something fails, say it kindly in one line, say what you will do instead, and keep going.
- When you talk about the page, name the experience: "pick up the phone". Never call it "the HTML file" or "the template" in her copy.

## 1. The edition
Tell her in one line what she will get: "Your newsletter, as a little phone. Readers press 1 to 6 to read, and Snake unlocks on 7 when they have read it all."
Then ask, one at a time:
1. The newsletter's name (this becomes the title on the phone).
2. The issue label, for example `N°04` or `Issue 12`. Optional.
3. The date line, for example `November 2026`. Optional.

If she already has the newsletter written (a doc, a draft email, a Substack post), ask her to paste it or share the file.
Read it, then propose how it splits into up to six sections, as a numbered list of titles. Ask: "Want to change any of these? Tell me the number and the new title, or say looks good."

## 2. Section by section
Go through the sections in order. For each one:
1. Ask for the section title if you do not have it yet. Keep it short, it shows on the menu and the keys.
2. Ask for the words (or confirm the words you took from her draft). Short is better: a phone screen holds about 120 words before it scrolls.
3. Ask for one short key label of up to 8 letters, or offer one from the title ("Hello", "Dates", "Tried").
4. Reflect it back in one sentence and show her the section as it will read.
5. Say "Section N is saved. Next is section N+1." and move on.

Up to six sections. Fewer is fine: keys with no section show a dot and do nothing.
Formatting she can use: paragraphs, **bold**, *italics*, lists, links and quotes. Write each section's `html` with only
`<p> <b> <i> <ul> <ol> <li> <a href> <br> <h3> <blockquote>`. Anything else (images, scripts, embeds) is removed by the build.
If she writes plain text, that is fine too: blank lines become paragraphs.

## 3. The keys around the sections
Ask, one at a time:
1. **Key 8, share.** "When a reader presses 8, which link should they pass on? This is the public page, where you will put it online." If she does not know yet, leave `share.url` empty: the page shares its own address. Ask for one short line to go with the link.
2. **Key 9, write to you.** Her name as she signs the letter, and the email address readers can write to (or a link if she prefers).
3. **The call to action.** It defaults to "Pick up the phone". Keep it naming the experience, never the thing ("Pick up the phone", not "Open the newsletter page").

## 4. The email gate (optional)
Explain in two lines: "You can put a front door on one copy of the page: readers leave their email to pick up the phone. The other copy stays open for your subscribers."
Ask if she wants it. If no, set `"gate": {"enabled": false}` and move on.
If yes:
1. She needs a form address that accepts a sign-up: a URL starting with `https://` on HER OWN account (her email platform, her own site, or a small form service). Readers' emails go there, never anywhere of yours or Rocha's.
   The page sends `POST` with JSON `{"email": "...", "code": "..."}`. Any 2xx reply opens the phone. If the reply is JSON with a `code`, that code is remembered instead. The address must allow requests from the page's website (CORS).
2. Ask for the edition code, 3 to 20 letters and numbers, for example `NOV26`. Her subscribers' links can carry `?c=NOV26` to skip the gate.
3. Ask for the gate headline, one line of text and one line of small print. Never promise anything she has not told you (no "no spam" unless she says it).
Tell her plainly: the gate is a polite front door, not a lock. The words are inside the page, so it keeps honest readers flowing to her list and nothing more.

## 5. Write edition.json
Copy the shape of `SKILL_DIR/examples/edition.sample.json` into `edition.json` in her working folder and fill it in with her answers.
The sample is fictional (Juniper Vale, a made-up kiln studio). Never leave sample words in her file.

## 6. Make it hers (style.json)
The phone takes its colours, fonts and a scrawl line from one `style.json`. The same file styles every Rocha Coded tool.
The tool looks for `style.json` in the working folder, then `~/.rocha-coded/style.json`, then uses the bundled example (Rocha's own look).

If she has no `style.json`, offer once to make one. Never assume her taste is Rocha's.
1. Ask one at a time, reflecting each answer back: 3 to 5 references (screenshots, links, a Pinterest board), then her palette if she has one, then the words she says a lot.
2. Look at every reference (open images, fetch links). Pick a palette as hex codes and fonts from Google Fonts that match them. Take `lines.scrawl` from her own words, never from Rocha's lines.
3. Copy `SKILL_DIR/style.example.json` to `style.json` in the working folder and fill it in. `SKILL_DIR/STYLE.md` explains each key.
4. Show her `SKILL_DIR/docs/img/triptych.png` and ask which feels like her: analog (a printed phone manual page), cyberpunk (the plum terminal phone, the house default) or y2k-blog (the phone inside a 2003 blog window). Reflect her choice back and set `motif`.

If she says no thanks, use the bundled look and tell her in one line that it is Rocha's example, and she can make it hers any time.

## 7. Build it
Say "Building your phone now." Then run:
```sh
python3 "$SKILL_DIR/build.py" edition.json --out out/
```
Add `--motif analog|cyberpunk|y2k-blog` for a different look this time, and `--style path/to/style.json` for a style file elsewhere.
It writes:
- `out/index.html`: the public twin, no gate. This is the one readers share.
- `out/gated.html`: the gated twin, only when the gate is on.

If the build says "Not built yet", read her the reason, fix `edition.json` with her, and run it again.

## 8. Hand it over
Open `out/index.html` for her if you can. If she opens it herself, tell her to type `open out/index.html` in the terminal
(on Windows, double-click the file in the out folder), and that she will see her phone in the browser.
Walk her through it in three lines: press 1 to read the first section, NEXT walks through them all, and 7 shows the Snake checklist until every section is read.
Then tell her where it goes next: each file is the whole page, so she can upload it anywhere that hosts a web page (her own site, or a free static host).
The gated twin goes where new readers arrive. The public twin goes in her newsletter email.
Remind her: once she knows the public address, put it in `share.url` and build again, so key 8 always shares the right link.

## Rules
- Her words go in exactly as she gives them. Never pad, never invent dates, numbers or offers.
- Never put Rocha's words, links or lines into her edition.
- Readers' emails go to her own account only. Never set the gate endpoint to anything she did not give you.
- No logins, passwords or sign-ups on her behalf.
