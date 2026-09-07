# Bigbuf network buffers (server)

**Status:** documented. No automated patcher yet (offsets not fully enumerated).

## What it does

Enlarges the network send and receive buffers from 64 KB to 256 KB. On a full server sending at a high packet rate, the 64 KB buffers can overflow and drop packets, which shows up as `NET INCOMING PACKET ERROR` and `NET OUTGOING PACKET ERROR` and as rubber-banding for players. Larger buffers absorb the bursts.

This pairs with the [packet send rate](07-packet-send-rate.md) patch: running at ~125 packets/sec with a high player count is exactly when the stock buffers overflow.

## Status and caveat

This change is present in the project's combined server builds and is known to work, but the individual buffer-size sites have not yet been isolated into a clean, asserted offset table suitable for an automated patcher. It is documented here for completeness. If you are enlarging these buffers by hand, note that buffer size interacts with the heap cap: apply the [2 GB memory](04-memory-2gb.md) patch first so the larger allocations have room.

Contributions that pin down the exact offsets (with original and patched bytes, asserted against a stock 1.7.5.7 server) are welcome via an issue or pull request, so a `patch_bigbuf.py` can be added.

## Related

- [Packet send rate](07-packet-send-rate.md)
- [2 GB memory cap](04-memory-2gb.md)
