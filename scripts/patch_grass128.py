"""Extend grass draw distance and density to 128 m (client, visual only).

Retail collects grass out to 42 m with a small per-definition vertex budget.
This patch raises the collection radius to 128 m, moves the fade band out to
64-128 m, lifts the vertex-buffer budget so denser grass fits, and adds a small
per-frame bound (via a code cave) so a sudden burst of new grass cells cannot
overflow the slot pool.

This is a client cosmetic change. It does not affect gameplay, hitboxes, or the
server. Players on a stock client simply see the normal short grass.

Changes (all asserted before writing):
  radius 42 -> 128 m                     .rdata float at VA 0x7DEA3C
  fade start -> 64 m (redirect operand)  code at VA 0x60A45D
  fade slope -> 1/(128-64)               .rdata float at VA 0x7DF1BC
  vertex budget 0xFFFF -> 0x3FFFFF x4    code at VA 0x5FF963/73/83/93
  per-frame new-cell bound (<=64)        hook VA 0x601BC5 into cave VA 0x7472D0

Full write-up: docs/patches/10-grass-128m.md

Usage:  python patch_grass128.py <in_client_LAA.exe> <out.exe>
Base:   stock Joint Ops 1.7.5.7 client with the LAA flag set.
"""
import struct
import sys

from patch_util import sha256, va_to_offset

RADIUS_M = 128.0
FADE_START_M = 64.0
FADE_END_M = 128.0
FADE_START_RDATA_VA = 0x7C3DD0     # an existing 64.0f constant in .rdata
VB_BUDGET = 0x3FFFFF               # retail 0xFFFF
HOOK = 0x601BC5
BACK = 0x601BD0
CAVE = 0x7472D0                    # int3 padding after a 'ret 0Ch'


def build(in_path, out_path):
    d = bytearray(open(in_path, "rb").read())
    print(f"input  {in_path}\n       sha256 {sha256(bytes(d))}")
    o = lambda va: va_to_offset(bytes(d), va)

    # 1. collection radius 42 -> 128
    p = o(0x7DEA3C)
    assert d[p:p + 4] == struct.pack("<f", 42.0), "radius const mismatch"
    d[p:p + 4] = struct.pack("<f", RADIUS_M)

    # 2. fade start: redirect the fld operand to a shared 64.0f
    p = o(0x60A45D)
    assert d[p:p + 6] == bytes.fromhex("d905608e7d00"), "fade-start fld mismatch"
    assert struct.unpack_from("<f", d, o(FADE_START_RDATA_VA))[0] == FADE_START_M
    struct.pack_into("<I", d, p + 2, FADE_START_RDATA_VA)

    # 3. fade slope (single-xref constant)
    p = o(0x7DF1BC)
    assert d[p:p + 4] == struct.pack("<f", 1 / 22), "fade-slope const mismatch"
    d[p:p + 4] = struct.pack("<f", 1 / (FADE_END_M - FADE_START_M))

    # 4. vertex-buffer budget x4
    for va in (0x5FF963, 0x5FF973, 0x5FF983, 0x5FF993):
        p = o(va)
        assert d[p:p + 6] == bytes.fromhex("81f9ffff0000"), hex(va)
        struct.pack_into("<I", d, p + 2, VB_BUDGET)

    # 5. per-frame new-key bound via code cave
    ph = o(HOOK)
    assert d[ph:ph + 11] == bytes.fromhex("3bc57507897cac2083c501"), "hook mismatch"
    pc = o(CAVE)
    assert d[pc:pc + 24] == b"\xcc" * 24, "cave not free"
    cave = bytes.fromhex(
        "3bc5"        # cmp eax,ebp
        "750c"        # jne L
        "83fd40"      # cmp ebp,64
        "7d07"        # jge L
        "897cac20"    # mov [esp+ebp*4+0x20],edi
        "83c501"      # add ebp,1
    )
    cave += b"\xe9" + struct.pack("<i", BACK - (CAVE + len(cave) + 5))   # L: jmp BACK
    d[pc:pc + len(cave)] = cave
    d[ph:ph + 5] = b"\xe9" + struct.pack("<i", CAVE - (HOOK + 5))         # jmp CAVE

    open(out_path, "wb").write(d)
    print(f"output {out_path}\n       sha256 {sha256(bytes(d))}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    build(sys.argv[1], sys.argv[2])
