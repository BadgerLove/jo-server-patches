# Long server chat + colours (server)

**Status:** verified, live on the FMJ 125 Hz server since 2026-09-26 (seen in game: 110-117 character lines on one line, colour changes part-way along a line, `<co>` back to the normal colour). **Script:** [`scripts/patch_long_chat.py`](../../scripts/patch_long_chat.py) with `--colour`.

## What it changes

Lines the **server** sends with the admin port's `CHAT SEND` (server messages, admin tools such as WolfRAT) can be up to **118 characters**, and `<cRRGGBB>` colour codes reach the players. **Players need nothing:** stock clients already show incoming chat up to 119 characters and draw colour codes. Players' own typing is unchanged.

## Why stock chat stops at 59 and has no colours

Every outgoing chat line goes through `Chat_SendTeamMessage @0x49A900` (server and client alike):

1. `Chat_CheckFloodControl @0x498F60` cuts the line in place: `if (strlen > 0x3B) message[59] = 0`. Its ring of recent lines keeps 64-byte copies.
2. `Chat_StripHtmlTags` copies the line into a **64-byte stack buffer**, dropping everything between `<` and `>`, and that stripped copy is what goes on the wire.

Proven live: a 62-character `CHAT SEND` came back from `CHAT GET` as 59 characters.

The receiving side draws chat (net msg `0x14` → `Chat_DispatchToChannel` → `Chat_AddMessageChannel1 @0x4985D0`) with the same routine WAC's `ptext` uses (msg `0x23` → `0x4EDB50` → `Chat_AddMessageChannel1`), and `ptext` colours have always worked. So both limits are the sender's, and the server can lift them for its own lines alone.

Raising the 59 alone is not safe: past 64 characters the strip overruns the stack buffer, and the function's stack cookie ends the server process.

## The code

| VA | Bytes | Meaning |
|----|-------|---------|
| `0x7BFD00` (58 B) | flood wrapper | caps the line at 119, runs the stock flood check (it cuts at 59 and stores that, which fits its 64-byte slots), then puts byte `[59]` back |
| `0x7BFD40` (53 B) | strip wrapper | strips into a 256-byte buffer at `0x7BFE00`, leaves a 63-byte copy in the caller's stack buffer (the peer path reads it) |
| `0x49A93B` | `e820e6ffff` → `e8c0533200` | call the flood wrapper |
| `0x49A971` | `e87adaffff` → `e8ca533200` | call the strip wrapper |
| `0x49A9DC` | `8d4c240451` → `5690909090` | `--colour`: send the line as typed (tags kept) |
| `0x49A9DC` | `8d4c240451` → `6800fe7b00` | without `--colour`: send the stripped line from the big buffer |

Only this one function changes. The caves live in the zero tail of the `_text` section: on an exe without [patch 14](14-spectator-chat-server.md) the script first maps that tail exactly as patch 14 does (`_text` VirtualSize `0x2AA10` → `0x2B000`; the section is already RWX). With patch 14 it coexists (stubs `0x7BFA20..0x7BFAC6`, flag `0x7BFCF0`), and the wire write still passes through 14's hook at `0x5047A0`.

## Limits that remain

- The admin port splits a command into at most **25 words**, so a `CHAT SEND` line carries at most **23**.
- The admin handler builds the line in a 122-byte buffer and adds a space: keep lines to **118 characters**. Colour codes count (`<cFF4040>` is 9).
- Players cannot inject colour: their own client strips tags before sending, and their lines are relayed by a different path.
- A player **name** containing `<` or `>` inside a server line would now be read as a tag; tools that put names in lines should replace those characters.
- The J message log shows colour codes as text (it always did for `ptext`).

## How to apply

```
python scripts/patch_long_chat.py jointops.exe jointops_patched.exe --colour
```

Works on a stock server exe on its own, or on top of the other server patches here. If you also want [patch 14](14-spectator-chat-server.md), apply 14 **first**: 14 expects the stock section size and refuses an exe that already has this patch. Restart the server on the new exe. In WolfRAT, tick **"My server has the long chat patch"** on the Chat tab (its "What is this?" link points here); leave it off on any other server.

## Verification

- Applied to the patch-14 server build (`a3e314f6…`): without `--colour` → `1ee93e27…`, with `--colour` → `273bc0ea…`.
- Applied on its own to a 1.7.5.7 exe carrying none of the other patches here except LAA and the 125 Hz send rate (`b9971c82…`), `--colour` → `0eb63bfc…`; emulated with the same results. (An earlier version of this page called that exe "stock with only the LAA flag"; its send-rate byte is the 125 Hz one.)
- Emulated (the whole send function, network and display stubbed): the stock exe reproduces the live 59 cut exactly; the patched one sends 62 and 118 in full, caps 144 at 119, sends short lines byte-identical to stock, keeps tags with `--colour`, and returns with the stack, registers and cookie intact.
- Live 2026-09-26: a 116-character line kept whole by the server; then five test lines seen in game, including red → yellow → blue on one line and an orange part followed by `<co>`.
