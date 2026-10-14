"""Shared code for patches 19 and 20 (keep claymores / keep AT mines after a respawn).

When a player dies and redeploys, `Server_ProcessPlayerDeath` calls
`Entity_RemovePlacedDevicesByOwner @0x546E00` (call at 0x5178D8), which removes
every satchel, claymore and AT mine that player placed.  The same function is
also called when a player leaves the server (call at 0x50A2BB).

Each patch replaces ONE type test inside that function with a jump to a small
cave.  The cave repeats the test, and when the device is of that type it looks
at the function's return address ([esp+0x10]; the function pushed four
registers): a redeploy (0x5178DD) keeps the device, anything else (a player
leaving) removes it as before.  Satchels and the other type are untouched, so
the two patches are independent and either can be applied alone.

The caves live in the zero tail of the `_text` section, after patch 15's line
buffer (0x7BFE00..0x7BFEFF).  Like patches 14 and 15 this maps that tail
(VirtualSize 0x2AA10 -> 0x2B000); the file size does not change.
"""
from __future__ import annotations

import os
import struct
import sys

from patch_long_chat import _map_cave_tail
from patch_util import Patch, apply

DEPLOY_RETURN = 0x5178DD        # after `call 0x546E00` at 0x5178D8 (redeploy)
LOOP_TOP = 0x546E20             # next placed device

# (name, site, retail test, its ammo-def global, after the test fails, the removal, cave)
DEVICES = {
    "claymore": (0x546E8B, "3b15", 0x24E7DD0, 0x546E9C, 0x546E93, 0x7BFF00),
    "at_mine": (0x546EAE, "3b05", 0x24E7DC0, LOOP_TOP, 0x546EBA, 0x7BFF20),
}
CAVE_SIZE = 31


def rel(src_next: int, dst: int) -> bytes:
    return struct.pack("<i", dst - src_next)


def build(device: str) -> list[Patch]:
    site, op, ammo, skip, remove, cave = DEVICES[device]
    test = bytes.fromhex(op) + struct.pack("<I", ammo)        # cmp reg,[ammo def]
    c = bytearray(test)
    c += b"\x0f\x85" + rel(cave + len(c) + 6, skip)          # jne: not this type, as retail
    c += bytes.fromhex("817c2410") + struct.pack("<I", DEPLOY_RETURN)  # cmp [esp+10h],redeploy
    c += b"\x0f\x84" + rel(cave + len(c) + 6, skip)          # je: redeploy, keep it
    c += b"\xe9" + rel(cave + len(c) + 5, remove)            # jmp: player left, remove it
    assert len(c) == CAVE_SIZE
    return [
        Patch(cave, bytes(CAVE_SIZE), bytes(c), f"cave: keep the {device} on a redeploy"),
        Patch(site, test, b"\xe9" + rel(site + 5, cave) + b"\x90", f"{device} test -> cave"),
    ]


def main(device: str, usage: str) -> None:
    if len(sys.argv) != 3:
        sys.exit(usage)
    data = bytearray(open(sys.argv[1], "rb").read())
    if not _map_cave_tail(data):
        apply(sys.argv[1], sys.argv[2], build(device))
        return
    print("_text VirtualSize 0x2AA10 -> 0x2B000 (maps the zero tail the cave uses; "
          "patches 14 and 15 do the same)")
    work = sys.argv[2] + ".mapped.tmp"
    open(work, "wb").write(data)
    try:
        apply(work, sys.argv[2], build(device))
    finally:
        os.remove(work)
