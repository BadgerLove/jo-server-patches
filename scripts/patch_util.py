"""Shared helpers for the JO patcher scripts.

Design goals:
  * Never modify the input file. Always read input, write a new output.
  * Refuse to write unless every expected original byte is present, so a
    wrong or already-patched file fails loudly instead of being corrupted.
  * Resolve virtual addresses to file offsets from the PE headers, so the
    scripts do not depend on a hard-coded section layout.

A "patch" is a list of Patch(va, old, new) records. `old` and `new` are equal
length byte strings. The engine asserts `data[off:off+len(old)] == old` for
each record before applying any of them.
"""
from __future__ import annotations

import hashlib
import struct
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Patch:
    va: int          # virtual address (image-base relative address in memory)
    old: bytes       # exact original bytes expected at this location
    new: bytes       # replacement bytes (must be the same length as old)
    note: str = ""

    def __post_init__(self):
        if len(self.old) != len(self.new):
            raise ValueError(f"length mismatch at {self.va:#x}: {len(self.old)} != {len(self.new)}")


def _sections(data: bytes):
    """Yield (virtual_addr, virtual_size, raw_offset) for each PE section."""
    pe = struct.unpack_from("<I", data, 0x3c)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("not a PE file")
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    image_base = struct.unpack_from("<I", data, pe + 24 + 28)[0]
    first = pe + 24 + opt
    for i in range(nsec):
        o = first + i * 40
        _vs, va, _rs, ro = struct.unpack_from("<IIII", data, o + 8)
        yield image_base + va, _vs, ro


def va_to_offset(data: bytes, va: int) -> int:
    for sec_va, sec_vs, sec_ro in _sections(data):
        if sec_va <= va < sec_va + sec_vs:
            return sec_ro + (va - sec_va)
    raise ValueError(f"VA {va:#x} is not inside any section")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def apply(in_path: str, out_path: str, patches: list[Patch]) -> None:
    data = bytearray(open(in_path, "rb").read())
    print(f"input  {in_path}")
    print(f"       sha256 {sha256(bytes(data))}")

    # Phase 1: verify every site before touching anything.
    plan = []
    for p in patches:
        off = va_to_offset(bytes(data), p.va)
        found = bytes(data[off:off + len(p.old)])
        if found != p.old:
            sys.exit(
                f"ABORT: unexpected bytes at VA {p.va:#x} (file {off:#x})\n"
                f"  expected {p.old.hex(' ')}\n"
                f"  found    {found.hex(' ')}\n"
                f"  (wrong build, or already patched)"
            )
        plan.append((off, p))

    # Phase 2: apply.
    changed = []
    for off, p in plan:
        data[off:off + len(p.new)] = p.new
        changed.append(off)
        tag = f"  {p.note}" if p.note else ""
        print(f"  patched VA {p.va:#08x} (file {off:#08x}) {p.old.hex()} -> {p.new.hex()}{tag}")

    open(out_path, "wb").write(data)
    print(f"output {out_path}")
    print(f"       sha256 {sha256(bytes(data))}")
    print(f"       {len(changed)} byte-range(s) changed")


def main(patches: list[Patch], usage: str) -> None:
    if len(sys.argv) != 3:
        sys.exit(usage)
    apply(sys.argv[1], sys.argv[2], patches)
