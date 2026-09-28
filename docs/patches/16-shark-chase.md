# Shark chase (host)

**Status:** verified in game 2026-09-27. Dale hosted "serve and play" with the patched exe on a hookah1 test map. Sharks stay in the water, turn and swim at you as soon as you jump in, never chase onto land or up onto a wooden platform, and the bite lands at the right distance. **Script:** [`scripts/patch_shark_chase.py`](../../scripts/patch_shark_chase.py). **Live on the FMJ server since 2026-09-27** (the script reproduces that exe byte for byte).

## What it changes

Sharks chase players who are swimming in deep water. They no longer charge at players standing in the shallows and beach themselves. **Nothing else changes.** Soldiers, players, tigers and any other creature run the stock code.

Only the **host** needs it: that's the server, or the player hosting "serve and play". AI only thinks on the host, so clients need nothing.

## Why stock sharks never chase

Joint Ops has no idea what a sea creature is. Sharks use the same AI as soldiers and tigers (`org1`, `Entity_UpdateInfantryAI @0x4B9910`), and being in water only swaps the animations: swim instead of walk, `swim_attack` instead of attack.

The AI's approach step (`0x4BC2C2..0x4BC31A`) moves an AI towards its target only when **both** of these hold:

1. **Min engagement < max engagement** (AI slot `+0x40` < `+0x44`, `jge` at `0x4BC2C8`). At spawn the min takes the placement's value, or the sight value if that is 0, so an AI placed without a minimum never approaches anything. Set it in Nile, or with WAC `SSNMin(ssn, metres)` (which writes `+0x40`).
2. **Solid ground no more than 3 m under the target.** `Entity_CheckGroundHeightAtPosition @0x4AFF70` (called at `0x4BC2E9`) takes the target's ground from `Entity_CalcAverageGroundHeight @0x457230`. That is a ray against terrain and objects, and the water surface does not count. The check fails if the result equals the water height (`0x26C6454`), and otherwise passes when `target.Z - ground <= 3.0 m`.

A player swimming over deep water fails 2, so the shark keeps circling. A player standing in shallow water passes, so the shark charges straight out onto the beach. Both were seen in game before this patch.

## The code

The call at `0x4BC2E9` goes to a small check first:

- **Not a shark:** the thinking AI is `esi` (written only at `0x4B992A` in this function), and its item definition is at `[esi+0x20]`, starting with the item name. If the name doesn't start with `Shar`, jump to the original `0x4AFF70`, unchanged.
- **Shark:** `ground = Entity_CalcAverageGroundHeight(target, 0, 1)`, the same call the original makes. Chase if `ground + depth - water < 0`, i.e. the water under the target is deeper than `--depth` (default **2 m**).

| VA | Bytes | Meaning |
|----|-------|---------|
| `0x4BC2E9` | `e8823cffff` → `e8e89d2600` | the approach step's ground check calls cave A |
| `0x7260D6` (41 B) | int3 padding → `8b4620 813853686172 0f85… 6a01 6a00 ff742410 e8… 83c40c 05<depth> e9…` | shark? else the original check; ground under the target; add the depth |
| `0x4AFFE1` (12 B) | int3 padding → `2b0554646c02 c1f81f f7d8 c3` | minus the water height, then 1 if below zero, else 0 |

Cave A uses the int3 padding at `0x7260D5..0x7260FF`. `0x726015` is taken by [patch 12](12-spawn-protection-config.md), so there is no overlap. Cave B is the padding right after `0x4AFF70`'s `ret`.

**Checked** with an emulator (unicorn) running the patched code from the call site, with the ground height stubbed:
- A shark over 12 m and over 3 m of water chases.
- A shark in 1.5 m of water, on land, or at exactly 2 m doesn't.
- A tiger, a custom creature and a soldier reach `0x4AFF70` with the stack and arguments unchanged.

The script's output is byte-identical to the build tested in game.

## Notes and limits

- The item name is matched on its first four letters (`Shar`). The TAC item list has one shark item, `Shark`, and nothing else starting with `Shar`.
- The item attribute `Landable` (item def `+0x54` bit `0x200`) is **not** a land/sea flag. Only two tiger items and two crawling zombies carry it.
- Sharks still need **min engagement < max engagement** (point 1 above). The tested map used Nile team 2, max attack 4 m, sight 90 m, and `SSNMin(ssn, 4)` in the map's WAC.
- For a **list** of water creatures, and for **land-and-water** creatures such as a crocodile (they chase on land and follow you into the water), use the onHook version, where the lists are settings ([opennova-int PR #44](https://github.com/opennova-net/opennova-int/pull/44), not merged yet).
- **WolfRAT 2.8.8** (Weather/Wildlife tab, Hunting sharks) makes the sharks aggressive and gives them a 4 m start-chasing distance where the map left none, so a map needs no WAC edit for point 1.
