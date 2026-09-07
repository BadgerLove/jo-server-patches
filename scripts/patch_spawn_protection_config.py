"""Make spawn protection configurable from game.cfg (no rebuild per duration).

After patching, add to game.cfg:      e_spawn_protection = 5      (seconds)
0, negative or absent = retail 9.92 s. The server echoes the line back when it
rewrites game.cfg, so the value survives restarts.

Mechanism (see docs/patches/12-spawn-protection-config.md):
  * the client-only `enable_keyboardtips` config key is repurposed: its parser
    literal and its writer format string are renamed in place.  THE NEW NAME
    MUST START WITH 'e' - the settings parser switches on the first letter
    before comparing names, and this comparison lives under case 'e'.
  * the defaults routine's `mov [key], 1` is NOPed so an absent line = 0 = retail.
  * a 17-byte GET routine in int3 padding: edi = [key] * 62; if edi <= 0 -> 620.
  * three 14-byte stubs (one per destination register) in int3 padding:
        push edi; call GET; mov [reg+0x124], edi; pop edi; ret
  * the six 10-byte `mov dword [reg+0x124], 620` sites become `call stub` + 5 NOPs.

Apply to a RETAIL-valued exe (spawn protection still 620 at all six sites). If
you already applied patch 03 (fixed duration), start again from an unpatched
copy; the two patches touch the same sites.

Server-side only. Clients need nothing.

Usage:  python patch_spawn_protection_config.py <in.exe> <out.exe>
"""
import struct
import sys

from patch_util import Patch, apply

KEY = b"e_spawn_protection"        # must start with 'e', at most 19 chars
CFG_GLOBAL = 0x2550844             # the repurposed enable_keyboardtips int
GET = 0x726015                     # 17 bytes of int3 padding
STUB = 0x7472C9                    # 3 x 14 bytes of int3 padding
PARSER_LITERAL = 0x7D477C          # "enable_keyboardtips\0"
WRITER_FORMAT = 0x7D3B90           # "enable_keyboardtips  = %i\n\0"
DEFAULT_STORE = 0x54D13B           # mov [CFG_GLOBAL], esi   (esi == 1)
SITES = {0x516BBA: "ecx", 0x517937: "eax", 0x517952: "ecx",
         0x517960: "edx", 0x519FE7: "eax", 0x51A882: "eax"}
MODRM = {"eax": 0x80, "ecx": 0x81, "edx": 0x82}
STORE = {"eax": "89b824010000", "ecx": "89b924010000", "edx": "89ba24010000"}
STOCK_TICKS = 620
TICKS_PER_SECOND = 62
NOP = b"\x90"
INT3 = b"\xcc"

OLD_KEY = b"enable_keyboardtips"
OLD_FMT = OLD_KEY + b"  = %i\n"
assert KEY[:1].lower() == b"e" and len(KEY) <= len(OLD_KEY)
NEW_KEY = KEY.ljust(len(OLD_KEY), b"\0")
NEW_FMT = KEY + b" " * (len(OLD_KEY) + 2 - len(KEY)) + b"= %i\n"


def rel(src, dst, length=5):
    return struct.pack("<i", dst - (src + length))


def build_patches():
    patches = [
        Patch(PARSER_LITERAL, OLD_KEY + b"\0", NEW_KEY + b"\0",
              f"parser key -> {KEY.decode()}"),
        Patch(WRITER_FORMAT, OLD_FMT + b"\0", NEW_FMT + b"\0", "cfg writer key"),
        Patch(DEFAULT_STORE, bytes.fromhex("8935") + struct.pack("<I", CFG_GLOBAL), NOP * 6,
              "default store NOPed (absent line = retail)"),
    ]
    get = (bytes.fromhex("6b3d") + struct.pack("<I", CFG_GLOBAL) + bytes([TICKS_PER_SECOND])
           + bytes.fromhex("85ff") + bytes.fromhex("7f05")
           + b"\xbf" + struct.pack("<I", STOCK_TICKS) + b"\xc3")
    patches.append(Patch(GET, INT3 * len(get), get, "GET: seconds*62, <=0 -> 620"))
    stubs = {}
    cur = STUB
    for reg in ("eax", "ecx", "edx"):
        s = b"\x57" + b"\xe8" + rel(cur + 1, GET) + bytes.fromhex(STORE[reg]) + b"\x5f" + b"\xc3"
        patches.append(Patch(cur, INT3 * len(s), s, f"stub for {reg}"))
        stubs[reg] = cur
        cur += len(s)
    for va, reg in SITES.items():
        old = b"\xc7" + bytes([MODRM[reg]]) + bytes.fromhex("24010000") + struct.pack("<I", STOCK_TICKS)
        new = b"\xe8" + rel(va, stubs[reg]) + NOP * 5
        patches.append(Patch(va, old, new, f"site -> call stub ({reg})"))
    return patches


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    apply(sys.argv[1], sys.argv[2], build_patches())
    print(f"\nNow add to game.cfg:  {KEY.decode()} = 5   (seconds; 0/absent = retail 9.92 s)")
