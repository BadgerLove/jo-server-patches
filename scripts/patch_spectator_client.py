"""Spectator HUD for casters (client): chat, name tags, health bars, chat send.

While spectating, a stock client hides the whole HUD (so no chat), never draws
name tags, and swallows the talk keys. This patch gives a spectator:

  A  chat visible      spectating sets HUD detail level 0 (as if F6 was pressed)
                       instead of 3, so incoming chat draws;
  B  name tags         NovaLogic's own tag drawer (HUD_DrawEntityLabel) is run for
                       every team-1/2 player and AI from a small code cave, coloured
                       blue/red by team, over the head, fading with distance;
  C  health bars       a bar under each tag (green > 66 %, yellow > 33 %, red) and a
                       percentage beside the player you have selected;
  D  chat send         the talk keys open the chat box while spectating and the
                       "all"/"team" senders no longer refuse to send.  The SERVER must
                       carry patch 14 for the line to reach anyone.

Client only.  Players on stock clients see nothing different.  Nothing here
changes gameplay, hitboxes or what the server sends.

Changes (all asserted before writing):
  PE     `_text` section VirtualSize 0x2AA10 -> 0x2B000 (the cave lives in its zero tail)
  cave   VA 0x7BFA20 tags loop (251 B), VA 0x7BFB20 bar drawer (441 B), VA 0x7BFCF0 "%d%%"
  A      VA 0x42E410  push 3 / mov [0x24D20BC],3  ->  push 0 / mov ...,0
  B      VA 0x5CAB95  call nullsub (0x44A4A0)     ->  call 0x7BFA20
  C      VA 0x5A426D  add esp,18h / test ebp,ebp  ->  jmp 0x7BFB20 (the cave redoes both)
  D      VA 0x49A6CA, 0x49A91A, 0x49B991  je -> jmp (three spectator guards)

Full write-up: docs/patches/13-spectator-hud-client.md

Usage:  python patch_spectator_client.py <in_client.exe> <out.exe>
Base:   stock Joint Ops 1.7.5.7 client (LAA or not); also applies cleanly on top of
        patch 10 (128 m grass).  Verified: grass-128 client -> sha256 e9a77dec...
"""
import struct
import sys

from patch_util import sha256, va_to_offset

CAVE = 0x7BFA20          # zero tail of the RWX '_text' section (VirtualSize ends 0x7BFA10)
CAVE_END = 0x7BFD00
TAGS_VA = 0x7BFA20
BAR_VA = 0x7BFB20
FMT_VA = 0x7BFCF0

# Pre-assembled x86 (position-dependent: assembled for the VAs above).  Source in
# the doc page; the loop reads the entity pool (0xA892E0/E4/E8) and the client
# player table ([0xA87048]: +0 count, +0x2C 64-byte slots, +0xD active, +0x24 entity).
TAGS = bytes.fromhex(
    "803dec60a800000f84ed000000833dbc204d02020f8de0000000f705341e4d02000400000f85d0000000"
    "60ff35c4184c02833dc4184c0200750ac705c4184c0202000000a1f460a800a310fa7b00c705f460a800"
    "000000008b35e092a8008b3de892a8008b2de492a80083ef01782f89f001eef740240001000075ee8a88"
    "62010000fec980f90177e13b05c85fb70074d96a0050e8f73edeff83c408ebcc8b1d4870a80085db7441"
    "8b7b2c85ff743a31f63b337d34807f0d0074268b472485c0741f8a9062010000feca80fa0177123b05c8"
    "5fb700740a5750e8b23edeff83c40883c60183c740ebc8a110fa7b00a3f460a8008f05c4184c0261c3"
)
BAR = bytes.fromhex(
    "83c418803dec60a800000f84a20100006083ec408b9c248801000053e85fbdc7ff83c4040fbfc883f901"
    "7d05b9010000000fbf831e01000085c07d0231c06bc06499f7f983f8647e05b8640000008904248bb424"
    "8000000083fe047d05be04000000897424288d3c76897c24040fafc7b96400000099f7f9894424088b84"
    "248400000089fad1fa29d08944240c8b84248800000001f0408944241089f099b905000000f7f983f802"
    "7d05b802000000894424148b44247025000000ff8944241889c2c1fa1889542424b900e00000833c2442"
    "7f10b900e0e000833c24217f05b90000e00009c1894c241cb92020200009c1894c242031ed3b6c24147d"
    "578b7c241001ef8b4424248b4c24208b54240c89d6037424045051575657526820144c02e88b3fe1ff83"
    "c41c8b74240885f67e218b54240c01d68b4424248b4c241c5051575657526820144c02e8623fe1ff83c4"
    "1c45eba33b1d10fa7b0075528b04248d4c24305068f0fc7b0051e855adfaff83c40c8b7424288b44240c"
    "0344240401f089f1d1f901c88b542414d1fa03542410d1fe29f28d4c2430ff74241c515250ffb424b400"
    "0000e8550adcff83c41483c4406185ede99945deff"
)
assert len(TAGS) == 251 and len(BAR) == 441


