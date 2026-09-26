# Hole-skip (players stop freezing on a lost packet)

**Status:** verified, live. **Script:** [`scripts/patch_hole_skip.py`](../../scripts/patch_hole_skip.py)

Community fix by "Spaghetti", with a second tuning for 125 Hz by the FMJ server.

## The problem it fixes

On a 64 Hz or 125 Hz server, a player who loses a packet can end up **frozen in place**. They are not disconnected: chat still reaches them and they stay on the server, but they cannot move until they reconnect by hand. It hits high-ping players most, because they lose packets most.

Joint Ops sends its ordered traffic through a reorder queue. The server drains the queue in sequence, and when the packet it expects next has not arrived, the retail drain loop stops and waits for it. If that packet never comes, the player's input stays stuck behind the hole.

32 Hz servers do not need this fix: at that rate high-ping players do not run into the stall. This is also why many community servers stayed on 32 Hz.

## What the fix does

The drain loop is sent through a small code cave. When the expected packet is missing, the cave looks at two numbers:

- how many packets are queued behind the hole, and
- how far ahead the newest packet is.

When both are past their thresholds, the cave moves the loop's place past the hole and carries on draining. The player keeps moving and only the lost packet is skipped.

## Two versions

The cave is identical in every build; only its two thresholds differ.

| Version | Queued | Behind | Notes |
|---|---|---|---|
| **64 Hz** | 8 | 64 | Spaghetti's original |
| **125 Hz** | 6 | 32 | At 125 Hz a packet arrives every 8 ms, so waiting for 64 packets is a ~512 ms stall. 32 halves it to ~256 ms |

Use the version that matches your server's [send rate](07-packet-send-rate.md). Running the 64 Hz version on a 125 Hz server leaves players stalling for half a second on every lost packet.

## Changes

```
hook  VA 0x626954  8B 8F B8 07 00 00 83 C1   mov ecx,[edi+7B8h] ; add ecx,..
              ->   E9 97 E4 16 00 90 90 90   jmp 0x794DF0 ; nop x3
cave  VA 0x794DF0  81 bytes in the zero padding at the end of .text
      VA 0x794E0A  queued threshold  (08 / 06)
      VA 0x794E1A  behind threshold  (40 / 20)
```

The cave sits just past `.text`'s virtual size but inside its raw data. Windows loads a section's whole raw data, so it is mapped and runs; this was confirmed by reading the cave back from a running server.

The cave, as it runs:

```
0x794DF0  mov ecx, [edi+0x7B8]       ; the instructions the hook replaced:
0x794DF6  add ecx, 1                 ;   next sequence number expected
0x794DF9  cmp [esi+0x14], ecx        ; is the queued packet the expected one?
0x794DFC  je  0x626962               ;   yes: process it as normal
0x794E02  mov ecx, [edi+0x7A8]       ; packets queued behind the hole
0x794E08  cmp ecx, 6                 ; queued threshold (8 in the 64 Hz version)
0x794E0B  jl  0x794E3C               ;   not enough: wait, as retail does
0x794E0D  mov eax, [edi+0x7B4]       ; newest sequence number seen
0x794E13  sub eax, [edi+0x7B8]       ;   minus where the loop is
0x794E19  cmp eax, 0x20              ; behind threshold (0x40 in the 64 Hz version)
0x794E1E  jbe 0x794E36               ;   not far enough: wait
0x794E20  mov ecx, [esi+0x14]        ; skip: move the loop's place to just
0x794E23  dec ecx                    ;   before the queued packet
0x794E24  mov [edi+0x7B8], ecx
0x794E2A  mov byte [edi+0x174], 1    ; note that a hole was skipped
0x794E31  jmp 0x626940               ; drain again from the top
0x794E36  mov eax, [edi+0x7A0]
0x794E3C  jmp 0x6269BB               ; retail's "wait for it" exit
```

## How to apply

```
python scripts/patch_packet_rate.py jointops.exe  jointops_64.exe  62
python scripts/patch_hole_skip.py   jointops_64.exe jointops_64hs.exe 64

python scripts/patch_packet_rate.py jointops.exe   jointops_125.exe 125
python scripts/patch_hole_skip.py   jointops_125.exe jointops_125hs.exe 125
```

On an exe that already has the cave with one of the two known settings, the script switches it to the version you ask for. Custom settings are refused, so they are never overwritten by accident. The script refuses 32.

Verified against the shipped JOexeFIX v2 builds: the 32 Hz server with send rate 62 and hole-skip 64 reproduces the 64 Hz server exactly; that exe with hole-skip 125, send rate 125 and the [125 FPS lock](11-fps-lock-125.md) reproduces the 125 Hz server exactly.

## Correction

This page used to describe hole-skip as a "NovaWorld connection fix" for clients failing to connect, and said it could not have an automated patcher because the cave was build-specific. Both were wrong. It fixes the lost-packet freeze described above, and the cave is byte-identical in every build that carries it, apart from the two thresholds.

## Credits

Hole-skip: community contributor "Spaghetti". 125 Hz tuning: the FMJ server. Retail protocol correctness work in the surrounding tooling: Taylor Finnell (Open Nova).

## Related

- [Packet send rate](07-packet-send-rate.md)
- [Bigbuf network buffers](08-network-bigbuf.md) (the reorder-queue cap of 1000 seen in the community builds belongs with bigbuf, not with hole-skip)
