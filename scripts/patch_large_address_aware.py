"""Set the Large Address Aware (LAA) flag in the PE header.

Without this flag a 32-bit process is limited to 2 GB of virtual address space,
so the 2 GB heap patch cannot actually be used. Setting
IMAGE_FILE_LARGE_ADDRESS_AWARE (0x0020) in the COFF Characteristics field lets
the process use the larger user-mode address space on a 64-bit OS.

This edits the PE header, not a code section, so it is located from the header
rather than a fixed offset. If the flag is already set the file is copied
unchanged and a note is printed.

Full write-up: docs/patches/05-large-address-aware.md

Usage:  python patch_large_address_aware.py <in.exe> <out.exe>
"""
import struct
import sys

from patch_util import sha256

LAA = 0x0020


def build(in_path, out_path):
    data = bytearray(open(in_path, "rb").read())
    print(f"input  {in_path}\n       sha256 {sha256(bytes(data))}")
    pe = struct.unpack_from("<I", data, 0x3c)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        sys.exit("ABORT: not a PE file")
    ch_off = pe + 4 + 18            # Characteristics: last 2 bytes of the COFF header
    ch = struct.unpack_from("<H", data, ch_off)[0]
    if ch & LAA:
        print(f"Characteristics 0x{ch:04x} already Large Address Aware; copying unchanged")
    else:
        new = ch | LAA
        struct.pack_into("<H", data, ch_off, new)
        print(f"  Characteristics 0x{ch:04x} -> 0x{new:04x} (set LAA) at file 0x{ch_off:x}")
    open(out_path, "wb").write(data)
    print(f"output {out_path}\n       sha256 {sha256(bytes(data))}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    build(sys.argv[1], sys.argv[2])
