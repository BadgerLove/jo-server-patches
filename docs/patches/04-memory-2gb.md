# Mission memory arena: 512 MB / 1 GB (server / client)

**Status:** verified, live. **Script:** [`scripts/patch_fastmem_arena.py`](../../scripts/patch_fastmem_arena.py)

**This page replaces the "2 GB memory cap" patch.** The original patch 04 did not change the game's memory limit. The adjustments are listed below; the old sites, the reason they looked right, and the revert tool are at the end.

## What it does

Joint Operations keeps all mission data in one fixed-size arena reserved at start-up by `FastMem_Init`. Its size is a single global, `dwSize = [0x03342E7C]`, written once in `Game_ParseCommandLineAndInit`:

```
VA 0x4A7CDD : mov dword [0x03342E7C], 0x0C000000    ; 192 MB (retail)
              imm32 at VA 0x4A7CE3, file offset 0xA7CE3
```

That number is the cap. The SYSDUMP line `Memory Usage  Allocated:0C000000h` prints it, and the mission loader logs "Mission is too large / Remove some object types and re-export" when `dwSize` minus used bytes drops under 12 MB.

The patch changes that one immediate:

| `--size` | Value | Notes |
|---|---|---|
| `512` (default) | `0x20000000` | The FMJ server has run at exactly this value since 2026. A busy 125 Hz map uses about 210 MB of it. |
| `1024` | `0x40000000` | Needs [Large Address Aware](05-large-address-aware.md) and a 64-bit host. Started and ran the FMJ server on 9 September 2026. |

One byte actually changes on disk (`0xA7CE6`: `0C` to `20` or `40`).

**2 GB is not offered.** Measured on 64-bit Windows: a 32-bit LAA process reserves and commits 1792 MB fine, 1920 MB only by landing above the 2 GB address line, and 2047 MB / 2048 MB fail outright. The game's allocator also treats the size as signed. `0x80000000` is a guaranteed start-up crash. 1 GB is the ceiling. A 1920 MB build was briefly considered and withdrawn untested: the arena would sit above the 2 GB address line where the game's signed pointer maths is unproven, and nothing needs it.

## How to apply

```
python scripts/patch_fastmem_arena.py jointops.exe jointops_512.exe
python scripts/patch_fastmem_arena.py jointops.exe jointops_1gb.exe --size 1024
python scripts/patch_large_address_aware.py jointops_1gb.exe jointops_1gb_laa.exe
```

The tool asserts `00 00 00 0C` at the site, so it refuses an already-patched file or the wrong build.

## onHook users: read this

onHook (the `binkw32.dll` proxy from OpenNova) patches this same site at runtime. It finds it by scanning for the retail bytes, including the `0C`, and **aborts the whole DLL if the scan misses**: the server reports "Failed to set up hooks" and Windows refuses to start the process (`0xC0000142`). So:

- With onHook loaded, run the **stock** arena byte. onHook sets 512 MB itself.
- To run a bigger arena under onHook, the constant onHook writes has to change (it is a hard-coded `0x20000000` inside the DLL), or ask for a configurable size. This exe patch is for bare servers and clients only.

## Verification

- `SYSDUMP.TXT` / status: `Memory Usage  Allocated:20000000h` (or `40000000h`).
- Disassemble VA `0x4A7CDD` and confirm `mov dword [0x3342E7C], 0x20000000`.
- Process private bytes rise by roughly the arena size once a map is loaded.

## The adjustment from the original patch 04

The original patch changed four immediates that each held `0x20000000` (`0x69813B`, `0x453CC6`, `0x4DE56E`, `0x5D1332`) to `0x80000000`, calling them a 512 MB heap cap. With the exe decompiled they are, in order: a D3DX shader flag, an event-trigger constant, a camera angle clamp (`0x20000000` = 45° in NovaLogic's angle units) and a minimap colour. None of them is memory. On a dedicated server they do nothing; on a client the clamp widens from ±45° to ±180°.

Why it passed as verified: the server it was tested on runs onHook, which raises the real arena to 512 MB at runtime. The server genuinely had more memory, the SYSDUMP said `Allocated:20000000h`, and the exe patch got the credit. The `Allocated:` value was then written off as a "display variable" because raising it to `0x80000000` crashed at start-up, which was the 2 GB reservation failing, not the site being wrong.

**Adjustments made (JOexeFIX v3, 9 September 2026):**

1. The four original sites are put back to retail on every shipped exe. Tool: [`scripts/revert_memory_2gb.py`](../../scripts/revert_memory_2gb.py) (asserts `0x80000000` at all four, writes `0x20000000`).
2. The real arena is set with `patch_fastmem_arena.py`: 512 MB for the standard pack, 1 GB as an option.
3. The client is rebuilt without the camera-clamp side effect.
4. The SYSDUMP note on this page ("separate display variable, cannot be raised") is withdrawn. It prints the cap.

Rebuilding JOexeFIX v3 from a v2 exe is therefore: `revert_memory_2gb.py`, then `patch_fastmem_arena.py --size 512` or `--size 1024`. Same hashes as the published zip.

## Related

- [Large Address Aware](05-large-address-aware.md) is required for 1 GB and still recommended for 512 MB.
- [SYSDUMP format](../systems/sysdump-format.md)
