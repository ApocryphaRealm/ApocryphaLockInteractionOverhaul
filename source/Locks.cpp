#include "PCH.h"

#include "Locks.h"

#include "Settings.h"
#include "Signature.h"
#include "utils/Logger.h"

#include <xbyak/xbyak.h>

#include <atomic>
#include <chrono>
#include <format>
#include <mutex>
#include <unordered_set>

namespace Locks
{
	namespace
	{
		// The contract with LockInteractionOverhaul.esp (tools/Build-ApocryphaLockInteractionOverhaulEsl.py).
		constexpr const char* kPluginFileName = "LockInteractionOverhaul.esp";
		constexpr RE::FormID kEffectLocalFormID = 0x800;
		constexpr RE::FormID kSpellLocalFormID = 0x801;

		// Skyrim.esm forms, read out of the live master by editor ID on 2026-09-06.
		constexpr RE::FormID kLockpick = 0x0000000A;
		constexpr RE::FormID kPerkLocksmith = 0x00058208;
		constexpr RE::FormID kPerkUnbreakable = 0x00058209;
		constexpr RE::FormID kPerkGoldenTouch = 0x0005820A;
		constexpr RE::FormID kPerkTreasureHunter = 0x00105F26;
		constexpr RE::FormID kPerkQuickHands = 0x00106259;
		constexpr RE::FormID kPerkWaxKey = 0x00107830;
		constexpr RE::FormID kSoundUnlock = 0x000C1917;   // UILockpickingUnlock
		constexpr RE::FormID kSoundSmash = 0x0010FE9A;    // QSTTG01UrnSmashSD
		constexpr RE::FormID kKeywordFrost = 0x0001CEAE;  // MagicDamageFrost
		constexpr RE::FormID kKeywordFire = 0x0001CEAD;   // MagicDamageFire
		constexpr RE::FormID kKeywordShock = 0x0001CEAF;  // MagicDamageShock

		// The game's own "what one pick of this lock level is worth" amounts, so skill gain here
		// matches vanilla picking exactly (and follows any mod that changes these settings).
		constexpr const char* kSkillUsage[settings::kTierCount] = {
			"fSkillUsageLockPickVeryEasy", "fSkillUsageLockPickEasy", "fSkillUsageLockPickAverage",
			"fSkillUsageLockPickHard", "fSkillUsageLockPickVeryHard"
		};

		// Remember Lockpick Angle's mechanism (Sayuri / Umgak, MIT): when a pick breaks the game
		// zeroes LockpickingMenu's pickAngle with `mov [rsi+0xDC], r14d` (RUNTIME_DATA at 0x48,
		// pickAngle at 0x94). Skip that store and the next pick starts where the last one broke.
		constexpr const char* kPickBreakSignature = "44 89 B6 DC 00 00 00";
		constexpr std::size_t kPickBreakInstructionSize = 7;

		RE::SpellItem* g_spell = nullptr;
		RE::EffectSetting* g_effect = nullptr;
		RE::TESBoundObject* g_lockpick = nullptr;
		std::atomic<RE::BGSPerk*> g_requiredPerk{ nullptr };

		std::atomic<bool> g_installed{ false };
		std::atomic<bool> g_standingDown{ false };
		std::atomic<bool> g_rlaStandingDown{ false };
		std::atomic<bool> g_patchAttached{ false };

		std::mutex g_lock;
		std::unordered_set<RE::FormID> g_frozen;
		std::string g_patchStatus = "not installed yet";
		std::string g_requiredPerkName = "none";
		std::string g_lastEvent;
		std::uint64_t g_opened = 0;
		std::chrono::steady_clock::time_point g_lastHoldNotice{};

		RE::PlayerCharacter* Player() { return RE::PlayerCharacter::GetSingleton(); }

		float Skill(RE::ActorValue a_av)
		{
			auto* player = Player();
			auto* avo = player ? player->AsActorValueOwner() : nullptr;
			return avo ? avo->GetActorValue(a_av) : 0.0F;
		}

		void SetLastEvent(std::string a_text)
		{
			std::scoped_lock l(g_lock);
			g_lastEvent = std::move(a_text);
		}

		void Notify(const std::string& a_text)
		{
			if (!settings::general::notifications) { return; }
#if RUNTIME_LINE == 17
			RE::SendHUDMessage::ShowHUDMessage(a_text.c_str(), nullptr, true);
#else
			RE::DebugNotification(a_text.c_str());
#endif
		}

