#include "PCH.h"

#include "UI.h"

#include "SKSEMenuFramework.h"

#include "Locks.h"
#include "Settings.h"

#include "utils/Logger.h"
#include "utils/Strings.h"
#include "utils/Toggle.h"

#include <algorithm>
#include <cstdio>
#include <functional>
#include <string>
#include <vector>

namespace UI
{
	namespace
	{
		std::string statusMessage;

		constexpr int kLogLevelCount = 7;
		constexpr const char* kLogLevelKeys[] = { "ALIO_Log_Trace", "ALIO_Log_Debug", "ALIO_Log_Info", "ALIO_Log_Warning", "ALIO_Log_Error", "ALIO_Log_Critical", "ALIO_Log_Off" };
		constexpr const char* kLogLevelLabels[] = { "Trace", "Debug", "Info", "Warning", "Error", "Critical", "Off" };
		constexpr const char* kWeaponModeKeys[] = { "ALIO_Weapons_TwoOnly", "ALIO_Weapons_OneAndTwo", "ALIO_Weapons_Any" };
		constexpr const char* kWeaponModeLabels[] = { "Two-handed weapons only", "One- and two-handed weapons", "Any weapon (bows, crossbows, staves, fists too)" };
		constexpr const char* kSpellModeKeys[] = { "ALIO_Spells_LockOnly", "ALIO_Spells_Destruction", "ALIO_Spells_Shock" };
		constexpr const char* kSpellModeLabels[] = { "Manipulate Lock only", "Plus Destruction: frost freezes, fire thaws or opens", "All of that plus shock spells open locks" };
		constexpr const char* kPerkKeys[] = { "ALIO_Perk_None", "ALIO_Perk_Locksmith", "ALIO_Perk_Unbreakable", "ALIO_Perk_QuickHands", "ALIO_Perk_WaxKey", "ALIO_Perk_GoldenTouch", "ALIO_Perk_TreasureHunter", "ALIO_Perk_Custom" };
		constexpr const char* kPerkLabels[] = { "None", "Locksmith", "Unbreakable", "Quick Hands", "Wax Key", "Golden Touch", "Treasure Hunter", "Custom (sPerkPlugin + uPerkFormID in the INI)" };
		constexpr const char* kTierKeys[] = { "ALIO_Tier_Novice", "ALIO_Tier_Apprentice", "ALIO_Tier_Adept", "ALIO_Tier_Expert", "ALIO_Tier_Master" };
		constexpr const char* kTierLabels[] = { "Novice", "Apprentice", "Adept", "Expert", "Master" };
		constexpr const char* kTierLockKeys[] = { "ALIO_TierLock_Novice", "ALIO_TierLock_Apprentice", "ALIO_TierLock_Adept", "ALIO_TierLock_Expert", "ALIO_TierLock_Master" };
		constexpr const char* kTierLockLabels[] = { "Novice lock", "Apprentice lock", "Adept lock", "Expert lock", "Master lock" };

		void OnMainThread(std::function<void()> a_task)
		{
			if (auto* taskInterface = SKSE::GetTaskInterface()) { taskInterface->AddTask(std::move(a_task)); }
		}

		bool HasRequiredExports()
		{
			constexpr const char* required[] = {
				"AddSectionItem", "igTextV", "igTextDisabledV", "igTextWrappedV", "igSetTooltipV", "igSeparatorText",
				"igCombo_Str_arr", "igSliderFloat", "igIsItemHovered", "igButton", "igSameLine", "igSpacing",
				"igPushItemWidth", "igPopItemWidth", "igGetCursorScreenPos", "igGetWindowDrawList", "igGetFrameHeight",
				"igInvisibleButton", "igPushID_Str", "igPopID", "ImDrawList_AddRectFilled", "ImDrawList_AddCircleFilled"
			};
			for (const char* name : required)
			{
				if (!GetMenuFrameworkFunction<void*>(name))
				{
					logger::warn("The menu framework does not export \"{}\"", name);
					return false;
				}
			}
			return true;
		}

