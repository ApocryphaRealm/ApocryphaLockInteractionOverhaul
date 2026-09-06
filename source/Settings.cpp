#include "PCH.h"

#include "Settings.h"

#include "utils/INISettingCollection.h"
#include "utils/Logger.h"
#include "utils/Setting.h"

#include <algorithm>
#include <cctype>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <map>
#include <string>
#include <vector>

namespace settings
{
	namespace
	{
		std::string iniPath;

		// Every key, table-driven: section, key, and where it lives. Defaults are captured from the
		// compiled values at Init, so RestoreDefaults is always "what a fresh install has".
		enum class Kind { kBool, kUInt, kFloat, kString };
		struct Entry
		{
			const char* section;
			const char* key;
			Kind kind;
			void* target;
			bool defBool = false;
			std::uint32_t defUInt = 0;
			float defFloat = 0.0F;
			std::string defString;
		};
		std::vector<Entry> g_entries;

		void Add(const char* a_section, const char* a_key, bool& a_v) { Entry e{ a_section, a_key, Kind::kBool, &a_v }; e.defBool = a_v; g_entries.push_back(e); }
		void Add(const char* a_section, const char* a_key, std::uint32_t& a_v) { Entry e{ a_section, a_key, Kind::kUInt, &a_v }; e.defUInt = a_v; g_entries.push_back(e); }
		void Add(const char* a_section, const char* a_key, float& a_v) { Entry e{ a_section, a_key, Kind::kFloat, &a_v }; e.defFloat = a_v; g_entries.push_back(e); }
		void Add(const char* a_section, const char* a_key, std::string& a_v) { Entry e{ a_section, a_key, Kind::kString, &a_v }; e.defString = a_v; g_entries.push_back(e); }

		std::string Lower(std::string a_s)
		{
			for (char& c : a_s) { c = static_cast<char>(std::tolower(static_cast<unsigned char>(c))); }
			return a_s;
		}

		std::string Trim(const std::string& a_s)
		{
			const auto b = a_s.find_first_not_of(" \t\r\n");
			if (b == std::string::npos) { return {}; }
			const auto e = a_s.find_last_not_of(" \t\r\n");
			return a_s.substr(b, e - b + 1);
		}

		bool ParseBool(const std::string& a_text, bool& a_out)
		{
			const std::string v = Lower(Trim(a_text));
			if (v == "1" || v == "true" || v == "yes") { a_out = true; return true; }
			if (v == "0" || v == "false" || v == "no") { a_out = false; return true; }
			return false;
		}

		bool ParseUInt(const std::string& a_text, std::uint32_t& a_out)
		{
			try { a_out = static_cast<std::uint32_t>(std::stoull(Trim(a_text), nullptr, 0)); return true; } catch (...) { return false; }
		}

		bool ParseFloat(const std::string& a_text, float& a_out)
		{
			try { a_out = std::stof(Trim(a_text)); return true; } catch (...) { return false; }
		}

		std::map<std::string, std::string> ReadKeys()
		{
			std::map<std::string, std::string> keys;
			std::ifstream in(iniPath);
			if (!in) { return keys; }
			std::string line, section;
			while (std::getline(in, line))
			{
				const std::string t = Trim(line);
				if (t.empty() || t[0] == ';' || t[0] == '#') { continue; }
				if (t.front() == '[' && t.back() == ']') { section = Lower(t.substr(1, t.size() - 2)); continue; }
				const auto eq = t.find('=');
				if (eq == std::string::npos) { continue; }
				keys[Lower(Trim(t.substr(0, eq))) + ":" + section] = Trim(t.substr(eq + 1));
			}
			return keys;
		}

		std::string ValueText(const Entry& a_e)
		{
			switch (a_e.kind)
			{
			case Kind::kBool: return *static_cast<bool*>(a_e.target) ? "1" : "0";
			case Kind::kUInt: return std::to_string(*static_cast<std::uint32_t*>(a_e.target));
			case Kind::kFloat: { char buf[32]; std::snprintf(buf, sizeof(buf), "%.3f", *static_cast<float*>(a_e.target)); return buf; }
			case Kind::kString: return *static_cast<std::string*>(a_e.target);
			}
			return {};
		}

