# First person in vehicles from game.cfg (server)

**Status:** checked in an emulator (unicorn) against the real game code; the exe version is **not yet tested in game**. The same rule (same site, same bit) was proven in game on 2026-10-11 as an onHook hook: every player was locked to first person in vehicles with stock clients. **Script:** [`scripts/patch_first_person_driver.py`](../../scripts/patch_first_person_driver.py). Also a tick box in **WolfRAT**'s Server patcher. **The exe does not grow.**

## What it changes

It makes the `game.cfg` line `mp_3rdperson_driver` work. **After patching, set it in the server's `game.cfg`** (with the server stopped):

```
mp_3rdperson_driver     = 0     players are locked to first person in vehicles
mp_3rdperson_driver     = 1     third person allowed (the game's normal)
```

It is read at each map start, so a change takes effect from the next map. **Only the server needs it:** stock clients already obey the lock, so players download nothing and nobody is kicked for mismatched files. It changes only the view in vehicles. Third person on foot is not affected.

## Why stock ignores the line

The game reads `mp_3rdperson_driver` from `game.cfg` and writes it back (variable `0x2550CA0`, default 1), but nothing in the game ever uses it.

Every client already has the lock. Its per-frame camera code forces first person while alive when the session rules word has bit `0x40` (`Render_ProcessMainSceneFrame @0x5CA235`). The host builds that word at every map start from its `mpattrib` (`0x2550A04`) and sends it to every player; joiners get it with the map (S2C `0x64`). Nothing ever sets bit `0x40`.

## The code

The host's load of `mpattrib` in `CNapiGameSession_InitRandomSeedOrRequest` jumps to a small piece of code that sets or clears bit `0x40` from the `game.cfg` value, then carries on as stock. `mpattrib` itself is never written, so the `game.cfg` line alone decides (an admin `set` can copy the rules word back into `mpattrib`, so a stale bit is always cleared when the line says 1).

```
mov eax, [0x2550A04]          ; mpattrib, as stock
and eax, ~0x40                ; third person allowed...
cmp dword [0x2550CA0], 0      ; ...unless mp_3rdperson_driver = 0
jne back
or  eax, 0x40                 ; first person in vehicles
back:
jmp 0x51E952                  ; mov [esi+2Ch], eax, as stock
```

| VA | Bytes | Meaning |
|----|-------|---------|
| `0x51E94D` | `a1040a5502` → `e9ee152a00` | the rules word load jumps to the cave |
| `0x7BFF40` (25 B) | zeros → `a1040a550283e0bf833da00c550200750383c840e9f9e9d5ff` | the code above |
| `_text` header | VirtualSize `0x2AA10` → `0x2B000` | maps the section's zero tail, as patches 14, 15, 19 and 20 do; the file size does not change |

The cave sits right after [patch 20](20-keep-at-mines.md)'s, so 14, 15, 19, 20 and 22 all fit together. Client exes carrying the spectator HUD ([patch 13](13-spectator-hud-client.md)) use this space, so the patch is for **server** exes. The script refuses an exe where the space is taken.

**Checked** in an emulator (unicorn): the patched code was run from `0x51E94D` to `0x51E952` for four `mpattrib` values and `mp_3rdperson_driver` 0, 1 and 2. In all 12 cases the result was `mpattrib` with bit `0x40` set exactly when the line is 0, and `mpattrib` itself was untouched.

## Notes and limits

- Not to be confused with `mp_permanent_death`, the line next to it. That one also does nothing useful in stock (it crashes clients), but its fix is in the **client**, so it is not here.
- **onHook:** its `ThirdPersonDriver` hook does the same thing at the same site. On an exe with this patch, onHook's check of the stock bytes fails and it leaves the site alone, so the exe patch decides. Use one or the other.