		const char* YesNo(bool a_value)
		{
			return a_value ? strings::TR("ALIO_Yes", "yes") : strings::TR("ALIO_No", "no");
		}

		// The lock tier as the player reads it. Locks::TierName() is the log/JSON form and stays
		// English; this is the drawn form.
		const char* TierText(int a_index)
		{
			return (a_index >= 0 && a_index < settings::kTierCount) ? strings::TR(kTierKeys[a_index], kTierLabels[a_index])
																	 : strings::TR("ALIO_Tier_KeyRequired", "key-required");
		}
		const char* TierText(Locks::Tier a_tier) { return TierText(static_cast<int>(a_tier)); }

		// A Combo whose option list is rebuilt from TR'd entries every frame (plan 2.2): store
		// owns the translated bytes for the duration of the call, so the pointers stay valid.
		bool ComboTR(const char* a_label, int* a_current,
					 const char* const* a_keys, const char* const* a_labels, int a_count)
		{
			std::vector<std::string> store;
			store.reserve(static_cast<std::size_t>(a_count));
			for (int i = 0; i < a_count; ++i) { store.emplace_back(strings::TR(a_keys[i], a_labels[i])); }
			std::vector<const char*> items;
			items.reserve(store.size());
			for (const auto& s : store) { items.push_back(s.c_str()); }
			return ImGuiMCP::Combo(a_label, a_current, items.data(), a_count);
		}

		void HelpMarker(const char* a_description)
		{
			ImGuiMCP::SameLine();
			ImGuiMCP::TextDisabled("%s", strings::TR("ALIO_HelpMark", "(?)"));
			if (ImGuiMCP::IsItemHovered()) { ImGuiMCP::SetTooltip("%s", a_description); }
		}

		// An integer 0..100 drawn as the framework's slider (there is no integer slider export).
		bool Percent(const char* a_label, std::uint32_t& a_value, const char* a_help)
		{
			float v = static_cast<float>(a_value);
			const bool changed = ImGuiMCP::SliderFloat(a_label, &v, 0.0F, 100.0F, "%.0f");
			if (changed) { a_value = static_cast<std::uint32_t>(std::clamp(v, 0.0F, 100.0F) + 0.5F); }
			HelpMarker(a_help);
			return changed;
		}

		void TierTable(const char* a_id, std::uint32_t* a_values, const char* a_skill)
		{
			ImGuiMCP::PushID(a_id);
			const char* const skill = a_skill;
			const char* const helpFormat = strings::TR("ALIO_TierHelp", "%s needed for a %s lock, 0 to 100.");
			for (int i = 0; i < settings::kTierCount; ++i)
			{
				char help[512] = {};
				std::snprintf(help, sizeof(help), helpFormat, skill, TierText(i));
				Percent(strings::TR(kTierLockKeys[i], kTierLockLabels[i]), a_values[i], help);
			}
			ImGuiMCP::PopID();
		}

