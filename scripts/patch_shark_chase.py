"""Shark chase (host).  Sharks swim at players in deep water, and never chase onto land.

Joint Ops has no idea what a sea creature is.  Sharks use the same AI as soldiers
and tigers (org1), and its approach step only moves an AI towards its target when
`Entity_CheckGroundHeightAtPosition @0x4AFF70` says the TARGET has solid ground
no more than 3 m below it (the water surface does not count).  A player swimming
over deep water fails that, so sharks just circle; a player standing in the
shallows passes, so sharks charge and beach themselves.

This patch sends that one call (in `Entity_UpdateInfantryAI`, the approach step
at 0x4BC2C2..0x4BC31A) to a small check first:
  - the thinking AI's item name (item definition at [esi+0x20]) starts "Shar"
      -> chase only if the water under the target is deeper than --depth metres
         (default 2): ground(target) + depth - water height < 0
  - anything else -> the original 0x4AFF70, unchanged (soldiers, players,
    tigers, zombies, custom creatures...)

Changes (all asserted before writing):
  site   VA 0x4BC2E9  call 0x4AFF70            -> call cave A
  cave A VA 0x7260D6  (41 B of int3 padding 0x7260D5..0x7260FF; 0x726015 is patch 12)
  cave B VA 0x4AFFE1  (12 B of the int3 padding after 0x4AFF70)

The AI think runs on the host only (server, or the player hosting "serve and
play"), so only the host exe needs this; clients need nothing.  Sharks also need
min engagement < max engagement to approach at all (Nile / WAC `SSNMin`).
For a configurable list of creatures (and land-and-water ones), use the onHook
version.

Usage:  python patch_shark_chase.py <in.exe> <out.exe> [--depth METRES]
Base:   a stock 1.7.5.7 exe or any build from this repo (server or client).
"""
import struct
import sys

from patch_util import Patch, apply

SITE, ORIG_CHECK, GROUND, WATER = 0x4BC2E9, 0x4AFF70, 0x457230, 0x26C6454
CAVE_A, CAVE_B = 0x7260D6, 0x4AFFE1
INT3 = b"\xcc"


def rel(src_next, dst):
    return struct.pack("<i", dst - src_next)


def build_patches(depth_m: float = 2.0) -> list[Patch]:
    depth = int(round(depth_m * 65536))
    a = bytearray()
    a += bytes.fromhex("8b4620")                          # mov eax,[esi+0x20]   item definition
    a += bytes.fromhex("8138") + b"Shar"                  # cmp dword [eax],'Shar'
    a += b"\x0f\x85" + rel(CAVE_A + len(a) + 6, ORIG_CHECK)  # jne original check
    a += bytes.fromhex("6a016a00")                        # push 1 / push 0
    a += bytes.fromhex("ff742410")                        # push [esp+0x10]      target entity
    a += b"\xe8" + rel(CAVE_A + len(a) + 5, GROUND)       # call Entity_CalcAverageGroundHeight
    a += bytes.fromhex("83c40c")                          # add esp,0xC
    a += b"\x05" + struct.pack("<i", depth)               # add eax,depth
    a += b"\xe9" + rel(CAVE_A + len(a) + 5, CAVE_B)       # jmp cave B
    b = bytearray()
    b += b"\x2b\x05" + struct.pack("<I", WATER)           # sub eax,[water height]
    b += bytes.fromhex("c1f81f")                          # sar eax,31   -1 if deep enough
    b += bytes.fromhex("f7d8")                            # neg eax      1 = chase
    b += b"\xc3"                                          # ret
    assert len(a) == 41 and len(b) == 12
    return [
        Patch(CAVE_A, INT3 * len(a), bytes(a), "cave A: shark check + ground under target"),
        Patch(CAVE_B, INT3 * len(b), bytes(b), "cave B: deep enough? 1 : 0"),
        Patch(SITE, b"\xe8" + rel(SITE + 5, ORIG_CHECK), b"\xe8" + rel(SITE + 5, CAVE_A),
              "approach step's ground check -> cave A"),
    ]


if __name__ == "__main__":
    args = sys.argv[1:]
    depth = 2.0
    if "--depth" in args:
        i = args.index("--depth")
        depth = float(args[i + 1])
        del args[i:i + 2]
    if len(args) != 2 or not 0 < depth < 30:
        sys.exit(__doc__)
    apply(args[0], args[1], build_patches(depth))
