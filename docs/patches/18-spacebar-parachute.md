# Spacebar parachute (server, live patch)

**Status:** verified in game 2026-10-07 on the FMJ TAC dedicated server, with stock TAC clients: **9 chutes opened by Jump, 0 by themselves.** A safety net that still opened the chute by itself in long falls was tried the same week and removed at the server admin's request, so the rule is fully manual. **Shipped in WolfRAT 2.9.3** (Server tab → Live patches → Spacebar parachute). **No exe script:** WolfRAT writes this into the running server's memory, so nothing on disk changes. The bytes below are enough to build an exe version, but none has been made or tested.

## What it changes

The stock game opens a carried parachute **by itself** after about a second of free fall. With this on, the player opens it by **holding Jump (space) while falling**, like the older Delta Force games, and it never opens by itself. **Nothing else changes.** It is still one parachute per life. The sound, animation, braking, closing on landing and what other players see are all the stock game's.

Only the **server** needs it (or the player hosting "serve and play"). The host decides when a chute opens and sends the result to every player, the same way it does for the stock automatic chute. Clients need nothing.

## How the stock parachute opens

In `Entity_UpdateInfantryPlayerBody`, the host opens a carried chute once the player's vertical speed passes **-14336** (entity `+0xA0`, about 1.1 s of free fall):

| VA | Bytes | Meaning |
|----|-------|---------|
| `0x4B7AE5` | `81bea000000000c8ffff` | `cmp dword [esi+0xA0], -14336`  vertical speed |
| `0x4B7AEF` | `7f0c` | `jg` not falling fast enough → skip |
| `0x4B7AF1` | `f6462c10` | `test byte [esi+0x2C], 0x10`  carrying a parachute |
| `0x4B7AF5` | `7406` | `je` none → skip |
| `0x4B7AF7` | `83c820894624` | `or eax, 0x20 / mov [esi+0x24], eax`  the chute-open flag |
| `0x4B7AFD` | | carries on |

The game has no parachute key. But every client already sends its Jump key to the server in each movement update (MoveOrder `+0x12C`, bit `0x20`), so the server can see it.

## The code

The 5 bytes at `0x4B7AE5` become a `jmp` to a small piece of code. It opens the chute only when **all** of these hold:

1. carrying a parachute (`[esi+0x2C] & 0x10`, as stock);
2. Jump held (`[esi+0x12C] & 0x20`);
3. airborne (`eax & 0x2000`; `eax` holds the entity flags at this point);
4. falling faster than **-6144**, about 0.5 s of fall. An ordinary jump on flat ground lands at about -5632, so holding space through a normal jump never spends the chute.

```
test byte [esi+0x2C], 0x10      ; carrying a chute?
je   back
test byte [esi+0x12C], 0x20     ; Jump held?
je   back
test eax, 0x2000                ; airborne?
je   back
cmp  dword [esi+0xA0], -6144    ; falling fast enough?
jg   back
inc  dword [opened_by_space]    ; counter (WolfRAT's page shows it)
or   eax, 0x20                  ; chute open, exactly as stock
mov  [esi+0x24], eax
back:
jmp  0x4B7AFD
```

WolfRAT's version also keeps a small header in front of the code: the tag `FMJCHUTE`, the threshold, the counter and the last fall speed. That's how it recognises its own code later. Off = the 5 stock bytes back.

## How WolfRAT applies it

- It reads the 18 stock bytes at `0x4B7AE5` first. If it finds something else (another exe, or onHook holding the site), it leaves the server alone and says so.
- It writes the new code into fresh memory in the server and reads it back. Only then does it write the 5-byte `jmp`, with the server paused for the moment that takes.
- Every switch-on gets a fresh copy of the code. A server thread may still be running inside the old one, so the old one is never rewritten.
- A map change keeps the patch (same server process). A server restart or crash loses it. WolfRAT checks every 5 seconds and puts it back when "re-apply" is ticked.
- Source: `wolfrat/live_patches.py` in [WolfRAT2](https://github.com/BadgerLove/WolfRAT2).

## Notes and limits

- **Fully manual.** A player who forgets to press space hits the ground. That's by design.
- The threshold (-6144) is a setting in WolfRAT's code. Closer to 0 lets players open earlier, but it must stay below an ordinary jump's -5632 or a normal jump with space held will spend the chute.
- onHook has the same rule as a setting, `SpacebarParachuteEnabled` (default off), as an open pull request. Its hook uses the same site, the same tests and the same threshold. Use one or the other: WolfRAT steps aside when onHook already holds the site.
