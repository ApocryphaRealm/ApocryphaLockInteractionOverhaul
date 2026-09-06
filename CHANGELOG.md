# ApocryphaLockOverhaul - changelog

Rule 61: this mod's own history, kept beside the code it describes.

<!-- VERSIONING-RULES -->
> **Versioning rules (CLAUDE.md rules 6 and 48):** `X.Y.Z`; a change increments the THIRD
> number; at `.9` the MINOR rolls. The next number is LAST WORKING + 1; failed/scratch/
> untested numbers are reused. Numbers come from version-ledger.ps1 + set-version.ps1.

## 1.0.0 - 2026-09-06 - working

### Added
- First version. An original rebuild of what Lock Overhaul does, on our own code (MIT), with an Apocrypha Menu Framework page: lock skill requirements per lock level, auto-pick, smashing locks with a weapon, an unlock spell (plus frost that freezes a lock and fire that thaws it), skill gain and crime for all of it. No file from the original is used.
- Remember Lockpick Angle's kept pick angle as the Pick Angle section (its MIT mechanism, credited): the one instruction that resets the pick angle when a pick breaks is found by signature and skipped when the section and its optional perk gate allow. Stands down while RememberLockpickAngle.dll is loaded.
- The whole mod stands down while Lock Overhaul.esp is loaded. Defaults measured against the original: requirement tables 0/25/50/75/100, frost malus 50.
- The cpc-style DevBench tool alo.control: state, every switch, look, describe, spawn, simulate (pick/smash/spell/fire/shock/frost/thaw), save, reload, deactivate.

### Proof
- Test Build, SE 1.5.97 (2026-09-06, six runs): requirements refuse an Expert lock at 15 of 75 and close the menu; auto-pick opens a Novice lock, uses one lockpick, raises Lockpicking; smash holds at 20 of 50, frost lowers the need, the frozen lock smashes open with One-handed skill use; a real weapon hit reaches the smash decision; Manipulate Lock is added when enabled, resists at 15 of 75, opens a Novice lock, and a real cast hits the lock through the hit event; the pick-angle patch attaches (signature matched once) - the break itself was not observed in the rig (no test input reaches the minigame) and is owed a keyboard check.
