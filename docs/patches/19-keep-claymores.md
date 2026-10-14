# Keep claymores after a respawn (server)

**Status:** checked in an emulator (unicorn) against the real game code; **not yet tested in game.** **Script:** [`scripts/patch_keep_claymores.py`](../../scripts/patch_keep_claymores.py). Also a tick box in **WolfRAT**'s Server patcher. The same rule has been proven in game as an onHook setting (`KeepClaymoresOnRespawn`, 2026-10-12); this is the exe version, for servers without onHook. **The exe does not grow:** the new code goes into existing empty space.

## What it changes

A player's claymores **stay armed when they die and redeploy**, and still go off. **Nothing else changes.** AT mines and satchels are removed on a redeploy as before ([patch 20](20-keep-at-mines.md) keeps AT mines), and a player who **leaves** the server still takes all their devices with them. The limit of 4 claymores per player is unchanged: when a player places a fifth, the oldest one goes, kept ones included.

Only the **server** needs it. The server removes devices and tells every player, so clients need nothing.

## Why stock removes them

When a player redeploys, `Server_ProcessPlayerDeath` calls `Entity_RemovePlacedDevicesByOwner @0x546E00` (the call at `0x5178D8`; skipped for a medic revive and for spectators). That function walks the placed-device pool and removes every satchel, claymore and AT mine the player owns, through `Server_RemoveEntityAndNotify @0x50A270`. It is also called when a player leaves the server (the call at `0x50A2BB`).

Inside it, each device type has its own test:

```
0x546E68  cmp ecx, [0x24E7DD8]   ; satchel?   -> remove
0x546E8B  cmp edx, [0x24E7DD0]   ; claymore?  -> remove (0x546E93)
0x546EAE  cmp eax, [0x24E7DC0]   ; AT mine?   -> remove (0x546EBA)
```

## The code

The claymore test jumps to a small piece of code. It repeats the test. For a claymore, it looks at who called the function: the return address sits at `[esp+0x10]`, because the function pushed four registers. A redeploy returns to `0x5178DD`, so the claymore is kept. Anything else (a player leaving) removes it as before.

```
cmp edx, [0x24E7DD0]              ; claymore?
jne 0x546E9C                      ; no: on to the next test, as stock
cmp dword [esp+0x10], 0x5178DD    ; called by the redeploy?
je  0x546E9C                      ; yes: keep it
jmp 0x546E93                      ; no (player left): remove it
```

| VA | Bytes | Meaning |
|----|-------|---------|
| `0x546E8B` | `3b15d07d4e02` → `e97090270090` | the claymore test jumps to the cave |
| `0x7BFF00` (31 B) | zeros → `3b15d07d4e020f85906fd8ff817c2410dd7851000f84826fd8ffe9746fd8ff` | the code above |
| `_text` header | VirtualSize `0x2AA10` → `0x2B000` | maps the section's zero tail, as patches 14 and 15 do; the file size does not change |

The cave sits after [patch 15](15-long-chat-server.md)'s line buffer (`0x7BFE00..0x7BFEFF`), so 14, 15, 19 and 20 all fit together. Client exes carrying the spectator HUD ([patch 13](13-spectator-hud-client.md)) use this space, so the patch is for **server** exes. The script refuses an exe where the space is taken.

**Checked** in an emulator (unicorn): the real `0x546E00` was run from the patched exe, with a fake device pool holding a satchel, two claymores, two AT mines, another player's claymore and a non-device:
- Called as a redeploy, it removes the satchel and the AT mines, and keeps both claymores.
- Called as a player leaving, it removes everything the player owns.
- The other player's claymore and the non-device are never touched.
- The stack and the saved registers come back intact.

## Notes and limits

- **onHook:** its `KeepClaymoresOnRespawn` / `KeepAvMinesOnRespawn` settings do the same thing by replacing the redeploy call. On an exe with this patch, onHook's check of the stock bytes fails and it leaves the redeploy alone, so the exe patch decides. Use one or the other.
- A kept claymore still counts towards its owner's 4. The cap (`Server_EnforcePlacedDeviceCapByOwner @0x5119E0`) keys on the player's body, and a respawn reuses it.
