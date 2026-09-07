# Spawn protection tuning (server)

**Status:** verified. **Script:** [`scripts/patch_spawn_protection.py`](../../scripts/patch_spawn_protection.py)

## What it does

Sets the post-respawn invulnerability window ("CEASE FIRE" spawn protection) to any duration you choose. Retail is 620 ticks, which at the fixed 16 ms game step is 9.92 seconds. Many admins want it shorter.

## Mechanism

`GamePlayerEntity+0x124` holds a spawn-protection countdown measured in game-logic ticks. The game step is a fixed 16 ms (62.5 Hz) in every build, so ticks convert to seconds as `ticks * 16 / 1000`. The field is:

- set to 620 at six code sites (round start, the death handlers, respawn, join),
- decremented once per tick in the per-slot update loop (a value of -1 means permanent, used for spectators),
- cleared to zero the moment the player fires,
- while non-zero, makes incoming projectile and explosion damage apply as zero.

## The patch

Rewrite the immediate at all six sites from 620 to your chosen tick count. Each site is `mov dword [reg+0x124], imm32` (`C7 <modrm> 24 01 00 00 <imm32>`); the tool anchors on the `+0x124` displacement plus the immediate so it cannot match the wrong location.

| VA | Site |
|----|------|
| `0x516BBA` | round start, every slot |
| `0x517937` | death: killer was a vehicle |
| `0x517952` | death: killer seat attribute `0x40000` |
| `0x517960` | normal respawn |
| `0x519FE7` | respawn-with-death-weapon handler |
| `0x51A882` | join / rejoin |

Server-side only. Clients need nothing.

## How to apply

```
python scripts/patch_spawn_protection.py jointops.exe jointops_patched.exe 5
```

The final argument is the duration in seconds (default 5). Five seconds becomes 312 ticks.

## Verification

The tool asserts the retail value 620 at all six sites before writing, so a wrong build is rejected. Tested against the live server build: all six sites match and rewrite cleanly.
