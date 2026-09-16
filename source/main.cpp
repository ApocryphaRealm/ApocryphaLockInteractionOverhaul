// ApocryphaRealm Lock Interaction Overhaul - own code, GPL-3.0-or-later (2026-09-06; relicensed from MIT 2026-09-13, see NOTICE.md). Lock skill requirements, auto-pick,
// smashing locks with a weapon, an unlock spell with frost and fire tricks, crime for all of it,
// and Remember Lockpick Angle's kept angle - an original rebuild of the Lock Overhaul idea, on
// the Apocrypha Menu Framework. The spell is a SPEL record in the tiny LockInteractionOverhaul.esp.
#include "PCH.h"

#include "DevBenchTool.h"
#include "Locks.h"
#include "Settings.h"
#include "UI.h"

#include "utils/Logger.h"
#include "utils/Strings.h"

namespace
{
	void MessageHandler(SKSE::MessagingInterface::Message* a_msg)
	{
		switch (a_msg->type)
		{
		case SKSE::MessagingInterface::kPostLoad:
			DevBenchTool::Init(false);
			break;
		case SKSE::MessagingInterface::kDataLoaded:
			strings::Configure("LockInteractionOverhaul");
			UI::Register();
			Locks::Install();
			DevBenchTool::Init(true);
			break;
		case SKSE::MessagingInterface::kPostLoadGame:
		case SKSE::MessagingInterface::kNewGame:
			// The spell follows the setting per character: a save that never had it gets it now.
			Locks::ApplySettings();
			break;
		default:
			break;
		}
	}
}

SKSEPluginLoad(const SKSE::LoadInterface* a_skse)
{
	SKSE::Init(a_skse);
	SKSE::log::init("LockInteractionOverhaul");

	settings::Init("LockInteractionOverhaul.ini");
	settings::ApplyLogLevel();

	logger::info("ApocryphaRealm Lock Interaction Overhaul {} loading",
				 SKSE::PluginDeclaration::GetSingleton()->GetVersion().string("."));
	logger::info("Build line: {}", RUNTIME_LINE == 17 ? "Skyrim 1.7.x" : "SE 1.5.97 / AE 1.6.x");

	// The pick-angle stub (about 150 bytes) plus its 5-byte branch.
	SKSE::AllocTrampoline(512);

	SKSE::GetMessagingInterface()->RegisterListener(MessageHandler);

	return true;
}