		void Clamp()
		{
			for (int i = 0; i < kTierCount; ++i)
			{
				requirements::pick[i] = std::min<std::uint32_t>(requirements::pick[i], 100u);
				smash::need[i] = std::min<std::uint32_t>(smash::need[i], 100u);
				spell::need[i] = std::min<std::uint32_t>(spell::need[i], 100u);
			}
			spell::frostMalus = std::min<std::uint32_t>(spell::frostMalus, 100u);
			smash::weapons = std::min<std::uint32_t>(smash::weapons, 2u);
			spell::allowed = std::min<std::uint32_t>(spell::allowed, 2u);
			pickangle::requiredPerk = std::min<std::uint32_t>(pickangle::requiredPerk, 7u);
			general::skillGainMult = std::clamp(general::skillGainMult, 0.1F, 5.0F);
			general::soundVolume = std::clamp(general::soundVolume, 0.0F, 1.0F);
			general::crimeGold = std::min<std::uint32_t>(general::crimeGold, 10000u);
		}

		bool LoadFileValues()
		{
			if (!std::filesystem::exists(iniPath))
			{
				logger::warn("INI not found at {}; keeping compiled defaults", iniPath);
				return false;
			}
			const auto k = ReadKeys();
			int applied = 0;
			for (const Entry& e : g_entries)
			{
				const auto it = k.find(Lower(e.key) + ":" + Lower(e.section));
				if (it == k.end()) { logger::debug("INI key {}:{} missing; keeping current value", e.key, e.section); continue; }
				bool ok = false;
				switch (e.kind)
				{
				case Kind::kBool: ok = ParseBool(it->second, *static_cast<bool*>(e.target)); break;
				case Kind::kUInt: ok = ParseUInt(it->second, *static_cast<std::uint32_t*>(e.target)); break;
				case Kind::kFloat: ok = ParseFloat(it->second, *static_cast<float*>(e.target)); break;
				case Kind::kString: *static_cast<std::string*>(e.target) = it->second; ok = true; break;
				}
				if (!ok) { logger::warn("INI value \"{}\" for {}:{} is not valid; keeping current value", it->second, e.key, e.section); }
				else { ++applied; }
			}
			Clamp();  // a hand-edited INI cannot put a value out of the page's range
			logger::info("settings loaded from {}: {} key(s) applied; requirements={} autoPick={} smash={} spell={} pickAngle={} crime={} logLevel={}",
						 iniPath, applied, requirements::enabled, requirements::autoPick, smash::enabled, spell::enabled, pickangle::enabled, general::crime, debug::logLevel);
			return true;
		}

		bool WriteKey(std::vector<std::string>& a_lines, const char* a_section, const char* a_key, const std::string& a_value)
		{
			const std::string wantSection = Lower(a_section);
			const std::string wantKey = Lower(a_key);
			std::string section;
			for (auto& line : a_lines)
			{
				const std::string t = Trim(line);
				if (!t.empty() && t.front() == '[' && t.back() == ']') { section = Lower(t.substr(1, t.size() - 2)); continue; }
				const auto eq = t.find('=');
				if (eq == std::string::npos || section != wantSection) { continue; }
				if (Lower(Trim(t.substr(0, eq))) == wantKey)
				{
					line = std::string(a_key) + "=" + a_value;
					return true;
				}
			}
			logger::warn("Save: key {} not found in [{}]", a_key, a_section);
			return false;
		}
	}

