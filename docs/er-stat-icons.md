# ER Stat Icons — Research Notes

## Status

Icons are **not yet sourced**. `hasStatIcons: false` is set in `frontend/src/erConfig.js`, so the stat grid and level-up modal render text labels only for ER (no `<img>` tags rendered).

DS2 has full icon support — this only affects the ER deployment.

---

## What We Know

- Elden Ring **does** have small attribute icons in the game's level-up UI (one per stat: VIG, MND, END, STR, DEX, INT, FAI, ARC).
- They are golden/amber-colored, similar in style to DS2's icons.
- DS2 stat icons are **39×38px, RGB PNG** (~3.5 KB each), sourced from Fextralife:
  - `https://darksouls2.wiki.fextralife.com/file/Dark-Souls-2/icon-vigor.png`
  - Same pattern for: `icon-endurance`, `icon-vitality`, `icon-attunement`, `icon-strength`, `icon-dexterity`, `icon-adaptability`, `icon-intelligence`, `icon-faith`

---

## Where to Get ER Icons

### Option 1 — Google Drive dump (recommended)
Community-compiled full icon dump by **RubyRed** (stopsoftbanningmepls):

**https://drive.google.com/drive/folders/1QlFDRjtwJvJXBED7JsLN7jnkxB6ySr3p**

Folder structure seen:
- Armor, Arrows/Bolts, Ashes of War, Bolstering Materials, Crafting Materials
- Gestures, Incantations, **Info**, Key Items, Loading Screens
- Melee Armaments, **Misc**, Ranged Weapons/Catalysts
- Shadow of the Erdtree DLC, Shields, Sorceries, Spell Sigils
- Spirit Ashes, Talismans, Tattoos, Tools, Unused Content

**Most likely locations:** `Info/` or `Misc/` — attribute icons are UI elements, not item icons.

### Option 2 — Fextralife ER wiki (confirmed dead end)
The ER wiki does **not** publish small stat icons the way the DS2 wiki does.
- `vigor_health.png` and `mind_focus.png` exist but are 720×432 concept art images, not stat icons.
- No `icon-vigor.png` equivalent found under any naming pattern tried.

### Option 3 — Other sources (dead ends)
- wiki.gg and Fandom ER wikis are Cloudflare-protected (can't scrape)
- GitHub planners (tcd/elden-ring-app, Volpestyle, AndyDaMandy) use text or generic UI icons, not per-stat icons
- Maxroll/GamesRadar use full-size screenshots, not icon assets

---

## How to Enable Icons When Ready

1. Download the 8 attribute icons from the Google Drive dump above
2. Rename them to match the expected filenames and drop into `frontend/public/icons/er/`:
   ```
   icon-vigor.png
   icon-mind.png
   icon-endurance.png
   icon-strength.png
   icon-dexterity.png
   icon-intelligence.png
   icon-faith.png
   icon-arcane.png
   ```
3. Resize to ~39×38px (to match DS2 icon dimensions) if needed
4. In `frontend/src/erConfig.js`, change `hasStatIcons: false` → `hasStatIcons: true`

The icon paths in `erConfig.js` `statFields` already point to `/icons/er/icon-{stat}.png` — no other code changes needed.
