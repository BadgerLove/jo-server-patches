# Spectator HUD for casters (client)

**Status:** verified, live (2026-09-25: tags, bars, colours and two-way chat all seen in game on a populated server). **Script:** [`scripts/patch_spectator_client.py`](../../scripts/patch_spectator_client.py). Server counterpart for chat: [patch 14](14-spectator-chat-server.md).

## What you get

Joint Ops has a spectator mode (join, pick no team, cycle players or roam), but a stock client makes it useless for casting or moderating: the HUD is switched off entirely (so no chat is visible), players carry no name tags, and pressing the talk key does nothing. After this patch a spectator sees:

- **Chat**, exactly as a player would (global plus both teams' team chat, which the server already sends to spectators).
- **Name tags over every player's head**, blue for team 1, red for team 2, using NovaLogic's own tag drawer and colours, fading with distance the way friendly tags do. AI soldiers on teams 1/2 are tagged too. Other spectators (team 0) and yourself are skipped.
- **A health bar under each tag** (green above 66 %, yellow above 33 %, red below), plus a percentage beside the player you currently have selected. A dead player keeps an empty bar, which is deliberate: medics can revive, and the bar refills.
- **Working chat keys.** T/Y open the chat box while spectating and the line is sent. It only reaches other players if the server carries [patch 14](14-spectator-chat-server.md); on a stock server it is silently dropped, as before.

Nothing changes for anyone else. The patch is entirely client-side rendering and input; it does not alter what the server sends, hitboxes, or gameplay, and it draws nothing while you are alive and playing.

## Only for real spectators

The tags and bars are gated on the client's spectator state, and that state is owned by the **server**: it is set by the server's "you are now spectating" message and re-asserted in every player-state update. A player cannot be alive and flagged as a spectator at the same time, a dead player waiting to respawn is not flagged, and a client that tampers with the flag is overruled on the next update (and is sent to the death screen while it is set). The patch adds no new information to the client and honours the host's **Friendly Tags** server setting: if the host turns friendly tags off, spectator tags go off too.

Known cosmetic limit: on some mods the health divisor is larger than a player's real maximum, so full health can read below 100 % (87 % on the TAC mod). The bar is still proportional.

## How to apply

```
python scripts/patch_spectator_client.py jointops.exe jointops_spectator.exe
```

Applies to a stock 1.7.5.7 client, an LAA client, or one carrying [patch 10](10-grass-128m.md). Everyone who wants to cast uses the patched exe; nobody else needs it. Once in the server, join without picking a team to spectate. If the tags do not appear, cycle **K** (Friendly Tags) once; the patch treats "off" as "on" for spectators, but the other modes are honoured.

## Verification

- Applied to the 128 m-grass client (`060c96a9…`) the script reproduces the live build byte for byte (`e9a77dec…`).
- Every code change was run in a CPU emulator against fabricated data before the first in-game test.
- In game (2026-09-25, 2-4 players): blue and red tags, bars changing colour with damage, percentage on the selected player, spectator chat both ways with the server patch in place.

## History

Found over two evenings by reading the stock code rather than adding an overlay: the game already knew how to draw and colour these tags for a spectator, only the call was missing. Along the way a stock crash was found and fixed on the server side ([patch 14](14-spectator-chat-server.md)). The mechanism notes are kept out of this public page on purpose.
