# Joint Operations: Typhoon Rising — Server & Client Patch Library

A documented set of binary patches for **Joint Operations: Typhoon Rising / Escalation (v1.7.5.7)**, the 2004 NovaLogic tactical shooter, plus small Python tools that apply each patch to a copy of an executable you already own.

Every patch here was found by static analysis and disassembly, then verified against the running game. Each one is documented with its exact address, the original bytes, the patched bytes, and the reasoning. The patcher scripts assert the original bytes before changing anything, so they fail loudly on the wrong file instead of corrupting it.

> This repository distributes **no NovaLogic code, executables, or game assets.** It contains only documentation and patcher scripts. You supply your own legally owned `jointops.exe`. See [DISCLAIMER](#legal--disclaimer).

## Why this exists

The game has been out of official support for two decades. A small community still runs dedicated servers for it. Several long-standing bugs and hard limits (a memory cap, a decades-old empty-server crash, a vehicle weapon glitch present since launch) were never fixable without touching the binary. This is the write-up of that work so other admins can apply the same fixes and build on them.

## Patch index

| # | Patch | Side | What it fixes / adds | Status |
|---|-------|------|----------------------|--------|
| 1 | [Admin-port crash fix](docs/patches/01-admin-port-crash-fix.md) | Server | Stops the empty-server crash caused by the remote-admin client table corrupting itself | Verified, live |
| 2 | [Vehicle weapon restore fix](docs/patches/02-vehicle-weapon-restore.md) | Client | Leaving a vehicle seat no longer forces the weapon you last died with | Verified, live |
| 3 | [Spawn protection tuning](docs/patches/03-spawn-protection.md) | Server | Sets the post-respawn invulnerability window to any duration | Verified |
| 4 | [Mission memory arena 512 MB / 1 GB](docs/patches/04-memory-2gb.md) | Both | Raises the mission memory arena from the retail 192 MB (replaces the original "2 GB memory cap", which did not touch memory; revert tool included) | Verified, live |
| 5 | [Large Address Aware](docs/patches/05-large-address-aware.md) | Both | PE flag so the 32-bit process can use the larger address space | Verified, live |
| 6 | [Unlimited FPS (Sleep removal)](docs/patches/06-unlimited-fps.md) | Both | Removes the frame-timing Sleep bottleneck | Verified |
| 7 | [Packet send rate](docs/patches/07-packet-send-rate.md) | Server | Controls the network send-hold-off (observed ~62 vs ~125 packets/sec) | Verified |
| 8 | [Bigbuf network buffers](docs/patches/08-network-bigbuf.md) | Server | Enlarges send/receive buffers to cut packet loss on full servers | Documented |
| 9 | [NWU hole-skip](docs/patches/09-nwu-hole-skip.md) | Both | NovaWorld connection fix (community "Spaghetti" fix) | Documented |
| 10 | [128 m grass (TAC visual)](docs/patches/10-grass-128m.md) | Client | Extends grass draw distance and density | Verified, live |
| 11 | [125 FPS lock](docs/patches/11-fps-lock-125.md) | Server | Locks the main loop to a chosen frame rate (set `lock_framerate = 7` for ~125 FPS) while sleeping between frames, instead of the 62.5 FPS ceiling or a CPU-burning unlimited loop | Verified, live |
| 12 | [Configurable spawn protection](docs/patches/12-spawn-protection-config.md) | Server | Spawn-protection duration becomes a `game.cfg` setting (`e_spawn_protection = 5`), no rebuild per change | Verified, live |

Deeper reference material lives in [docs/systems/](docs/systems/):
- [SYSDUMP crash-dump format](docs/systems/sysdump-format.md)
- [Remote admin protocol (port 4000)](docs/systems/admin-protocol.md)
- [Empty-server crash: full analysis](docs/systems/empty-server-crash-analysis.md)

## How to apply a patch

You need Python 3.9+ and your own copy of the target executable.

```
python scripts/patch_admin_crash.py  path\to\jointops.exe  path\to\jointops_patched.exe
```

Each script prints the SHA-256 of the input and output and the list of byte offsets it changed. If the input does not contain the expected original bytes, it exits without writing anything. Nothing is ever done to the file you pass in; a new output file is written.

Addresses in the docs are given as both a **virtual address (VA)** and a **file offset**. For this build the `.text` section maps `VA = file_offset - 0x1000 + 0x401000`; the helper in [`scripts/patch_util.py`](scripts/patch_util.py) does the conversion from the PE headers so it works regardless.

## Build compatibility

The patches target retail **v1.7.5.7** (expansion `revx02`). Some server-side offsets sit in base game code and apply to a stock server exe; others were developed against a combined build (arena + packet-rate + NovaWorld fixes). Because every script asserts the original bytes first, an incompatible file is rejected safely rather than mangled. If an assert fails on your build, open an issue with the reported offset and bytes.

## Credits

- Reverse engineering, patches, docs: **BadgerLove / FMJ Squad**.
- NovaWorld connection ("NWU hole-skip") fix: community contributor "Spaghetti".
- Retail protocol correctness pass on the admin tooling: Taylor Finnell (Open Nova).

## Legal & disclaimer

Joint Operations: Typhoon Rising is © NovaLogic / its current rights holders. This project is an unofficial, non-commercial community effort and is not affiliated with or endorsed by them.

This repository contains **only** original documentation and patcher source code. It does **not** contain, and will never contain, any part of the game: no executables, no game data files, no decompiled source. To use these tools you must already own a legal copy of the game and supply your own executable. Patching your own copy is done at your own risk. Keep a backup.

Released under the [MIT License](LICENSE) for the documentation and scripts in this repo.
