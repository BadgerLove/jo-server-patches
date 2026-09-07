# 2 GB memory cap (server / client)

**Status:** verified, live. **Script:** [`scripts/patch_memory_2gb.py`](../../scripts/patch_memory_2gb.py)

## What it does

Raises the heap cap from 512 MB to 2 GB. On a busy server the 512 MB limit plus OS and DLL overhead can exhaust the address space; lifting it removes a class of memory-pressure instability.

## Why earlier attempts failed

The obvious target is the connection-speed profile table, which maps a bandwidth profile to a memory limit. Patching only that does nothing, because two global heap stores write 512 MB independently during init. All four sites must change together.

## The patch

Each site loads or stores the 32-bit value `0x20000000` (512 MB), which becomes `0x80000000` (2 GB). Stored little-endian this is the dword `00 00 00 20` to `00 00 00 80`; only the high byte moves. The addresses below point at the immediate itself (verified by disassembly), not the instruction start.

| VA | Instruction | Purpose |
|----|-------------|---------|
| `0x69813B` | `mov eax, imm32` | connection-speed profile table |
| `0x453CC6` | `mov eax, imm32` | config lookup |
| `0x4DE56E` | `mov dword [0x00B764A8], imm32` | global heap store 1 |
| `0x5D1332` | `mov dword [0x02BE0F78], imm32` | global heap store 2 |

## Required companion

A 32-bit process cannot use more than 2 GB of address space unless it is **Large Address Aware**. Run [`patch_large_address_aware.py`](05-large-address-aware.md) as well, or the raised cap has no effect.

## Note on SYSDUMP

The SYSDUMP "Allocated:" line reads a *separate* display variable, not these globals, and is not changed here. After patching, the server really has 2 GB but the crash dump may still print the old figure. That display value cannot be safely raised (doing so breaks startup), so it is left alone.

## How to apply

```
python scripts/patch_memory_2gb.py jointops.exe jointops_2gb.exe
python scripts/patch_large_address_aware.py jointops_2gb.exe jointops_2gb_laa.exe
```

## Verification

The tool asserts `00 00 00 20` at all four sites, so it correctly refuses a file that is already 2 GB or is the wrong build.
