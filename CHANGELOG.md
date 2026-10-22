# LockInteractionOverhaul - changelog

Rule 61: this mod's own history, kept beside the code it describes.

<!-- VERSIONING-RULES -->
> **Versioning rules (CLAUDE.md rules 6 and 48):** `X.Y.Z`; a change increments the THIRD
> number; at `.9` the MINOR rolls. The next number is LAST WORKING + 1; failed/scratch/
> untested numbers are reused. Numbers come from version-ledger.ps1 + set-version.ps1.

## 1.1.0 - 2026-10-22 - working

### Fixed
- Opening an owned lock (auto-pick, smash, spell) now reports the game's own trespass crime, Actor::TrespassAlarm(lock, owner, -1), the call every vanilla lock site makes, so a witness adds the bounty and guards confront or arrest as for vanilla lockpicking. Before, it raised a steal alarm on the door or chest as if it were a stolen item, the wrong crime type for a lock, so guards shouted 'Stop right there' but no bounty or fight followed (reported by MadAl777, 2026-10-22).

### Changed
- The Crime section's 'Reported value' slider (uCrimeGold) is retired: a trespass crime's bounty is the game's own. The INI key stays so older INI files load; it is ignored.

### Added
- Spells that work on locks gains a frost-only step: the page now lists Manipulate Lock only, plus frost (freezes a lock), plus fire (thaws or opens), plus shock (opens). uAllowedSpells keeps its values 0, 1, 2 and adds 3 = frost only; the new text is in all eleven languages.

## 1.0.6 - 2026-10-11 - working

### Fixed
- Player skills are read only from a placed player (parentCell set): the lock verdicts' Skill() returns 0 and the DevBench state op reports -1 before a character is loaded, instead of reading actor values off the main menu's empty player singleton - the class of read that crashed HUD Position Manager on 2026-09-29 (package gate rule or-player-actor-values-need-a-placed-player, which this package was the first to meet).
- Two translated texts still named the files from before the 1.0.4 rename in all eleven languages: the missing-plugin warning said ApocryphaLockInteractionOverhaul.esl and the Log level help said ApocryphaLockInteractionOverhaul.log; the translation files had not been regenerated after the rename. They now say LockInteractionOverhaul.esp and LockInteractionOverhaul.log (tools/gen-translations.py, unchanged for these keys).
- The live lock readout's Smash and Magic lines read '(10 of 0)' on a frozen Adept chest. The numbers were right - a frozen lock needs uFrostMalus (50) less weapon skill, so Adept's 50 became 0, and any Novice lock needs 0 - but 'have of needed' reads as a fraction out of zero. Both lines now use the Pick line's shape, '(10, needs 0)', in all eleven languages.
- The Unlock Spell page's 'Know the spell Manipulate Lock' switch applies at once: turning it on adds the spell to the player and turning it off removes it, through Locks::ApplySettings() (SyncSpell queued to the game's main thread as a task that captures nothing). Before, the switch only changed the setting, and the spell followed at the next save load or new game (kPostLoadGame/kNewGame run ApplySettings) - the capture run of 2026-10-11 had to reload a save to get the spell. The pick-angle switch already worked this way.

### Changed
- The log now defaults to info (uLogLevel=2, in the shipped INI and in the compiled default that Restore defaults uses) instead of trace (0), the level the project ships every mod at: a bug report's LockInteractionOverhaul.log carries the load, settings, warning and error lines, with the level header saying how to turn on trace. Set uLogLevel=0 for everything.
- Built so the DLL and PDB carry no build-machine paths: no user folder and no project folder (the linker's temp files and CommonLibSSE-NG's own sources are now built outside / trimmed from them).

## 1.0.5 - 2026-09-18 - untested

### Changed
- The Address Library pre-check runs before anything else at load: a missing Address Library file for the game version
  gets a message naming the file and the plugin loads inert, instead of CommonLibSSE-NG's bare failure line
  (oproso's report on the Perfected Wheeler page, 2026-09-18: a guard placed after SKSE::Init never ran). No other change.

## 1.0.4 - 2026-09-16 - untested

### Changed
- The plugin is now LockInteractionOverhaul.esp, a light ESPFE instead of a .esl, so it can be positioned in the load order rather than pinned to the top. The DLL, INI and log lose the Apocrypha prefix too. Both are breaking: saves that used the old plugin lose what it gave them, and the old INI is no longer read.

## 1.0.3 - 2026-09-13 - untested

### Changed
- Relicensed the whole mod under GPL-3.0-or-later, as CommonLibSSE-NG 7.2.0 (linked by the Skyrim 1.7.x build) and the SKSE Menu Framework 3 consumer header require (Nexus moderation, 2026-09-13). `LICENSE` is now the GPL-3.0 text; `NOTICE.md` carries the copyright and licence notice; `THIRD_PARTY_NOTICES.md` keeps the notices of the MIT components (the SE/AE CommonLib, the DevBench consumer API, Remember Lockpick Angle's mechanism). The erroneous MIT licence is removed from the source, the manifests and the DLL's version resource. No gameplay change.

## 1.0.2 - 2026-09-07 - working

### Added
- The settings pages are shown in the game's language: eleven translation files (Interface\Translations\LockInteractionOverhaul_<language>.txt) - Japanese, Korean, Chinese, Russian, German, French, Spanish, Italian, Polish, Czech and English - and every page follows the Apocrypha Menu Framework's Language setting (1.6.5 or newer; English on older versions). The framework is looked up by its sort-first name first. alio.control gained op=strings (active language, source and loaded count).

## 1.0.1 - 2026-09-06 - working

### Changed
- Renamed to ApocryphaRealm Lock Interaction Overhaul (the owner's name). The binary, INI, plugin file, log and DevBench tool follow: LockInteractionOverhaul.dll / .ini / .esl / .log, tool alio.control. The spell and effect records are unchanged; the plugin file's new name is the only thing a save would notice, and 1.0.0 was never published.

## 1.0.0 - 2026-09-06 - working

### Added
- First version. An original rebuild of what Lock Overhaul does, on our own code (MIT), with an Apocrypha Menu Framework page: lock skill requirements per lock level, auto-pick, smashing locks with a weapon, an unlock spell (plus frost that freezes a lock and fire that thaws it), skill gain and crime for all of it. No file from the original is used.
- Remember Lockpick Angle's kept pick angle as the Pick Angle section (its MIT mechanism, credited): the one instruction that resets the pick angle when a pick breaks is found by signature and skipped when the section and its optional perk gate allow. Stands down while RememberLockpickAngle.dll is loaded.
- The whole mod stands down while Lock Overhaul.esp is loaded. Defaults measured against the original: requirement tables 0/25/50/75/100, frost malus 50.
- The cpc-style DevBench tool alio.control: state, every switch, look, describe, spawn, simulate (pick/smash/spell/fire/shock/frost/thaw), save, reload, deactivate.

### Proof
- Test Build, SE 1.5.97 (2026-09-06, six runs): requirements refuse an Expert lock at 15 of 75 and close the menu; auto-pick opens a Novice lock, uses one lockpick, raises Lockpicking; smash holds at 20 of 50, frost lowers the need, the frozen lock smashes open with One-handed skill use; a real weapon hit reaches the smash decision; Manipulate Lock is added when enabled, resists at 15 of 75, opens a Novice lock, and a real cast hits the lock through the hit event; the pick-angle patch attaches (signature matched once) - the break itself was not observed in the rig (no test input reaches the minigame) and is owed a keyboard check.
