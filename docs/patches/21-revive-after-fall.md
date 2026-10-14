# Revive after a fall (host)

**Status:** checked against the game code; **not yet tested in game.** **Script:** [`scripts/patch_revive_after_fall.py`](../../scripts/patch_revive_after_fall.py). Also a tick box in **WolfRAT**'s Server patcher. **One byte; the exe does not grow.**

## The bug

A player killed up high whose body then falls (a blast throws it off a roof, or a death animation tips it over an edge) **can never be revived**. Players see the body on the ground and the medic is right beside it, but nothing happens. It has been in the game since release. It is often blamed on lag, as if the server still had the body up where it died. It does not: the server drops the body to the ground like everyone else.

## Why it happens

When a body lands hard, the host runs fall damage on it. The players' fall damage never checks whether the body is already dead. Health is already 0, so no more is taken, but fall damage also writes **the player as his own killer**:

```
0x4B7D1B  cmp [esi+0xA0], -1057*fallmps   ; landed hard enough?
0x4B7D3B  cmp is_authority, 0             ; host only
0x4B7D43  test dword [esi+0x24], 0x4000000 ; Indestructible? -> skip
...
0x4B7D76  mov [esi+0x11E], cx             ; health -= damage (0 stays 0)
0x4B7D7D  mov [esi+0x178], esi            ; last attacker = himself
```

A medic revive refuses a player whose last attacker is the medic or the player himself (a suicide). So the revive is refused for every body that landed hard after death: with the stock `fallmps` of 13, a drop of about 7 m, less if a blast first threw the body upwards.

The AI soldiers' copy of the same landing code already skips dead bodies (`test dl, 2` at `0x4BF843`). The players' copy does not.

## What it changes

Fall damage **skips a body that is already dead**, as it does for AI soldiers. One byte: the Indestructible test also tests the dead flag (`0x2`).

| VA | Bytes | Meaning |
|----|-------|---------|
| `0x4B7D43` | `f7462400000004` → `f7462402000004` | `test [esi+0x24], 0x4000000` → `0x4000002`: Indestructible **or dead** skips fall damage |

**Unchanged:** living players take fall damage exactly as before. A player killed **by** the fall still cannot be revived, as stock: the dead flag is only set on the tick after the landing that killed him.

Fall damage and the revive both run on the **host** (the server, or the player hosting "serve and play"), so only the host exe needs this. Clients need nothing.
