# Keep AT mines after a respawn (server)

**Status:** checked in an emulator (unicorn) against the real game code; **not yet tested in game.** **Script:** [`scripts/patch_keep_at_mines.py`](../../scripts/patch_keep_at_mines.py). Also a tick box in **WolfRAT**'s Server patcher. The same rule has been proven in game as an onHook setting (`KeepAvMinesOnRespawn`, 2026-10-12); this is the exe version, for servers without onHook. **The exe does not grow.**

## What it changes

A player's AT mines (`AV_Mine`) **stay armed when they die and redeploy**, and still go off. **Nothing else changes.** Claymores and satchels are removed on a redeploy as before ([patch 19](19-keep-claymores.md) keeps claymores), and a player who **leaves** the server still takes all their devices with them. The limit of 3 AT mines per player is unchanged.

Only the **server** needs it; clients need nothing.

## How it works

It works the same way as [patch 19](19-keep-claymores.md); read that page for the stock code. The only differences are the test that is changed and the cave:

```
cmp eax, [0x24E7DC0]              ; AT mine?
jne 0x546E20                      ; no: next device, as stock
cmp dword [esp+0x10], 0x5178DD    ; called by the redeploy?
je  0x546E20                      ; yes: keep it
jmp 0x546EBA                      ; no (player left): remove it
```

| VA | Bytes | Meaning |
|----|-------|---------|
| `0x546EAE` | `3b05c07d4e02` → `e96d90270090` | the AT-mine test jumps to the cave |
| `0x7BFF20` (31 B) | zeros → `3b05c07d4e020f85f46ed8ff817c2410dd7851000f84e66ed8ffe97b6fd8ff` | the code above |
| `_text` header | VirtualSize `0x2AA10` → `0x2B000` | as patches 14, 15 and 19 (only once) |

Patches 19 and 20 touch different bytes, so either can go in alone, and in either order. **Checked** in the same emulator run as patch 19, on this patch alone and on both together.
