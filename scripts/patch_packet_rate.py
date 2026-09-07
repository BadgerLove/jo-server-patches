"""Set the network send-hold-off (server packet send rate).

A single byte in NapiNPServer_GetSendHoldoffTicks controls how many scheduler
ticks the server waits between network sends. Lowering it makes the server send
position updates more often, which players perceive as smoother movement and
hit registration.

  VA 0x4C4B13 (file 0x0C4B13):  byte
    0x04  ~32 packets/sec
    0x02  ~62 packets/sec   (retail default)
    0x01  ~125 packets/sec

Observed packet rates are from Wireshark captures on a live server; the exact
Hz depends on the scheduler. NOTE: this is the *network send* cadence only. The
game-logic step is a fixed 16 ms (62.5 Hz) in every build and is not changed by
this byte. An earlier note calling this a "tick divisor / 1000 Hz internal" was
wrong; the true offset and meaning were confirmed by diffing the 32/64/125
builds.

Higher send rates use more upload bandwidth and CPU. 125 is fine on a LAN or a
well-connected host; test before using it on a constrained line.

Full write-up: docs/patches/07-packet-send-rate.md

Usage:  python patch_packet_rate.py <in.exe> <out.exe> [32|62|125]
        default target is 125
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
              note=f"send hold-off -> ~{target} packets/sec"),
    ])


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    build(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) == 4 else 125)
