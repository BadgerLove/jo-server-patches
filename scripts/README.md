# Patcher scripts

Small Python 3.9+ tools that apply one patch each to a copy of an executable you supply. They never modify the input; they write a new output file. Every script asserts the original bytes first and exits without writing if they do not match, so a wrong or already-patched file is rejected safely.

## Requirements

- Python 3.9 or newer. No third-party packages.
- Your own legally owned `jointops.exe` (retail v1.7.5.7). No game files are included here.

Run scripts from inside this `scripts/` directory (they import the shared helper `patch_util.py`).

## Scripts

| Script | Side | Patch |
|--------|------|-------|
| `patch_admin_crash.py` | server | admin client-table crash fix |
| `patch_vehicle_weapon.py` | client | vehicle-seat weapon restore fix |
| `patch_spawn_protection.py` | server | spawn-protection duration (seconds arg) |
| `patch_memory_2gb.py` | both | 512 MB to 2 GB heap cap |
| `patch_large_address_aware.py` | both | set the LAA PE flag |
| `patch_packet_rate.py` | server | network send rate (32/62/125 arg) |
| `patch_grass128.py` | client | 128 m grass (visual) |
| `patch_fps_lock.py` | server | lock main loop to a chosen FPS; then set `lock_framerate = 7` in game.cfg for ~125 |

`patch_util.py` is the shared engine: it resolves virtual addresses to file offsets from the PE headers, verifies every site, then applies all changes and prints the input/output SHA-256.

Unlimited FPS ([docs](../docs/patches/06-unlimited-fps.md)), Bigbuf ([docs](../docs/patches/08-network-bigbuf.md)) and the NWU fix ([docs](../docs/patches/09-nwu-hole-skip.md)) are documented but do not ship an automated patcher yet; see their pages for why.

## Example

```
# make a 2 GB, large-address-aware server exe
python patch_memory_2gb.py            jointops.exe        jointops_a.exe
python patch_large_address_aware.py   jointops_a.exe      jointops_b.exe
python patch_admin_crash.py           jointops_b.exe      jointops_server.exe
```

Each step prints the byte ranges it changed and the resulting hash. Always keep your original.

## A note on chaining

Each script reads and writes a whole file, so chain them by feeding one output into the next, as above. Order does not matter for independent patches; the asserts protect you either way.
