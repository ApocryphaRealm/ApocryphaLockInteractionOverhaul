#include "PCH.h"

#include "UI.h"

#include "SKSEMenuFramework.h"

#include "Locks.h"
#include "Settings.h"

#include "utils/Logger.h"
#include "utils/Toggle.h"

#include <algorithm>
#include <functional>
#include <string>

namespace UI
{
	namespace
	{
		std::string statusMessage;

		constexpr const char* kLogLevelNames[] = { "Trace", "Debug", "Info", "Warning", "Error", "Critical", "Off" };
		constexpr int kLogLevelCount = 7;
		constexpr const char* kWeaponModes[] = { "Two-handed weapons only", "One- and two-handed weapons", "Any weapon (bows, crossbows, staves, fists too)" };
		constexpr const char* kSpellModes[] = { "Manipulate Lock only", "Plus Destruction: frost freezes, fire thaws or opens", "All of that plus shock spells open locks" };
		constexpr const char* kPerkNames[] = { "None", "Locksmith", "Unbreakable", "Quick Hands", "Wax Key", "Golden Touch", "Treasure Hunter", "Custom (sPerkPlugin + uPerkFormID in the INI)" };

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

		void HelpMarker(const char* a_description)
		{
			ImGuiMCP::SameLine();
			ImGuiMCP::TextDisabled("(?)");
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

		void TierTable(const char* a_id, std::uint32_t* a_values, const char* a_skillName)
		{
			ImGuiMCP::PushID(a_id);
			for (int i = 0; i < settings::kTierCount; ++i)
			{
				const std::string label = std::string(settings::kTierNames[i]) + " lock";
				const std::string help = std::string(a_skillName) + " needed for a " + settings::kTierNames[i] + " lock, 0 to 100.";
				Percent(label.c_str(), a_values[i], help.c_str());
			}
			ImGuiMCP::PopID();
		}

		void CrosshairReadout()
		{
			const auto info = Locks::LookingAt();
			if (!info.valid) { ImGuiMCP::TextDisabled("Look at a locked chest or door to see how this mod judges it."); return; }
			if (!info.locked) { ImGuiMCP::Text("%s: not locked.", info.name.c_str()); return; }
			if (info.requiresKey) { ImGuiMCP::Text("%s: needs a key - this mod leaves it alone.", info.name.c_str()); return; }
			ImGuiMCP::Text("%s: %s lock%s%s", info.name.c_str(), Locks::TierName(info.tier), info.frozen ? ", frozen" : "", info.crime ? ", opening it is a crime" : "");
			const auto pick = Locks::CanPick(info);
			const auto smash1 = Locks::CanSmash(info, RE::ActorValue::kOneHanded);
			const auto smash2 = Locks::CanSmash(info, RE::ActorValue::kTwoHanded);
			const auto alt = Locks::CanUnlockBySpell(info, RE::ActorValue::kAlteration);
			const auto des = Locks::CanUnlockBySpell(info, RE::ActorValue::kDestruction);
			ImGuiMCP::Text("Pick: %s (Lockpicking %u, needs %u)", pick.allowed ? "yes" : "no", pick.have, pick.needed);
			ImGuiMCP::Text("Smash: one-handed %s (%u of %u), two-handed %s (%u of %u)", smash1.allowed ? "yes" : "no", smash1.have, smash1.needed, smash2.allowed ? "yes" : "no", smash2.have, smash2.needed);
			ImGuiMCP::Text("Magic: Alteration %s (%u of %u), Destruction %s (%u of %u)", alt.allowed ? "yes" : "no", alt.have, alt.needed, des.allowed ? "yes" : "no", des.have, des.needed);
		}

		void StandDownBanner()
		{
			const auto s = Locks::GetState();
			if (s.standingDown)
			{
				ImGuiMCP::TextWrapped("Lock Overhaul.esp is loaded, so this mod is standing down completely - nothing on these pages does anything until that mod is removed.");
				ImGuiMCP::Spacing();
			}
		}

		void RenderButtons()
		{
			ImGuiMCP::SeparatorText("");
			if (ImGuiMCP::Button("Save"))
			{
				statusMessage = "Saving...";
				OnMainThread([]() { statusMessage = settings::Save() ? "Settings saved." : "Could not write the INI. See the log for why."; });
			}
			HelpMarker("Writes every setting on every section to the plugin's INI so it survives a restart.");
			ImGuiMCP::SameLine();
			if (ImGuiMCP::Button("Reload from INI"))
			{
				statusMessage = "Reloading...";
				OnMainThread([]() {
					statusMessage = settings::Reload() ? "Settings reloaded from the INI." : "Could not read the INI. See the log for why.";
					Locks::ApplySettings();
				});
			}
			HelpMarker("Throws away any change made here since the last save and re-reads the INI from disk.");
			ImGuiMCP::SameLine();
			if (ImGuiMCP::Button("Restore defaults"))
			{
				OnMainThread([]() { settings::RestoreDefaults(); Locks::ApplySettings(); logger::debug("Restored default settings"); });
				statusMessage = "Defaults restored (everything off). Press Save to keep them.";
			}
			HelpMarker("Puts every setting back to its fresh-install value - every feature off. Nothing is written until you press Save.");
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
		SKSEMenuFramework::SetSection("Apocrypha Lock Overhaul");
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
		using namespace settings;
		StandDownBanner();
		ImGuiMCP::TextWrapped("A lock needs a Lockpicking skill for its level before the picking menu opens; below it the menu closes again and no lockpick is lost. Key-required locks are never touched.");
		ImGuiMCP::Spacing();
		ImGuiMCP::PushItemWidth(260.0F);
		ImGuiMCP::SeparatorText("Lock requirements");
		ImGuiMCP::Toggle("Require a Lockpicking skill per lock level", &requirements::enabled);
		HelpMarker("On: the table below gates the picking menu. Off: any lock can be tried, as in vanilla.");
		TierTable("pick", requirements::pick, "Lockpicking");
		ImGuiMCP::SeparatorText("Auto pick");
		ImGuiMCP::Toggle("Open locks without the minigame", &requirements::autoPick);
		HelpMarker("With enough Lockpicking (the table above) the lock simply opens: one lockpick is used (none with the Unbreakable perk), Lockpicking rises as the game's own picking would raise it, and opening an owned lock is a crime unless you have Quick Hands.");
		ImGuiMCP::Toggle("Open the chest or door straight away", &requirements::openAfterPick);
		HelpMarker("After auto-picking, the object is activated so it opens at once instead of needing a second press.");
		ImGuiMCP::SeparatorText("What that means right now");
		CrosshairReadout();
		ImGuiMCP::PopItemWidth();
		RenderButtons();
	}

	void __stdcall SmashPanel::Render()
	{
		using namespace settings;
		StandDownBanner();
		ImGuiMCP::TextWrapped("Hit a locked chest or door with a weapon. With enough weapon skill for the lock's level it breaks open; the skill you used rises, and an owned lock reports you.");
		ImGuiMCP::Spacing();
		ImGuiMCP::PushItemWidth(300.0F);
		ImGuiMCP::Toggle("Smash locks with a weapon", &smash::enabled);
		HelpMarker("On: a weapon hit on a locked object is judged against the table below.");
		int mode = static_cast<int>(std::min<std::uint32_t>(smash::weapons, 2u));
		if (ImGuiMCP::Combo("Allowed weapons", &mode, kWeaponModes, 3)) { smash::weapons = static_cast<std::uint32_t>(mode); }
		HelpMarker("Which weapons count. Two-handed weapons always do; one-handed and everything else are up to this setting. Bows and crossbows use Archery, staves use Destruction, fists count as one-handed.");
		TierTable("smash", smash::need, "Weapon skill (One-handed or Two-handed)");
		ImGuiMCP::TextWrapped("A frozen lock (see Unlock Spell) needs %u less skill to smash.", spell::frostMalus);
		ImGuiMCP::PopItemWidth();
		RenderButtons();
	}

	void __stdcall SpellPanel::Render()
	{
		using namespace settings;
		StandDownBanner();
		const auto s = Locks::GetState();
		ImGuiMCP::TextWrapped("Manipulate Lock is an Alteration spell that works a lock's mechanism from a distance. Cast it at a lock: with enough Alteration for the lock's level it opens. Destruction can join in: frost freezes a lock (easier to smash), fire thaws it or opens it outright, shock opens it too if allowed.");
		ImGuiMCP::Spacing();
		ImGuiMCP::PushItemWidth(300.0F);
		ImGuiMCP::Toggle("Know the spell Manipulate Lock", &spell::enabled);
		HelpMarker("On: the spell is added to your spell book (Alteration, cost 30). Off: it is taken away again.");
		if (!s.spellResolved) { ImGuiMCP::TextWrapped("ApocryphaLockOverhaul.esl is not loaded - enable it in your mod manager or the spell cannot exist."); }
		else { ImGuiMCP::TextDisabled("%s", s.spellKnown ? "You know Manipulate Lock." : "You do not know Manipulate Lock right now."); }
		int mode = static_cast<int>(std::min<std::uint32_t>(spell::allowed, 2u));
		if (ImGuiMCP::Combo("Spells that work on locks", &mode, kSpellModes, 3)) { spell::allowed = static_cast<std::uint32_t>(mode); }
		HelpMarker("Manipulate Lock uses your Alteration; fire and shock use your Destruction against the same table.");
		TierTable("spell", spell::need, "Magic skill (Alteration for the spell, Destruction for fire and shock)");
		Percent("Frost makes a lock easier to smash by", spell::frostMalus, "A frozen lock needs this much less weapon skill to smash, 0 to 100.");
		ImGuiMCP::Text("Locks frozen right now: %u", s.frozenCount);
		ImGuiMCP::PopItemWidth();
		RenderButtons();
	}

	void __stdcall PickAnglePanel::Render()
	{
		using namespace settings;
		StandDownBanner();
		const auto s = Locks::GetState();
		ImGuiMCP::TextWrapped("When a lockpick breaks, the next pick starts at the angle where the last one broke instead of resetting to the middle - Remember Lockpick Angle's behaviour, built in. Optionally only once you have a perk.");
		ImGuiMCP::Spacing();
		ImGuiMCP::PushItemWidth(300.0F);
		bool enabled = pickangle::enabled;
		if (ImGuiMCP::Toggle("Remember the pick angle", &enabled)) { pickangle::enabled = enabled; Locks::ApplySettings(); }
		HelpMarker("On: a broken pick's angle is kept. Off: vanilla - every new pick starts at the middle.");
		int perk = static_cast<int>(std::min<std::uint32_t>(pickangle::requiredPerk, 7u));
		if (ImGuiMCP::Combo("Only with this perk", &perk, kPerkNames, 8)) { pickangle::requiredPerk = static_cast<std::uint32_t>(perk); Locks::ApplySettings(); }
		HelpMarker("The angle is kept only while your character has this perk. Custom: name the plugin and the perk's form ID in the INI (sPerkPlugin, uPerkFormID).");
		ImGuiMCP::Text("Perk gate: %s", s.requiredPerkName.c_str());
		if (s.pickAngleStandingDown) { ImGuiMCP::TextWrapped("RememberLockpickAngle.dll is loaded - this section stands down and that mod keeps the angle."); }
		else { ImGuiMCP::TextWrapped("Patch: %s", s.patchStatus.c_str()); }
		ImGuiMCP::PopItemWidth();
		RenderButtons();
	}

	void __stdcall GeneralPanel::Render()
	{
		using namespace settings;
		StandDownBanner();
		ImGuiMCP::PushItemWidth(260.0F);
		ImGuiMCP::SeparatorText("Skill gain");
		ImGuiMCP::Toggle("Opening a lock raises the skill that opened it", &general::skillGain);
		HelpMarker("The game's own per-level amounts (fSkillUsageLockPick...), applied to Lockpicking, the weapon skill or the magic school that opened the lock.");
		ImGuiMCP::SliderFloat("Skill gain multiplier", &general::skillGainMult, 0.1F, 5.0F, "%.2f x");
		HelpMarker("Scales that gain, 0.1 to 5.");
		ImGuiMCP::SeparatorText("Sound");
		ImGuiMCP::Toggle("Play a sound when a lock opens", &general::sound);
		HelpMarker("The game's own unlock sound for picks and spells, a smash for weapons.");
		ImGuiMCP::SliderFloat("Volume", &general::soundVolume, 0.0F, 1.0F, "%.2f");
		HelpMarker("0 to 1.");
		ImGuiMCP::SeparatorText("Crime");
		ImGuiMCP::Toggle("Opening a lock you do not own is a crime", &general::crime);
		HelpMarker("Witnessed by the game's own rules: followers and animals do not report you, a nearby townsperson does. Quick Hands exempts auto-picking only, as the perk does in vanilla.");
		float gold = static_cast<float>(general::crimeGold);
		if (ImGuiMCP::SliderFloat("Reported value", &gold, 0.0F, 500.0F, "%.0f gold")) { general::crimeGold = static_cast<std::uint32_t>(std::clamp(gold, 0.0F, 500.0F) + 0.5F); }
		HelpMarker("What the offence is reported as being worth.");
		ImGuiMCP::SeparatorText("Messages");
		ImGuiMCP::Toggle("Show a message when this mod acts", &general::notifications);
		HelpMarker("A short line on screen when a lock is refused, opened, frozen or thawed.");
		ImGuiMCP::SeparatorText("Everything off");
		if (ImGuiMCP::Button("Deactivate every feature"))
		{
			OnMainThread([]() { Locks::DeactivateAll(); });
			statusMessage = "Every feature switched off; the spell is removed. Press Save to keep that.";
		}
		HelpMarker("Switches off requirements, auto-pick, smashing, the spell and the pick angle at once - the state to be in before removing the mod.");
		ImGuiMCP::PopItemWidth();
		RenderButtons();
	}

	void __stdcall DebugPanel::Render()
	{
		using namespace settings;
		const auto s = Locks::GetState();
		ImGuiMCP::PushItemWidth(260.0F);
		int level = std::clamp(static_cast<int>(debug::logLevel), 0, kLogLevelCount - 1);
		if (ImGuiMCP::Combo("Log level", &level, kLogLevelNames, kLogLevelCount)) { debug::logLevel = static_cast<std::uint32_t>(level); ApplyLogLevel(); }
		HelpMarker("Applies immediately. The log is at Documents\\My Games\\Skyrim Special Edition\\SKSE\\ApocryphaLockOverhaul.log.");
		ImGuiMCP::SeparatorText("Live");
		ImGuiMCP::Text("Locks opened by this mod this session: %llu", static_cast<unsigned long long>(s.opened));
		ImGuiMCP::Text("Frozen locks: %u", s.frozenCount);
		ImGuiMCP::TextWrapped("Last event: %s", s.lastEvent.empty() ? "nothing yet" : s.lastEvent.c_str());
		ImGuiMCP::TextWrapped("Spell: %s", s.spellResolved ? (s.spellKnown ? "resolved, known" : "resolved, not known") : "NOT resolved (ESL missing)");
		ImGuiMCP::TextWrapped("Pick-angle patch: %s", s.patchStatus.c_str());
		ImGuiMCP::TextWrapped("Standing down: %s", s.standingDown ? "yes (Lock Overhaul.esp)" : "no");
		ImGuiMCP::SeparatorText("The lock you are looking at");
		CrosshairReadout();
		ImGuiMCP::PopItemWidth();
		RenderButtons();
	}
}
