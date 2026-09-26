"""Hole-skip: players stop freezing in place when a packet is lost (server).

Joint Ops delivers ordered packets through a reorder queue. When the packet the
server expects next has not arrived, the retail drain loop stops and waits for
it. On a fast server a player who loses one packet is left frozen: still
connected, chat still arrives, but they cannot move until they reconnect.

Spaghetti's fix sends the drain loop through a code cave. When the expected
packet is missing, the cave checks two things: how many packets are queued
behind the hole, and how far ahead the newest one is. Past both thresholds it
moves the cursor past the hole and carries on draining, so the player keeps
moving and only the lost packet is skipped.

The two thresholds are the only difference between the versions:

    64 Hz version   8 queued, 64 behind    Spaghetti's original
    125 Hz version  6 queued, 32 behind    FMJ tuning: at 125 Hz, 64 packets is
                                           a ~512 ms stall, 32 is ~256 ms

32 Hz servers do not need it: at that rate high-ping players do not hit the
stall.

Changes (all asserted before writing):
  hook  VA 0x626954  8B 8F B8 07 00 00 83 C1  (mov ecx,[edi+7B8h]; add ecx,..)
                ->   E9 97 E4 16 00 90 90 90  (jmp 0x794DF0; nop x3)
  cave  VA 0x794DF0  81 bytes in the zero padding at the end of .text
        VA 0x794E0A  queued-packets threshold (inside the cave)
        VA 0x794E1A  how-far-behind threshold (inside the cave)

On an exe that already carries the cave with one of the two known settings the
script switches it to the version asked for. Custom settings are refused, so
they are never overwritten by accident.

Full write-up: docs/patches/09-nwu-hole-skip.md

Usage:  python patch_hole_skip.py <in_server.exe> <out.exe> [64|125]
        default 125. Pair with patch_packet_rate.py (62 = the 64 Hz build, 125).
"""
import sys

from patch_util import Patch, apply, va_to_offset

HOOK_VA = 0x626954
HOOK_OLD = bytes.fromhex("8b8fb807000083c1")
HOOK_NEW = bytes.fromhex("e997e41600909090")
CAVE_VA = 0x794DF0
CAVE = bytes.fromhex(
    "8b8fb807000083c101394e140f84601be9ff8b8fa807000083f9087c2f8b87b40700002b87b8070000"
    "3d4000000076168b4e1449898fb8070000c6877401000001e90a1be9ff8b87a0070000e97a1be9ff"
)
QUEUED_VA, BEHIND_VA = CAVE_VA + 0x1A, CAVE_VA + 0x2A
VERSIONS = {64: (8, 64), 125: (6, 32)}
assert len(CAVE) == 0x51 and CAVE[0x1A] == 8 and CAVE[0x2A] == 64


def cave_for(hz: int) -> bytes:
    cave = bytearray(CAVE)
    cave[0x1A], cave[0x2A] = VERSIONS[hz]
    return bytes(cave)


def build_patches(data: bytes, hz: int) -> list:
    hook = data[va_to_offset(data, HOOK_VA):][:len(HOOK_OLD)]
    at = va_to_offset(data, CAVE_VA)
    space = data[at:at + len(CAVE)]
    if hook == HOOK_OLD:
        # Free space is zeros. The 32 Hz JOexeFIX exes keep one stray byte of an
        # earlier cave at the very end: the same byte this cave writes there.
        if space[:-1] != bytes(len(CAVE) - 1) or space[-1] not in (0x00, CAVE[-1]):
            sys.exit(f"ABORT: the space at VA {CAVE_VA:#x} is already used (wrong build?)")
        return [Patch(CAVE_VA, space, cave_for(hz), f"hole-skip cave ({hz} Hz version)"),
                Patch(HOOK_VA, HOOK_OLD, HOOK_NEW, "drain loop -> hole-skip cave")]
    if hook == HOOK_NEW:
        current = (space[0x1A], space[0x2A])
        known = {v: k for k, v in VERSIONS.items()}
        if space != cave_for(known.get(current, 64)) or current not in known:
            sys.exit(f"ABORT: hole-skip is in with settings {current}, not a known version; "
                     "left alone")
        if known[current] == hz:
            sys.exit(f"Hole-skip is already the {hz} Hz version; nothing to do.")
        new = VERSIONS[hz]
        return [Patch(QUEUED_VA, bytes([current[0]]), bytes([new[0]]), f"queued threshold -> {new[0]}"),
                Patch(BEHIND_VA, bytes([current[1]]), bytes([new[1]]), f"behind threshold -> {new[1]}")]
    sys.exit(f"ABORT: unexpected bytes at VA {HOOK_VA:#x}: {hook.hex()} (wrong build?)")


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    hz = int(sys.argv[3]) if len(sys.argv) == 4 else 125
    if hz not in VERSIONS:
        sys.exit("speed must be 64 or 125 (32 Hz does not need hole-skip)")
    apply(sys.argv[1], sys.argv[2], build_patches(open(sys.argv[1], "rb").read(), hz))
