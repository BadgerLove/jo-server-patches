# Admin-port crash fix (server)

**Status:** verified, running live. **Script:** [`scripts/patch_admin_crash.py`](../../scripts/patch_admin_crash.py)

## Symptom

A dedicated server that is **empty** crashes and writes a SYSDUMP every one to four days, often after many hours of zero players. A populated server almost never hits it, because it gets cycled or restarted first. The crash address is not always the same, which makes it look random.

## Root cause

The remote-admin console (TCP port 4000, used by admin tools like WolfRAT and the server monitor) keeps a table of connected clients. Each client slot is 64 bytes. When the table needs to grow, `CAdminServer_AcceptConnection` allocates a correctly-sized new array but copies the old contents with the wrong length:

```
new = operator_new((count + 5) * 64)     ; correct size
memcpy(new, old, count * 4)              ; BUG: copies count*4, should be count*64
```

Only one sixteenth of each existing slot is preserved. Every slot past the first fraction is left as uninitialised heap, which contains a garbage receive-buffer pointer and a garbage username pointer. A later admin operation then either logs a command (dereferencing the bad username pointer while formatting `"User command (%s)"`) or frees the bad buffer pointer on disconnect. Both crash.

This is why the crash shows up as two different faults that are really one bug: a bad-pointer read in the string formatter, and a heap free of a corrupt block in ntdll.

The table only grows once concurrent connections exceed its capacity, which grows in steps of five. Admin tools that connect without cleanly reaping their slot (see the companion note below) leak slots until the table grows, and each growth corrupts it.

## The patch

Change the copy length from `count*4` to `count*64`.

| VA | File offset | Original | Patched | Meaning |
|----|-------------|----------|---------|---------|
| `0x4056E6` | `0x56E6` | `03 C0 03 C0` (`add eax,eax; add eax,eax`) | `C1 E0 06 90` (`shl eax,6; nop`) | copy count*64 |

Four bytes, same length, nothing else touched. The instruction after it (`push eax`) and all downstream code are unchanged.

## Companion fix: stop leaking slots

The server only frees a client slot when a read *errors*. A tool that closes its TCP connection gracefully (FIN) leaves the server's `recv` returning 0, which it does not treat as a disconnect, so the slot leaks. Admin tools should close **abortively** (send RST) so the server reaps the slot at once. Set `SO_LINGER` to 0 before closing:

```python
sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
sock.close()
```

With both the binary patch and abortive-closing tools, the table never grows into the buggy code and the crash cannot occur, even on an unpatched server. WolfRAT already does the abortive close; make sure any custom monitor does too.

## How to apply

```
python scripts/patch_admin_crash.py jointops.exe jointops_patched.exe
```

## Verification

Applying this to the retail-derived server build reproduces, byte for byte, the build that has been running live. See [the full analysis](../systems/empty-server-crash-analysis.md) for the crash-dump evidence across dozens of SYSDUMPs.