def _sections(d):
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    n = struct.unpack_from("<H", d, pe + 6)[0]
    opt = struct.unpack_from("<H", d, pe + 20)[0]
    base = struct.unpack_from("<I", d, pe + 52)[0]
    for i in range(n):
        o = pe + 24 + opt + i * 40
        vs, va, rs, ro = struct.unpack_from("<IIII", d, o + 8)
        yield d[o:o + 8].rstrip(b"\0"), o, base + va, vs, rs, ro


def build(in_path, out_path):
    d = bytearray(open(in_path, "rb").read())
    print(f"input  {in_path}\n       sha256 {sha256(bytes(d))}")

    # _text: VirtualSize 0x2AA10 -> 0x2B000 so the cave is inside the mapped image.
    txt = [s for s in _sections(d) if s[0] == b"_text"]
    assert len(txt) == 1, "no _text section"
    _name, hdr, sva, vs, rs, _ro = txt[0]
    assert sva == 0x795000 and vs == 0x2AA10 and rs == 0x2B000, (hex(sva), hex(vs), hex(rs))
    ch = struct.unpack_from("<I", d, hdr + 36)[0]
    assert ch & 0xE0000000 == 0xE0000000, f"_text not RWX: {ch:#x}"
    struct.pack_into("<I", d, hdr + 8, 0x2B000)
    o = lambda va: va_to_offset(bytes(d), va)

    co = o(CAVE)
    assert d[co - 0x10:o(CAVE_END)] == b"\0" * (CAVE_END - CAVE + 0x10), "cave not empty"
    d[o(TAGS_VA):o(TAGS_VA) + len(TAGS)] = TAGS
    d[o(BAR_VA):o(BAR_VA) + len(BAR)] = BAR
    d[o(FMT_VA):o(FMT_VA) + 5] = b"%d%%\0"

    def put(va, old, new, note):
        p = o(va)
        assert d[p:p + len(old)] == old, f"{va:#x} ({note}): found {bytes(d[p:p+len(old)]).hex()} want {old.hex()}"
        d[p:p + len(new)] = new
        print(f"  patched VA {va:#08x} {old.hex()} -> {new.hex()}  {note}")

    # A: spectate sets HUD level 0 instead of 3
    put(0x42E410, bytes.fromhex("6a03c705bc204d0203000000"), bytes.fromhex("6a00c705bc204d0200000000"), "A chat visible")
    # B: spectator frame's spare nullsub call -> tags cave
    put(0x5CAB95, bytes.fromhex("e806f9e7ff"), b"\xe8" + struct.pack("<i", TAGS_VA - (0x5CAB95 + 5)), "B name tags")
    # C: after the tag text is drawn -> bar cave (which redoes add esp,18h / test ebp,ebp)
    put(0x5A426D, bytes.fromhex("83c41885ed"), b"\xe9" + struct.pack("<i", BAR_VA - (0x5A426D + 5)), "C health bars")
    # D: chat send - three 'je' spectator guards become 'jmp'
    put(0x49A6CA, bytes.fromhex("740d833d28194c02"), bytes.fromhex("eb0d833d28194c02"), "D team sender")
    put(0x49A91A, bytes.fromhex("740d833d28194c02"), bytes.fromhex("eb0d833d28194c02"), "D all sender")
    put(0x49B991, bytes.fromhex("740d833d28194c02"), bytes.fromhex("eb0d833d28194c02"), "D talk-key handler (opens the box)")

    open(out_path, "wb").write(d)
    print(f"output {out_path}\n       sha256 {sha256(bytes(d))}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    build(sys.argv[1], sys.argv[2])