		Tier TierOf(RE::LOCK_LEVEL a_level)
		{
			switch (a_level)
			{
			case RE::LOCK_LEVEL::kVeryEasy: return Tier::kNovice;
			case RE::LOCK_LEVEL::kEasy: return Tier::kApprentice;
			case RE::LOCK_LEVEL::kAverage: return Tier::kAdept;
			case RE::LOCK_LEVEL::kHard: return Tier::kExpert;
			case RE::LOCK_LEVEL::kVeryHard: return Tier::kMaster;
			default: return Tier::kNone;
			}
		}

		float GameSettingFloat(const char* a_name, float a_fallback)
		{
			auto* gs = RE::GameSettingCollection::GetSingleton();
			auto* setting = gs ? gs->GetSetting(a_name) : nullptr;
			if (!setting)
			{
				static std::unordered_set<std::string> warned;
				if (warned.insert(a_name).second) { logger::warn("game setting {} not found; using {}", a_name, a_fallback); }
				return a_fallback;
			}
			return setting->GetFloat();
		}

		void PlaySoundAt(RE::FormID a_descriptor, RE::TESObjectREFR* a_ref)
		{
			if (!settings::general::sound) { return; }
			auto* form = RE::TESForm::LookupByID<RE::BGSSoundDescriptorForm>(a_descriptor);
			auto* audio = RE::BSAudioManager::GetSingleton();
			if (!form || !form->soundDescriptor || !audio)
			{
				logger::debug("sound 0x{:08X} not available; nothing played", a_descriptor);
				return;
			}
#if RUNTIME_LINE == 17
			// CommonLibSSE-NG 7.x exposes no BuildSoundDataFromDescriptor; the manager plays a descriptor directly (no volume/position control).
			(void)a_ref;
			audio->Play(form->soundDescriptor);
#else
			RE::BSSoundHandle handle;
			if (audio->BuildSoundDataFromDescriptor(handle, form->soundDescriptor))
			{
				handle.SetVolume(settings::general::soundVolume);
				if (a_ref) { handle.SetPosition(a_ref->GetPosition()); }
				handle.Play();
			}
#endif
		}

		void GrantSkill(RE::ActorValue a_av, Tier a_tier)
		{
			if (!settings::general::skillGain || a_tier == Tier::kNone) { return; }
			auto* player = Player();
			if (!player) { return; }
			const float base = GameSettingFloat(kSkillUsage[static_cast<int>(a_tier)], 15.0F);
			const float points = base * settings::general::skillGainMult;
			player->UseSkill(a_av, points, nullptr);
			logger::debug("skill use: actor value {} +{:.1f} ({} x {:.2f}) for a {} lock", static_cast<int>(a_av), points, base, settings::general::skillGainMult, TierName(a_tier));
		}

		void Alarm(RE::TESObjectREFR* a_ref, const LockInfo& a_info, const char* a_how)
		{
			if (!settings::general::crime || !a_info.crime || !a_ref) { return; }
			auto* player = Player();
			if (!player) { return; }
			auto* base = a_ref->GetBaseObject();
			auto* owner = a_ref->GetOwner();
			player->StealAlarm(a_ref, base, 1, static_cast<std::int32_t>(settings::general::crimeGold), owner, true);
			logger::debug("crime: {} {} against its owner - alarm raised at {} gold", a_how, a_info.name, settings::general::crimeGold);
		}

		bool HasPerk(RE::FormID a_perk)
		{
			auto* player = Player();
			auto* perk = RE::TESForm::LookupByID<RE::BGSPerk>(a_perk);
			return player && perk && player->HasPerk(perk);
		}

		bool IsFrozen(RE::FormID a_ref)
		{
			std::scoped_lock l(g_lock);
			return g_frozen.contains(a_ref);
		}

		// The one place a lock opens. Returns false when the reference has no lock any more.
		bool Unlock(RE::TESObjectREFR* a_ref, const LockInfo& a_info, const char* a_how, RE::FormID a_sound)
		{
			auto* lock = a_ref ? a_ref->GetLock() : nullptr;
			if (!lock) { logger::warn("unlock: {} has no lock data; nothing done", a_info.name); return false; }
			lock->SetLocked(false);
			{
				std::scoped_lock l(g_lock);
				g_frozen.erase(a_info.refID);
				++g_opened;
				g_lastEvent = std::format("{} lock on {} {}", TierName(a_info.tier), a_info.name, a_how);
			}
			PlaySoundAt(a_sound, a_ref);
			logger::info("{} lock on {} (0x{:08X}) {}", TierName(a_info.tier), a_info.name, a_info.refID, a_how);
			Notify(std::format("{} {}", a_info.name, a_how));
			return true;
		}

