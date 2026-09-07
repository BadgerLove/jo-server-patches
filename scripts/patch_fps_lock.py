"""Lock the server main loop to a chosen frame rate, tunable from game.cfg.

After this patch, `lock_framerate` in game.cfg is the FRAME TARGET IN MILLISECONDS
instead of a yes/no switch:

    lock_framerate = 7     ->  ~125 FPS   (recommended; measured 126-127 live)
    lock_framerate = 8     ->  ~112 FPS
    lock_framerate = 16    ->  stock 62.5 FPS
    lock_framerate = 0     ->  throttle off (unthrottled, full CPU)

Why 7 and not 8: each Sleep(1) overshoots by ~0.9 ms, so a 7 ms target lands on
~7.9 ms real frames = 125 FPS. An old config with `lock_framerate = 1` now means
a 1 ms target (near-unthrottled), so set it explicitly.

How the engine throttles (Game_MainLoop @0x52B630) and the three things that had
to change (all verified live on 2026-09-07):

 1. The target. Originally  target = (lock_framerate != 0) << 8  = 256 units of
    1/16 ms = 16 ms = the 62.5 FPS ceiling, baked in as a shift. Now the raw
    config value is loaded and multiplied by 16, so it is milliseconds.
 2. The clock. The loop measured elapsed time with GetTickCount, which on
    Windows 10 only advances in 15-16 ms steps even at 1 ms timer resolution,
    so it could never observe 8 ms passing and always exited at the next 15.6 ms
    jump (~59-64 FPS). Every clock reference in the loop is retargeted to the
    winmm timeGetTime import the exe already has, which advances every 1 ms
    because the engine calls timeBeginPeriod(1) at startup. Same ms-since-boot
    DWORD semantics, so nothing else changes.
 3. The Sleep call. If a previous "unlimited FPS" patch NOPed out the
    `push 1; call [Sleep]` and its loop-back, they are restored; on a stock exe
    they are already intact and left alone.

Byte changes (all in place, no code cave):
  0x52B85E  33 C0 39 05 44 07 55 02 89 35 08 1F 4E 02 0F 95 C0
        ->  A1 44 07 55 02 89 35 08 1F 4E 02 90 90 90 90 90 90
            (xor eax,eax; cmp [cfg],eax; store; setne al -> mov eax,[cfg]; store; nops)
  0x52B89F  C1 E0 08 -> C1 E0 04     shl eax,8 -> shl eax,4   (target = ms*16, loop entry)
  0x52B8CA  C1 E2 08 -> C1 E2 04     shl edx,8 -> shl edx,4   (target = ms*16, loop repeat)
  0x52B75C, 0x52B798, 0x52B8B8, 0x52BA7E   call [GetTickCount] -> call [timeGetTime]
  0x52BA95                                 mov ebx,[GetTickCount] -> mov ebx,[timeGetTime]
  0x52B8B0  restore 6A 01 FF 15 D4 00 7C 00 if NOPed     (push 1; call [Sleep])
  0x52B8DF  restore 72 C7 if NOPed                        (jb loop)

Full write-up: docs/patches/11-fps-lock-125.md

Usage:  python patch_fps_lock.py <in.exe> <out.exe>
        then set  lock_framerate = 7  in game.cfg
"""
import struct
import sys

from patch_util import Patch, apply, va_to_offset

GETTICKCOUNT_IAT = 0x7C0208   # KERNEL32!GetTickCount
TIMEGETTIME_IAT = 0x7C0454    # WINMM!timeGetTime

FIXED = [
    Patch(va=0x52B85E,
          old=bytes.fromhex("33c0390544075502" "8935081f4e02" "0f95c0"),
          new=bytes.fromhex("a144075502" "8935081f4e02" "909090909090"),
          note="load raw lock_framerate value (ms) instead of (value != 0)"),
    Patch(va=0x52B89F, old=bytes.fromhex("c1e008"), new=bytes.fromhex("c1e004"),
          note="target = ms*16 (loop entry)"),
    Patch(va=0x52B8CA, old=bytes.fromhex("c1e208"), new=bytes.fromhex("c1e204"),
          note="target = ms*16 (loop repeat)"),
]

# (VA of instruction, opcode prefix) for every GetTickCount reference in the loop
CLOCK_SITES = [
    (0x52B75C, b"\xff\x15"), (0x52B798, b"\xff\x15"), (0x52B8B8, b"\xff\x15"),
    (0x52BA7E, b"\xff\x15"), (0x52BA95, b"\x8b\x1d"),
]

SLEEP_VA, SLEEP_INTACT, SLEEP_NOPED = 0x52B8B0, bytes.fromhex("6a01ff15d4007c00"), b"\x90" * 8
JB_VA, JB_INTACT, JB_NOPED = 0x52B8DF, bytes.fromhex("72c7"), b"\x90\x90"


def build(in_path, out_path):
    data = open(in_path, "rb").read()
    patches = list(FIXED)
    for va, prefix in CLOCK_SITES:
        patches.append(Patch(
            va=va,
            old=prefix + struct.pack("<I", GETTICKCOUNT_IAT),
            new=prefix + struct.pack("<I", TIMEGETTIME_IAT),
            note="loop clock GetTickCount -> timeGetTime (1 ms resolution)"))
    for va, intact, noped, what in (
        (SLEEP_VA, SLEEP_INTACT, SLEEP_NOPED, "restore Sleep(1) call"),
        (JB_VA, JB_INTACT, JB_NOPED, "restore throttle loop-back"),
    ):
        off = va_to_offset(data, va)
        cur = data[off:off + len(intact)]
        if cur == noped:
            patches.append(Patch(va=va, old=noped, new=intact, note=what))
        elif cur != intact:
            sys.exit(f"ABORT: unexpected bytes at VA {va:#x}: {cur.hex()} (wrong build?)")
    apply(in_path, out_path, patches)
    print("\nNow set in game.cfg:   lock_framerate = 7    (target in ms; 7 -> ~125 FPS)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    build(sys.argv[1], sys.argv[2])
