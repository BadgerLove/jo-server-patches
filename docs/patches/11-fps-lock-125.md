# 125 FPS lock (server)

**Status:** built and disassembly-verified; live confirmation in progress. **Script:** [`scripts/patch_fps_lock.py`](../../scripts/patch_fps_lock.py)

## The problem

Retail throttles the main loop to 62.5 FPS. The common "unlimited FPS" fix removes the throttle entirely, which gets you ~285 FPS but burns nearly a whole CPU core busy-looping. What admins actually want is a *locked* 125 FPS: fast enough to match a 125 packets/sec send rate, but sleeping between frames so the box stays quiet.

Several earlier attempts to get there with QueryPerformanceCounter busy-wait code caves failed. Reading the loop shows why: it was solving the wrong problem.

## How the throttle really works

`Game_MainLoop` keeps the frame time in units of 1/16 ms and throttles with, in effect:

```
while (frame_time_fp4 < (lock_framerate != 0) << 8)
    Sleep(1);
```

`<< 8` is 256 units = **16 ms per frame = the 62.5 FPS ceiling.** The target is not a config value anywhere; it is a shift immediate baked into two instructions (the `framerate` config key exists as a string but is dead). Change both shifts from 8 to 7 and the target becomes 128 units = 8 ms = 125 FPS.

## Why Sleep(1) is fine

The usual objection is that `Sleep(1)` sleeps ~15 ms on Windows. Not here. The engine calls `timeBeginPeriod(1)` at startup (in its multimedia-timer setup), so the system timer resolution is 1 ms while the game runs; a live server measures exactly 1.000 ms. `Sleep(1)` is therefore ~1 ms and the loop can hit an 8 ms target with about a millisecond of jitter. No busy-wait, no code cave, no QPC needed.

The old 59 FPS was never a Sleep-granularity problem. It was simply the 16 ms target.

## The patch

| VA | Original | Patched | Meaning |
|----|----------|---------|---------|
| `0x52B89F` | `C1 E0 08` (`shl eax,8`) | `C1 E0 07` (`shl eax,7`) | loop-entry target 16 ms to 8 ms |
| `0x52B8CA` | `C1 E2 08` (`shl edx,8`) | `C1 E2 07` (`shl edx,7`) | loop-repeat target 16 ms to 8 ms |

If the file previously had the "unlimited FPS" patch applied (the `push 1; call [Sleep]` at `0x52B8B0` and the `jb` at `0x52B8DF` NOPed out), the script restores them. On a stock exe they are already intact and are left alone.

Do not touch the nearby `shl esi,8` at `0x52B88C`: that is a separate fixed-timestep override, not the throttle.

## Config

Set in `game.cfg`:

```
lock_framerate = 1
```

With `0` the throttle is bypassed and the loop runs unthrottled regardless of this patch.

## What it does not change

Game logic still steps every 16 ms; at 125 FPS an update fires every other frame, exactly as the engine already handles at higher unthrottled rates. The engine's 33 ms multimedia timer is the audio mixer, unrelated to networking, so the packet send rate should be unaffected. Confirm with a packet capture after deploying.

## How to apply

```
python scripts/patch_fps_lock.py jointops.exe jointops_fps125.exe
```

## Verification

Applied to the live admin-fix server build, the script reproduces the deployed 125 FPS candidate byte-for-byte. On a stock client it asserts cleanly and changes only the two shift bytes.
