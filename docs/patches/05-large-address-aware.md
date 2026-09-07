# Large Address Aware (server / client)

**Status:** verified, live. **Script:** [`scripts/patch_large_address_aware.py`](../../scripts/patch_large_address_aware.py)

## What it does

Sets the `IMAGE_FILE_LARGE_ADDRESS_AWARE` flag (`0x0020`) in the PE header. Without it, a 32-bit process is limited to 2 GB of user-mode virtual address space. With it, on a 64-bit Windows host the process can use up to 4 GB.

This is a prerequisite for the [2 GB memory cap](04-memory-2gb.md) patch to have any effect.

## The patch

The flag lives in the two-byte **Characteristics** field of the COFF file header, which is the last field of that header (at PE signature + 22). The patcher locates it from the header rather than a fixed offset and ORs in `0x0020`. Retail reads `0x0103`; after the patch it reads `0x0123`.

The tool is idempotent: if the flag is already set it copies the file unchanged and says so.

## How to apply

```
python scripts/patch_large_address_aware.py jointops.exe jointops_laa.exe
```

## Notes

This is a pure header change, not a code patch, so it is safe and reversible and does not affect gameplay by itself. It only unlocks address space that other patches (or the OS under memory pressure) can then use.
