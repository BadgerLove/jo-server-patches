"""Raise the FastMem arena (the real mission-memory cap) from 192 MB.

Joint Operations keeps all mission data in one fixed-size arena reserved by
`FastMem_Init`. Its size is a single global, `dwSize` = [0x03342E7C], written
once at start-up in `Game_ParseCommandLineAndInit`:

  VA 0x4A7CDD : mov dword [0x03342E7C], 0x0C000000    (192 MB)
                imm32 at VA 0x4A7CE3 (file 0xA7CE3)

The SYSDUMP line `Memory Usage  Allocated:0C000000h` prints this global, and
"Mission is too large / Remove some object types and re-export" fires when
dwSize minus used bytes drops under 12 MB. This one immediate is the cap.

Sizes:
  512 MB (default)  0x20000000  proven: onHook has rewritten the live FMJ
                                server to this value at runtime since 2026
  1 GB  (--size 1024) 0x40000000 optional; needs Large Address Aware and a
                                64-bit host, and is the practical ceiling
  1920 MB (--size 1920) 0x78000000 EXPERIMENTAL. Largest size a 32-bit LAA
                                process can reserve; the arena lands above the
                                2 GB address line, where signed pointer maths
                                may break. Untested in play.
  2 GB  is NOT offered. Measured: a 32-bit LAA process fails to reserve 2047 MB
        or more, and the allocator treats the size as signed. 0x80000000 is a
        guaranteed start-up crash.

Pair with patch_large_address_aware.py. If the exe is run under onHook
(binkw32.dll proxy), read onhook.log first: onHook locates this same site by
byte pattern and rewrites it to 512 MB itself.

Full write-up: docs/patches/04-memory-2gb.md (replaces the original patch 04;
revert_memory_2gb.py undoes that one first on a v1/v2 JOexeFIX exe)

Usage:  python patch_fastmem_arena.py <in.exe> <out.exe> [--size 512|1024|1920]
"""
import sys

from patch_util import Patch, apply

ARENA_IMM_VA = 0x4A7CE3                 # imm32 of `mov dword [0x3342E7C], imm32`
OLD = (0x0C000000).to_bytes(4, "little")  # 192 MB, retail 1.7.5.7

SIZES = {
    512:  (0x20000000).to_bytes(4, "little"),
    1024: (0x40000000).to_bytes(4, "little"),
    1920: (0x78000000).to_bytes(4, "little"),   # experimental, see docstring
}


def build_patches(size_mb: int) -> list:
    if size_mb not in SIZES:
        sys.exit(f"--size must be one of {sorted(SIZES)} (MB); 2048 is deliberately unsupported")
    return [Patch(va=ARENA_IMM_VA, old=OLD, new=SIZES[size_mb],
                  note=f"FastMem arena dwSize [0x3342E7C]: 192 MB -> {size_mb} MB")]


def main() -> None:
    args = list(sys.argv[1:])
    size_mb = 512
    if "--size" in args:
        i = args.index("--size")
        try:
            size_mb = int(args[i + 1])
        except (IndexError, ValueError):
            sys.exit(__doc__)
        del args[i:i + 2]
    if len(args) != 2:
        sys.exit(__doc__)
    apply(args[0], args[1], build_patches(size_mb))


if __name__ == "__main__":
    main()
