# style.json

One file holds your look. Every Rocha Coded tool reads the same file, so you make it once.

## Where it goes
The tool looks in this order and uses the first one it finds:
1. `style.json` in the folder you are working in (your Cowork folder, or wherever you run Claude Code)
2. `~/.rocha-coded/style.json`, to use one look across every project
3. `examples/style.rocha-coded.json`, the bundled example (Rocha's look)

Start from `style.example.json`: copy it to `style.json` and fill it in. Or ask Claude to make one with you.

## The keys
| Key | What to put there | Used by this tool |
|---|---|---|
| `name` | your brand or studio name | no (the phone's name comes from your edition) |
| `owner` | your name, as you sign things | no (the edition's `author.name` is used) |
| `handle` | your Instagram or main social handle | no |
| `site` | your website address | no |
| `palette.hero` | your ground colour, the deep one everything sits on, as a hex code like `#50163C` | the page behind the phone in cyberpunk, the window title bar in y2k-blog, the gate backdrop |
| `palette.wine` | a second deep colour | the keys in cyberpunk, the phone body and sidebar labels in y2k-blog |
| `palette.accent` | your one bright accent | the highlighted menu row, the Snake key, the Pick up the phone button |
| `palette.paper` | a light paper colour | the manual page, the blog window, the gate card |
| `palette.paper_pink` | a second paper colour | the screen in analog, the keys and sidebar boxes in y2k-blog |
| `palette.ink` | your text colour | type, outlines and the drawn handset |
| `palette.marker` | the colour of the handwritten scrawl | the scrawl in analog, the Snake heart on paper screens |
| `palette.plum` | a deep shade | the screen in cyberpunk |
| `palette.gold` | a highlight colour | the screws, status light and labels in cyberpunk, the window buttons in y2k-blog |
| `palette.cool` | one cool accent, used rarely | no |
| `fonts.masthead` | a big display font from Google Fonts | the edition title |
| `fonts.label` | a font for labels and buttons | the soft keys, key labels and the deck line |
| `fonts.body` | a reading font | the deck line, the manual callouts, the gate text |
| `fonts.scrawl` | a handwriting or marker font | the scrawl in analog |
| `fonts.script` | a signature script font | no |
| `fonts.mono` | a typewriter font | the words on the screen, the numbers on the keys |
| `fonts.pixel` (optional) | a pixel font from Google Fonts | the screen labels in cyberpunk and y2k-blog (Silkscreen if empty) |
| `motif` | `analog`, `cyberpunk` or `y2k-blog` (older names like `guest-check` or `retro-tv` still work and map to the nearest one) | yes: the manual page, the plum terminal phone, or the blog window. If you have no style.json, this tool starts in cyberpunk |
| `lines.scrawl` | a short line in your own words | the handwritten line on the analog manual page |
| `lines.celebrate` | a line you say when things go well | the mood box in y2k-blog |
| `lines.masthead`, `headline`, `todo`, `stamp`, `affirm`, `invite`, `magazine` | more of your own lines | kept for other tools |
| `references` | 3 to 5 images or links that feel like you | Claude looks at these when it makes your style with you |
| `notes` | your look in one or two sentences | Claude reads this too |

## Good to know
- Colours must be hex codes (`#RRGGBB`). Anything else is skipped and the bundled colour is used for that slot.
- Fonts are Google Fonts names, letters, numbers and spaces only. If a font is not on Google Fonts, or the reader is offline, the page uses a similar font already on their device.
- Any colour or font you leave empty borrows the bundled example's, so the phone always looks finished.
- Your words and your name never borrow. Leave `lines.scrawl` empty and the manual page prints no scrawl.
- Your edition's words live in `edition.json`, not here. This file is only the look.