		void OnMainThread(std::function<void()> a_task)
		{
			if (auto* tasks = SKSE::GetTaskInterface()) { tasks->AddTask(std::move(a_task)); }
			else { a_task(); }
		}

		void HideLockpickingMenu()
		{
			if (auto* queue = RE::UIMessageQueue::GetSingleton())
			{
				queue->AddMessage(RE::BSFixedString(RE::LockpickingMenu::MENU_NAME.data()), RE::UI_MESSAGE_TYPE::kHide, nullptr);
			}
		}

		// ---- the LockpickingMenu opening: requirements and auto-pick ----
		class MenuSink : public RE::BSTEventSink<RE::MenuOpenCloseEvent>
		{
		public:
			static MenuSink* GetSingleton() { static MenuSink s; return &s; }

			RE::BSEventNotifyControl ProcessEvent(const RE::MenuOpenCloseEvent* a_event, RE::BSTEventSource<RE::MenuOpenCloseEvent>*) override
			{
				if (!a_event || !a_event->opening || g_standingDown.load(std::memory_order_acquire)) { return RE::BSEventNotifyControl::kContinue; }
				if (std::string_view(a_event->menuName.c_str()) != RE::LockpickingMenu::MENU_NAME) { return RE::BSEventNotifyControl::kContinue; }
				if (!settings::requirements::enabled && !settings::requirements::autoPick) { return RE::BSEventNotifyControl::kContinue; }

#if RUNTIME_LINE == 17
				auto targetPtr = RE::LockpickingMenu::GetTargetReference();   // a TESObjectREFRPtr on 7.x
				RE::TESObjectREFR* ref = targetPtr ? targetPtr.get() : nullptr;
#else
				RE::TESObjectREFR* ref = RE::LockpickingMenu::GetTargetReference();
#endif
				if (!ref) { ref = CrosshairRef(); }
				const LockInfo info = Describe(ref);
				if (!info.valid || !info.locked || info.requiresKey)
				{
					logger::debug("lockpicking menu opened on {} - {}; left to the game", info.valid ? info.name : "no reference", info.requiresKey ? "needs a key" : "not a lock this mod handles");
					return RE::BSEventNotifyControl::kContinue;
				}

				const Verdict v = CanPick(info);
				if (settings::requirements::enabled && !v.allowed)
				{
					HideLockpickingMenu();
					logger::info("refused: {} lock on {} needs Lockpicking {}, the player has {}", TierName(info.tier), info.name, v.needed, v.have);
					SetLastEvent(std::format("refused to pick the {} lock on {} ({} of {})", TierName(info.tier), info.name, v.have, v.needed));
					Notify(std::format("Your Lockpicking of {} is not enough for this {} lock - it needs {}.", v.have, TierName(info.tier), v.needed));
					return RE::BSEventNotifyControl::kContinue;
				}
				if (settings::requirements::autoPick)
				{
					HideLockpickingMenu();
					const RE::FormID refID = info.refID;
					OnMainThread([refID]() {
						auto* target = RE::TESForm::LookupByID<RE::TESObjectREFR>(refID);
						if (target) { AutoPick(target); }
					});
				}
				return RE::BSEventNotifyControl::kContinue;
			}
		};

		// ---- a weapon or a spell hitting a locked object ----
		bool WeaponAllowed(RE::TESObjectWEAP* a_weapon, RE::ActorValue& a_skill)
		{
			using WT = RE::WEAPON_TYPE;
			const auto type = a_weapon ? a_weapon->GetWeaponType() : WT::kHandToHandMelee;
			const auto mode = settings::smash::weapons;   // 0 two-handed only, 1 one+two, 2 any
			switch (type)
			{
			case WT::kTwoHandSword:
			case WT::kTwoHandAxe:
				a_skill = RE::ActorValue::kTwoHanded; return true;
			case WT::kOneHandSword:
			case WT::kOneHandDagger:
			case WT::kOneHandAxe:
			case WT::kOneHandMace:
				a_skill = RE::ActorValue::kOneHanded; return mode >= 1;
			case WT::kBow:
			case WT::kCrossbow:
				a_skill = RE::ActorValue::kArchery; return mode >= 2;
			case WT::kStaff:
				a_skill = RE::ActorValue::kDestruction; return mode >= 2;
			default:
				a_skill = RE::ActorValue::kOneHanded; return mode >= 2;   // unarmed
			}
		}

		bool HasEffectKeyword(RE::MagicItem* a_item, RE::FormID a_keyword)
		{
			if (!a_item) { return false; }
			for (auto* effect : a_item->effects)
			{
				if (effect && effect->baseEffect && effect->baseEffect->HasKeywordID(a_keyword)) { return true; }
			}
			return false;
		}

