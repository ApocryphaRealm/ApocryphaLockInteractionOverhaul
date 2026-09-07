#pragma once

// ApocryphaRealm Lock Interaction Overhaul - settings. Plain-file INI (redirector-proof, the project standard);
// every value lives here in memory and the page edits it live. Everything is OFF by default.

#include <cstdint>
#include <string>

namespace settings
{
	// The five lock tiers, in LOCK_LEVEL order: VeryEasy, Easy, Average, Hard, VeryHard.
	constexpr int kTierCount = 5;
	constexpr const char* kTierNames[kTierCount] = { "Novice", "Apprentice", "Adept", "Expert", "Master" };

	namespace debug
	{
		inline std::uint32_t logLevel = 0;  // uLogLevel:Debug
	}

	namespace requirements
	{
		inline bool enabled = false;                                     // bLockRequirements:Requirements
		inline std::uint32_t pick[kTierCount] = { 0, 25, 50, 75, 100 };  // uNovice..uMaster:Requirements - Lockpicking needed per tier
		inline bool autoPick = false;                                    // bAutoPick:Requirements - open without the minigame when the skill suffices
		inline bool openAfterPick = true;                                // bOpenAfterPick:Requirements - activate the object once auto-picked
	}

	namespace smash
	{
		inline bool enabled = false;                                     // bSmashLocks:Smash
		inline std::uint32_t weapons = 1;                                // uAllowedWeapons:Smash - 0 two-handed only, 1 one- and two-handed, 2 any weapon
		inline std::uint32_t need[kTierCount] = { 0, 25, 50, 75, 100 };  // uNovice..uMaster:Smash - weapon skill needed per tier
	}

	namespace spell
	{
		inline bool enabled = false;                                     // bUnlockSpell:Spell
		inline std::uint32_t allowed = 0;                                // uAllowedSpells:Spell - 0 the unlock spell only, 1 plus Destruction without shock, 2 all
		inline std::uint32_t need[kTierCount] = { 0, 25, 50, 75, 100 };  // uNovice..uMaster:Spell - magic skill needed per tier
		inline std::uint32_t frostMalus = 50;                            // uFrostMalus:Spell - a frozen lock needs this much less skill to smash
	}

	namespace pickangle
	{
		inline bool enabled = false;            // bRememberPickAngle:PickAngle
		inline std::uint32_t requiredPerk = 0;  // uRequiredPerk:PickAngle - 0 none, 1 Locksmith, 2 Unbreakable, 3 Quick Hands, 4 Wax Key, 5 Golden Touch, 6 Treasure Hunter, 7 custom (below)
		inline std::string perkPlugin;          // sPerkPlugin:PickAngle - custom perk's plugin file name
		inline std::uint32_t perkFormID = 0;    // uPerkFormID:PickAngle - custom perk's local form ID
	}

	namespace general
	{
		inline bool skillGain = true;        // bSkillGain:General
		inline float skillGainMult = 1.0F;   // fSkillGainMult:General - 0.1 .. 5
		inline bool sound = true;            // bSound:General
		inline float soundVolume = 1.0F;     // fSoundVolume:General - 0 .. 1
		inline bool crime = true;            // bCrime:General
		inline std::uint32_t crimeGold = 5;  // uCrimeGold:General - the value reported when a lock is opened against its owner
		inline bool notifications = true;    // bNotifications:General
	}

	void Init(const std::string& a_iniFileName);
	bool Reload();
	bool Save();
	void RestoreDefaults();
	void ApplyLogLevel();
	const std::string& GetIniPath();
}
