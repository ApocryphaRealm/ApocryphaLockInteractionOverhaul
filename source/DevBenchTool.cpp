#include "PCH.h"

#include "DevBenchTool.h"

#include "DevBench/DevBenchAPI.h"
#include "Locks.h"
#include "Settings.h"
#include "utils/Logger.h"

#include <cstdlib>
#include <format>
#include <string>
#include <string_view>

namespace DevBenchTool
{
	namespace
	{
		RE::FormID g_lastSpawned = 0;   // the last container the spawn op placed (test rig)

		std::string EscapeJson(std::string_view a_in)
		{
			std::string out;
			out.reserve(a_in.size() + 8);
			for (const char c : a_in)
			{
				switch (c)
				{
				case '\\': out += "\\\\"; break;
				case '"': out += "\\\""; break;
				case '\n': out += "\\n"; break;
				default: out += c; break;
				}
			}
			return out;
		}

		// "key":"value" -> value (empty when absent).
		std::string JsonString(std::string_view a_args, const char* a_key)
		{
			const std::string needle = std::format("\"{}\"", a_key);
			auto pos = a_args.find(needle);
			if (pos == std::string_view::npos) { return {}; }
			pos = a_args.find(':', pos + needle.size());
			if (pos == std::string_view::npos) { return {}; }
			pos = a_args.find('"', pos);
			if (pos == std::string_view::npos) { return {}; }
			const auto end = a_args.find('"', pos + 1);
			if (end == std::string_view::npos) { return {}; }
			return std::string(a_args.substr(pos + 1, end - pos - 1));
		}

		std::string LockJson(const Locks::LockInfo& a_info)
		{
			if (!a_info.valid) { return R"({"valid":false})"; }
			const auto pick = Locks::CanPick(a_info);
			const auto smash1 = Locks::CanSmash(a_info, RE::ActorValue::kOneHanded);
			const auto smash2 = Locks::CanSmash(a_info, RE::ActorValue::kTwoHanded);
			const auto alt = Locks::CanUnlockBySpell(a_info, RE::ActorValue::kAlteration);
			const auto des = Locks::CanUnlockBySpell(a_info, RE::ActorValue::kDestruction);
			return std::format(
				R"({{"valid":true,"ref":"0x{:08X}","name":"{}","locked":{},"requiresKey":{},"tier":"{}","frozen":{},"crime":{},)"
				R"("pick":{{"allowed":{},"have":{},"needed":{}}},"smashOneHanded":{{"allowed":{},"have":{},"needed":{}}},"smashTwoHanded":{{"allowed":{},"have":{},"needed":{}}},)"
				R"("alteration":{{"allowed":{},"have":{},"needed":{}}},"destruction":{{"allowed":{},"have":{},"needed":{}}}}})",
				a_info.refID, EscapeJson(a_info.name), a_info.locked, a_info.requiresKey, Locks::TierName(a_info.tier), a_info.frozen, a_info.crime,
				pick.allowed, pick.have, pick.needed, smash1.allowed, smash1.have, smash1.needed, smash2.allowed, smash2.have, smash2.needed,
				alt.allowed, alt.have, alt.needed, des.allowed, des.have, des.needed);
		}

		bool Flag(std::string_view a_args, const char* a_op, bool& a_target)
		{
			// "requirements:1" / "requirements:0" anywhere in the args
			const std::string on = std::format("\"{}:1\"", a_op), off = std::format("\"{}:0\"", a_op);
			if (a_args.find(on) != std::string_view::npos) { a_target = true; return true; }
			if (a_args.find(off) != std::string_view::npos) { a_target = false; return true; }
			return false;
		}

