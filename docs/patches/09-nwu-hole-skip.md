# NWU hole-skip (NovaWorld connection fix)

**Status:** documented. Community fix, credited below. No automated patcher (build-specific code cave).

## What it does

Fixes NovaWorld (NWU, the NovaWorld UDP protocol) connection failures. The retail handler has a validation step that fails on some modern networks, preventing clients from connecting through NovaWorld. The fix routes execution around that check.

## Mechanism

The fix is installed as a code cave in the `.text` section around `0x394DF0` (VA `0x794DF0`). The live binary that carries it can be recognised by the instruction pattern that writes `mov byte [edi+0x174], 0` inside the cave. A related, separate tuning of NWU thresholds for high packet rates lives just after it (two bytes near `0x394E0A` and `0x394E1A` differ between the 62 and 125 packet-rate builds).

## Status and caveat

This is a community-contributed fix (credited to "Spaghetti") and it is build-specific: the cave contents and surrounding bytes vary between builds, so it is not suitable for a generic byte-asserted patcher the way the other fixes are. It is documented here so the mechanism and location are recorded. If you are rebuilding a server exe from stock and need NovaWorld connectivity, start from a build that already carries this cave, or reproduce it from the pattern above.

## Credits

NovaWorld hole-skip fix: community contributor "Spaghetti". Retail protocol correctness work in the surrounding tooling: Taylor Finnell (Open Nova).