		void CrosshairReadout()
		{
			const auto info = Locks::LookingAt();
			if (!info.valid) { ImGuiMCP::TextDisabled("%s", strings::TR("ALIO_LookAtNothing", "Look at a locked chest or door to see how this mod judges it.")); return; }
			if (!info.locked) { ImGuiMCP::Text(strings::TR("ALIO_LookNotLocked", "%s: not locked."), info.name.c_str()); return; }
			if (info.requiresKey) { ImGuiMCP::Text(strings::TR("ALIO_LookNeedsKey", "%s: needs a key - this mod leaves it alone."), info.name.c_str()); return; }
			ImGuiMCP::Text(strings::TR("ALIO_LookLock", "%s: %s lock%s%s"), info.name.c_str(), TierText(info.tier),
						   info.frozen ? strings::TR("ALIO_LookFrozen", ", frozen") : "",
						   info.crime ? strings::TR("ALIO_LookCrime", ", opening it is a crime") : "");
			const auto pick = Locks::CanPick(info);
			const auto smash1 = Locks::CanSmash(info, RE::ActorValue::kOneHanded);
			const auto smash2 = Locks::CanSmash(info, RE::ActorValue::kTwoHanded);
			const auto alt = Locks::CanUnlockBySpell(info, RE::ActorValue::kAlteration);
			const auto des = Locks::CanUnlockBySpell(info, RE::ActorValue::kDestruction);
			ImGuiMCP::Text(strings::TR("ALIO_LookPick", "Pick: %s (Lockpicking %u, needs %u)"), pick.allowed ? YesNo(true) : YesNo(false), pick.have, pick.needed);
			ImGuiMCP::Text(strings::TR("ALIO_LookSmash", "Smash: one-handed %s (%u of %u), two-handed %s (%u of %u)"), YesNo(smash1.allowed), smash1.have, smash1.needed, YesNo(smash2.allowed), smash2.have, smash2.needed);
			ImGuiMCP::Text(strings::TR("ALIO_LookMagic", "Magic: Alteration %s (%u of %u), Destruction %s (%u of %u)"), YesNo(alt.allowed), alt.have, alt.needed, YesNo(des.allowed), des.have, des.needed);
		}

		void StandDownBanner()
		{
			const auto s = Locks::GetState();
			if (s.standingDown)
			{
				ImGuiMCP::TextWrapped("%s", strings::TR("ALIO_StandDown", "Lock Overhaul.esp is loaded, so this mod is standing down completely - nothing on these pages does anything until that mod is removed."));
				ImGuiMCP::Spacing();
			}
		}

		void RenderButtons()
		{
			ImGuiMCP::SeparatorText("");
			if (ImGuiMCP::Button(strings::TR("ALIO_SaveBtn", "Save")))
			{
				statusMessage = strings::TR("ALIO_StatusSaving", "Saving...");
				OnMainThread([]() { statusMessage = settings::Save() ? strings::TR("ALIO_StatusSaved", "Settings saved.")
												 : strings::TR("ALIO_StatusSaveFail", "Could not write the INI. See the log for why."); });
			}
			HelpMarker(strings::TR("ALIO_HelpSave", "Writes every setting on every section to the plugin's INI so it survives a restart."));
			ImGuiMCP::SameLine();
			if (ImGuiMCP::Button(strings::TR("ALIO_ReloadBtn", "Reload from INI")))
			{
				statusMessage = strings::TR("ALIO_StatusReloading", "Reloading...");
				OnMainThread([]() {
					statusMessage = settings::Reload() ? strings::TR("ALIO_StatusReloaded", "Settings reloaded from the INI.")
													   : strings::TR("ALIO_StatusReloadFail", "Could not read the INI. See the log for why.");
					Locks::ApplySettings();
				});
			}
			HelpMarker(strings::TR("ALIO_HelpReload", "Throws away any change made here since the last save and re-reads the INI from disk."));
			ImGuiMCP::SameLine();
			if (ImGuiMCP::Button(strings::TR("ALIO_RestoreBtn", "Restore defaults")))
			{
				OnMainThread([]() { settings::RestoreDefaults(); Locks::ApplySettings(); logger::debug("Restored default settings"); });
				statusMessage = strings::TR("ALIO_StatusRestored", "Defaults restored (everything off). Press Save to keep them.");
			}
			HelpMarker(strings::TR("ALIO_HelpRestore", "Puts every setting back to its fresh-install value - every feature off. Nothing is written until you press Save."));
			if (!statusMessage.empty()) { ImGuiMCP::TextWrapped("%s", statusMessage.c_str()); }
			ImGuiMCP::Spacing();
			ImGuiMCP::Text("%s", settings::GetIniPath().c_str());
		}
	}

