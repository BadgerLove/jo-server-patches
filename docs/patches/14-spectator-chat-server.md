# Spectator chat relay + Kill List crash fix (server)

**Status:** verified, live (server running it since 2026-09-25 00:50; spectator chat seen by players; crash fix by analysis and emulation). **Script:** [`scripts/patch_spectator_server.py`](../../scripts/patch_spectator_server.py). Client counterpart: [patch 13](13-spectator-hud-client.md).

Two changes. Take both, or just the crash fix with `--crash-fix-only`.

## K. Kill List crash fix (one byte, helps every stock client)

### The bug

Players **on stock clients** SYSDUMP while a spectator is on the server, typically the moment the spectator leaves:

```
access violation at 00423d64h, attempting to read from 00000162h
EBP 00000000
```

`HUD_DrawKillList @0x423A30` draws the scoreboard from 56-byte rows (`+0` player index, `+4` spectator flag). A spectator row jumps straight to `mov cl,[ebp+0x162]` (the row's entity team) at `0x423D64`, **skipping the `test ebp,ebp` null check that normal rows get**:

```
00423cfa  cmp byte [ebx+4], 0        ; spectator row?
00423cfe  je  0x423d19               ;   no -> normal path (with null check)
00423d0f  mov dword [esp+0x10], 0x1b8 ; x = 440 (spectator column)
00423d17  jmp 0x423d64               ;   *** skips the null check ***
00423d19  test ebp, ebp
00423d1b  je  0x424254               ; normal rows: no entity -> skip the row
...
00423d64  mov cl, byte [ebp+0x162]   ; CRASH when the row's entity is null
```

`ebp` is the row's player entity on the drawing client. A spectator whose slot is gone (just left) or whose entity the client never held gives null, and every client with the Kill List open crashes at once. It is a retail NovaLogic bug; it needs a spectator to trigger, which is why it is rarely seen.

### The fix

Clients cannot all be patched, so the server stops sending the bit. In `NetPacket_SerializeScoreboard0x16` the row flags byte is built as `(spectator & 1) + 2 * team` at `0x504C2B`: `and dl,1` becomes `and dl,0`. Without the bit, stock clients send the row down the normal path, where a null entity or team 0 simply skips it. The scoreboard's separate "Number of Spectators" trailer count is untouched, so the spectator count still shows.

Only other reader of that bit: the one-life "players left" counter, where a spectator may now be counted. Not observed to matter.

## S. Spectator chat relay

### Why spectators are mute

Four independent mutes: three on the spectator's own client ([patch 13](13-spectator-hud-client.md), D) and one here. The server's chat handler drops any chat packet from a slot with the spectator flag (`slot+0x188D7`) unless the game is between rounds (`0x24C1928`). Even if it relayed the line, every receiving stock client drops a chat line whose **sender index** resolves to a spectator.

### What the patch does

A 22-byte gate at `0x5137C7` (`cmp spectator / je / cmp between-rounds / je drop`) becomes a jump into a stub that lets a spectator through when:

- channel byte is **1** (everyone): always; or
- channel byte is **2** (team): only if the sender's entity team is **not** 1 or 2. A real spectator is team 0, so its team chat reaches other spectators only, never a playing team. A dead player waiting to respawn (still team 1/2) is dropped as before.

An allowed message sets a flag dword in the cave (`0x7BFCF0`). While it is set:

- `NetPacket_WriteTwoBytesAndCString @0x5047A0` writes the sender index as **`0xFF`** on the wire, the same value the server console's own chat uses, so stock clients cannot resolve the sender to a spectator and display the line. The name is already inside the text ("Name: hello").
- `Chat_DispatchToChannel @0x42B910` gets the same `0xFF` for the server's own copy (the chat log that remote-admin tools read from port 4000).

The handler's single shared exit at `0x51416D` clears the flag. That exit was chosen after the first attempt at `0x514163` overlapped two early-drop jump targets inside it (`0x514165/6`); a byte scan of `.text` confirms nothing branches into `0x51416E..0x514174`.

Cost: players can no longer scoreboard-mute a spectator (the sender is anonymous on the wire).

### The code

| VA | Bytes | Meaning |
|----|-------|---------|
| PE header, `_text` | `VirtualSize 0x2AA10 -> 0x2B000` | map the zero tail (already RWX) |
| `0x7BFA20` (76 B) | gate stub | channel/team test, sets flag, continues at `0x5137DD` or drops to `0x514165` |
| `0x7BFA70` (24 B) | write stub | flag → sender byte `[esp+0xC] = 0xFF`, then the displaced prologue, back to `0x5047A5` |
| `0x7BFA90` (24 B) | dispatch stub | flag → `[esp+4] = 0xFF`, displaced prologue, back to `0x42B915` |
| `0x7BFAB0` (23 B) | exit stub | clear flag, displaced `pop edi / xor ecx,esp / call cookie`, back to `0x514175` |
| `0x504C2B` | `80e201` → `80e200` | K |
| `0x5137C7` (22 B) | `80bed788010000 740d 833d28194c0200 0f8488090000` → `e9 54c22a00` + 17 × `90` | S-G |
| `0x5047A0` | `8b442408 55` → `e9 cbb22b00` | S-W |
| `0x42B910` | `0fb6442404` → `e9 7b413900` | S-D |
| `0x51416D` | `5f 33cc e806692500` → `e9 3eb92a00` + 3 × `90` | S-X |

## How to apply

```
python scripts/patch_spectator_server.py jointops.exe jointops_patched.exe
python scripts/patch_spectator_server.py jointops.exe jointops_patched.exe --crash-fix-only
```

Restart the server on the new exe. No config change. Spectators additionally need [patch 13](13-spectator-hud-client.md) on their own client to open the chat box.

## Verification

- Applied to the combined server base (`68de3776…`: arena + 125 FPS lock + admin fix + NWU) the script reproduces the live server exe byte for byte (`a3e314f6…`).
- Emulated before going live: the chat handler with all four hooks in place against real captured packets (all channels, the early-drop paths, the rate limiter), and the scoreboard writer (rows byte-identical to retail except the spectator bit).
- Live 2026-09-25: a spectator's chat displayed to players as "Name: text" (confirmed by the players). The crash fix has not been provoked deliberately; the reasoning is the disassembly above plus the scoreboard emulation.

## History

The crash was diagnosed from a player's SYSDUMP on 2026-09-24 (register dump plus the stack showed the spectator-column x offset `0x1B8` and a null `ebp`). Write-up of the dump format in [docs/systems/sysdump-format.md](../systems/sysdump-format.md).
