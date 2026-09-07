# Packet send rate (server)

**Status:** verified. **Script:** [`scripts/patch_packet_rate.py`](../../scripts/patch_packet_rate.py)

## What it does

Controls how often the server sends state updates to each client. A single byte in `NapiNPServer_GetSendHoldoffTicks` sets the send hold-off in game updates. Lowering it makes the server send more often, which players feel as smoother movement and better hit registration.

## How the rate works

The server's game logic runs at a fixed 62.5 Hz (16 ms step) regardless of frame rate. Once per update the network hold-off countdown is decremented, and when it reaches zero a packet is sent to each client and the countdown reloads. So, **per direction, per client**:

```
packets per second  =  62.5 / hold-off
```

| VA | File offset | Value (hold-off) | Server-to-client packets/sec | Total both directions |
|----|-------------|------------------|------------------------------|-----------------------|
| `0x4C4B13` | `0x0C4B13` | `0x04` | ~16 | ~31 |
| | | `0x02` (retail default) | ~31 | ~62 |
| | | `0x01` | ~62 | ~125 |

Measured with a packet capture on the client machine, filtered to the game conversation only: hold-off 2 gave a flat 31 packets a second in each direction. The client sends at the same rate, so a capture that does not separate directions shows roughly double.

## Two things that trip people up

**Filter your capture.** A packets-per-second graph of a whole network interface on a server that also hosts websites, other game servers, admin tools, or an open Remote Desktop session will show hundreds of packets a second that have nothing to do with the game. Filter to the game port and one client before reading a number off it. An open Remote Desktop session alone can add 200+ packets a second.

**Count one direction.** Earlier notes for this patch quoted "62 stock, 125 patched". Those were both directions added together (31+31 and 62+62). The table above is per direction.

## Important correction

This byte was previously described as a "tick divisor" setting an internal 1000 Hz game rate. **That was wrong.** The game-logic step is a fixed 16 ms in every build; this byte only changes the network send cadence. The correct offset and meaning were confirmed by diffing the 32 Hz, 64 Hz and 125 Hz builds, whose only game-code difference at this address is `0x04` vs `0x02` vs `0x01`. This is also why spawn protection still lasts its full ~10 seconds regardless of this setting.

Note that the [125 FPS lock](11-fps-lock-125.md) does not change the packet rate either: the send cadence is tied to the 62.5 Hz update, not to frames.

## Trade-offs

Lower hold-off uses more upload bandwidth and a little more CPU. `0x01` (~62 per direction per client) is comfortable on a LAN or a well-connected host; test it on a constrained line with a full server before committing.

## How to apply

```
python scripts/patch_packet_rate.py jointops.exe jointops_fast.exe 125
```

The final argument is kept for compatibility with the old naming: `125` sets hold-off 1, `62` sets hold-off 2, `32` sets hold-off 4. The tool checks the current value is one of the three known settings before changing it.