	void Register()
	{
		if (!SKSEMenuFramework::IsInstalled())
		{
			logger::info("No menu framework is installed; settings will be read from the INI only");
			return;
		}
		if (!HasRequiredExports())
		{
			logger::warn("The installed menu framework is older than this plugin's settings menu needs. Update it (Apocrypha Menu Framework, or SKSE Menu Framework version 3 or newer).");
			return;
		}
		SKSEMenuFramework::SetSection("ApocryphaRealm Lock Interaction Overhaul");
		SKSEMenuFramework::AddSectionItem("Requirements", RequirementsPanel::Render);
		SKSEMenuFramework::AddSectionItem("Smash Locks", SmashPanel::Render);
		SKSEMenuFramework::AddSectionItem("Unlock Spell", SpellPanel::Render);
		SKSEMenuFramework::AddSectionItem("Pick Angle", PickAnglePanel::Render);
		SKSEMenuFramework::AddSectionItem("General", GeneralPanel::Render);
		SKSEMenuFramework::AddSectionItem("Debug", DebugPanel::Render);
		logger::info("Registered the settings pages with the menu framework");
	}

	void __stdcall RequirementsPanel::Render()
	{
		strings::Tick();
		using namespace settings;
		StandDownBanner();
		ImGuiMCP::TextWrapped("%s", strings::TR("ALIO_ReqIntro", "A lock needs a Lockpicking skill for its level before the picking menu opens; below it the menu closes again and no lockpick is lost. Key-required locks are never touched."));
		ImGuiMCP::Spacing();
		ImGuiMCP::PushItemWidth(260.0F);
		ImGuiMCP::SeparatorText(strings::TR("ALIO_ReqHeader", "Lock requirements"));
		ImGuiMCP::Toggle(strings::TR("ALIO_ReqEnabled", "Require a Lockpicking skill per lock level"), &requirements::enabled);
		HelpMarker(strings::TR("ALIO_HelpReqEnabled", "On: the table below gates the picking menu. Off: any lock can be tried, as in vanilla."));
		TierTable("pick", requirements::pick, strings::TR("ALIO_SkillLockpicking", "Lockpicking"));
		ImGuiMCP::SeparatorText(strings::TR("ALIO_AutoPickHeader", "Auto pick"));
		ImGuiMCP::Toggle(strings::TR("ALIO_AutoPick", "Open locks without the minigame"), &requirements::autoPick);
		HelpMarker(strings::TR("ALIO_HelpAutoPick", "With enough Lockpicking (the table above) the lock simply opens: one lockpick is used (none with the Unbreakable perk), Lockpicking rises as the game's own picking would raise it, and opening an owned lock is a crime unless you have Quick Hands."));
		ImGuiMCP::Toggle(strings::TR("ALIO_OpenAfterPick", "Open the chest or door straight away"), &requirements::openAfterPick);
		HelpMarker(strings::TR("ALIO_HelpOpenAfterPick", "After auto-picking, the object is activated so it opens at once instead of needing a second press."));
		ImGuiMCP::SeparatorText(strings::TR("ALIO_ReqReadoutHeader", "What that means right now"));
		CrosshairReadout();
		ImGuiMCP::PopItemWidth();
		RenderButtons();
	}

