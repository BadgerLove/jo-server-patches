"""Set the post-respawn spawn-protection (CEASE FIRE invulnerability) duration.

GamePlayerEntity+0x124 holds a spawn-protection countdown in game-logic ticks
(16 ms fixed step, 62.5 Hz). Retail sets it to 620 ticks (9.92 s) at six sites.
While it is non-zero the player takes no damage; it is cleared early when the
player fires. This tool rewrites all six immediates to a duration you choose.

Server-side only: the countdown runs on the server; clients need nothing.

Sites (each is `mov dword [reg+0x124], 620`, C7 8x 24 01 00 00 <imm32>):
  VA 0x516BBA  round start, every slot
  VA 0x517937  death: killer was a vehicle
  VA 0x517952  death: killer seat attribute 0x40000
  VA 0x517960  normal respawn
  VA 0x519FE7  respawn-with-death-weapon handler
  VA 0x51A882  join / rejoin

Full write-up: docs/patches/03-spawn-protection.md

Usage:  python patch_spawn_protection.py <in.exe> <out.exe> [seconds]
        default is 5.0 seconds
"""
import struct
import sys

from patch_util import Patch, apply

STOCK_TICKS = 620
TICK_MS = 16.0
SITES = {
    0x516BBA: "round start, every slot",
    0x517937: "death: killer was a vehicle",
    0x517952: "death: killer seat attribute 0x40000",
    0x517960: "normal respawn",
    0x519FE7: "respawn-with-death-weapon handler",
    0x51A882: "join / rejoin",
}


DISP = bytes.fromhex("24010000")   # disp32 = +0x124, the spawn-protection field


def build(in_path, out_path, seconds):
    ticks = int(round(seconds * 1000.0 / TICK_MS))
    if not 1 <= ticks <= 0x7fffffff:
        sys.exit("seconds out of range")
    # Each site is  C7 <modrm> 24 01 00 00 <imm32>.  We anchor on the disp32
    # (+0x124) plus the immediate, starting 2 bytes into the instruction, so a
    # wrong build cannot match by coincidence.
    old = DISP + struct.pack("<i", STOCK_TICKS)
    new = DISP + struct.pack("<i", ticks)
    print(f"spawn protection {seconds} s -> {ticks} ticks "
          f"(retail {STOCK_TICKS} = {STOCK_TICKS * TICK_MS / 1000:.2f} s)")
    patches = [
        Patch(va=va + 2, old=old, new=new, note=what) for va, what in SITES.items()
    ]
    apply(in_path, out_path, patches)


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    build(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) == 4 else 5.0)
