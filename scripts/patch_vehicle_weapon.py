"""Fix the vehicle-seat weapon-restore bug (client-side).

Leaving a vehicle control or gun seat re-mounts the weapon cached at
GamePlayerEntity+0x308. That cache is written on spawn / loadout sync / kit
screen and by the seat-attach code, but NOT by the number-key or mouse-wheel
weapon switch, which only update the live slot at g_currentWeaponSlot. Control
seats with no seat weapon skip the attach-time save, so dismounting restores
the stale spawn weapon: "the weapon you last died with".

Fix: in Entity_DetachFromVehicle @0x4355F0 make the local-player restore always
use g_currentWeaponSlot, which every hand-weapon switch keeps current.
  VA 0x435640:  3B C2 74 0C  (cmp eax,edx ; je fallback)
            ->  EB 0E 90 90  (jmp fallback ; nop ; nop)
Remote-player / server behaviour is untouched.

Full write-up: docs/patches/02-vehicle-weapon-restore.md

Usage:  python patch_vehicle_weapon.py <in_client.exe> <out.exe>
Base: any 1.7.5.7 client build (stock or a visual-mod build).
"""
from patch_util import Patch, main

PATCHES = [
    Patch(
        va=0x435640,
        old=bytes.fromhex("3bc2740c"),
        new=bytes.fromhex("eb0e9090"),
        note="dismount restores live weapon slot, not the spawn cache",
    ),
]

if __name__ == "__main__":
    main(PATCHES, __doc__)
