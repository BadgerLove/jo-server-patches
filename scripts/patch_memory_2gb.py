"""Raise the server/client heap cap from 512 MB to 2 GB.

The 512 MB limit is written in four places: two `mov eax, imm32` loads (the
connection-speed profile table and a config lookup) and two `mov dword [mem],
imm32` global heap stores. Changing only the profile table (as earlier attempts
did) does nothing, because the globals set 512 MB independently. All four must
move together.

Each site's 32-bit immediate is 0x20000000 (512 MB) and becomes 0x80000000
(2 GB). Stored little-endian, that is the dword `00 00 00 20` -> `00 00 00 80`;
only the high byte changes. The VAs below point at the immediate itself, which
was verified by disassembly:

  VA 0x69813B : mov eax, imm32           (connection-speed profile table)
  VA 0x453CC6 : mov eax, imm32           (config lookup)
  VA 0x4DE56E : mov dword [0x00B764A8]   (global heap store 1)
  VA 0x5D1332 : mov dword [0x02BE0F78]   (global heap store 2)

To actually use the larger address space the executable must also be Large
Address Aware: run patch_large_address_aware.py as well.

The SYSDUMP "Allocated:" line reads a separate display variable and is not
touched here, so it may still report the old figure while the real heap is 2 GB.

Full write-up: docs/patches/04-memory-2gb.md

Usage:  python patch_memory_2gb.py <in.exe> <out.exe>
"""
from patch_util import Patch, main

OLD = bytes.fromhex("00000020")   # 0x20000000 little-endian = 512 MB
NEW = bytes.fromhex("00000080")   # 0x80000000 little-endian = 2 GB

PATCHES = [
    Patch(va=0x69813B, old=OLD, new=NEW, note="connection-speed profile table"),
    Patch(va=0x453CC6, old=OLD, new=NEW, note="config lookup"),
    Patch(va=0x4DE56E, old=OLD, new=NEW, note="global heap store 1 [0x00B764A8]"),
    Patch(va=0x5D1332, old=OLD, new=NEW, note="global heap store 2 [0x02BE0F78]"),
]

if __name__ == "__main__":
    main(PATCHES, __doc__)
