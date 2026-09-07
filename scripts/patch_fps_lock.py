"""Lock the main loop to ~125 FPS (8 ms frames) instead of the 62.5 FPS ceiling.

How the engine throttles (Game_MainLoop @0x52B630):

    while (frame_time_fp4 < (lock_framerate != 0) << 8)
        Sleep(1);

frame_time_fp4 is measured in 1/16 ms, so `<< 8` = 256 = 16 ms per frame, the
62.5 FPS ceiling. The target is a shift immediate, not a config value (the
`framerate` config key is dead). Changing both shifts from 8 to 7 makes the
target 128 = 8 ms = 125 FPS.

Sleep(1) really is ~1 ms here: the engine calls timeBeginPeriod(1) at startup
(System_StartMultimediaTimer @0x7620D0), so the loop can hit an 8 ms target
with about a millisecond of jitter. No busy-wait or code cave is needed.

Changes (in place):
  VA 0x52B89F  C1 E0 08 -> C1 E0 07   (shl eax,8 -> shl eax,7)  loop-entry target
  VA 0x52B8CA  C1 E2 08 -> C1 E2 07   (shl edx,8 -> shl edx,7)  loop-repeat target
  VA 0x52B8B0  restore `push 1; call [Sleep]` if a previous "unlimited FPS"
               patch NOPed it out (left alone if already intact)
  VA 0x52B8DF  restore the `jb` loop-back likewise

Requires `lock_framerate = 1` in game.cfg; with 0 the throttle is bypassed and
the loop runs unthrottled.

Full write-up: docs/patches/11-fps-lock-125.md

Usage:  python patch_fps_lock.py <in.exe> <out.exe>
"""
import sys

from patch_util import Patch, apply, va_to_offset

SHIFTS = [
    Patch(va=0x52B89F, old=bytes.fromhex("c1e008"), new=bytes.fromhex("c1e007"),
          note="frame target 16 ms -> 8 ms (loop entry)"),
    Patch(va=0x52B8CA, old=bytes.fromhex("c1e208"), new=bytes.fromhex("c1e207"),
          note="frame target 16 ms -> 8 ms (loop repeat)"),
]

SLEEP_VA, SLEEP_INTACT, SLEEP_NOPED = 0x52B8B0, bytes.fromhex("6a01ff15d4007c00"), b"\x90" * 8
JB_VA, JB_INTACT, JB_NOPED = 0x52B8DF, bytes.fromhex("72c7"), b"\x90\x90"


def build(in_path, out_path):
    data = open(in_path, "rb").read()
    patches = list(SHIFTS)
    for va, intact, noped, what in (
        (SLEEP_VA, SLEEP_INTACT, SLEEP_NOPED, "restore Sleep(1) call"),
        (JB_VA, JB_INTACT, JB_NOPED, "restore throttle loop-back"),
    ):
        cur = data[va_to_offset(data, va):va_to_offset(data, va) + len(intact)]
        if cur == noped:
            patches.append(Patch(va=va, old=noped, new=intact, note=what))
        elif cur != intact:
            sys.exit(f"ABORT: unexpected bytes at VA {va:#x}: {cur.hex()} (wrong build?)")
    apply(in_path, out_path, patches)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    build(sys.argv[1], sys.argv[2])