		void HandleSpellHit(RE::TESObjectREFR* a_ref, const LockInfo& a_info, bool a_ours, bool a_frost, bool a_fire, bool a_shock)
		{
			if (a_ours)
			{
				if (!settings::spell::enabled) { return; }
				SpellUnlock(a_ref, RE::ActorValue::kAlteration);
				return;
			}
			if (settings::spell::allowed == 0) { return; }   // only the unlock spell works on locks
			if (a_frost)
			{
				Freeze(a_ref);
				return;
			}
			if (a_fire)
			{
				if (a_info.frozen) { Thaw(a_ref); }
				else { SpellUnlock(a_ref, RE::ActorValue::kDestruction); }
				return;
			}
			if (a_shock && settings::spell::allowed >= 2)
			{
				SpellUnlock(a_ref, RE::ActorValue::kDestruction);
			}
		}

		class HitSink : public RE::BSTEventSink<RE::TESHitEvent>
		{
		public:
			static HitSink* GetSingleton() { static HitSink s; return &s; }

			RE::BSEventNotifyControl ProcessEvent(const RE::TESHitEvent* a_event, RE::BSTEventSource<RE::TESHitEvent>*) override
			{
				if (!a_event || g_standingDown.load(std::memory_order_acquire)) { return RE::BSEventNotifyControl::kContinue; }
				auto* target = a_event->target.get();
				auto* cause = a_event->cause.get();
				auto* player = Player();
				if (!target || !cause || !player || cause != player) { return RE::BSEventNotifyControl::kContinue; }
				if (!settings::smash::enabled && !settings::spell::enabled && settings::spell::allowed == 0) { return RE::BSEventNotifyControl::kContinue; }

				const LockInfo info = Describe(target);
				if (!info.valid || !info.locked || info.requiresKey) { return RE::BSEventNotifyControl::kContinue; }

				auto* source = RE::TESForm::LookupByID(a_event->source);
				const RE::FormID refID = info.refID;
				if (auto* weapon = source ? source->As<RE::TESObjectWEAP>() : nullptr; weapon || (!source && a_event->source == 0))
				{
					if (!settings::smash::enabled) { return RE::BSEventNotifyControl::kContinue; }
					RE::ActorValue skill = RE::ActorValue::kOneHanded;
					if (!WeaponAllowed(weapon, skill))
					{
						logger::debug("hit on {} with a weapon this mod's setting does not allow to smash (mode {})", info.name, settings::smash::weapons);
						return RE::BSEventNotifyControl::kContinue;
					}
					logger::debug("hit event: {} hit by weapon 0x{:08X}", info.name, a_event->source);
					OnMainThread([refID, skill]() {
						if (auto* r = RE::TESForm::LookupByID<RE::TESObjectREFR>(refID)) { Smash(r, skill, true); }
					});
					return RE::BSEventNotifyControl::kContinue;
				}
				if (!source) { return RE::BSEventNotifyControl::kContinue; }

				bool ours = false, frost = false, fire = false, shock = false;
				if (auto* magic = source->As<RE::MagicItem>())
				{
					ours = (g_spell && magic == g_spell);
					frost = HasEffectKeyword(magic, kKeywordFrost);
					fire = HasEffectKeyword(magic, kKeywordFire);
					shock = HasEffectKeyword(magic, kKeywordShock);
				}
				else if (auto* effect = source->As<RE::EffectSetting>())
				{
					ours = (g_effect && effect == g_effect);
					frost = effect->HasKeywordID(kKeywordFrost);
					fire = effect->HasKeywordID(kKeywordFire);
					shock = effect->HasKeywordID(kKeywordShock);
				}
				else
				{
					logger::debug("hit on {} from 0x{:08X} ({}) - neither a weapon nor a spell; ignored", info.name, a_event->source, source->GetFormType());
					return RE::BSEventNotifyControl::kContinue;
				}
				if (!ours && !frost && !fire && !shock) { return RE::BSEventNotifyControl::kContinue; }
				logger::debug("hit event: {} hit by spell/effect 0x{:08X} - ours={} frost={} fire={} shock={}", info.name, a_event->source, ours, frost, fire, shock);
				OnMainThread([refID, ours, frost, fire, shock]() {
					if (auto* r = RE::TESForm::LookupByID<RE::TESObjectREFR>(refID)) { HandleSpellHit(r, Describe(r), ours, frost, fire, shock); }
				});
				return RE::BSEventNotifyControl::kContinue;
			}
		};

		// ---- the pick-angle patch ----
		extern "C" bool ALO_KeepPickAngle() { return KeepPickAngle(); }

