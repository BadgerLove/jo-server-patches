# Configurable spawn protection (server)

**Status:** verified, live (config value parsed and echoed back by a dedicated server, 2026-09-07). **Script:** [`scripts/patch_spawn_protection_config.py`](../../scripts/patch_spawn_protection_config.py)

> ## After patching, add this to `game.cfg`:
> ```
> e_spawn_protection = 5
> ```
> Value is **seconds**. `0`, a negative number, or no line at all gives the retail 9.92 s. The key name **must** be exactly `e_spawn_protection` (see "Why the odd name").

## What you get

The post-respawn invulnerability window ("CEASE FIRE") becomes a `game.cfg` setting instead of a number baked into the exe. Change the line, restart the server, done. [Patch 03](03-spawn-protection.md) does the same job with a fixed duration chosen at patch time; use one or the other, not both.

The server rewrites `game.cfg` from its own variables at startup, and this key is part of that rewrite, so the line survives restarts and shows you what the server actually loaded.

## Mechanism

The countdown itself is unchanged from patch 03: `GamePlayerEntity+0x124` is set to 620 ticks (16 ms each) at six sites and counts down on the server. This patch replaces the six hard-coded stores with a call to a tiny routine that computes the value from a config variable.

### Borrowing a config key

The engine has no spare config slots, so an existing key is repurposed: `enable_keyboardtips`. It is a client-only UI preference (whether the keyboard-tips widget shows), never read on a dedicated server, and its parser entry and writer entry are simple `int` reads and writes on one global (`0x2550844`). Both strings are renamed in place; the new name has to fit in the old string's bytes (19 characters).

The defaults routine sets that global to 1 before the config is read. That store is NOPed, so a missing line leaves 0, which the GET routine maps to retail.

### Why the odd name

`Config_ParseSettingsLine` switches on the **lower-cased first letter of the key** and only then compares names inside that case. The `enable_keyboardtips` comparison lives under `case 'e'`. A renamed key that starts with any other letter is never compared, the global stays 0, and the server writes `= 0` back into `game.cfg`. Our first build used `spawn_protection` and failed exactly this way. Hence `e_spawn_protection`. If you edit the script to pick another name, keep the leading `e` and 19 characters or fewer.

### The code

| VA | Bytes | Meaning |
|----|-------|---------|
| `0x7D477C` | `"enable_keyboardtips"` → `"e_spawn_protection"` | parser literal |
| `0x7D3B90` | `"enable_keyboardtips  = %i\n"` → `"e_spawn_protection   = %i\n"` | config writer format |
| `0x54D13B` | `mov [0x2550844], esi` → 6 × `nop` | no default of 1 |
| `0x726015` (17 B, int3 padding) | `imul edi,[0x2550844],62; test edi,edi; jg +5; mov edi,620; ret` | GET: seconds × 62 ticks, ≤ 0 → retail |
| `0x7472C9` / `D7` / `E5` (3 × 14 B, int3 padding) | `push edi; call GET; mov [reg+0x124],edi; pop edi; ret` | one stub per destination register |
| `0x516BBA, 0x517937, 0x517952, 0x517960, 0x519FE7, 0x51A882` | `mov dword [reg+0x124],620` (10 B) → `call stub` + 5 × `nop` | the six set sites |

`edi` is saved and restored around every use, no flags are consumed after any of the six sites, and a whole-`.text` scan confirms there are exactly six retail stores. 62 ticks per second (rather than 62.5) keeps the multiply to one instruction; 5 seconds reads as 4.96 s.

## How to apply

```
python scripts/patch_spawn_protection_config.py jointops.exe jointops_patched.exe
```

Then add `e_spawn_protection = 5` to `game.cfg` (any whitespace around `=` is fine) and restart the server. After the restart the line will have been rewritten in the server's own column layout; if it reads `= 0`, the key was not recognised.

If your exe already carries patch 03, start from an unpatched copy: the script asserts the retail 620 at all six sites.

## Verification

The script reproduces the live server build byte-for-byte when applied to the same base (the FPS-lock + admin-fix build), and a dry run against a retail client exe asserts clean at every site. Live: after a restart with `e_spawn_protection = 5`, the server's rewritten `game.cfg` reads `e_spawn_protection   = 5`.
