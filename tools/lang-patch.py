# -*- coding: utf-8 -*-
"""lang-patch.py - one-shot, re-runnable language-support patch for the ApocryphaRealm Lock
Interaction Overhaul.

Applies the consumer-side mechanism from the translation rollout plan, section 2:

  * include/utils/Strings.h is vendored separately (copied from the template, unchanged);
  * include/SKSEMenuFramework.h gets "!ApocryphaMenuFramework" as the FIRST module lookup;
  * source/main.cpp calls strings::Configure("ApocryphaLockInteractionOverhaul") at kDataLoaded;
  * source/UI.cpp calls strings::Tick() as the first line of all SIX page render functions and
    routes every drawn literal through strings::TR("ALIO_...", "English");
  * source/DevBenchTool.cpp gains an op=strings returning strings::StatusJson().

Every edit is a must-match anchor replace: an anchor that is not found EXACTLY ONCE raises, so a
stale run against changed source fails loudly instead of leaving the code half patched. Each
patch step is skipped when its done-marker is already present, so the script is re-runnable.

Run: `python tools/lang-patch.py` (paths are relative to this script's grandparent directory).

Encoding note: source files are read and written as UTF-8 with newline='' in BOTH directions, so
a raw CR inside a string literal survives and the existing CRLF endings are preserved exactly
(logic library, 2026-09-02).
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def fit(s, crlf):
    """Anchors below are written with CRLF; a file kept in LF gets the LF form of the same text.

    The repo mixes the two - the vendored SKSEMenuFramework.h is CRLF, the mod's own sources are
    LF - and an anchor with the wrong ending simply never matches.
    """
    return s if crlf else s.replace("\r\n", "\n")


def apply_one(text, anchor, replacement, label, crlf=True):
    anchor, replacement = fit(anchor, crlf), fit(replacement, crlf)
    n = text.count(anchor)
    if n != 1:
        raise RuntimeError("[{}] anchor found {} time(s), expected exactly 1:\n{!r}".format(label, n, anchor))
    return text.replace(anchor, replacement, 1)


def apply_all(text, pairs, label):
    crlf = "\r\n" in text
    for i, (anchor, replacement) in enumerate(pairs):
        text = apply_one(text, anchor, replacement, "{}[{}]".format(label, i), crlf)
    return text


# ------------------------------------------------------------------------------------------------
# 1) include/SKSEMenuFramework.h - "!ApocryphaMenuFramework" first, ahead of the alias name.
# ------------------------------------------------------------------------------------------------
def patch_skse_menu_framework_h():
    path = os.path.join(REPO, "include", "SKSEMenuFramework.h")
    text = read(path)
    if 'GetModuleHandleW(L"!ApocryphaMenuFramework")' in text:
        print("  SKSEMenuFramework.h: already patched")
        return
    anchor = (
        '        menuFramework = GetModuleHandleW(L"ApocryphaMenuFramework");\r\n'
        '        if (!menuFramework) {\r\n'
        '            menuFramework = GetModuleHandleW(L"SKSEMenuFramework");\r\n'
        '        }\r\n'
    )
    replacement = (
        '        menuFramework = GetModuleHandleW(L"!ApocryphaMenuFramework");\r\n'
        '        if (!menuFramework) {\r\n'
        '            menuFramework = GetModuleHandleW(L"ApocryphaMenuFramework");\r\n'
        '        }\r\n'
        '        if (!menuFramework) {\r\n'
        '            menuFramework = GetModuleHandleW(L"SKSEMenuFramework");\r\n'
        '        }\r\n'
    )
    text = apply_one(text, anchor, replacement, "SKSEMenuFramework.h:GetMenuFrameworkModule", "\r\n" in text)
    write(path, text)
    print("  SKSEMenuFramework.h: patched")


# ------------------------------------------------------------------------------------------------
# 2) source/main.cpp - strings::Configure(...) at kDataLoaded.
# ------------------------------------------------------------------------------------------------
def patch_main_cpp():
    path = os.path.join(REPO, "source", "main.cpp")
    text = read(path)
    if 'strings::Configure("ApocryphaLockInteractionOverhaul")' in text:
        print("  main.cpp: already patched")
        return
    pairs = [
        ('#include "utils/Logger.h"',
         '#include "utils/Logger.h"\r\n#include "utils/Strings.h"'),
        ('\t\tcase SKSE::MessagingInterface::kDataLoaded:\r\n\t\t\tUI::Register();',
         '\t\tcase SKSE::MessagingInterface::kDataLoaded:\r\n'
         '\t\t\tstrings::Configure("ApocryphaLockInteractionOverhaul");\r\n'
         '\t\t\tUI::Register();'),
    ]
    text = apply_all(text, pairs, "main.cpp")
    write(path, text)
    print("  main.cpp: patched")


# ------------------------------------------------------------------------------------------------
# 3) source/DevBenchTool.cpp - op=strings, and the descriptor line that documents it.
# ------------------------------------------------------------------------------------------------
def patch_devbench_tool_cpp():
    path = os.path.join(REPO, "source", "DevBenchTool.cpp")
    text = read(path)
    if 'has("strings")' in text:
        print("  DevBenchTool.cpp: already patched")
        return
    pairs = [
        ('#include "utils/Logger.h"',
         '#include "utils/Logger.h"\r\n#include "utils/Strings.h"'),
        ('\t\t\tif (has("deactivate"))',
         '\t\t\tif (has("strings")) { reply(std::format(R"({{"ok":true,"op":"strings","strings":{}}})", strings::StatusJson())); return; }\r\n'
         '\t\t\tif (has("deactivate"))'),
        ('op=save, op=reload, op=deactivate.\\","',
         'op=save, op=reload, op=deactivate. op=strings reports the active language, source and loaded translation count.\\","'),
    ]
    text = apply_all(text, pairs, "DevBenchTool.cpp")
    write(path, text)
    print("  DevBenchTool.cpp: patched")


# ------------------------------------------------------------------------------------------------
# 4) source/UI.cpp - Tick() in all six render functions, TR() on every drawn literal.
#
# The pairs below are the whole routing, one line of source per pair, in file order. Conventions
# (plan 2.2): a plain literal drawn by Text/TextWrapped/TextDisabled becomes X("%s", TR(...)); a
# literal that IS a printf format keeps its specifiers inside the TR text when it carries a real
# word, and is left alone when it is bare numeric ("%.0f", "%.2f"); an ImGui id/label suffix and
# the framework's section/page names stay English; INI keys, file names, form ids and log lines
# are never routed.
# ------------------------------------------------------------------------------------------------
ARRAYS_OLD = (
    '\t\tconstexpr const char* kLogLevelNames[] = { "Trace", "Debug", "Info", "Warning", "Error", "Critical", "Off" };\r\n'
    '\t\tconstexpr int kLogLevelCount = 7;\r\n'
    '\t\tconstexpr const char* kWeaponModes[] = { "Two-handed weapons only", "One- and two-handed weapons", "Any weapon (bows, crossbows, staves, fists too)" };\r\n'
    '\t\tconstexpr const char* kSpellModes[] = { "Manipulate Lock only", "Plus Destruction: frost freezes, fire thaws or opens", "All of that plus shock spells open locks" };\r\n'
    '\t\tconstexpr const char* kPerkNames[] = { "None", "Locksmith", "Unbreakable", "Quick Hands", "Wax Key", "Golden Touch", "Treasure Hunter", "Custom (sPerkPlugin + uPerkFormID in the INI)" };\r\n'
)

# Each combo/tier list is a parallel key/label pair: the key array names the translation key, the
# label array holds the compiled English. gen-translations.py pairs them positionally, exactly as
# it pairs the TR("key", "english") calls elsewhere in this file.
ARRAYS_NEW = (
    '\t\tconstexpr int kLogLevelCount = 7;\r\n'
    '\t\tconstexpr const char* kLogLevelKeys[] = { "ALIO_Log_Trace", "ALIO_Log_Debug", "ALIO_Log_Info", "ALIO_Log_Warning", "ALIO_Log_Error", "ALIO_Log_Critical", "ALIO_Log_Off" };\r\n'
    '\t\tconstexpr const char* kLogLevelLabels[] = { "Trace", "Debug", "Info", "Warning", "Error", "Critical", "Off" };\r\n'
    '\t\tconstexpr const char* kWeaponModeKeys[] = { "ALIO_Weapons_TwoOnly", "ALIO_Weapons_OneAndTwo", "ALIO_Weapons_Any" };\r\n'
    '\t\tconstexpr const char* kWeaponModeLabels[] = { "Two-handed weapons only", "One- and two-handed weapons", "Any weapon (bows, crossbows, staves, fists too)" };\r\n'
    '\t\tconstexpr const char* kSpellModeKeys[] = { "ALIO_Spells_LockOnly", "ALIO_Spells_Destruction", "ALIO_Spells_Shock" };\r\n'
    '\t\tconstexpr const char* kSpellModeLabels[] = { "Manipulate Lock only", "Plus Destruction: frost freezes, fire thaws or opens", "All of that plus shock spells open locks" };\r\n'
    '\t\tconstexpr const char* kPerkKeys[] = { "ALIO_Perk_None", "ALIO_Perk_Locksmith", "ALIO_Perk_Unbreakable", "ALIO_Perk_QuickHands", "ALIO_Perk_WaxKey", "ALIO_Perk_GoldenTouch", "ALIO_Perk_TreasureHunter", "ALIO_Perk_Custom" };\r\n'
    '\t\tconstexpr const char* kPerkLabels[] = { "None", "Locksmith", "Unbreakable", "Quick Hands", "Wax Key", "Golden Touch", "Treasure Hunter", "Custom (sPerkPlugin + uPerkFormID in the INI)" };\r\n'
    '\t\tconstexpr const char* kTierKeys[] = { "ALIO_Tier_Novice", "ALIO_Tier_Apprentice", "ALIO_Tier_Adept", "ALIO_Tier_Expert", "ALIO_Tier_Master" };\r\n'
    '\t\tconstexpr const char* kTierLabels[] = { "Novice", "Apprentice", "Adept", "Expert", "Master" };\r\n'
    '\t\tconstexpr const char* kTierLockKeys[] = { "ALIO_TierLock_Novice", "ALIO_TierLock_Apprentice", "ALIO_TierLock_Adept", "ALIO_TierLock_Expert", "ALIO_TierLock_Master" };\r\n'
    '\t\tconstexpr const char* kTierLockLabels[] = { "Novice lock", "Apprentice lock", "Adept lock", "Expert lock", "Master lock" };\r\n'
)

HELPERS_NEW = (
    '\t\t// The lock tier as the player reads it. Locks::TierName() is the log/JSON form and stays\r\n'
    '\t\t// English; this is the drawn form.\r\n'
    '\t\tconst char* TierText(int a_index)\r\n'
    '\t\t{\r\n'
    '\t\t\treturn (a_index >= 0 && a_index < settings::kTierCount) ? strings::TR(kTierKeys[a_index], kTierLabels[a_index])\r\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t : strings::TR("ALIO_Tier_KeyRequired", "key-required");\r\n'
    '\t\t}\r\n'
    '\t\tconst char* TierText(Locks::Tier a_tier) { return TierText(static_cast<int>(a_tier)); }\r\n'
    '\r\n'
    '\t\t// A Combo whose option list is rebuilt from TR\'d entries every frame (plan 2.2): store\r\n'
    '\t\t// owns the translated bytes for the duration of the call, so the pointers stay valid.\r\n'
    '\t\tbool ComboTR(const char* a_label, int* a_current,\r\n'
    '\t\t\t\t\t const char* const* a_keys, const char* const* a_labels, int a_count)\r\n'
    '\t\t{\r\n'
    '\t\t\tstd::vector<std::string> store;\r\n'
    '\t\t\tstore.reserve(static_cast<std::size_t>(a_count));\r\n'
    '\t\t\tfor (int i = 0; i < a_count; ++i) { store.emplace_back(strings::TR(a_keys[i], a_labels[i])); }\r\n'
    '\t\t\tstd::vector<const char*> items;\r\n'
    '\t\t\titems.reserve(store.size());\r\n'
    '\t\t\tfor (const auto& s : store) { items.push_back(s.c_str()); }\r\n'
    '\t\t\treturn ImGuiMCP::Combo(a_label, a_current, items.data(), a_count);\r\n'
    '\t\t}\r\n'
    '\r\n'
)

TIER_TABLE_OLD = (
    '\t\tvoid TierTable(const char* a_id, std::uint32_t* a_values, const char* a_skillName)\r\n'
    '\t\t{\r\n'
    '\t\t\tImGuiMCP::PushID(a_id);\r\n'
    '\t\t\tfor (int i = 0; i < settings::kTierCount; ++i)\r\n'
    '\t\t\t{\r\n'
    '\t\t\t\tconst std::string label = std::string(settings::kTierNames[i]) + " lock";\r\n'
    '\t\t\t\tconst std::string help = std::string(a_skillName) + " needed for a " + settings::kTierNames[i] + " lock, 0 to 100.";\r\n'
    '\t\t\t\tPercent(label.c_str(), a_values[i], help.c_str());\r\n'
    '\t\t\t}\r\n'
    '\t\t\tImGuiMCP::PopID();\r\n'
    '\t\t}\r\n'
)

TIER_TABLE_NEW = (
    '\t\tvoid TierTable(const char* a_id, std::uint32_t* a_values, const char* a_skill)\r\n'
    '\t\t{\r\n'
    '\t\t\tImGuiMCP::PushID(a_id);\r\n'
    '\t\t\tconst char* const skill = a_skill;\r\n'
    '\t\t\tconst char* const helpFormat = strings::TR("ALIO_TierHelp", "%s needed for a %s lock, 0 to 100.");\r\n'
    '\t\t\tfor (int i = 0; i < settings::kTierCount; ++i)\r\n'
    '\t\t\t{\r\n'
    '\t\t\t\tchar help[512] = {};\r\n'
    '\t\t\t\tstd::snprintf(help, sizeof(help), helpFormat, skill, TierText(i));\r\n'
    '\t\t\t\tPercent(strings::TR(kTierLockKeys[i], kTierLockLabels[i]), a_values[i], help);\r\n'
    '\t\t\t}\r\n'
    '\t\t\tImGuiMCP::PopID();\r\n'
    '\t\t}\r\n'
)

UI_PAIRS = [
    # --- includes ---
    ('#include "utils/Toggle.h"',
     '#include "utils/Strings.h"\r\n#include "utils/Toggle.h"'),
    ('#include <algorithm>\r\n#include <functional>\r\n#include <string>',
     '#include <algorithm>\r\n#include <cstdio>\r\n#include <functional>\r\n#include <string>\r\n#include <vector>'),

    # --- the option/tier tables, and the two helpers that draw from them ---
    (ARRAYS_OLD, ARRAYS_NEW),
    ('\t\tvoid HelpMarker(const char* a_description)', HELPERS_NEW + '\t\tvoid HelpMarker(const char* a_description)'),
    ('\t\t\tImGuiMCP::TextDisabled("(?)");',
     '\t\t\tImGuiMCP::TextDisabled("%s", strings::TR("ALIO_HelpMark", "(?)"));'),
    (TIER_TABLE_OLD, TIER_TABLE_NEW),

    # --- CrosshairReadout ---
    ('ImGuiMCP::TextDisabled("Look at a locked chest or door to see how this mod judges it."); return;',
     'ImGuiMCP::TextDisabled("%s", strings::TR("ALIO_LookAtNothing", "Look at a locked chest or door to see how this mod judges it.")); return;'),
    ('ImGuiMCP::Text("%s: not locked.", info.name.c_str());',
     'ImGuiMCP::Text(strings::TR("ALIO_LookNotLocked", "%s: not locked."), info.name.c_str());'),
    ('ImGuiMCP::Text("%s: needs a key - this mod leaves it alone.", info.name.c_str());',
     'ImGuiMCP::Text(strings::TR("ALIO_LookNeedsKey", "%s: needs a key - this mod leaves it alone."), info.name.c_str());'),
    ('\t\t\tImGuiMCP::Text("%s: %s lock%s%s", info.name.c_str(), Locks::TierName(info.tier), info.frozen ? ", frozen" : "", info.crime ? ", opening it is a crime" : "");',
     '\t\t\tImGuiMCP::Text(strings::TR("ALIO_LookLock", "%s: %s lock%s%s"), info.name.c_str(), TierText(info.tier),\r\n'
     '\t\t\t\t\t\t   info.frozen ? strings::TR("ALIO_LookFrozen", ", frozen") : "",\r\n'
     '\t\t\t\t\t\t   info.crime ? strings::TR("ALIO_LookCrime", ", opening it is a crime") : "");'),
    ('\t\t\tImGuiMCP::Text("Pick: %s (Lockpicking %u, needs %u)", pick.allowed ? "yes" : "no", pick.have, pick.needed);',
     '\t\t\tImGuiMCP::Text(strings::TR("ALIO_LookPick", "Pick: %s (Lockpicking %u, needs %u)"), pick.allowed ? YesNo(true) : YesNo(false), pick.have, pick.needed);'),
    ('\t\t\tImGuiMCP::Text("Smash: one-handed %s (%u of %u), two-handed %s (%u of %u)", smash1.allowed ? "yes" : "no", smash1.have, smash1.needed, smash2.allowed ? "yes" : "no", smash2.have, smash2.needed);',
     '\t\t\tImGuiMCP::Text(strings::TR("ALIO_LookSmash", "Smash: one-handed %s (%u of %u), two-handed %s (%u of %u)"), YesNo(smash1.allowed), smash1.have, smash1.needed, YesNo(smash2.allowed), smash2.have, smash2.needed);'),
    ('\t\t\tImGuiMCP::Text("Magic: Alteration %s (%u of %u), Destruction %s (%u of %u)", alt.allowed ? "yes" : "no", alt.have, alt.needed, des.allowed ? "yes" : "no", des.have, des.needed);',
     '\t\t\tImGuiMCP::Text(strings::TR("ALIO_LookMagic", "Magic: Alteration %s (%u of %u), Destruction %s (%u of %u)"), YesNo(alt.allowed), alt.have, alt.needed, YesNo(des.allowed), des.have, des.needed);'),

    # --- StandDownBanner ---
    ('\t\t\t\tImGuiMCP::TextWrapped("Lock Overhaul.esp is loaded, so this mod is standing down completely - nothing on these pages does anything until that mod is removed.");',
     '\t\t\t\tImGuiMCP::TextWrapped("%s", strings::TR("ALIO_StandDown", "Lock Overhaul.esp is loaded, so this mod is standing down completely - nothing on these pages does anything until that mod is removed."));'),

    # --- RenderButtons ---
    ('if (ImGuiMCP::Button("Save"))',
     'if (ImGuiMCP::Button(strings::TR("ALIO_SaveBtn", "Save")))'),
    ('\t\t\t\tstatusMessage = "Saving...";',
     '\t\t\t\tstatusMessage = strings::TR("ALIO_StatusSaving", "Saving...");'),
    ('statusMessage = settings::Save() ? "Settings saved." : "Could not write the INI. See the log for why.";',
     'statusMessage = settings::Save() ? strings::TR("ALIO_StatusSaved", "Settings saved.")\r\n'
     '\t\t\t\t\t\t\t\t\t\t\t\t : strings::TR("ALIO_StatusSaveFail", "Could not write the INI. See the log for why.");'),
    ('\t\t\tHelpMarker("Writes every setting on every section to the plugin\'s INI so it survives a restart.");',
     '\t\t\tHelpMarker(strings::TR("ALIO_HelpSave", "Writes every setting on every section to the plugin\'s INI so it survives a restart."));'),
    ('if (ImGuiMCP::Button("Reload from INI"))',
     'if (ImGuiMCP::Button(strings::TR("ALIO_ReloadBtn", "Reload from INI")))'),
    ('\t\t\t\tstatusMessage = "Reloading...";',
     '\t\t\t\tstatusMessage = strings::TR("ALIO_StatusReloading", "Reloading...");'),
    ('\t\t\t\t\tstatusMessage = settings::Reload() ? "Settings reloaded from the INI." : "Could not read the INI. See the log for why.";',
     '\t\t\t\t\tstatusMessage = settings::Reload() ? strings::TR("ALIO_StatusReloaded", "Settings reloaded from the INI.")\r\n'
     '\t\t\t\t\t\t\t\t\t\t\t\t\t   : strings::TR("ALIO_StatusReloadFail", "Could not read the INI. See the log for why.");'),
    ('\t\t\tHelpMarker("Throws away any change made here since the last save and re-reads the INI from disk.");',
     '\t\t\tHelpMarker(strings::TR("ALIO_HelpReload", "Throws away any change made here since the last save and re-reads the INI from disk."));'),
    ('if (ImGuiMCP::Button("Restore defaults"))',
     'if (ImGuiMCP::Button(strings::TR("ALIO_RestoreBtn", "Restore defaults")))'),
    ('\t\t\t\tstatusMessage = "Defaults restored (everything off). Press Save to keep them.";',
     '\t\t\t\tstatusMessage = strings::TR("ALIO_StatusRestored", "Defaults restored (everything off). Press Save to keep them.");'),
    ('\t\t\tHelpMarker("Puts every setting back to its fresh-install value - every feature off. Nothing is written until you press Save.");',
     '\t\t\tHelpMarker(strings::TR("ALIO_HelpRestore", "Puts every setting back to its fresh-install value - every feature off. Nothing is written until you press Save."));'),

    # --- RequirementsPanel ---
    ('\t\tusing namespace settings;\r\n\t\tStandDownBanner();\r\n\t\tImGuiMCP::TextWrapped("A lock needs a Lockpicking skill',
     '\t\tstrings::Tick();\r\n\t\tusing namespace settings;\r\n\t\tStandDownBanner();\r\n\t\tImGuiMCP::TextWrapped("A lock needs a Lockpicking skill'),
    ('\t\tImGuiMCP::TextWrapped("A lock needs a Lockpicking skill for its level before the picking menu opens; below it the menu closes again and no lockpick is lost. Key-required locks are never touched.");',
     '\t\tImGuiMCP::TextWrapped("%s", strings::TR("ALIO_ReqIntro", "A lock needs a Lockpicking skill for its level before the picking menu opens; below it the menu closes again and no lockpick is lost. Key-required locks are never touched."));'),
    ('ImGuiMCP::SeparatorText("Lock requirements");',
     'ImGuiMCP::SeparatorText(strings::TR("ALIO_ReqHeader", "Lock requirements"));'),
    ('ImGuiMCP::Toggle("Require a Lockpicking skill per lock level", &requirements::enabled);',
     'ImGuiMCP::Toggle(strings::TR("ALIO_ReqEnabled", "Require a Lockpicking skill per lock level"), &requirements::enabled);'),
    ('\t\tHelpMarker("On: the table below gates the picking menu. Off: any lock can be tried, as in vanilla.");',
     '\t\tHelpMarker(strings::TR("ALIO_HelpReqEnabled", "On: the table below gates the picking menu. Off: any lock can be tried, as in vanilla."));'),
    ('\t\tTierTable("pick", requirements::pick, "Lockpicking");',
     '\t\tTierTable("pick", requirements::pick, strings::TR("ALIO_SkillLockpicking", "Lockpicking"));'),
    ('ImGuiMCP::SeparatorText("Auto pick");',
     'ImGuiMCP::SeparatorText(strings::TR("ALIO_AutoPickHeader", "Auto pick"));'),
    ('ImGuiMCP::Toggle("Open locks without the minigame", &requirements::autoPick);',
     'ImGuiMCP::Toggle(strings::TR("ALIO_AutoPick", "Open locks without the minigame"), &requirements::autoPick);'),
    ('\t\tHelpMarker("With enough Lockpicking (the table above) the lock simply opens: one lockpick is used (none with the Unbreakable perk), Lockpicking rises as the game\'s own picking would raise it, and opening an owned lock is a crime unless you have Quick Hands.");',
     '\t\tHelpMarker(strings::TR("ALIO_HelpAutoPick", "With enough Lockpicking (the table above) the lock simply opens: one lockpick is used (none with the Unbreakable perk), Lockpicking rises as the game\'s own picking would raise it, and opening an owned lock is a crime unless you have Quick Hands."));'),
    ('ImGuiMCP::Toggle("Open the chest or door straight away", &requirements::openAfterPick);',
     'ImGuiMCP::Toggle(strings::TR("ALIO_OpenAfterPick", "Open the chest or door straight away"), &requirements::openAfterPick);'),
    ('\t\tHelpMarker("After auto-picking, the object is activated so it opens at once instead of needing a second press.");',
     '\t\tHelpMarker(strings::TR("ALIO_HelpOpenAfterPick", "After auto-picking, the object is activated so it opens at once instead of needing a second press."));'),
    ('ImGuiMCP::SeparatorText("What that means right now");',
     'ImGuiMCP::SeparatorText(strings::TR("ALIO_ReqReadoutHeader", "What that means right now"));'),

    # --- SmashPanel ---
    ('\t\tusing namespace settings;\r\n\t\tStandDownBanner();\r\n\t\tImGuiMCP::TextWrapped("Hit a locked chest',
     '\t\tstrings::Tick();\r\n\t\tusing namespace settings;\r\n\t\tStandDownBanner();\r\n\t\tImGuiMCP::TextWrapped("Hit a locked chest'),
    ('\t\tImGuiMCP::TextWrapped("Hit a locked chest or door with a weapon. With enough weapon skill for the lock\'s level it breaks open; the skill you used rises, and an owned lock reports you.");',
     '\t\tImGuiMCP::TextWrapped("%s", strings::TR("ALIO_SmashIntro", "Hit a locked chest or door with a weapon. With enough weapon skill for the lock\'s level it breaks open; the skill you used rises, and an owned lock reports you."));'),
    ('ImGuiMCP::Toggle("Smash locks with a weapon", &smash::enabled);',
     'ImGuiMCP::Toggle(strings::TR("ALIO_SmashEnabled", "Smash locks with a weapon"), &smash::enabled);'),
    ('\t\tHelpMarker("On: a weapon hit on a locked object is judged against the table below.");',
     '\t\tHelpMarker(strings::TR("ALIO_HelpSmashEnabled", "On: a weapon hit on a locked object is judged against the table below."));'),
    ('\t\tif (ImGuiMCP::Combo("Allowed weapons", &mode, kWeaponModes, 3)) { smash::weapons = static_cast<std::uint32_t>(mode); }',
     '\t\tif (ComboTR(strings::TR("ALIO_AllowedWeapons", "Allowed weapons"), &mode, kWeaponModeKeys, kWeaponModeLabels, 3)) { smash::weapons = static_cast<std::uint32_t>(mode); }'),
    ('\t\tHelpMarker("Which weapons count. Two-handed weapons always do; one-handed and everything else are up to this setting. Bows and crossbows use Archery, staves use Destruction, fists count as one-handed.");',
     '\t\tHelpMarker(strings::TR("ALIO_HelpAllowedWeapons", "Which weapons count. Two-handed weapons always do; one-handed and everything else are up to this setting. Bows and crossbows use Archery, staves use Destruction, fists count as one-handed."));'),
    ('\t\tTierTable("smash", smash::need, "Weapon skill (One-handed or Two-handed)");',
     '\t\tTierTable("smash", smash::need, strings::TR("ALIO_SkillWeapon", "Weapon skill (One-handed or Two-handed)"));'),
    ('\t\tImGuiMCP::TextWrapped("A frozen lock (see Unlock Spell) needs %u less skill to smash.", spell::frostMalus);',
     '\t\tImGuiMCP::TextWrapped(strings::TR("ALIO_SmashFrostNote", "A frozen lock (see Unlock Spell) needs %u less skill to smash."), spell::frostMalus);'),

    # --- SpellPanel ---
    ('\t\tusing namespace settings;\r\n\t\tStandDownBanner();\r\n\t\tconst auto s = Locks::GetState();\r\n\t\tImGuiMCP::TextWrapped("Manipulate Lock is an Alteration spell',
     '\t\tstrings::Tick();\r\n\t\tusing namespace settings;\r\n\t\tStandDownBanner();\r\n\t\tconst auto s = Locks::GetState();\r\n\t\tImGuiMCP::TextWrapped("Manipulate Lock is an Alteration spell'),
    ('\t\tImGuiMCP::TextWrapped("Manipulate Lock is an Alteration spell that works a lock\'s mechanism from a distance. Cast it at a lock: with enough Alteration for the lock\'s level it opens. Destruction can join in: frost freezes a lock (easier to smash), fire thaws it or opens it outright, shock opens it too if allowed.");',
     '\t\tImGuiMCP::TextWrapped("%s", strings::TR("ALIO_SpellIntro", "Manipulate Lock is an Alteration spell that works a lock\'s mechanism from a distance. Cast it at a lock: with enough Alteration for the lock\'s level it opens. Destruction can join in: frost freezes a lock (easier to smash), fire thaws it or opens it outright, shock opens it too if allowed."));'),
    ('ImGuiMCP::Toggle("Know the spell Manipulate Lock", &spell::enabled);',
     'ImGuiMCP::Toggle(strings::TR("ALIO_SpellEnabled", "Know the spell Manipulate Lock"), &spell::enabled);'),
    ('\t\tHelpMarker("On: the spell is added to your spell book (Alteration, cost 30). Off: it is taken away again.");',
     '\t\tHelpMarker(strings::TR("ALIO_HelpSpellEnabled", "On: the spell is added to your spell book (Alteration, cost 30). Off: it is taken away again."));'),
    ('if (!s.spellResolved) { ImGuiMCP::TextWrapped("LockInteractionOverhaul.esp is not loaded - enable it in your mod manager or the spell cannot exist."); }',
     'if (!s.spellResolved) { ImGuiMCP::TextWrapped("%s", strings::TR("ALIO_EslMissing", "LockInteractionOverhaul.esp is not loaded - enable it in your mod manager or the spell cannot exist.")); }'),
    ('else { ImGuiMCP::TextDisabled("%s", s.spellKnown ? "You know Manipulate Lock." : "You do not know Manipulate Lock right now."); }',
     'else { ImGuiMCP::TextDisabled("%s", s.spellKnown ? strings::TR("ALIO_SpellKnown", "You know Manipulate Lock.") : strings::TR("ALIO_SpellNotKnown", "You do not know Manipulate Lock right now.")); }'),
    ('\t\tif (ImGuiMCP::Combo("Spells that work on locks", &mode, kSpellModes, 3)) { spell::allowed = static_cast<std::uint32_t>(mode); }',
     '\t\tif (ComboTR(strings::TR("ALIO_AllowedSpells", "Spells that work on locks"), &mode, kSpellModeKeys, kSpellModeLabels, 3)) { spell::allowed = static_cast<std::uint32_t>(mode); }'),
    ('\t\tHelpMarker("Manipulate Lock uses your Alteration; fire and shock use your Destruction against the same table.");',
     '\t\tHelpMarker(strings::TR("ALIO_HelpAllowedSpells", "Manipulate Lock uses your Alteration; fire and shock use your Destruction against the same table."));'),
    ('\t\tTierTable("spell", spell::need, "Magic skill (Alteration for the spell, Destruction for fire and shock)");',
     '\t\tTierTable("spell", spell::need, strings::TR("ALIO_SkillMagic", "Magic skill (Alteration for the spell, Destruction for fire and shock)"));'),
    ('\t\tPercent("Frost makes a lock easier to smash by", spell::frostMalus, "A frozen lock needs this much less weapon skill to smash, 0 to 100.");',
     '\t\tPercent(strings::TR("ALIO_FrostMalus", "Frost makes a lock easier to smash by"), spell::frostMalus, strings::TR("ALIO_HelpFrostMalus", "A frozen lock needs this much less weapon skill to smash, 0 to 100."));'),
    ('\t\tImGuiMCP::Text("Locks frozen right now: %u", s.frozenCount);',
     '\t\tImGuiMCP::Text(strings::TR("ALIO_FrozenNow", "Locks frozen right now: %u"), s.frozenCount);'),

    # --- PickAnglePanel ---
    ('\t\tusing namespace settings;\r\n\t\tStandDownBanner();\r\n\t\tconst auto s = Locks::GetState();\r\n\t\tImGuiMCP::TextWrapped("When a lockpick breaks',
     '\t\tstrings::Tick();\r\n\t\tusing namespace settings;\r\n\t\tStandDownBanner();\r\n\t\tconst auto s = Locks::GetState();\r\n\t\tImGuiMCP::TextWrapped("When a lockpick breaks'),
    ('\t\tImGuiMCP::TextWrapped("When a lockpick breaks, the next pick starts at the angle where the last one broke instead of resetting to the middle - Remember Lockpick Angle\'s behaviour, built in. Optionally only once you have a perk.");',
     '\t\tImGuiMCP::TextWrapped("%s", strings::TR("ALIO_AngleIntro", "When a lockpick breaks, the next pick starts at the angle where the last one broke instead of resetting to the middle - Remember Lockpick Angle\'s behaviour, built in. Optionally only once you have a perk."));'),
    ('if (ImGuiMCP::Toggle("Remember the pick angle", &enabled))',
     'if (ImGuiMCP::Toggle(strings::TR("ALIO_AngleEnabled", "Remember the pick angle"), &enabled))'),
    ('\t\tHelpMarker("On: a broken pick\'s angle is kept. Off: vanilla - every new pick starts at the middle.");',
     '\t\tHelpMarker(strings::TR("ALIO_HelpAngleEnabled", "On: a broken pick\'s angle is kept. Off: vanilla - every new pick starts at the middle."));'),
    ('\t\tif (ImGuiMCP::Combo("Only with this perk", &perk, kPerkNames, 8)) { pickangle::requiredPerk = static_cast<std::uint32_t>(perk); Locks::ApplySettings(); }',
     '\t\tif (ComboTR(strings::TR("ALIO_AnglePerk", "Only with this perk"), &perk, kPerkKeys, kPerkLabels, 8)) { pickangle::requiredPerk = static_cast<std::uint32_t>(perk); Locks::ApplySettings(); }'),
    ('\t\tHelpMarker("The angle is kept only while your character has this perk. Custom: name the plugin and the perk\'s form ID in the INI (sPerkPlugin, uPerkFormID).");',
     '\t\tHelpMarker(strings::TR("ALIO_HelpAnglePerk", "The angle is kept only while your character has this perk. Custom: name the plugin and the perk\'s form ID in the INI (sPerkPlugin, uPerkFormID)."));'),
    ('\t\tImGuiMCP::Text("Perk gate: %s", s.requiredPerkName.c_str());',
     '\t\tImGuiMCP::Text(strings::TR("ALIO_AnglePerkGate", "Perk gate: %s"), s.requiredPerkName.c_str());'),
    ('if (s.pickAngleStandingDown) { ImGuiMCP::TextWrapped("RememberLockpickAngle.dll is loaded - this section stands down and that mod keeps the angle."); }',
     'if (s.pickAngleStandingDown) { ImGuiMCP::TextWrapped("%s", strings::TR("ALIO_AngleStandDown", "RememberLockpickAngle.dll is loaded - this section stands down and that mod keeps the angle.")); }'),
    ('else { ImGuiMCP::TextWrapped("Patch: %s", s.patchStatus.c_str()); }',
     'else { ImGuiMCP::TextWrapped(strings::TR("ALIO_AnglePatch", "Patch: %s"), s.patchStatus.c_str()); }'),

    # --- GeneralPanel ---
    ('\t\tusing namespace settings;\r\n\t\tStandDownBanner();\r\n\t\tImGuiMCP::PushItemWidth(260.0F);\r\n\t\tImGuiMCP::SeparatorText("Skill gain");',
     '\t\tstrings::Tick();\r\n\t\tusing namespace settings;\r\n\t\tStandDownBanner();\r\n\t\tImGuiMCP::PushItemWidth(260.0F);\r\n\t\tImGuiMCP::SeparatorText(strings::TR("ALIO_SkillGainHeader", "Skill gain"));'),
    ('ImGuiMCP::Toggle("Opening a lock raises the skill that opened it", &general::skillGain);',
     'ImGuiMCP::Toggle(strings::TR("ALIO_SkillGain", "Opening a lock raises the skill that opened it"), &general::skillGain);'),
    ('\t\tHelpMarker("The game\'s own per-level amounts (fSkillUsageLockPick...), applied to Lockpicking, the weapon skill or the magic school that opened the lock.");',
     '\t\tHelpMarker(strings::TR("ALIO_HelpSkillGain", "The game\'s own per-level amounts (fSkillUsageLockPick...), applied to Lockpicking, the weapon skill or the magic school that opened the lock."));'),
    ('\t\tImGuiMCP::SliderFloat("Skill gain multiplier", &general::skillGainMult, 0.1F, 5.0F, "%.2f x");',
     '\t\tImGuiMCP::SliderFloat(strings::TR("ALIO_SkillGainMult", "Skill gain multiplier"), &general::skillGainMult, 0.1F, 5.0F, "%.2f x");'),
    ('\t\tHelpMarker("Scales that gain, 0.1 to 5.");',
     '\t\tHelpMarker(strings::TR("ALIO_HelpSkillGainMult", "Scales that gain, 0.1 to 5."));'),
    ('ImGuiMCP::SeparatorText("Sound");',
     'ImGuiMCP::SeparatorText(strings::TR("ALIO_SoundHeader", "Sound"));'),
    ('ImGuiMCP::Toggle("Play a sound when a lock opens", &general::sound);',
     'ImGuiMCP::Toggle(strings::TR("ALIO_Sound", "Play a sound when a lock opens"), &general::sound);'),
    ('\t\tHelpMarker("The game\'s own unlock sound for picks and spells, a smash for weapons.");',
     '\t\tHelpMarker(strings::TR("ALIO_HelpSound", "The game\'s own unlock sound for picks and spells, a smash for weapons."));'),
    ('\t\tImGuiMCP::SliderFloat("Volume", &general::soundVolume, 0.0F, 1.0F, "%.2f");',
     '\t\tImGuiMCP::SliderFloat(strings::TR("ALIO_Volume", "Volume"), &general::soundVolume, 0.0F, 1.0F, "%.2f");'),
    ('\t\tHelpMarker("0 to 1.");',
     '\t\tHelpMarker(strings::TR("ALIO_HelpVolume", "0 to 1."));'),
    ('ImGuiMCP::SeparatorText("Crime");',
     'ImGuiMCP::SeparatorText(strings::TR("ALIO_CrimeHeader", "Crime"));'),
    ('ImGuiMCP::Toggle("Opening a lock you do not own is a crime", &general::crime);',
     'ImGuiMCP::Toggle(strings::TR("ALIO_Crime", "Opening a lock you do not own is a crime"), &general::crime);'),
    ('\t\tHelpMarker("Witnessed by the game\'s own rules: followers and animals do not report you, a nearby townsperson does. Quick Hands exempts auto-picking only, as the perk does in vanilla.");',
     '\t\tHelpMarker(strings::TR("ALIO_HelpCrime", "Witnessed by the game\'s own rules: followers and animals do not report you, a nearby townsperson does. Quick Hands exempts auto-picking only, as the perk does in vanilla."));'),
    ('\t\tif (ImGuiMCP::SliderFloat("Reported value", &gold, 0.0F, 500.0F, "%.0f gold"))',
     '\t\tif (ImGuiMCP::SliderFloat(strings::TR("ALIO_CrimeGold", "Reported value"), &gold, 0.0F, 500.0F, strings::TR("ALIO_GoldFormat", "%.0f gold")))'),
    ('\t\tHelpMarker("What the offence is reported as being worth.");',
     '\t\tHelpMarker(strings::TR("ALIO_HelpCrimeGold", "What the offence is reported as being worth."));'),
    ('ImGuiMCP::SeparatorText("Messages");',
     'ImGuiMCP::SeparatorText(strings::TR("ALIO_MessagesHeader", "Messages"));'),
    ('ImGuiMCP::Toggle("Show a message when this mod acts", &general::notifications);',
     'ImGuiMCP::Toggle(strings::TR("ALIO_Notifications", "Show a message when this mod acts"), &general::notifications);'),
    ('\t\tHelpMarker("A short line on screen when a lock is refused, opened, frozen or thawed.");',
     '\t\tHelpMarker(strings::TR("ALIO_HelpNotifications", "A short line on screen when a lock is refused, opened, frozen or thawed."));'),
    ('ImGuiMCP::SeparatorText("Everything off");',
     'ImGuiMCP::SeparatorText(strings::TR("ALIO_DeactivateHeader", "Everything off"));'),
    ('if (ImGuiMCP::Button("Deactivate every feature"))',
     'if (ImGuiMCP::Button(strings::TR("ALIO_DeactivateBtn", "Deactivate every feature")))'),
    ('\t\t\tstatusMessage = "Every feature switched off; the spell is removed. Press Save to keep that.";',
     '\t\t\tstatusMessage = strings::TR("ALIO_StatusDeactivated", "Every feature switched off; the spell is removed. Press Save to keep that.");'),
    ('\t\tHelpMarker("Switches off requirements, auto-pick, smashing, the spell and the pick angle at once - the state to be in before removing the mod.");',
     '\t\tHelpMarker(strings::TR("ALIO_HelpDeactivate", "Switches off requirements, auto-pick, smashing, the spell and the pick angle at once - the state to be in before removing the mod."));'),

    # --- DebugPanel ---
    ('\t\tusing namespace settings;\r\n\t\tconst auto s = Locks::GetState();\r\n\t\tImGuiMCP::PushItemWidth(260.0F);',
     '\t\tstrings::Tick();\r\n\t\tusing namespace settings;\r\n\t\tconst auto s = Locks::GetState();\r\n\t\tImGuiMCP::PushItemWidth(260.0F);'),
    ('\t\tif (ImGuiMCP::Combo("Log level", &level, kLogLevelNames, kLogLevelCount)) { debug::logLevel = static_cast<std::uint32_t>(level); ApplyLogLevel(); }',
     '\t\tif (ComboTR(strings::TR("ALIO_LogLevel", "Log level"), &level, kLogLevelKeys, kLogLevelLabels, kLogLevelCount)) { debug::logLevel = static_cast<std::uint32_t>(level); ApplyLogLevel(); }'),
    ('\t\tHelpMarker("Applies immediately. The log is at Documents\\\\My Games\\\\Skyrim Special Edition\\\\SKSE\\\\ApocryphaLockInteractionOverhaul.log.");',
     '\t\tHelpMarker(strings::TR("ALIO_HelpLogLevel", "Applies immediately. The log is at Documents\\\\My Games\\\\Skyrim Special Edition\\\\SKSE\\\\ApocryphaLockInteractionOverhaul.log."));'),
    ('ImGuiMCP::SeparatorText("Live");',
     'ImGuiMCP::SeparatorText(strings::TR("ALIO_LiveHeader", "Live"));'),
    ('\t\tImGuiMCP::Text("Locks opened by this mod this session: %llu", static_cast<unsigned long long>(s.opened));',
     '\t\tImGuiMCP::Text(strings::TR("ALIO_OpenedCount", "Locks opened by this mod this session: %llu"), static_cast<unsigned long long>(s.opened));'),
    ('\t\tImGuiMCP::Text("Frozen locks: %u", s.frozenCount);',
     '\t\tImGuiMCP::Text(strings::TR("ALIO_FrozenCount", "Frozen locks: %u"), s.frozenCount);'),
    ('\t\tImGuiMCP::TextWrapped("Last event: %s", s.lastEvent.empty() ? "nothing yet" : s.lastEvent.c_str());',
     '\t\tImGuiMCP::TextWrapped(strings::TR("ALIO_LastEvent", "Last event: %s"), s.lastEvent.empty() ? strings::TR("ALIO_NothingYet", "nothing yet") : s.lastEvent.c_str());'),
    ('\t\tImGuiMCP::TextWrapped("Spell: %s", s.spellResolved ? (s.spellKnown ? "resolved, known" : "resolved, not known") : "NOT resolved (ESL missing)");',
     '\t\tImGuiMCP::TextWrapped(strings::TR("ALIO_SpellState", "Spell: %s"), s.spellResolved ? (s.spellKnown ? strings::TR("ALIO_SpellResolvedKnown", "resolved, known") : strings::TR("ALIO_SpellResolvedNotKnown", "resolved, not known")) : strings::TR("ALIO_SpellUnresolved", "NOT resolved (ESL missing)"));'),
    ('\t\tImGuiMCP::TextWrapped("Pick-angle patch: %s", s.patchStatus.c_str());',
     '\t\tImGuiMCP::TextWrapped(strings::TR("ALIO_PatchState", "Pick-angle patch: %s"), s.patchStatus.c_str());'),
    ('\t\tImGuiMCP::TextWrapped("Standing down: %s", s.standingDown ? "yes (Lock Overhaul.esp)" : "no");',
     '\t\tImGuiMCP::TextWrapped(strings::TR("ALIO_StandingDown", "Standing down: %s"), s.standingDown ? strings::TR("ALIO_StandingDownYes", "yes (Lock Overhaul.esp)") : YesNo(false));'),
    ('ImGuiMCP::SeparatorText("The lock you are looking at");',
     'ImGuiMCP::SeparatorText(strings::TR("ALIO_CrosshairHeader", "The lock you are looking at"));'),
]

# YesNo() lives with the other helpers; inserted with them so the CrosshairReadout pairs compile.
YESNO_NEW = (
    '\t\tconst char* YesNo(bool a_value)\r\n'
    '\t\t{\r\n'
    '\t\t\treturn a_value ? strings::TR("ALIO_Yes", "yes") : strings::TR("ALIO_No", "no");\r\n'
    '\t\t}\r\n'
    '\r\n'
)


def patch_ui_cpp():
    path = os.path.join(REPO, "source", "UI.cpp")
    text = read(path)
    if "strings::Tick();" in text:
        print("  UI.cpp: already patched")
        return
    pairs = list(UI_PAIRS)
    # splice YesNo in front of the other helpers (pair index 3 is the helper insertion)
    anchor, replacement = pairs[3]
    pairs[3] = (anchor, YESNO_NEW + replacement)
    text = apply_all(text, pairs, "UI.cpp")
    write(path, text)
    print("  UI.cpp: patched ({} anchors)".format(len(pairs)))


def main():
    print("lang-patch.py - ApocryphaRealm Lock Interaction Overhaul")
    patch_skse_menu_framework_h()
    patch_main_cpp()
    patch_devbench_tool_cpp()
    patch_ui_cpp()
    print("done")


if __name__ == "__main__":
    main()
