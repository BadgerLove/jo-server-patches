"""Undo the original patch 04 ("2 GB memory cap") on an exe that carries it.

The original patch 04 raised four immediates from 0x20000000 to 0x80000000
believing they were a 512 MB heap cap. They are a D3DX shader flag, an
event-trigger constant, a camera angle clamp and a minimap colour, and none of
them is memory. This tool puts all four back to retail so the real arena patch
(patch_fastmem_arena.py) can be applied on a clean base. Every JOexeFIX v3 exe
is a v2 exe run through this script and then patch_fastmem_arena.py.

  VA 0x69813B : mov eax, imm32            D3DX shader texture-type flag
  VA 0x453CC6 : mov eax, imm32            event-trigger constant
  VA 0x4DE56E : mov dword [0x00B764A8]    camera angle clamp (0x20000000 = 45 deg)
  VA 0x5D1332 : mov dword [0x02BE0F78]    minimap colour

Each site must currently hold 0x80000000; a retail or already-reverted file is
refused. Full write-up: docs/patches/04-memory-2gb.md

Usage:  python revert_memory_2gb.py <in.exe> <out.exe>
"""
from patch_util import Patch, main

PATCHED = bytes.fromhex("00000080")   # 0x80000000 little-endian, as left by the original patch 04
RETAIL = bytes.fromhex("00000020")    # 0x20000000 little-endian, retail 1.7.5.7

PATCHES = [
    Patch(va=0x69813B, old=PATCHED, new=RETAIL, note="D3DX shader flag"),
    Patch(va=0x453CC6, old=PATCHED, new=RETAIL, note="event-trigger constant"),
    Patch(va=0x4DE56E, old=PATCHED, new=RETAIL, note="camera angle clamp [0x00B764A8]"),
    Patch(va=0x5D1332, old=PATCHED, new=RETAIL, note="minimap colour [0x02BE0F78]"),
]

if __name__ == "__main__":
    main(PATCHES, __doc__)