		// Mid-function site, so every volatile register the compiled callee may clobber is
		// preserved (logic library 38: the site keeps live values in rsi and r14, and a C++ callee
		// may clobber rax/rcx/rdx/r8-r11/xmm0-5). The original store runs inside the preserved
		// region when the answer is "reset"; rsi and r14 are non-volatile and untouched.
		struct PickAngleStub : Xbyak::CodeGenerator
		{
			PickAngleStub(std::uintptr_t a_return, void* a_decide)
			{
				Xbyak::Label keep, back;
				push(rax); push(rcx); push(rdx); push(r8); push(r9); push(r10); push(r11);
				push(rbx);
				mov(rbx, rsp);
				sub(rsp, 0x60);
				and_(rsp, -16);
				movaps(xword[rsp], xmm0);
				movaps(xword[rsp + 0x10], xmm1);
				movaps(xword[rsp + 0x20], xmm2);
				movaps(xword[rsp + 0x30], xmm3);
				movaps(xword[rsp + 0x40], xmm4);
				movaps(xword[rsp + 0x50], xmm5);
				sub(rsp, 0x20);
				mov(rax, reinterpret_cast<std::uintptr_t>(a_decide));
				call(rax);
				add(rsp, 0x20);
				test(al, al);
				jnz(keep);
				mov(dword[rsi + 0xDC], r14d);   // the game's own store: the pick angle resets
				L(keep);
				movaps(xmm0, xword[rsp]);
				movaps(xmm1, xword[rsp + 0x10]);
				movaps(xmm2, xword[rsp + 0x20]);
				movaps(xmm3, xword[rsp + 0x30]);
				movaps(xmm4, xword[rsp + 0x40]);
				movaps(xmm5, xword[rsp + 0x50]);
				mov(rsp, rbx);
				pop(rbx);
				pop(r11); pop(r10); pop(r9); pop(r8); pop(rdx); pop(rcx); pop(rax);
				jmp(ptr[rip + back]);
				L(back);
				dq(a_return);
			}
		};

		void InstallPickAnglePatch()
		{
			if (g_patchAttached.load(std::memory_order_acquire)) { return; }
			const auto found = Signature::Find(kPickBreakSignature, 0);
			std::string status;
			if (!found.found || found.matches != 1)
			{
				status = std::format("refused: the pick-break instruction was {} ({}); the pick angle resets as in vanilla", found.matches == 0 ? "not found" : "found more than once", found.note);
				logger::warn("pick-angle patch {}", status);
				std::scoped_lock l(g_lock); g_patchStatus = status; return;
			}
			const auto base = REL::Module::get().base();
			PickAngleStub stub(found.address + kPickBreakInstructionSize, reinterpret_cast<void*>(&ALO_KeepPickAngle));
			stub.ready();
			auto& trampoline = SKSE::GetTrampoline();
			void* code = trampoline.allocate(stub);
			if (!code)
			{
				status = "refused: no trampoline space for the pick-angle stub";
				logger::error("pick-angle patch {}", status);
				std::scoped_lock l(g_lock); g_patchStatus = status; return;
			}
			trampoline.write_branch<5>(found.address, reinterpret_cast<std::uintptr_t>(code));
			g_patchAttached.store(true, std::memory_order_release);
			status = std::format("attached at game offset 0x{:X} (the pick-break store, matched once); the angle is kept whenever the setting and its perk gate allow", found.address - base);
			logger::info("pick-angle patch {}", status);
			std::scoped_lock l(g_lock); g_patchStatus = status;
		}

		void ResolveRequiredPerk()
		{
			using namespace settings::pickangle;
			RE::BGSPerk* perk = nullptr;
			std::string name = "none";
			static constexpr RE::FormID kVanilla[] = { 0, kPerkLocksmith, kPerkUnbreakable, kPerkQuickHands, kPerkWaxKey, kPerkGoldenTouch, kPerkTreasureHunter };
			static constexpr const char* kVanillaNames[] = { "none", "Locksmith", "Unbreakable", "Quick Hands", "Wax Key", "Golden Touch", "Treasure Hunter" };
			if (requiredPerk >= 1 && requiredPerk <= 6)
			{
				perk = RE::TESForm::LookupByID<RE::BGSPerk>(kVanilla[requiredPerk]);
				name = perk ? kVanillaNames[requiredPerk] : std::format("{} (not found!)", kVanillaNames[requiredPerk]);
			}
			else if (requiredPerk == 7)
			{
				auto* data = RE::TESDataHandler::GetSingleton();
				perk = (data && !perkPlugin.empty()) ? data->LookupForm<RE::BGSPerk>(perkFormID, perkPlugin) : nullptr;
				name = perk ? std::format("{} (0x{:X} in {})", perk->GetName() ? perk->GetName() : "custom perk", perkFormID, perkPlugin)
							: std::format("custom perk 0x{:X} in \"{}\" NOT FOUND - no gate applied", perkFormID, perkPlugin);
				if (!perk) { logger::warn("pick-angle perk gate: {}", name); }
			}
			g_requiredPerk.store(perk, std::memory_order_release);
			{ std::scoped_lock l(g_lock); g_requiredPerkName = name; }
			logger::debug("pick-angle perk gate: {}", name);
		}

