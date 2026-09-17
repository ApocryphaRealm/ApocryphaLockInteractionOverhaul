# ApocryphaRealm Lock Interaction Overhaul

Version 1.0.4

An original SKSE plugin (GPL-3.0-or-later) that gives locks skill requirements and new ways to open them, with
every setting on an Apocrypha Menu Framework page. It is a from-scratch rebuild of what the
Papyrus mod *Lock Overhaul* does - inspiration only; no file, script or asset from it is used -
plus *Remember Lockpick Angle*'s kept angle, whose MIT mechanism is credited below.

## What it does (everything off by default)

- **Requirements** - a lock needs a Lockpicking skill for its level (Novice to Master) before the
  picking menu opens; below it the menu closes again and no lockpick is lost.
- **Auto pick** - with enough Lockpicking the lock simply opens: one lockpick used (none with
  Unbreakable), the game's own skill gain, a crime if it was not yours (unless Quick Hands).
- **Smash locks** - hit a locked chest or door with a weapon; enough weapon skill breaks it open.
- **Unlock spell** - *Manipulate Lock* (Alteration) works a lock from a distance. Destruction can
  join in: frost freezes a lock (easier to smash), fire thaws or opens it, shock opens it.
- **Pick angle** - when a pick breaks, the next one starts where it broke (optionally only with
  a perk). Stands down while RememberLockpickAngle.dll is loaded.
- **General** - skill gain and its multiplier, sound and volume, crime and its reported value,
  on-screen messages, and one button that switches everything off.

Key-required locks are never touched. The whole mod stands down while `Lock Overhaul.esp` is loaded.

## Files

`SKSE\Plugins\LockInteractionOverhaul.dll` (+ `.pdb`, `.ini`) and `LockInteractionOverhaul.esp` - a
two-record light plugin (the spell and its effect), no scripts, no overrides. The log is
`Documents\My Games\Skyrim Special Edition\SKSE\LockInteractionOverhaul.log`.

## Building

`configure.bat` then `build.bat` (SE 1.5.97 / AE 1.6.x line); `configure17.bat` / `build17.bat`
for the Skyrim 1.7.x line. Both discover the toolchain with `find-msvc.bat` and need `VCPKG_ROOT`.
`python tools\Build-LockInteractionOverhaulEsl.py` writes the ESL into `dist\`.

## Credits

- **Lock Overhaul** by Quad2Core (Skyrim SE upload by 8Phantasm) - the idea and the feature set,
  as described on its page. Nothing of it is used.
- **Remember Lockpick Angle** by Sayuri ("Umgak"), MIT - the pick-angle mechanism (skipping the
  game's reset of the pick angle when a pick breaks) is reimplemented on CommonLibSSE-NG from its
  MIT source; the MIT notice is preserved in `THIRD_PARTY_NOTICES.md`.
- CommonLibSSE-NG, SKSE, and the Apocrypha Menu Framework.

## Licence

GPL-3.0-or-later - see `LICENSE` and `NOTICE.md`. The Skyrim 1.7.x build links CommonLibSSE-NG 7.2.0
(GPL-3.0-or-later with its exceptions), and the settings pages use SKSE Menu Framework 3's consumer header
(GPL-3.0), so the whole work is GPL. Components under other licences, with their notices, are listed in
`THIRD_PARTY_NOTICES.md`. Up to 1.0.2 the repository carried an MIT licence in error.