	void __stdcall SmashPanel::Render()
	{
		strings::Tick();
		using namespace settings;
		StandDownBanner();
		ImGuiMCP::TextWrapped("%s", strings::TR("ALIO_SmashIntro", "Hit a locked chest or door with a weapon. With enough weapon skill for the lock's level it breaks open; the skill you used rises, and an owned lock reports you."));
		ImGuiMCP::Spacing();
		ImGuiMCP::PushItemWidth(300.0F);
		ImGuiMCP::Toggle(strings::TR("ALIO_SmashEnabled", "Smash locks with a weapon"), &smash::enabled);
		HelpMarker(strings::TR("ALIO_HelpSmashEnabled", "On: a weapon hit on a locked object is judged against the table below."));
		int mode = static_cast<int>(std::min<std::uint32_t>(smash::weapons, 2u));
		if (ComboTR(strings::TR("ALIO_AllowedWeapons", "Allowed weapons"), &mode, kWeaponModeKeys, kWeaponModeLabels, 3)) { smash::weapons = static_cast<std::uint32_t>(mode); }
		HelpMarker(strings::TR("ALIO_HelpAllowedWeapons", "Which weapons count. Two-handed weapons always do; one-handed and everything else are up to this setting. Bows and crossbows use Archery, staves use Destruction, fists count as one-handed."));
		TierTable("smash", smash::need, strings::TR("ALIO_SkillWeapon", "Weapon skill (One-handed or Two-handed)"));
		ImGuiMCP::TextWrapped(strings::TR("ALIO_SmashFrostNote", "A frozen lock (see Unlock Spell) needs %u less skill to smash."), spell::frostMalus);
		ImGuiMCP::PopItemWidth();
		RenderButtons();
	}

	void __stdcall SpellPanel::Render()
	{
		strings::Tick();
		using namespace settings;
		StandDownBanner();
		const auto s = Locks::GetState();
		ImGuiMCP::TextWrapped("%s", strings::TR("ALIO_SpellIntro", "Manipulate Lock is an Alteration spell that works a lock's mechanism from a distance. Cast it at a lock: with enough Alteration for the lock's level it opens. Destruction can join in: frost freezes a lock (easier to smash), fire thaws it or opens it outright, shock opens it too if allowed."));
		ImGuiMCP::Spacing();
		ImGuiMCP::PushItemWidth(300.0F);
		ImGuiMCP::Toggle(strings::TR("ALIO_SpellEnabled", "Know the spell Manipulate Lock"), &spell::enabled);
		HelpMarker(strings::TR("ALIO_HelpSpellEnabled", "On: the spell is added to your spell book (Alteration, cost 30). Off: it is taken away again."));
		if (!s.spellResolved) { ImGuiMCP::TextWrapped("%s", strings::TR("ALIO_EslMissing", "ApocryphaLockInteractionOverhaul.esl is not loaded - enable it in your mod manager or the spell cannot exist.")); }
		else { ImGuiMCP::TextDisabled("%s", s.spellKnown ? strings::TR("ALIO_SpellKnown", "You know Manipulate Lock.") : strings::TR("ALIO_SpellNotKnown", "You do not know Manipulate Lock right now.")); }
		int mode = static_cast<int>(std::min<std::uint32_t>(spell::allowed, 2u));
		if (ComboTR(strings::TR("ALIO_AllowedSpells", "Spells that work on locks"), &mode, kSpellModeKeys, kSpellModeLabels, 3)) { spell::allowed = static_cast<std::uint32_t>(mode); }
		HelpMarker(strings::TR("ALIO_HelpAllowedSpells", "Manipulate Lock uses your Alteration; fire and shock use your Destruction against the same table."));
		TierTable("spell", spell::need, strings::TR("ALIO_SkillMagic", "Magic skill (Alteration for the spell, Destruction for fire and shock)"));
		Percent(strings::TR("ALIO_FrostMalus", "Frost makes a lock easier to smash by"), spell::frostMalus, strings::TR("ALIO_HelpFrostMalus", "A frozen lock needs this much less weapon skill to smash, 0 to 100."));
		ImGuiMCP::Text(strings::TR("ALIO_FrozenNow", "Locks frozen right now: %u"), s.frozenCount);
		ImGuiMCP::PopItemWidth();
		RenderButtons();
	}

