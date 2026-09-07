"""Set the network send-hold-off (server packet send rate).

A single byte in NapiNPServer_GetSendHoldoffTicks controls how many scheduler
ticks the server waits between network sends. Lowering it makes the server send
position updates more often, which players perceive as smoother movement and
hit registration.

  VA 0x4C4B13 (file 0x0C4B13):  byte = send hold-off in 62.5 Hz game updates
    0x04  hold-off 4  ->  ~16 packets/sec per direction per client
    0x02  hold-off 2  ->  ~31 packets/sec per direction   (retail default)
    0x01  hold-off 1  ->  ~62 packets/sec per direction

Per direction, packets/sec = 62.5 / hold-off (measured: hold-off 2 gave a flat
31/s each way in a client-side capture filtered to the game conversation). A
capture that does not separate directions shows about double; earlier notes
quoting "62 / 125" were both directions summed. Filter your capture to the game
port and one client: an idle server's NIC (websites, other services, an open
Remote Desktop session) can add hundreds of unrelated packets a second.

This is the *network send* cadence only. The game-logic step is a fixed 16 ms
(62.5 Hz) in every build and is not changed by this byte or by the FPS lock. An
earlier note calling this a "tick divisor / 1000 Hz internal" was wrong; the
true offset and meaning were confirmed by diffing the 32/64/125 builds.

Higher send rates use more upload bandwidth and CPU. 125 is fine on a LAN or a
well-connected host; test before using it on a constrained line.

Full write-up: docs/patches/07-packet-send-rate.md

Usage:  python patch_packet_rate.py <in.exe> <out.exe> [32|62|125]
        the argument keeps the old naming: 125 = hold-off 1, 62 = hold-off 2,
        32 = hold-off 4. Default 125 (hold-off 1).
"""
import sys

from patch_util import Patch, apply

VA = 0x4C4B13
RATE_TO_BYTE = {32: 0x04, 62: 0x02, 125: 0x01}
KNOWN = {0x04, 0x02, 0x01}


def build(in_path, out_path, target):
    if target not in RATE_TO_BYTE:
        sys.exit(f"target must be one of {sorted(RATE_TO_BYTE)}")
    data = open(in_path, "rb").read()
    from patch_util import va_to_offset
    cur = data[va_to_offset(data, VA)]
    if cur not in KNOWN:
        sys.exit(f"ABORT: unexpected current value 0x{cur:02x} at VA {VA:#x} (wrong build?)")
    new = RATE_TO_BYTE[target]
    apply(in_path, out_path, [
        Patch(va=VA, old=bytes([cur]), new=bytes([new]),
              note=f"send hold-off -> ~{ {32:16,62:31,125:62}[target] } packets/sec per direction"),
    ])


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    build(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) == 4 else 125)
