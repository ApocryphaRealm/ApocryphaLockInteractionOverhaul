#pragma once

// ApocryphaRealm Lock Interaction Overhaul - the DevBench "alio.control" tool: live state, every switch, the lock
// under the crosshair, and a simulate op that runs the same decision path the game events run.

namespace DevBenchTool
{
	// Registers with DevBench when it is present. a_lastAttempt: log at info if still absent.
	void Init(bool a_lastAttempt);
}