	void Init(const std::string& a_iniFileName)
	{
		iniPath = (std::filesystem::current_path() / "Data" / "SKSE" / "Plugins" / a_iniFileName).string();

		g_entries.clear();
		Add("Debug", "uLogLevel", debug::logLevel);
		Add("Requirements", "bLockRequirements", requirements::enabled);
		Add("Requirements", "bAutoPick", requirements::autoPick);
		Add("Requirements", "bOpenAfterPick", requirements::openAfterPick);
		Add("Smash", "bSmashLocks", smash::enabled);
		Add("Smash", "uAllowedWeapons", smash::weapons);
		Add("Spell", "bUnlockSpell", spell::enabled);
		Add("Spell", "uAllowedSpells", spell::allowed);
		Add("Spell", "uFrostMalus", spell::frostMalus);
		Add("PickAngle", "bRememberPickAngle", pickangle::enabled);
		Add("PickAngle", "uRequiredPerk", pickangle::requiredPerk);
		Add("PickAngle", "sPerkPlugin", pickangle::perkPlugin);
		Add("PickAngle", "uPerkFormID", pickangle::perkFormID);
		Add("General", "bSkillGain", general::skillGain);
		Add("General", "fSkillGainMult", general::skillGainMult);
		Add("General", "bSound", general::sound);
		Add("General", "fSoundVolume", general::soundVolume);
		Add("General", "bCrime", general::crime);
		Add("General", "uCrimeGold", general::crimeGold);
		Add("General", "bNotifications", general::notifications);
		static const char* const kTierKeys[kTierCount] = { "uNovice", "uApprentice", "uAdept", "uExpert", "uMaster" };
		for (int i = 0; i < kTierCount; ++i)
		{
			Add("Requirements", kTierKeys[i], requirements::pick[i]);
			Add("Smash", kTierKeys[i], smash::need[i]);
			Add("Spell", kTierKeys[i], spell::need[i]);
		}

		// The engine-style setting collection mirrors the same keys (the project's
		// INISettingCollection pattern), so tooling that reads settings by "key:Section" sees them.
		auto* collection = utils::INISettingCollection::GetSingleton();
		for (const Entry& e : g_entries)
		{
			const std::string name = std::string(e.key) + ":" + e.section;
			switch (e.kind)
			{
			case Kind::kBool: collection->AddSettings(utils::MakeSetting(name.c_str(), *static_cast<bool*>(e.target))); break;
			case Kind::kUInt: collection->AddSettings(utils::MakeSetting(name.c_str(), static_cast<unsigned int>(*static_cast<std::uint32_t*>(e.target)))); break;
			case Kind::kFloat: collection->AddSettings(utils::MakeSetting(name.c_str(), *static_cast<float*>(e.target))); break;
			case Kind::kString: break;
			}
		}

		LoadFileValues();
	}

	bool Reload()
	{
		const bool ok = LoadFileValues();
		ApplyLogLevel();
		return ok;
	}

	bool Save()
	{
		std::vector<std::string> lines;
		{
			std::ifstream in(iniPath);
			if (!in) { logger::error("Save: could not open {} for reading", iniPath); return false; }
			std::string line;
			while (std::getline(in, line)) { lines.push_back(line); }
		}
		Clamp();
		bool ok = true;
		for (const Entry& e : g_entries) { ok &= WriteKey(lines, e.section, e.key, ValueText(e)); }
		std::ofstream out(iniPath, std::ios::trunc);
		if (!out) { logger::error("Save: could not open {} for writing", iniPath); return false; }
		for (const auto& line : lines) { out << line << '\n'; }
		logger::info("settings saved to {}", iniPath);
		return ok;
	}

	void RestoreDefaults()
	{
		for (const Entry& e : g_entries)
		{
			switch (e.kind)
			{
			case Kind::kBool: *static_cast<bool*>(e.target) = e.defBool; break;
			case Kind::kUInt: *static_cast<std::uint32_t*>(e.target) = e.defUInt; break;
			case Kind::kFloat: *static_cast<float*>(e.target) = e.defFloat; break;
			case Kind::kString: *static_cast<std::string*>(e.target) = e.defString; break;
			}
		}
		ApplyLogLevel();
	}

	void ApplyLogLevel()
	{
		const auto lvl = static_cast<spdlog::level::level_enum>(std::clamp<std::uint32_t>(debug::logLevel, 0u, 6u));
		SKSE::log::set_level(lvl, lvl);
	}

	const std::string& GetIniPath() { return iniPath; }
}