		void SyncSpell()
		{
			auto* player = Player();
			if (!player || !g_spell || g_standingDown.load(std::memory_order_acquire)) { return; }
			const bool has = player->HasSpell(g_spell);
			if (settings::spell::enabled && !has)
			{
				player->AddSpell(g_spell);
				logger::info("unlock spell: \"{}\" added to the player", g_spell->GetName());
				Notify("You know the spell Manipulate Lock.");
			}
			else if (!settings::spell::enabled && has)
			{
				player->RemoveSpell(g_spell);
				logger::info("unlock spell: \"{}\" removed from the player", g_spell->GetName());
			}
		}

		void ResolveForms()
		{
			auto* data = RE::TESDataHandler::GetSingleton();
			if (data && !g_spell)
			{
				g_spell = data->LookupForm<RE::SpellItem>(kSpellLocalFormID, kPluginFileName);
				g_effect = data->LookupForm<RE::EffectSetting>(kEffectLocalFormID, kPluginFileName);
				if (g_spell) { logger::info("{}: spell \"{}\" resolved (0x{:08X})", kPluginFileName, g_spell->GetName(), g_spell->GetFormID()); }
				else { logger::warn("{} is not loaded - the unlock spell cannot exist; the other features are unaffected", kPluginFileName); }
			}
			if (!g_lockpick) { g_lockpick = RE::TESForm::LookupByID<RE::TESBoundObject>(kLockpick); }
		}
	}

	const char* TierName(Tier a_tier)
	{
		const int i = static_cast<int>(a_tier);
		return (i >= 0 && i < settings::kTierCount) ? settings::kTierNames[i] : "key-required";
	}

	RE::TESObjectREFR* CrosshairRef()
	{
		auto* data = RE::CrosshairPickData::GetSingleton();
		if (!data) { return nullptr; }
		auto ptr = data->target.get();
		return ptr ? ptr.get() : nullptr;
	}

	LockInfo Describe(RE::TESObjectREFR* a_ref)
	{
		LockInfo info;
		if (!a_ref) { return info; }
		auto* lock = a_ref->GetLock();
		if (!lock) { return info; }
		info.valid = true;
		info.refID = a_ref->GetFormID();
		info.locked = a_ref->IsLocked();
		const auto level = a_ref->GetLockLevel();
		info.requiresKey = (level == RE::LOCK_LEVEL::kRequiresKey);
		info.tier = TierOf(level);
		info.frozen = IsFrozen(info.refID);
		info.crime = a_ref->IsCrimeToActivate();
		const char* name = a_ref->GetDisplayFullName();
		info.name = (name && *name) ? name : "the lock";
		return info;
	}

	LockInfo LookingAt() { return Describe(CrosshairRef()); }

	Verdict CanPick(const LockInfo& a_lock)
	{
		Verdict v;
		v.have = static_cast<std::uint32_t>(Skill(RE::ActorValue::kLockpicking));
		v.needed = a_lock.tier == Tier::kNone ? 0 : settings::requirements::pick[static_cast<int>(a_lock.tier)];
		v.allowed = !settings::requirements::enabled || v.have >= v.needed;
		v.why = v.allowed ? "Lockpicking suffices" : "Lockpicking too low";
		return v;
	}

	Verdict CanSmash(const LockInfo& a_lock, RE::ActorValue a_skill)
	{
		Verdict v;
		v.have = static_cast<std::uint32_t>(Skill(a_skill));
		std::uint32_t need = a_lock.tier == Tier::kNone ? 0 : settings::smash::need[static_cast<int>(a_lock.tier)];
		if (a_lock.frozen) { need = need > settings::spell::frostMalus ? need - settings::spell::frostMalus : 0; }
		v.needed = need;
		v.allowed = v.have >= v.needed;
		v.why = v.allowed ? (a_lock.frozen ? "weapon skill suffices (the lock is frozen)" : "weapon skill suffices") : "weapon skill too low";
		return v;
	}

