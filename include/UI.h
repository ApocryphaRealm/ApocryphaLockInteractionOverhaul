#pragma once

// ApocryphaRealm Lock Interaction Overhaul - the Apocrypha Menu Framework page, one section per feature.

namespace UI
{
	void Register();

	namespace RequirementsPanel { void __stdcall Render(); }
	namespace SmashPanel { void __stdcall Render(); }
	namespace SpellPanel { void __stdcall Render(); }
	namespace PickAnglePanel { void __stdcall Render(); }
	namespace GeneralPanel { void __stdcall Render(); }
	namespace DebugPanel { void __stdcall Render(); }
}
