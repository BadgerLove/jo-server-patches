"""Revive after a fall (host).  A body that falls after death can still be revived.

Stock: when a dead player's body drops a long way (thrown off a roof by a blast,
or a death animation tips it over an edge), the host runs ordinary fall damage
on it as it lands.  Health is already 0, so nothing more is taken, but the fall
damage records the player as his OWN killer.  A medic revive refuses a player
who killed himself, so the body can never be revived, although the medic is
right next to it.

This patch makes fall damage skip a body that is already dead (the creature AI
already does this).  One byte: the Indestructible test before the fall damage
also tests the dead flag.  Living players take fall damage exactly as before,
and a player killed BY the fall still cannot be revived (the dead flag is only
set on the next tick), as stock.

Changes (all asserted before writing):
  VA 0x4B7D43  test dword [esi+0x24],0x4000000 -> test dword [esi+0x24],0x4000002

Fall damage and the revive both run on the host only (server, or the player
hosting "serve and play"), so only the host exe needs this; clients need
nothing.  The exe does not grow.

Usage:  python patch_revive_after_fall.py <in.exe> <out.exe>
Base:   a stock 1.7.5.7 exe or any build from this repo (server or client).
"""
from patch_util import Patch, main

SITE = 0x4B7D43
STOCK = bytes.fromhex("f7462400000004")   # test dword [esi+0x24], 0x04000000  (Indestructible)
PATCHED = bytes.fromhex("f7462402000004")  # test dword [esi+0x24], 0x04000002  (Indestructible or dead)


def build_patches() -> list[Patch]:
    return [Patch(SITE, STOCK, PATCHED, "fall damage skips a dead body")]


if __name__ == "__main__":
    main(build_patches(), __doc__)
