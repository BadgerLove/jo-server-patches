# Remote admin protocol (TCP port 4000)

The dedicated server exposes a remote-admin console on TCP port 4000. This is what admin tools connect to. Understanding it is useful for writing tools and for the [admin-port crash](empty-server-crash-analysis.md).

## Framing

Every message is an 8-byte header followed by an ASCII payload.

- **Header:** a 4-byte magic and a 4-byte total length (little-endian). Different message directions use different magics (challenge, response, command).
- **Payload:** ASCII text, null-terminated for commands.

## Connection sequence

1. Client opens a TCP connection.
2. Server accepts it, allocates a client slot, and sends a 32-byte random challenge.
3. Client sends a login (username and password; the password step uses the challenge).
4. On success the server replies `OK - User: <name> successfully logged in.` and stores the account's permission bitmask on the slot.
5. Authenticated clients send commands; each is dispatched by a permission check.

A special unauthenticated `QUERY` returns a status line without logging in.

## Commands

Top-level verbs, each gated by a permission bit: `QUIT`, `GET`, `SET`, `MISSION`, `PLAYER`, `WEAPON`, `CMD`, `GOTO`, `CHAT`, `ADMINUSER`, `BANLIST`. Examples:

- `MISSION LIST` / `MISSION AVAILABLE` / `MISSION SETNEXT <index>` then `GOTO GAMESTATE` to cycle the map.
- `PLAYER LIST` / `PLAYER PUNT|BAN|KILL|SWAPTEAM|ZEROSCORE <id>`.
- `CHAT SEND <msg>` (payload limits apply; keep chat messages short to avoid overflowing the server's fixed receive buffer).

## Slot lifecycle and the leak trap

Client slots are 64 bytes each, held in a growable array. The server reaps a slot only when a socket read **errors**. A graceful TCP close (FIN) makes the server's `recv` return 0, which it does **not** treat as a disconnect, so the slot lingers. A tool that connects and closes politely on a timer leaks a slot every cycle.

To avoid the leak, close **abortively** (send RST) so `recv` returns an error and the slot is freed:

```python
sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
sock.close()
```

Leaked slots grow the client-table array, and the grow path has a bug that corrupts the table. See the [admin-port crash fix](../patches/01-admin-port-crash-fix.md).