		void ControlTool(void*, const char* a_argsJson, void* a_sink, DevBenchAPI::WriteFn a_write)
		{
			const std::string_view args = a_argsJson ? a_argsJson : "";
			auto has = [&](const char* a_op) { return args.find(std::format("\"{}\"", a_op)) != std::string_view::npos; };
			auto reply = [&](const std::string& a_json) { a_write(a_sink, a_json.c_str()); };

			bool flagged = false;
			flagged |= Flag(args, "requirements", settings::requirements::enabled);
			flagged |= Flag(args, "autopick", settings::requirements::autoPick);
			flagged |= Flag(args, "openafter", settings::requirements::openAfterPick);
			flagged |= Flag(args, "smash", settings::smash::enabled);
			flagged |= Flag(args, "spell", settings::spell::enabled);
			flagged |= Flag(args, "pickangle", settings::pickangle::enabled);
			flagged |= Flag(args, "crime", settings::general::crime);
			flagged |= Flag(args, "skillgain", settings::general::skillGain);
			flagged |= Flag(args, "notify", settings::general::notifications);
			if (const auto w = JsonString(args, "weapons"); !w.empty()) { settings::smash::weapons = std::min<std::uint32_t>(static_cast<std::uint32_t>(std::strtoul(w.c_str(), nullptr, 10)), 2u); flagged = true; }
			if (const auto sp = JsonString(args, "spells"); !sp.empty()) { settings::spell::allowed = std::min<std::uint32_t>(static_cast<std::uint32_t>(std::strtoul(sp.c_str(), nullptr, 10)), 2u); flagged = true; }
			if (const auto p = JsonString(args, "perk"); !p.empty()) { settings::pickangle::requiredPerk = std::min<std::uint32_t>(static_cast<std::uint32_t>(std::strtoul(p.c_str(), nullptr, 10)), 7u); flagged = true; }
			if (flagged) { Locks::ApplySettings(); }

			if (has("save")) { const bool ok = settings::Save(); reply(std::format(R"({{"ok":{},"op":"save"}})", ok)); return; }
			if (has("reload")) { const bool ok = settings::Reload(); Locks::ApplySettings(); reply(std::format(R"({{"ok":{},"op":"reload"}})", ok)); return; }
			if (has("deactivate")) { if (auto* t = SKSE::GetTaskInterface()) { t->AddTask([]() { Locks::DeactivateAll(); }); } reply(R"({"ok":true,"op":"deactivate"})"); return; }
			if (has("look")) { reply(std::format(R"({{"ok":true,"op":"look","lock":{}}})", LockJson(Locks::LookingAt()))); return; }
			if (has("describe"))
			{
				// The lock state of a named reference (hex form id), read directly - the test rig's way to
				// confirm a console `lock` took before driving anything at it.
				const auto refText = JsonString(args, "ref");
				const RE::FormID refID = refText.empty() ? 0 : static_cast<RE::FormID>(std::strtoul(refText.c_str(), nullptr, 16));
				auto* ref = refID ? RE::TESForm::LookupByID<RE::TESObjectREFR>(refID) : Locks::CrosshairRef();
				reply(std::format(R"({{"ok":true,"op":"describe","lock":{}}})", LockJson(Locks::Describe(ref))));
				return;
			}

			if (has("spawn"))
			{
				// Test rig: place a container (base form id, hex) at the player and answer with the new
				// reference's id, so a proof can `prid` it and `lock` it by console. Main-thread queued;
				// the id is read back from the next state call (spawned field).
				const auto baseText = JsonString(args, "spawn");
				const RE::FormID baseID = static_cast<RE::FormID>(std::strtoul(baseText.c_str(), nullptr, 16));
				auto* base = baseID ? RE::TESForm::LookupByID<RE::TESBoundObject>(baseID) : nullptr;
				if (!base) { reply(std::format(R"({{"ok":false,"op":"spawn","error":"no bound object 0x{:08X}"}})", baseID)); return; }
				if (auto* t = SKSE::GetTaskInterface())
				{
					t->AddTask([base]() {
						auto* player = RE::PlayerCharacter::GetSingleton();
						if (!player) { return; }
						auto ref = player->PlaceObjectAtMe(base, false);
						g_lastSpawned = ref ? ref->GetFormID() : 0;
						logger::info("spawn: {} placed at the player as 0x{:08X}", base->GetName(), g_lastSpawned);
					});
				}
				reply(std::format(R"({{"ok":true,"op":"spawn","base":"0x{:08X}"}})", baseID));
				return;
			}
			if (has("simulate"))
			{
				// Runs the same decision path the game events run, on the named reference (or the
				// crosshair's), main-thread queued. how: pick | smash1 | smash2 | spell | fire | shock | frost | thaw
				const auto refText = JsonString(args, "ref");
				const auto how = JsonString(args, "how");
				const RE::FormID refID = refText.empty() ? 0 : static_cast<RE::FormID>(std::strtoul(refText.c_str(), nullptr, 16));
				if (how.empty()) { reply(R"({"ok":false,"op":"simulate","error":"how is required: pick|smash1|smash2|spell|fire|shock|frost|thaw"})"); return; }
				if (auto* t = SKSE::GetTaskInterface())
				{
					t->AddTask([refID, how]() {
						auto* ref = refID ? RE::TESForm::LookupByID<RE::TESObjectREFR>(refID) : Locks::CrosshairRef();
						if (!ref) { logger::warn("simulate {}: no reference (0x{:08X})", how, refID); return; }
						if (how == "pick") { Locks::AutoPick(ref); }
						else if (how == "smash1") { Locks::Smash(ref, RE::ActorValue::kOneHanded, false); }
						else if (how == "smash2") { Locks::Smash(ref, RE::ActorValue::kTwoHanded, false); }
						else if (how == "spell") { Locks::SpellUnlock(ref, RE::ActorValue::kAlteration); }
						else if (how == "fire" || how == "shock") { Locks::SpellUnlock(ref, RE::ActorValue::kDestruction); }
						else if (how == "frost") { Locks::Freeze(ref); }
						else if (how == "thaw") { Locks::Thaw(ref); }
						else { logger::warn("simulate: unknown how \"{}\"", how); }
					});
				}
				reply(std::format(R"({{"ok":true,"op":"simulate","how":"{}","ref":"0x{:08X}"}})", EscapeJson(how), refID));
				return;
			}

			const auto s = Locks::GetState();
			using namespace settings;
			const std::string json = std::format(
				R"({{"ok":true,"settings":{{"requirements":{},"autoPick":{},"openAfterPick":{},"pick":[{},{},{},{},{}],"smash":{},"weapons":{},"smashNeed":[{},{},{},{},{}],)"
				R"("spell":{},"spells":{},"spellNeed":[{},{},{},{},{}],"frostMalus":{},"pickAngle":{},"requiredPerk":{},"skillGain":{},"skillGainMult":{:.2f},"sound":{},"soundVolume":{:.2f},"crime":{},"crimeGold":{},"notifications":{},"logLevel":{}}},)"
				R"("runtime":{{"standingDown":{},"pickAngleStandingDown":{},"spellResolved":{},"spellFormId":"0x{:08X}","spellKnown":{},"patchAttached":{},"patchStatus":"{}","requiredPerkName":"{}","frozenCount":{},"opened":{},"lastEvent":"{}",)"
				R"("lockpicking":{:.1f},"oneHanded":{:.1f},"twoHanded":{:.1f},"alteration":{:.1f},"destruction":{:.1f},"spawned":"0x{:08X}"}},"look":{}}})",
				requirements::enabled, requirements::autoPick, requirements::openAfterPick, requirements::pick[0], requirements::pick[1], requirements::pick[2], requirements::pick[3], requirements::pick[4],
				smash::enabled, smash::weapons, smash::need[0], smash::need[1], smash::need[2], smash::need[3], smash::need[4],
				spell::enabled, spell::allowed, spell::need[0], spell::need[1], spell::need[2], spell::need[3], spell::need[4], spell::frostMalus,
				pickangle::enabled, pickangle::requiredPerk, general::skillGain, general::skillGainMult, general::sound, general::soundVolume, general::crime, general::crimeGold, general::notifications, debug::logLevel,
				s.standingDown, s.pickAngleStandingDown, s.spellResolved, s.spellFormID, s.spellKnown, s.patchAttached, EscapeJson(s.patchStatus), EscapeJson(s.requiredPerkName), s.frozenCount, s.opened, EscapeJson(s.lastEvent),
				[]() { auto* p = RE::PlayerCharacter::GetSingleton(); return p ? p->AsActorValueOwner()->GetActorValue(RE::ActorValue::kLockpicking) : -1.0F; }(),
				[]() { auto* p = RE::PlayerCharacter::GetSingleton(); return p ? p->AsActorValueOwner()->GetActorValue(RE::ActorValue::kOneHanded) : -1.0F; }(),
				[]() { auto* p = RE::PlayerCharacter::GetSingleton(); return p ? p->AsActorValueOwner()->GetActorValue(RE::ActorValue::kTwoHanded) : -1.0F; }(),
				[]() { auto* p = RE::PlayerCharacter::GetSingleton(); return p ? p->AsActorValueOwner()->GetActorValue(RE::ActorValue::kAlteration) : -1.0F; }(),
				[]() { auto* p = RE::PlayerCharacter::GetSingleton(); return p ? p->AsActorValueOwner()->GetActorValue(RE::ActorValue::kDestruction) : -1.0F; }(),
				g_lastSpawned, LockJson(Locks::LookingAt()));
			reply(json);
		}
	}

