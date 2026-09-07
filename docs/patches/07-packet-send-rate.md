# Packet send rate (server)

**Status:** verified. **Script:** [`scripts/patch_packet_rate.py`](../../scripts/patch_packet_rate.py)

## What it does

Controls how often the server sends network updates. A single byte in `NapiNPServer_GetSendHoldoffTicks` sets the send hold-off. Lowering it makes the server send position and state more often, which players feel as smoother movement and better hit registration.

## The patch

| VA | File offset | Value | Observed rate |
|----|-------------|-------|---------------|
| `0x4C4B13` | `0x0C4B13` | `0x04` | ~32 packets/sec |
| | | `0x02` | ~62 packets/sec (retail default) |
| | | `0x01` | ~125 packets/sec |

Observed rates are from Wireshark captures on a live server; the exact figure depends on the scheduler.

## Important correction

This byte was previously described in project notes as a "tick divisor" that set an internal 1000 Hz game rate. **That was wrong.** The game-logic step is a fixed 16 ms (62.5 Hz) in every build; this byte only changes the *network send* cadence. The correct offset and meaning were confirmed by diffing the 32 Hz, 64 Hz and 125 Hz builds, whose only game-code difference at this address is `0x04` vs `0x02` vs `0x01`. This is why spawn protection still lasted its full ~10 seconds regardless of this setting: the countdown runs on the 16 ms game step, not on the send rate.

## Trade-offs

Higher send rates use more upload bandwidth and more CPU. `0x01` (~125/sec) is comfortable on a LAN or a well-connected host; test it on a constrained line before committing.

## How to apply

```
python scripts/patch_packet_rate.py jointops.exe jointops_fast.exe 125
```

The final argument is the target rate: `32`, `62`, or `125` (default `125`). The tool checks the current value is one of the three known settings before changing it.