	void __stdcall PickAnglePanel::Render()
	{
		strings::Tick();
		using namespace settings;
		StandDownBanner();
		const auto s = Locks::GetState();
		ImGuiMCP::TextWrapped("%s", strings::TR("ALIO_AngleIntro", "When a lockpick breaks, the next pick starts at the angle where the last one broke instead of resetting to the middle - Remember Lockpick Angle's behaviour, built in. Optionally only once you have a perk."));
		ImGuiMCP::Spacing();
		ImGuiMCP::PushItemWidth(300.0F);
		bool enabled = pickangle::enabled;
		if (ImGuiMCP::Toggle(strings::TR("ALIO_AngleEnabled", "Remember the pick angle"), &enabled)) { pickangle::enabled = enabled; Locks::ApplySettings(); }
		HelpMarker(strings::TR("ALIO_HelpAngleEnabled", "On: a broken pick's angle is kept. Off: vanilla - every new pick starts at the middle."));
		int perk = static_cast<int>(std::min<std::uint32_t>(pickangle::requiredPerk, 7u));
		if (ComboTR(strings::TR("ALIO_AnglePerk", "Only with this perk"), &perk, kPerkKeys, kPerkLabels, 8)) { pickangle::requiredPerk = static_cast<std::uint32_t>(perk); Locks::ApplySettings(); }
		HelpMarker(strings::TR("ALIO_HelpAnglePerk", "The angle is kept only while your character has this perk. Custom: name the plugin and the perk's form ID in the INI (sPerkPlugin, uPerkFormID)."));
		ImGuiMCP::Text(strings::TR("ALIO_AnglePerkGate", "Perk gate: %s"), s.requiredPerkName.c_str());
		if (s.pickAngleStandingDown) { ImGuiMCP::TextWrapped("%s", strings::TR("ALIO_AngleStandDown", "RememberLockpickAngle.dll is loaded - this section stands down and that mod keeps the angle.")); }
		else { ImGuiMCP::TextWrapped(strings::TR("ALIO_AnglePatch", "Patch: %s"), s.patchStatus.c_str()); }
		ImGuiMCP::PopItemWidth();
		RenderButtons();
	}

	void __stdcall GeneralPanel::Render()
	{
		strings::Tick();
		using namespace settings;
		StandDownBanner();
		ImGuiMCP::PushItemWidth(260.0F);
		ImGuiMCP::SeparatorText(strings::TR("ALIO_SkillGainHeader", "Skill gain"));
		ImGuiMCP::Toggle(strings::TR("ALIO_SkillGain", "Opening a lock raises the skill that opened it"), &general::skillGain);
		HelpMarker(strings::TR("ALIO_HelpSkillGain", "The game's own per-level amounts (fSkillUsageLockPick...), applied to Lockpicking, the weapon skill or the magic school that opened the lock."));
		ImGuiMCP::SliderFloat(strings::TR("ALIO_SkillGainMult", "Skill gain multiplier"), &general::skillGainMult, 0.1F, 5.0F, "%.2f x");
		HelpMarker(strings::TR("ALIO_HelpSkillGainMult", "Scales that gain, 0.1 to 5."));
		ImGuiMCP::SeparatorText(strings::TR("ALIO_SoundHeader", "Sound"));
		ImGuiMCP::Toggle(strings::TR("ALIO_Sound", "Play a sound when a lock opens"), &general::sound);
		HelpMarker(strings::TR("ALIO_HelpSound", "The game's own unlock sound for picks and spells, a smash for weapons."));
		ImGuiMCP::SliderFloat(strings::TR("ALIO_Volume", "Volume"), &general::soundVolume, 0.0F, 1.0F, "%.2f");
		HelpMarker(strings::TR("ALIO_HelpVolume", "0 to 1."));
		ImGuiMCP::SeparatorText(strings::TR("ALIO_CrimeHeader", "Crime"));
		ImGuiMCP::Toggle(strings::TR("ALIO_Crime", "Opening a lock you do not own is a crime"), &general::crime);
		HelpMarker(strings::TR("ALIO_HelpCrime", "Witnessed by the game's own rules: followers and animals do not report you, a nearby townsperson does. Quick Hands exempts auto-picking only, as the perk does in vanilla."));
		float gold = static_cast<float>(general::crimeGold);
		if (ImGuiMCP::SliderFloat(strings::TR("ALIO_CrimeGold", "Reported value"), &gold, 0.0F, 500.0F, strings::TR("ALIO_GoldFormat", "%.0f gold"))) { general::crimeGold = static_cast<std::uint32_t>(std::clamp(gold, 0.0F, 500.0F) + 0.5F); }
		HelpMarker(strings::TR("ALIO_HelpCrimeGold", "What the offence is reported as being worth."));
		ImGuiMCP::SeparatorText(strings::TR("ALIO_MessagesHeader", "Messages"));
		ImGuiMCP::Toggle(strings::TR("ALIO_Notifications", "Show a message when this mod acts"), &general::notifications);
		HelpMarker(strings::TR("ALIO_HelpNotifications", "A short line on screen when a lock is refused, opened, frozen or thawed."));
		ImGuiMCP::SeparatorText(strings::TR("ALIO_DeactivateHeader", "Everything off"));
		if (ImGuiMCP::Button(strings::TR("ALIO_DeactivateBtn", "Deactivate every feature")))
		{
			OnMainThread([]() { Locks::DeactivateAll(); });
			statusMessage = strings::TR("ALIO_StatusDeactivated", "Every feature switched off; the spell is removed. Press Save to keep that.");
		}
		HelpMarker(strings::TR("ALIO_HelpDeactivate", "Switches off requirements, auto-pick, smashing, the spell and the pick angle at once - the state to be in before removing the mod."));
		ImGuiMCP::PopItemWidth();
		RenderButtons();
	}

