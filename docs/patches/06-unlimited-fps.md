# Unlimited FPS / Sleep removal (server / client)

**Status:** documented, and **superseded**. No automated patcher is shipped (see "Verification").

> **Prefer the [125 FPS lock](11-fps-lock-125.md) instead.** This patch removes the throttle entirely, so the server busy-loops at ~285 FPS and burns a whole CPU core. The 125 FPS lock keeps the throttle and just changes its target, giving a steady 125 FPS while the process sleeps between frames. It also corrects the premise below: `Sleep(1)` is ~1 ms on this engine, not 15 ms, because the engine sets a 1 ms timer resolution at startup. The 59 FPS cap was the hardcoded 16 ms target, not Sleep granularity.

## What it does

Removes the frame-timing `Sleep(1)` bottleneck. On Windows a `Sleep(1)` actually parks the thread for about 15 ms because of the default timer resolution, which caps the loop near 59 FPS. NOPing the sleep and its loop-back lets the engine run at its natural speed (around 285 FPS on modern hardware, at the cost of roughly one full CPU core).

For a dedicated server this mostly matters in combination with the packet-rate change: a faster loop lets the network scheduler send more often.

## The patch

Three sites in the frame-timing path:

| File offset | Original | Patched | Effect |
|-------------|----------|---------|--------|
| `0x12B8B0` | `6A 01 FF 15 D4 00 7C 00` (`push 1; call [Sleep]`) | `90 × 8` | remove the Sleep call |
| `0x12B8DF` | `72 C7` (`jb loop_back`) | `90 90` | remove the loop-back |
| `0x362124` | `8B 0D 4C 2F 34 03` (`mov ecx,[timer_delay]`) | `B9 08 00 00 00 90` (`mov ecx,8; nop`) | fix timer delay to 8 ms (optional) |

The first two give the FPS unlock. The third is an optional refinement to the timer delay and can be applied independently.

## Verification

These offsets and bytes are from the project's own verified patch history. An automated patcher is **not** included here because every locally available build already has the Sleep NOP applied, so the original bytes could not be re-confirmed against a clean stock executable at the time of writing. Apply by hand with a hex editor using the table above, and confirm the "Original" bytes are present before changing them. If you verify these against a stock 1.7.5.7 executable, please open an issue so a script can be added with confidence.

## Related

- [Packet send rate](07-packet-send-rate.md) — pairs with this for a faster server send cadence.
