# Berserk ignores its own kind (host)

**Status:** verified in game 2026-09-27. The same bytes were written into the running FMJ server as a live patch, on a hookah1 test map with four berserk sharks: they stopped attacking each other and kept hunting players. **Script:** [`scripts/patch_berserk_kin.py`](../../scripts/patch_berserk_kin.py). Its output is byte-identical to the staged exe built that night. The exe itself has not been match-tested; the live patch has, and the bytes are the same. **WolfRAT 2.8.8 and later** writes this fix into the running server by itself before it makes any shark berserk (Weather/Wildlife tab, Hunting sharks), so a server running WolfRAT needs no exe change.

## What it changes

A berserk creature no longer attacks other creatures of the **same kind**. Berserk sharks ignore other sharks, and berserk tigers ignore other tigers on their own team. **Nothing else changes.** Players are never berserk, soldiers and non-berserk AI run the stock code, and two **different** creatures still fight each other as before.

Only the **host** needs it: that's the server, or the player hosting "serve and play". AI only thinks on the host, so clients need nothing.

## Why stock berserk creatures fight each other

Nile's **Berserk** tick sets bit `0x200` in the AI slot flags (AI slot `+0x04`). It means "attack anyone, whatever the team". The target scan in `Entity_FindTargets @0x53A610` checks for it before the ordinary team filter:

```
0x53A7EA  candidate's AI slot has 0x200  -> eligible target (0x53A82A)
          scanner's   AI slot has 0x200  -> eligible target
0x53A80E  ordinary team filter: candidate team 0, or same team as the scanner -> skip (0x53A710)
```

So a berserk creature skips the team filter for **every** candidate, including others of its own kind. Four berserk sharks on team 0 hunt the players and each other. That is what a map gets when it ticks Berserk on its sharks, and what WolfRAT's Hunting sharks needs to avoid.

This leg is only reached by the AI threat scan (`Entity_FindNearestThreat`'s call at `0x4B0A40`, context flags `0x100`). The weapon-effect call at `0x545925` passes `0x662` and never gets here.

## The code

When the berserk exception fires, the patch first checks the item definition (`[entity+0x20]`, a pointer to the creature's `items.def` row). Every Shark shares one row and every Tiger another. If the scanner and the candidate have the **same** row, the exception does not apply and the candidate goes through the ordinary team filter instead. Team-0 sharks therefore skip each other, and a berserk tiger still attacks a tiger on the other team, as any soldier would.

The berserk leg is re-packed in place to make room for a jump. `test byte [eax+5],2` tests the same bit as the retail `test dword [eax+4],0x200` in fewer bytes.

| VA | Bytes | Meaning |
|----|-------|---------|
| `0x53A7EA` (36 B) | `8b466885c07409f7400400020000753085d274108b426885c07409f7400400020000751c` → `8b466885c07406f6400502751185d274138b426885c0740cf64005027406e919b81e0090` | the same two berserk tests, packed; both "berserk" exits jump to the cave |
| `0x726026` (25 B) | int3 padding → `85d274108b462085c074093b42200f84d447e1ffe9eb47e1ff` | no scanner: retail; same item definition: ordinary team filter (`0x53A80E`); otherwise eligible (`0x53A82A`) |

The cave uses the int3 padding right after [patch 12](12-spawn-protection-config.md)'s stub (`0x726015..0x726025`). [Patch 16](16-shark-chase.md) starts at `0x7260D6`, so all three fit together.

## Notes and limits

- **Same kind = same `items.def` row.** Two creature items with different names (say a custom `Shark2`) count as different kinds and will still attack each other when berserk.
- The patch does not make anything berserk. That comes from the map (Nile's Berserk tick) or from WolfRAT's Hunting sharks.
- Use it with [patch 16](16-shark-chase.md) so berserk sharks also chase swimmers in deep water.
- **WolfRAT and onHook:** WolfRAT reads the running server's code before making a shark berserk. Stock code: it adds this fix. This fix already there (from this exe patch or an earlier WolfRAT): it leaves it. onHook's `BerserkIgnoresOwnKind` (default on) holding the site: it leaves it. Anything it does not recognise: it makes **no** shark berserk, so the sharks cannot turn on each other.
