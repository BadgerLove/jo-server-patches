"""Spectator chat relay + Kill List crash fix (server).

Two server-side changes, both about spectators:

  K  Kill List crash fix (ONE byte).  Stock clients crash (SYSDUMP at 0x423D64,
     read of address 0x162) drawing the scoreboard when a spectator's row has no
     entity behind it, e.g. the spectator just left.  The server stops sending
     the "spectator" bit in scoreboard rows, so every client takes the normal
     row path, which checks for a null entity.  Helps every stock client.
     `--crash-fix-only` applies just this byte.

  S  Spectator chat relay.  A spectator's chat packet is normally dropped by the
     server mid-round.  With this patch a spectator may send channel 1 (everyone)
     always, and channel 2 (own team) only when their team byte is not 1/2, so a
     real spectator's team chat reaches other spectators, never a playing team.
     The relayed line carries sender index 0xFF (the same value the server
     console uses) so stock clients cannot resolve the sender and do not drop
     it; the name is already in the text ("Name: hello").  The spectator needs
     the client side (patch 13) to type in the first place.
     Cost: players cannot scoreboard-mute a spectator.

Changes (all asserted before writing):
  PE     `_text` VirtualSize 0x2AA10 -> 0x2B000 (cave in its zero tail; section is RWX)
  cave   VA 0x7BFA20..0x7BFAC6 four stubs (gate / write / dispatch / exit), flag dword at 0x7BFCF0
  K      VA 0x504C2B  and dl,1 -> and dl,0        (NetPacket_SerializeScoreboard0x16)
  S  G   VA 0x5137C7  22 B spectator gate -> jmp gate stub + nops   (chat handler)
  S  W   VA 0x5047A0  prologue -> jmp write stub  (NetPacket_WriteTwoBytesAndCString)
  S  D   VA 0x42B910  prologue -> jmp dispatch stub (Chat_DispatchToChannel, server's own copy)
  S  X   VA 0x51416D  shared handler exit -> jmp exit stub (clears the flag)

Full write-up: docs/patches/14-spectator-chat-server.md

Usage:  python patch_spectator_server.py <in_server.exe> <out.exe> [--crash-fix-only]
Base:   the combined server build (arena + 125 FPS lock + admin fix + NWU) ->
        sha256 a3e314f6... ; the asserts also hold on a stock 1.7.5.7 server exe.
"""
import struct
import sys

from patch_util import sha256, va_to_offset

CAVE = 0x7BFA20
CAVE_END = 0x7BFD00
FLAG = 0x7BFCF0

# Pre-assembled stubs at 0x7BFA20 (gate 76 B), 0x7BFA70 (write 24 B), 0x7BFA90
# (dispatch 24 B), 0x7BFAB0 (exit 23 B); zero padding between.  Source in the doc.
STUBS = bytes.fromhex(
    "80bed7880100007439833d28194c0200753083bc243c050000017c2b8a073c0174163c0275218b0685c0"
    "741b8a8062010000fec83c01760fc705f0fc7b0001000000e9763dd5ffe9f946d5ff00000000"
    "833df0fc7b00007405c644240cff8b44240855e91d4dd4ff0000000000000000"
    "833df0fc7b00007405c6442404ff0fb6442404e96dbec6ff0000000000000000"
    "c705f0fc7b00000000005f31e1e8b9affaffe9ae46d5ff"
)
assert len(STUBS) == 0xA7


def _sections(d):
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    n = struct.unpack_from("<H", d, pe + 6)[0]
    opt = struct.unpack_from("<H", d, pe + 20)[0]
    base = struct.unpack_from("<I", d, pe + 52)[0]
    for i in range(n):
        o = pe + 24 + opt + i * 40
        vs, va, rs, ro = struct.unpack_from("<IIII", d, o + 8)
        yield d[o:o + 8].rstrip(b"\0"), o, base + va, vs, rs, ro


def build(in_path, out_path, crash_fix_only=False):
    d = bytearray(open(in_path, "rb").read())
    print(f"input  {in_path}\n       sha256 {sha256(bytes(d))}")
    o = lambda va: va_to_offset(bytes(d), va)

    def put(va, old, new, note):
        p = o(va)
        assert d[p:p + len(old)] == old, f"{va:#x} ({note}): found {bytes(d[p:p+len(old)]).hex()} want {old.hex()}"
        d[p:p + len(new)] = new
        print(f"  patched VA {va:#08x} {old.hex()} -> {new.hex()}  {note}")

    # K: never send the spectator bit in scoreboard rows
    put(0x504C2B, bytes.fromhex("80e201"), bytes.fromhex("80e200"), "K Kill List crash fix")

    if not crash_fix_only:
        txt = [s for s in _sections(d) if s[0] == b"_text"]
        assert len(txt) == 1, "no _text section"
        _name, hdr, sva, vs, rs, _ro = txt[0]
        assert sva == 0x795000 and vs == 0x2AA10 and rs == 0x2B000, (hex(sva), hex(vs), hex(rs))
        ch = struct.unpack_from("<I", d, hdr + 36)[0]
        assert ch & 0xE0000000 == 0xE0000000, f"_text not RWX: {ch:#x}"
        struct.pack_into("<I", d, hdr + 8, 0x2B000)
        co = o(CAVE)
        assert d[co - 0x10:o(CAVE_END)] == b"\0" * (CAVE_END - CAVE + 0x10), "cave not empty"
        d[co:co + len(STUBS)] = STUBS

        gate, write, dispatch, exit_ = 0x7BFA20, 0x7BFA70, 0x7BFA90, 0x7BFAB0
        jmp = lambda frm, to: b"\xe9" + struct.pack("<i", to - (frm + 5))
        put(0x5137C7, bytes.fromhex("80bed788010000740d833d28194c02000f8488090000"),
            jmp(0x5137C7, gate).ljust(22, b"\x90"), "S-G spectator gate")
        put(0x5047A0, bytes.fromhex("8b44240855"), jmp(0x5047A0, write), "S-W sender index 0xFF on the wire")
        put(0x42B910, bytes.fromhex("0fb6442404"), jmp(0x42B910, dispatch), "S-D sender index 0xFF, server copy")
        put(0x51416D, bytes.fromhex("5f33cce806692500"), jmp(0x51416D, exit_).ljust(8, b"\x90"), "S-X clear flag on exit")

    open(out_path, "wb").write(d)
    print(f"output {out_path}\n       sha256 {sha256(bytes(d))}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--crash-fix-only"]
    if len(args) != 2:
        sys.exit(__doc__)
    build(args[0], args[1], crash_fix_only="--crash-fix-only" in sys.argv)
