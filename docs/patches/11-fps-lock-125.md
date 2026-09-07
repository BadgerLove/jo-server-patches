# 125 FPS lock (server)

**Status:** verified, live (measured 126-127 FPS on a dedicated server, 2026-09-07). **Script:** [`scripts/patch_fps_lock.py`](../../scripts/patch_fps_lock.py)

> ## After patching, set this in `game.cfg`:
> ```
> lock_framerate = 7
> ```
> **`lock_framerate` is now the frame target in milliseconds, not an on/off switch.** 7 gives ~125 FPS. An old config with `lock_framerate = 1` would now mean a 1 ms target, which is nearly unthrottled again. Set it explicitly.

## What you get

A server that runs a steady ~125 FPS and **sleeps between frames**, so the CPU core sits near idle instead of at 98%. This replaces the common "unlimited FPS" hack, which removes the throttle entirely and busy-loops at ~285 FPS.

| `lock_framerate` | frame target | real FPS |
|---|---|---|
| `0` | off | unthrottled, full CPU |
| `7` | 7 ms | **~125** (recommended) |
| `8` | 8 ms | ~112 |
| `16` | 16 ms | stock 62.5 |

## The problem, and why earlier attempts failed

Retail caps the main loop at 62.5 FPS. Several attempts over the years to raise that to a locked 125 with QueryPerformanceCounter busy-wait code caves either crashed or had no effect, and the ones that "worked" still measured 59 FPS. Reading the loop shows there were **three** separate obstacles, and every previous attempt only ever addressed one.

### 1. The target is a shift, not a setting

`Game_MainLoop` keeps frame time in units of 1/16 ms and throttles with, in effect:

```
while (frame_time < (lock_framerate != 0) << 8)
    Sleep(1);
```

`<< 8` is 256 units = **16 ms = 62.5 FPS**, baked into two shift instructions. The `framerate` config key exists as a string but nothing reads it. This patch loads the raw `lock_framerate` value and multiplies by 16 instead, so the value is milliseconds.

### 2. The clock cannot see 8 ms

This is the one nobody found, and it is why even a correct target still read 59 FPS. The loop measures elapsed time with `GetTickCount`. On Windows 10 that counter advances only in **15-16 ms steps**, even when the system timer resolution is 1 ms (measured on the live box: 38 steps in 0.6 s). So the Sleep loop sleeps, sees zero elapsed, sleeps again, and only exits when the counter jumps by 15.6 ms. The target byte is irrelevant if the clock cannot resolve it.

The engine already imports `timeGetTime` from winmm, which advances every 1 ms (595 steps in 0.6 s on the same box) because the engine calls `timeBeginPeriod(1)` at startup. This patch retargets all five clock references in the loop to that import. Both functions return milliseconds since boot as a wrapping DWORD, so the semantics are identical; only the resolution changes.

### 3. Sleep(1) was often removed

The "unlimited FPS" hack NOPs out the `Sleep(1)` call and its loop-back. If they are missing, the script restores them; on a stock exe they are already intact.

## Why 7 and not 8

Each `Sleep(1)` overshoots by roughly 0.9 ms. An 8 ms target measured 112 FPS (8.9 ms real frames). A 7 ms target measures 126-127 FPS (about 7.9 ms real). Since the value is tunable in the config, you can adjust for your own hardware without rebuilding.

## The patch

| VA | Original | Patched | Meaning |
|----|----------|---------|---------|
| `0x52B85E` (17 bytes) | `xor eax,eax; cmp [cfg],eax; store; setne al` | `mov eax,[cfg]; store; nop x6` | use the raw value |
| `0x52B89F` | `C1 E0 08` (`shl eax,8`) | `C1 E0 04` (`shl eax,4`) | target = ms x 16, loop entry |
| `0x52B8CA` | `C1 E2 08` (`shl edx,8`) | `C1 E2 04` (`shl edx,4`) | target = ms x 16, loop repeat |
| `0x52B75C`, `0x52B798`, `0x52B8B8`, `0x52BA7E` | `call [GetTickCount]` | `call [timeGetTime]` | 1 ms clock |
| `0x52BA95` | `mov ebx,[GetTickCount]` | `mov ebx,[timeGetTime]` | 1 ms clock (indirect) |
| `0x52B8B0`, `0x52B8DF` | NOPs (if unlimited-FPS applied) | `push 1; call [Sleep]`, `jb` | restore throttle |

All in place, no code cave. Do not touch the nearby `shl esi,8` at `0x52B88C`; that is a separate fixed-timestep override.

Safe to repurpose the config value: the stored target is read only inside this loop, and the config global is read only here and echoed verbatim by the settings writer.

## What it does not change

Game logic still steps every 16 ms; at 125 FPS an update fires roughly every other frame, exactly as the engine already handles at higher unthrottled rates. The engine's 33 ms multimedia timer is the audio mixer, unrelated to networking. As a side benefit, frame time is now measured accurately instead of in 15 ms lumps, so the game-step accumulation is smoother.

## How to apply

```
python scripts/patch_fps_lock.py jointops.exe jointops_fps.exe
```

Then set `lock_framerate = 7` in `game.cfg` and restart the server.

## Verifying it worked

The loop stores its averaged FPS in the process at `0x024E1F10` (refreshed about every 2 s) and the target it is using at `0x024E1F0C`. Reading those from the running process (requires an elevated prompt, since the server runs elevated) should show ~125 and 7 respectively. Task Manager should show the server's core drop from ~98% to low single digits.

## Verification

Applied to a stock-derived server build, the script reproduces the live 126 FPS build byte-for-byte.
