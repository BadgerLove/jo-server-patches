# Vehicle weapon restore fix (client)

**Status:** verified, live. Present in the game since 2004. **Script:** [`scripts/patch_vehicle_weapon.py`](../../scripts/patch_vehicle_weapon.py)

## Symptom

You are carrying, say, the sniper rifle. You get into a vehicle seat, then get out. Instead of the rifle you were holding, you are now holding the weapon you last **died** with. Every player has lived with this for twenty years.

## Root cause

When you leave a vehicle control or gun seat, the game re-mounts the weapon cached at `GamePlayerEntity+0x308`. That cache is written on spawn, on loadout sync, on the kit screen, and by the seat-attach code, but it is **not** written by the number-key or mouse-wheel weapon switch. Those only update the live slot at `g_currentWeaponSlot` (`0xB76474`).

Control seats that have no seat weapon skip the attach-time save entirely. So when you dismount, the restore reads the stale cache, which still holds your spawn loadout weapon. That weapon is "the one you last died with".

## The patch

In `Entity_DetachFromVehicle` (`0x4355F0`), make the local-player restore always use the live `g_currentWeaponSlot` instead of the stale cache. Two sibling copies of this function at `0x4949D0` and `0x546D00` have no callers, so only this one matters.

| VA | Original | Patched | Meaning |
|----|----------|---------|---------|
| `0x435640` | `3B C2 74 0C` (`cmp eax,edx; je fallback`) | `EB 0E 90 90` (`jmp fallback; nop; nop`) | always take the live-slot path |

Remote-player and server behaviour (cache to equipped-slot) is untouched, so this is safe to run as a client change on any server.

## How to apply

```
python scripts/patch_vehicle_weapon.py jointops.exe jointops_patched.exe
```

Works on any 1.7.5.7 client build (stock or a visual-mod build); the script asserts the original bytes.

## Verification

Applying this to the stock LAA client reproduces the live vehicle-fix build byte for byte, and the fix has been confirmed in play across all seat-exit cases.