	Verdict CanUnlockBySpell(const LockInfo& a_lock, RE::ActorValue a_school)
	{
		Verdict v;
		v.have = static_cast<std::uint32_t>(Skill(a_school));
		v.needed = a_lock.tier == Tier::kNone ? 0 : settings::spell::need[static_cast<int>(a_lock.tier)];
		v.allowed = v.have >= v.needed;
		v.why = v.allowed ? "magic skill suffices" : "magic skill too low";
		return v;
	}

	bool AutoPick(RE::TESObjectREFR* a_ref)
	{
		const LockInfo info = Describe(a_ref);
		if (!info.valid || !info.locked || info.requiresKey) { return false; }
		auto* player = Player();
		if (!player) { return false; }
		const Verdict v = CanPick(info);
		if (!v.allowed)
		{
			Notify(std::format("Your Lockpicking of {} is not enough for this {} lock - it needs {}.", v.have, TierName(info.tier), v.needed));
			return false;
		}
		const bool unbreakable = HasPerk(kPerkUnbreakable);
		if (!unbreakable)
		{
			std::int32_t count = 0;
			if (g_lockpick)
			{
				auto counts = player->GetInventoryCounts();
				if (auto it = counts.find(g_lockpick); it != counts.end()) { count = it->second; }
			}
			if (count <= 0)
			{
				logger::info("auto-pick: no lockpicks for the {} lock on {}", TierName(info.tier), info.name);
				SetLastEvent(std::format("no lockpick for {}", info.name));
				Notify("You have no lockpicks.");
				return false;
			}
			player->RemoveItem(g_lockpick, 1, RE::ITEM_REMOVE_REASON::kRemove, nullptr, nullptr);
		}
		if (!Unlock(a_ref, info, "picked", kSoundUnlock)) { return false; }
		GrantSkill(RE::ActorValue::kLockpicking, info.tier);
		if (!HasPerk(kPerkQuickHands)) { Alarm(a_ref, info, "auto-picked"); }
		if (settings::requirements::openAfterPick)
		{
			a_ref->ActivateRef(player, 0, nullptr, 1, false);
		}
		return true;
	}

	bool Smash(RE::TESObjectREFR* a_ref, RE::ActorValue a_skill, bool a_fromEvent)
	{
		const LockInfo info = Describe(a_ref);
		if (!info.valid || !info.locked || info.requiresKey) { return false; }
		const Verdict v = CanSmash(info, a_skill);
		if (!v.allowed)
		{
			const auto now = std::chrono::steady_clock::now();
			bool notice = false;
			{
				std::scoped_lock l(g_lock);
				if (now - g_lastHoldNotice > std::chrono::seconds(2)) { g_lastHoldNotice = now; notice = true; }
				g_lastEvent = std::format("the {} lock on {} held ({} of {})", TierName(info.tier), info.name, v.have, v.needed);
			}
			logger::debug("smash: {} lock on {} held - weapon skill {} of {}{}", TierName(info.tier), info.name, v.have, v.needed, a_fromEvent ? "" : " (simulated)");
			if (notice) { Notify(std::format("The lock holds. ({} of {} weapon skill)", v.have, v.needed)); }
			return false;
		}
		if (!Unlock(a_ref, info, "smashed open", kSoundSmash)) { return false; }
		GrantSkill(a_skill, info.tier);
		Alarm(a_ref, info, "smashed");
		return true;
	}

	bool SpellUnlock(RE::TESObjectREFR* a_ref, RE::ActorValue a_school)
	{
		const LockInfo info = Describe(a_ref);
		if (!info.valid || !info.locked || info.requiresKey) { return false; }
		const Verdict v = CanUnlockBySpell(info, a_school);
		if (!v.allowed)
		{
			logger::debug("spell: {} lock on {} resisted - magic skill {} of {}", TierName(info.tier), info.name, v.have, v.needed);
			SetLastEvent(std::format("the {} lock on {} resisted the spell ({} of {})", TierName(info.tier), info.name, v.have, v.needed));
			Notify(std::format("The lock resists your magic. ({} of {} skill)", v.have, v.needed));
			return false;
		}
		if (!Unlock(a_ref, info, "opened by magic", kSoundUnlock)) { return false; }
		GrantSkill(a_school, info.tier);
		Alarm(a_ref, info, "opened by magic");
		return true;
	}

	void Freeze(RE::TESObjectREFR* a_ref)
	{
		const LockInfo info = Describe(a_ref);
		if (!info.valid || !info.locked || info.requiresKey) { return; }
		bool fresh = false;
		{
			std::scoped_lock l(g_lock);
			fresh = g_frozen.insert(info.refID).second;
			g_lastEvent = std::format("the {} lock on {} froze", TierName(info.tier), info.name);
		}
		if (fresh)
		{
			logger::info("frost: the {} lock on {} (0x{:08X}) is frozen - smashing it needs {} less skill", TierName(info.tier), info.name, info.refID, settings::spell::frostMalus);
			Notify(std::format("The lock on {} freezes over.", info.name));
		}
	}

