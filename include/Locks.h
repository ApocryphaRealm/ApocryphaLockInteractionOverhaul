#pragma once

// ApocryphaRealm Lock Interaction Overhaul - the core. Everything the mod does to a lock goes through here:
//
//   * the LockpickingMenu opening (requirements + auto-pick),
//   * a weapon or a spell hitting a locked object (smash + unlock spell + frost/fire),
//   * the pick-angle patch (Remember Lockpick Angle's mechanism, MIT, credited),
//   * the ESL's spell (added to and removed from the player as the feature is switched),
//   * the frozen-lock set (session only, nothing persists),
//
// and one decision function per feature that the events, the settings page's readout and the
// DevBench tool all share, so what is driven in a test is exactly what runs in play.

#include <cstdint>
#include <string>

namespace Locks
{
	// Call at kDataLoaded: resolves forms, registers the sinks, installs the pick-angle patch,
	// syncs the spell to the setting. Safe to call again.
	void Install();

	// The spell and the pick-angle patch follow their settings; call after any change to them.
	void ApplySettings();

	// Everything off, in memory (the page's Deactivate button).
	void DeactivateAll();

	enum class Tier : int { kNovice = 0, kApprentice, kAdept, kExpert, kMaster, kNone = -1 };
	const char* TierName(Tier a_tier);

	// What one lock looks like to this mod.
	struct LockInfo
	{
		bool valid = false;
		bool locked = false;
		bool requiresKey = false;
		bool frozen = false;
		bool crime = false;           // opening it against its owner is a crime
		Tier tier = Tier::kNone;
		std::uint32_t refID = 0;
		std::string name;             // the base object's display name, for messages
	};
	LockInfo Describe(RE::TESObjectREFR* a_ref);

	// Verdicts - the same functions the events run. a_skill is the player's current skill in
	// the relevant school; the requirement comes from the settings by tier.
	struct Verdict
	{
		bool allowed = false;
		std::uint32_t needed = 0;
		std::uint32_t have = 0;
		std::string why;
	};
	Verdict CanPick(const LockInfo& a_lock);                      // Lockpicking vs the requirement table
	Verdict CanSmash(const LockInfo& a_lock, RE::ActorValue a_skill);  // weapon skill vs the smash table (frost malus applied)
	Verdict CanUnlockBySpell(const LockInfo& a_lock, RE::ActorValue a_school);  // magic skill vs the spell table

	// Actions, main thread only. Each logs, notifies, grants skill, raises the alarm as the
	// settings say. Return true when the lock opened.
	bool AutoPick(RE::TESObjectREFR* a_ref);
	bool Smash(RE::TESObjectREFR* a_ref, RE::ActorValue a_skill, bool a_fromEvent);
	bool SpellUnlock(RE::TESObjectREFR* a_ref, RE::ActorValue a_school);
	void Freeze(RE::TESObjectREFR* a_ref);
	void Thaw(RE::TESObjectREFR* a_ref);

	// Pick-angle patch: true = keep the angle when a pick breaks (called from the stub).
	bool KeepPickAngle();

	struct State
	{
		bool standingDown = false;       // Lock Overhaul.esp is loaded
		bool pickAngleStandingDown = false;  // RememberLockpickAngle.dll is loaded
		bool spellResolved = false;
		std::uint32_t spellFormID = 0;
		bool spellKnown = false;         // the player has the spell right now
		std::string patchStatus;         // the pick-angle patch's verified/attached/refused line
		bool patchAttached = false;
		std::string requiredPerkName;    // what the pick-angle gate resolved to
		std::uint32_t frozenCount = 0;
		std::uint64_t opened = 0;        // locks opened by this mod this session
		std::string lastEvent;
	};
	State GetState();

	// The lock under the crosshair (for the page readout and the DevBench tool).
	LockInfo LookingAt();
	RE::TESObjectREFR* CrosshairRef();
}
