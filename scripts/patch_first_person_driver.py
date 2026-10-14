"""First person in vehicles from game.cfg (server).  Makes `mp_3rdperson_driver = 0` work.

The game reads `mp_3rdperson_driver` from game.cfg and saves it back
(variable 0x2550CA0), but nothing ever uses it, so 0 never locks anyone to
first person.  Every client already has the lock: while alive, its camera is
forced to first person when the session rules word has bit 0x40.  That word
is built by the host at every mission start from its `mpattrib` (0x2550A04)
and sent to every player; nothing ever sets bit 0x40.

This patch sends the host's `mov eax, [mpattrib]` (0x51E94D, in
`CNapiGameSession_InitRandomSeedOrRequest`) to a 25-byte cave that sets bit
0x40 when mp_3rdperson_driver is 0 and clears it otherwise, so the game.cfg
line alone decides.  mpattrib itself is never written.

Changes (all asserted before writing):
  site VA 0x51E94D  mov eax,[0x2550A04]  -> jmp cave
  cave VA 0x7BFF40  (25 B in the zero tail of `_text`)
  PE   `_text` VirtualSize 0x2AA10 -> 0x2B000, if patches 14/15/19/20 have not done it

AFTER PATCHING set this in the server's game.cfg (server stopped):
  mp_3rdperson_driver = 0     players locked to first person in vehicles
  mp_3rdperson_driver = 1     third person allowed (the game's normal)
It is read at each map start.  Only the server needs it; stock clients obey.

Usage:  python patch_first_person_driver.py <in_server.exe> <out.exe>
"""
import os
import struct
import sys

from patch_long_chat import _map_cave_tail
from patch_util import Patch, apply

SITE, RESUME = 0x51E94D, 0x51E952
MPATTRIB, DRIVER = 0x2550A04, 0x2550CA0
CAVE = 0x7BFF40
FORCE_FIRST_PERSON = 0x40


def build() -> list[Patch]:
    c = bytearray()
    c += b"\xa1" + struct.pack("<I", MPATTRIB)                    # mov eax,[mpattrib]
    c += bytes([0x83, 0xE0, ~FORCE_FIRST_PERSON & 0xFF])          # and eax,~40h
    c += b"\x83\x3d" + struct.pack("<I", DRIVER) + b"\x00"         # cmp dword [driver],0
    c += b"\x75\x03"                                              # jne: third person allowed
    c += bytes([0x83, 0xC8, FORCE_FIRST_PERSON])                  # or eax,40h
    c += b"\xe9" + struct.pack("<i", RESUME - (CAVE + len(c) + 5))  # jmp back
    assert len(c) == 25
    return [
        Patch(CAVE, bytes(len(c)), bytes(c), "cave: rules bit 0x40 from mp_3rdperson_driver"),
        Patch(SITE, b"\xa1" + struct.pack("<I", MPATTRIB),
              b"\xe9" + struct.pack("<i", CAVE - (SITE + 5)), "rules word load -> cave"),
    ]


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    data = bytearray(open(sys.argv[1], "rb").read())
    if not _map_cave_tail(data):
        apply(sys.argv[1], sys.argv[2], build())
    else:
        print("_text VirtualSize 0x2AA10 -> 0x2B000 (maps the zero tail the cave uses)")
        work = sys.argv[2] + ".mapped.tmp"
        open(work, "wb").write(data)
        try:
            apply(work, sys.argv[2], build())
        finally:
            os.remove(work)
    print("Now set mp_3rdperson_driver = 0 in the server's game.cfg to lock first person in vehicles.")