	void __stdcall DebugPanel::Render()
	{
		strings::Tick();
		using namespace settings;
		const auto s = Locks::GetState();
		ImGuiMCP::PushItemWidth(260.0F);
		int level = std::clamp(static_cast<int>(debug::logLevel), 0, kLogLevelCount - 1);
		if (ComboTR(strings::TR("ALIO_LogLevel", "Log level"), &level, kLogLevelKeys, kLogLevelLabels, kLogLevelCount)) { debug::logLevel = static_cast<std::uint32_t>(level); ApplyLogLevel(); }
		HelpMarker(strings::TR("ALIO_HelpLogLevel", "Applies immediately. The log is at Documents\\My Games\\Skyrim Special Edition\\SKSE\\ApocryphaLockInteractionOverhaul.log."));
		ImGuiMCP::SeparatorText(strings::TR("ALIO_LiveHeader", "Live"));
		ImGuiMCP::Text(strings::TR("ALIO_OpenedCount", "Locks opened by this mod this session: %llu"), static_cast<unsigned long long>(s.opened));
		ImGuiMCP::Text(strings::TR("ALIO_FrozenCount", "Frozen locks: %u"), s.frozenCount);
		ImGuiMCP::TextWrapped(strings::TR("ALIO_LastEvent", "Last event: %s"), s.lastEvent.empty() ? strings::TR("ALIO_NothingYet", "nothing yet") : s.lastEvent.c_str());
		ImGuiMCP::TextWrapped(strings::TR("ALIO_SpellState", "Spell: %s"), s.spellResolved ? (s.spellKnown ? strings::TR("ALIO_SpellResolvedKnown", "resolved, known") : strings::TR("ALIO_SpellResolvedNotKnown", "resolved, not known")) : strings::TR("ALIO_SpellUnresolved", "NOT resolved (ESL missing)"));
		ImGuiMCP::TextWrapped(strings::TR("ALIO_PatchState", "Pick-angle patch: %s"), s.patchStatus.c_str());
		ImGuiMCP::TextWrapped(strings::TR("ALIO_StandingDown", "Standing down: %s"), s.standingDown ? strings::TR("ALIO_StandingDownYes", "yes (Lock Overhaul.esp)") : YesNo(false));
		ImGuiMCP::SeparatorText(strings::TR("ALIO_CrosshairHeader", "The lock you are looking at"));
		CrosshairReadout();
		ImGuiMCP::PopItemWidth();
		RenderButtons();
	}
}
