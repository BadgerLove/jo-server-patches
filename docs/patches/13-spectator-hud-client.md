# Spectator HUD for casters (client)

**Status:** verified, live (2026-09-25: tags, bars, colours and two-way chat all seen in game on a populated server). **Script:** [`scripts/patch_spectator_client.py`](../../scripts/patch_spectator_client.py). Server counterpart for chat: [patch 14](14-spectator-chat-server.md).

## What you get

Joint Ops has a spectator mode (join, pick no team, cycle players or roam), but a stock client makes it useless for casting or moderating: the HUD is switched off entirely (so no chat is visible), players carry no name tags, and pressing the talk key does nothing. After this patch a spectator sees:

- **Chat**, exactly as a player would (global plus both teams' team chat, which the server already sends to spectators).
- **Name tags over every player's head**, blue for team 1, red for team 2, using NovaLogic's own tag drawer and colours, fading with distance the way friendly tags do. AI soldiers on teams 1/2 are tagged too. Other spectators (team 0) and yourself are skipped.
- **A health bar under each tag** (green above 66 %, yellow above 33 %, red below), plus a percentage beside the player you currently have selected. A dead player keeps an empty bar, which is deliberate: medics can revive, and the bar refills.
- **Working chat keys.** T/Y open the chat box while spectating and the line is sent. It only reaches other players if the server carries [patch 14](14-spectator-chat-server.md); on a stock server it is silently dropped, as before.

Nothing changes for anyone else. The patch is entirely client-side rendering and input; it does not alter what the server sends, hitboxes, or gameplay, and it draws nothing while you are alive and playing.

## Mechanism

Four independent pieces. All addresses are for the retail 1.7.5.7 client; the script asserts every original byte.

### A. Chat visible: don't hide the HUD

Becoming a spectator runs a routine that stores HUD detail level **3** (everything off) at `0x42E410` (`push 3 / mov [0x24D20BC], 3`). Level 3 is also what F6 cycles through, and the chat box only draws at levels 0/1. The two constants become **0**, so spectating behaves as if F6 had been pressed once. No new code.

### B. Name tags: run the tag drawer from the spectator frame

The frame loop sends a spectator down a separate branch (it opens `death.mnu`) and never reaches `HUD_RenderAllOverlays`, the only caller of the tag pass. Yet the label routine `HUD_DrawEntityLabel @0x5A39B0` is fully spectator-aware: it already bypasses the ally/game-type gates while spectating and colours by team from `entity+0x162` using `tagcolor_blueteam` / `tagcolor_redteam`. It just never gets called.

The spectator branch contains a spare `call` to an empty function at `0x5CAB95`. That call is redirected to a 251-byte cave at `0x7BFA20` which:

1. bails unless `g_death_screen_active` (`0xA860EC`, set only by the server's spectator message), HUD level < 2 and the server's "friendly tags off" bit (`0x24D1E34 & 0x400`) is clear;
2. treats the player's Friendly Tags option (`0x24C18C4`) `off` as `full` for the duration (restored after);
3. **saves and zeroes the selected-target pointer `0xA860F4`** for the duration. The stock drawer pins the label of the selected spectator target to the top-centre of the screen in every camera mode, so in a free camera one player floats mid-screen. With the pointer blanked everyone takes the projected over-the-head path; in first-person follow the followed player's own tag clips at the camera, which is what you want;
4. loop 1: the entity pool (`0xA892E0` base, `0xA892E4` stride, `0xA892E8` count) for non-player entities (`Flags & 0x100` clear) on team 1/2, calling `HUD_DrawEntityLabel(entity, 0)`;
5. loop 2: the **client player table** `[0xA87048]` (`+0` slot count, `+0x2C` array of 64-byte slots, `+0xD` active, `+0x24` entity), calling `HUD_DrawEntityLabel(entity, slot)` for active team-1/2 players other than yourself. The tag list the server normally sends (message `0x04C`) is empty for spectators, which is why the player table is walked instead.

Two gates that look reasonable but are wrong, found live: the local player entity **does exist** for a spectator (so a null check is fine) but its `Flags & 2` "spectating" bit is **clear** on the client; gate on `0xA860EC` only.

### C. Health bars

`HUD_DrawEntityLabel` computes the health ratio for its own health icon in the same function that draws the text, so the data is at hand. After the tag text draw, `0x5A426D` (`add esp,18h / test ebp,ebp`) becomes a `jmp` into a 441-byte cave at `0x7BFB20` which, only while spectating, draws a bar under the name: width 3× font height, rows `max(2, h/5)`, fill = `health (entity+0x11E) / Entity_GetMaxHealthWithDifficulty(entity)` clamped 0..100, same distance-fade alpha as the tag, background `0x202020`, drawn with the 2-D line routine `0x5D3BD0` on the overlay context `0x24C1420`. For the selected player (the saved `0xA860F4` copy) it also prints `NN%` to the right via `sprintf` + the HUD text routine `0x580720`. The cave then redoes the two displaced instructions and jumps back to `0x5A4272`.

Known cosmetic limit: on some mods the divisor is larger than a player's real maximum, so full health can read below 100 % (87 % on the TAC mod). The bar is still proportional.

### D. Chat send: three spectator guards on the client

Sending as a spectator was muted in **four** places; three are on the client, one on the server ([patch 14](14-spectator-chat-server.md)). Each client site is a `je` that skips a spawn-gate check when not spectating; making it a `jmp` lets a spectator through the same path as a live player:

| VA | Function | Role |
|----|----------|------|
| `0x49B991` | talk-key action handler (`0x49AD40`, actions 100/101/109/110/111) | returned before opening the chat box: the key felt dead |
| `0x49A6CA` | team sender (`0x49A6B0`) | refused to send while spectating |
| `0x49A91A` | all sender (`0x49A900`) | refused to send while spectating |

The key-binding table itself (`0x8159A8`, 108-byte entries) already permits T/Y on the death screen (permission bit 2 set), so nothing there is touched. The crew (vehicle) key keeps its own spectator refusal; the squad and admin senders stay blocked.

### The code

| VA | Bytes | Meaning |
|----|-------|---------|
| PE header, `_text` | `VirtualSize 0x2AA10 -> 0x2B000` | map the zero tail so the caves execute (section is already RWX) |
| `0x7BFA20` (251 B, zeros) | tags cave | B above |
| `0x7BFB20` (441 B, zeros) | bar cave | C above |
| `0x7BFCF0` | `"%d%%\0"` | percentage format |
| `0x42E410` | `6a03 c705bc204d02 03000000` → `6a00 c705bc204d02 00000000` | A |
| `0x5CAB95` | `e8 06f9e7ff` → `e8 864e1f00` | B: call cave |
| `0x5A426D` | `83c418 85ed` → `e9 aeb82100` | C: jmp cave |
| `0x49A6CA`, `0x49A91A`, `0x49B991` | `74 0d` → `eb 0d` | D |

## How to apply

```
python scripts/patch_spectator_client.py jointops.exe jointops_spectator.exe
```

Applies to a stock 1.7.5.7 client, an LAA client, or one carrying [patch 10](10-grass-128m.md). Everyone who wants to cast uses the patched exe; nobody else needs it. Once in the server, join without picking a team to spectate. If the tags do not appear, cycle **K** (Friendly Tags) once; the cave forces "off" to "on", but the other modes are honoured.

## Verification

- Applied to the 128 m-grass client (`060c96a9…`) the script reproduces the live build byte for byte (`e9a77dec…`).
- Every cave was run in a CPU emulator against fabricated pool/table data before the first in-game test: label calls for the right entities only, stack and callee-saved registers preserved, tag mode and the selected-target pointer restored.
- In game (2026-09-25, 2-4 players): blue and red tags, bars changing colour with damage, percentage on the selected player, spectator chat both ways with the server patch in place.

## History

Found over two evenings by reading the stock code rather than adding an overlay: the label routine and its colours were already there, only the call was missing. Along the way two debug-overlay builds measured the gates directly (which is how the "spectating bit is clear on the client" surprise was caught) and a stock crash was found and fixed on the server side ([patch 14](14-spectator-chat-server.md)).