	void Thaw(RE::TESObjectREFR* a_ref)
	{
		const LockInfo info = Describe(a_ref);
		if (!info.valid) { return; }
		bool was = false;
		{
			std::scoped_lock l(g_lock);
			was = g_frozen.erase(info.refID) > 0;
			if (was) { g_lastEvent = std::format("the {} lock on {} thawed", TierName(info.tier), info.name); }
		}
		if (was)
		{
			logger::info("fire: the lock on {} (0x{:08X}) thawed", info.name, info.refID);
			Notify(std::format("The ice on {} melts away.", info.name));
		}
	}

	bool KeepPickAngle()
	{
		if (!settings::pickangle::enabled || g_rlaStandingDown.load(std::memory_order_acquire)) { return false; }
		auto* perk = g_requiredPerk.load(std::memory_order_acquire);
		bool keep = true;
		if (perk)
		{
			auto* player = Player();
			keep = player && player->HasPerk(perk);
		}
		logger::debug("pick broke: the angle is {}{}", keep ? "kept" : "reset", perk ? (keep ? " (perk held)" : " (perk missing)") : "");
		return keep;
	}

	void ApplySettings()
	{
		OnMainThread([]() {
			ResolveRequiredPerk();
			SyncSpell();
		});
	}

	void DeactivateAll()
	{
		settings::requirements::enabled = false;
		settings::requirements::autoPick = false;
		settings::smash::enabled = false;
		settings::spell::enabled = false;
		settings::pickangle::enabled = false;
		{
			std::scoped_lock l(g_lock);
			g_frozen.clear();
			g_lastEvent = "every feature switched off";
		}
		ApplySettings();
		logger::info("every feature switched off (Deactivate)");
	}

	void Install()
	{
		if (g_installed.exchange(true)) { ApplySettings(); return; }

		auto* data = RE::TESDataHandler::GetSingleton();
		const bool loOriginal = data && (data->LookupLoadedModByName("Lock Overhaul.esp") || data->LookupLoadedLightModByName("Lock Overhaul.esp"));
		g_standingDown.store(loOriginal, std::memory_order_release);
		g_rlaStandingDown.store(GetModuleHandleA("RememberLockpickAngle.dll") != nullptr, std::memory_order_release);
		if (loOriginal) { logger::warn("Lock Overhaul.esp is loaded - this mod stands down entirely so the two never act on one lock"); }
		if (g_rlaStandingDown.load()) { logger::info("RememberLockpickAngle.dll is loaded - the pick-angle section stands down; that mod keeps the angle"); }

		ResolveForms();
		if (!loOriginal)
		{
			if (auto* ui = RE::UI::GetSingleton()) { ui->AddEventSink<RE::MenuOpenCloseEvent>(MenuSink::GetSingleton()); }
			if (auto* holder = RE::ScriptEventSourceHolder::GetSingleton()) { holder->AddEventSink<RE::TESHitEvent>(HitSink::GetSingleton()); }
			logger::info("sinks registered: LockpickingMenu open (requirements, auto-pick), hit events (smash, spells)");
			if (!g_rlaStandingDown.load()) { InstallPickAnglePatch(); }
			else { std::scoped_lock l(g_lock); g_patchStatus = "standing down: RememberLockpickAngle.dll is loaded"; }
		}
		else
		{
			std::scoped_lock l(g_lock);
			g_patchStatus = "standing down: Lock Overhaul.esp is loaded";
		}
		ApplySettings();
	}

	State GetState()
	{
		State s;
		s.standingDown = g_standingDown.load(std::memory_order_acquire);
		s.pickAngleStandingDown = g_rlaStandingDown.load(std::memory_order_acquire);
		s.spellResolved = g_spell != nullptr;
		s.spellFormID = g_spell ? g_spell->GetFormID() : 0;
		auto* player = Player();
		s.spellKnown = player && g_spell && player->HasSpell(g_spell);
		s.patchAttached = g_patchAttached.load(std::memory_order_acquire);
		std::scoped_lock l(g_lock);
		s.patchStatus = g_patchStatus;
		s.requiredPerkName = g_requiredPerkName;
		s.frozenCount = static_cast<std::uint32_t>(g_frozen.size());
		s.opened = g_opened;
		s.lastEvent = g_lastEvent;
		return s;
	}
}
