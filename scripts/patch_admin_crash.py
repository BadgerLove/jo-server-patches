"""Fix the empty-server crash caused by the remote-admin client table.

CAdminServer_AcceptConnection grows its array of connected admin clients when
the connection count exceeds capacity. Each client slot is 64 bytes, but the
grow path copies only count*4 bytes of the old array into the new one, leaving
every existing slot filled with uninitialised heap. A later admin operation
then dereferences a garbage pointer in one of those slots and the server
crashes (see docs/patches/01-admin-port-crash-fix.md).

Fix: change the copy length from count*4 to count*64.
  VA 0x4056E6:  03 C0 03 C0  (add eax,eax ; add eax,eax  = eax*4)
            ->  C1 E0 06 90  (shl eax,6 ; nop            = eax*64)

Same length, four bytes, nothing else touched.

Usage:  python patch_admin_crash.py <in.exe> <out.exe>
"""
from patch_util import Patch, main

PATCHES = [
    Patch(
        va=0x4056E6,
        old=bytes.fromhex("03c003c0"),
        new=bytes.fromhex("c1e00690"),
        note="admin client-table grow: copy count*64 not count*4",
    ),
]

if __name__ == "__main__":
    main(PATCHES, __doc__)
