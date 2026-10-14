"""Berserk ignores its own kind (host).  Berserk creatures stop attacking each other.

A creature placed with Nile's "Berserk" tick (AI slot +0x04 bit 0x200) attacks
anyone, whatever its team.  The target scan in `Entity_FindTargets @0x53A610`
skips the ordinary team filter for a berserk candidate or a berserk scanner, so
four berserk sharks on team 0 hunt the players AND each other.

This patch adds one test to that berserk exception: when the scanner and the
candidate have the same item definition ([entity+0x20], one items.def row per
kind: every Shark shares one, every Tiger another), the exception does not
apply and the ordinary team filter decides instead.  Team-0 sharks therefore
ignore each other; a berserk tiger still attacks a tiger on the other team,
as any soldier would.  Players (never berserk), different creatures and
non-berserk AI are unchanged.

Changes (all asserted before writing):
  leg  VA 0x53A7EA  (36 B) the two berserk tests re-packed in place
                    (test byte [eax+5],2 == test dword [eax+4],0x200),
                    both "berserk" exits now jump to the cave
  cave VA 0x726026  (25 B of int3 padding after patch 12's stub at 0x726015;
                    patch 16 starts at 0x7260D6, so no overlap)

The AI think runs on the host only (server, or the player hosting "serve and
play"), so only the host exe needs this; clients need nothing.

Usage:  python patch_berserk_kin.py <in.exe> <out.exe>
Base:   a stock 1.7.5.7 exe or any build from this repo (server or client).
"""
import struct

from patch_util import Patch, main

LEG, TEAM_FILTER, ELIGIBLE = 0x53A7EA, 0x53A80E, 0x53A82A
CAVE = 0x726026
INT3 = b"\xcc"

ORIG_LEG = bytes.fromhex(
    "8b466885c07409f7400400020000753085d274108b426885c07409f7400400020000751c")


def rel(src_next, dst):
    return struct.pack("<i", dst - src_next)


def short(src_next, dst):
    d = dst - src_next
    assert -128 <= d <= 127, (hex(src_next), hex(dst))
    return struct.pack("<b", d)


def build_patches() -> list[Patch]:
    k = LEG + 30                                          # "berserk": jmp cave
    a = bytearray()
    a += bytes.fromhex("8b4668")                          # mov eax,[esi+0x68]   candidate AI slot
    a += bytes.fromhex("85c0")                            # test eax,eax
    a += b"\x74" + short(LEG + len(a) + 2, LEG + 13)      # je scanner test
    a += bytes.fromhex("f6400502")                        # test byte [eax+5],2  candidate berserk
    a += b"\x75" + short(LEG + len(a) + 2, k)             # jne k
    a += bytes.fromhex("85d2")                            # test edx,edx         scanner
    a += b"\x74" + short(LEG + len(a) + 2, TEAM_FILTER)
    a += bytes.fromhex("8b4268")                          # mov eax,[edx+0x68]   scanner AI slot
    a += bytes.fromhex("85c0")                            # test eax,eax
    a += b"\x74" + short(LEG + len(a) + 2, TEAM_FILTER)
    a += bytes.fromhex("f6400502")                        # test byte [eax+5],2  scanner berserk
    a += b"\x74" + short(LEG + len(a) + 2, TEAM_FILTER)
    a += b"\xe9" + rel(LEG + len(a) + 5, CAVE)            # k: jmp cave
    a += b"\x90"
    c = bytearray()
    e = CAVE + 20
    c += bytes.fromhex("85d2")                            # test edx,edx         no scanner: retail
    c += b"\x74" + short(CAVE + len(c) + 2, e)
    c += bytes.fromhex("8b4620")                          # mov eax,[esi+0x20]   candidate item def
    c += bytes.fromhex("85c0")                            # test eax,eax
    c += b"\x74" + short(CAVE + len(c) + 2, e)
    c += bytes.fromhex("3b4220")                          # cmp eax,[edx+0x20]   same kind?
    c += b"\x0f\x84" + rel(CAVE + len(c) + 6, TEAM_FILTER)  # je ordinary team filter
    c += b"\xe9" + rel(CAVE + len(c) + 5, ELIGIBLE)       # e: jmp eligible (retail berserk)
    assert len(a) == len(ORIG_LEG) and CAVE + 20 + 5 == CAVE + len(c)
    return [
        Patch(CAVE, INT3 * len(c), bytes(c), "cave: same item definition? -> team filter"),
        Patch(LEG, ORIG_LEG, bytes(a), "berserk leg re-packed, exits to the cave"),
    ]


if __name__ == "__main__":
    main(build_patches(), __doc__)
