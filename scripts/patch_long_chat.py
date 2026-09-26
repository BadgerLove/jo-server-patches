"""Long server chat (server).  Admin CHAT SEND lines up to 118 characters.

Every outgoing chat line in Joint Ops is cut to 59 bytes by the flood check
(`Chat_CheckFloodControl @0x498F60` writes a 0 at message[59]), because the
flood ring keeps 64-byte copies and the send path strips tags into a 64-byte
stack buffer.  Proven live 2026-09-26: a 62-character CHAT SEND came back 59.

This patch lifts that for `Chat_SendTeamMessage @0x49A900` only, the function
the admin port's CHAT SEND uses, so server/tool messages can be longer.  Players'
own typing is untouched (their client cuts at 59 before it ever reaches us).
Receiving clients need nothing: incoming chat is shown straight from the packet,
kept up to 119 characters per line and word-wrapped.

Changes (all asserted before writing):
  cave   VA 0x7BFD00 (58 B)  flood wrapper: caps the line at 119 bytes, lets the
                             flood check run (it cuts at 59 and stores that in
                             its ring, which still fits its 64-byte slots), then
                             puts the byte at [59] back so the full line goes on
  cave   VA 0x7BFD40 (53 B)  strip wrapper: strips tags into a 256-byte buffer at
                             0x7BFE00, then leaves a safe 63-byte copy in the
                             caller's 64-byte stack buffer (the peer path uses it)
  site 1 VA 0x49A93B  call Chat_CheckFloodControl -> call flood wrapper
  site 2 VA 0x49A971  call Chat_StripHtmlTags     -> call strip wrapper
  site 3 VA 0x49A9DC  lea ecx,[esp+4] / push ecx  -> push 0x7BFE00  (the line
                             that goes on the wire comes from the big buffer)

Coexists with patch 14 (stubs 0x7BFA20..0x7BFAC6, flag 0x7BFCF0): nothing here
overlaps, and the network write still passes through its 0x5047A0 hook.

Limits that remain: the admin port splits a command into at most 25 words, so
CHAT SEND carries at most 23; the admin handler's message buffer is 122 bytes,
so keep lines to 118 characters (the handler adds a trailing space).

Usage:  python patch_long_chat.py <in_server.exe> <out.exe> [--colour]
        --colour also keeps <cRRGGBB> colour tags in the line players receive.
Base:   a stock 1.7.5.7 server exe or any build from this repo; with or without
        patch 14 (if 14 is not there, this maps the same section tail it does).
"""
import os
import struct
import sys

from patch_util import Patch, apply

FLOOD = bytes.fromhex(
    "56538b74240c89f1803900740341ebf829f183f9777604c646770031db83f93b76058a5e3b"
    "b70156e83392cdff83c40484ff7403885e3b5b5ec3"
)
STRIP = bytes.fromhex(
    "56578b442410506800fe7b00e89f86cdff83c408be00fe7b008b7c240cb93f0000008a0688"
    "0784c0740846474975f3c607005f5ec3"
)
assert len(FLOOD) == 58 and len(STRIP) == 53

PATCHES = [
    Patch(0x7BFD00, bytes(len(FLOOD)), FLOOD, "flood wrapper cave"),
    Patch(0x7BFD40, bytes(len(STRIP)), STRIP, "strip wrapper cave"),
    Patch(0x7BFE00, bytes(0x100), bytes(0x100), "256-byte line buffer (must be free)"),
    Patch(0x49A93B, bytes.fromhex("e820e6ffff"), bytes.fromhex("e8c0533200"), "call flood wrapper"),
    Patch(0x49A971, bytes.fromhex("e87adaffff"), bytes.fromhex("e8ca533200"), "call strip wrapper"),
    Patch(0x49A9DC, bytes.fromhex("8d4c240451"), bytes.fromhex("6800fe7b00"), "send the big buffer"),
]

# --colour: send the line as typed, tags included (push esi = the message),
# instead of the tag-stripped copy.  Clients draw chat with the same routine
# WAC ptext uses (Chat_AddMessageChannel1), which renders <cRRGGBB>, so public
# chat from the server gets colours with no client change.  Players cannot
# inject tags: their own client strips before sending and their lines are
# relayed by a different path.
COLOUR_SITE = Patch(0x49A9DC, bytes.fromhex("8d4c240451"), bytes.fromhex("5690909090"),
                    "send the line as typed (colour tags kept)")

TEXT2_VA, TEXT2_RAW = 0x795000, 0x2B000
TEXT2_STOCK_VS = 0x2AA10


def _map_cave_tail(data: bytearray) -> bool:
    """The caves live in the zero tail of the `_text` section.  Patch 14 maps
    it (VirtualSize 0x2AA10 -> 0x2B000); on an exe without patch 14 do the
    same here, after the same checks.  True if the header was changed."""
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    count = struct.unpack_from("<H", data, pe + 6)[0]
    first = pe + 24 + struct.unpack_from("<H", data, pe + 20)[0]
    image_base = struct.unpack_from("<I", data, pe + 24 + 28)[0]
    for i in range(count):
        hdr = first + i * 40
        if data[hdr:hdr + 8].rstrip(b"\0") != b"_text":
            continue
        vs, va, rs = struct.unpack_from("<III", data, hdr + 8)
        flags = struct.unpack_from("<I", data, hdr + 36)[0]
        if image_base + va != TEXT2_VA or rs != TEXT2_RAW or flags & 0xE0000000 != 0xE0000000:
            sys.exit("ABORT: the _text section is not the one this patch expects (wrong build).")
        if vs == TEXT2_RAW:
            return False                      # already mapped (patch 14)
        if vs != TEXT2_STOCK_VS:
            sys.exit(f"ABORT: unexpected _text VirtualSize {vs:#x} (wrong build).")
        struct.pack_into("<I", data, hdr + 8, TEXT2_RAW)
        return True
    sys.exit("ABORT: no _text section (wrong build).")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--colour"]
    if len(args) != 2:
        sys.exit("usage: python patch_long_chat.py <in_server.exe> <out.exe> [--colour]")
    patches = PATCHES[:-1] + [COLOUR_SITE] if "--colour" in sys.argv else PATCHES
    data = bytearray(open(args[0], "rb").read())
    if _map_cave_tail(data):
        print("_text VirtualSize 0x2AA10 -> 0x2B000 (maps the zero tail the caves use; "
              "patch 14 does the same)")
        work = args[1] + ".mapped.tmp"
        open(work, "wb").write(data)
        try:
            apply(work, args[1], patches)
        finally:
            os.remove(work)
    else:
        apply(args[0], args[1], patches)