	void Init(bool a_lastAttempt)
	{
		static bool registered = false;
		if (registered) { return; }
		DevBenchAPI::IDevBenchInterface001* devBench = DevBenchAPI::GetDevBenchInterface001();
		if (!devBench)
		{
			if (a_lastAttempt) { logger::info("DevBench not detected; skipping the \"alio.control\" tool"); }
			else { logger::debug("DevBench not detected yet; will retry at the next message"); }
			return;
		}
		constexpr const char* descriptor =
			"{"
			"\"description\":\"ApocryphaRealm Lock Interaction Overhaul live state and controls. No op: settings + runtime + the lock under the crosshair. "
			"Switches: requirements:<0|1>, autopick:<0|1>, openafter:<0|1>, smash:<0|1>, spell:<0|1>, pickangle:<0|1>, crime:<0|1>, skillgain:<0|1>, notify:<0|1>; "
			"weapons:<0-2>, spells:<0-2>, perk:<0-7> as string values. op=look: the crosshair lock. op=simulate with ref (hex form id, or the crosshair) and how "
			"(pick|smash1|smash2|spell|fire|shock|frost|thaw) runs the same decision path the game events run. op=save, op=reload, op=deactivate.\","
			"\"inputSchema\":{\"type\":\"object\",\"properties\":{\"op\":{\"type\":\"string\"},\"ref\":{\"type\":\"string\"},\"how\":{\"type\":\"string\"}}},"
			"\"readOnly\":false"
			"}";
		if (devBench->RegisterTool("alio.control", descriptor, &ControlTool, nullptr))
		{
			logger::info("Registered \"alio.control\" with DevBench (build {})", devBench->GetBuildNumber());
			registered = true;
		}
	}
}
