# 128 m grass (client, visual)

**Status:** verified, live. **Script:** [`scripts/patch_grass128.py`](../../scripts/patch_grass128.py)

## What it does

Extends ground grass from the retail 42 m draw distance out to 128 m, with matching density, for a much richer battlefield. It is purely cosmetic and client-side: it does not change hitboxes, cover, gameplay, or anything the server sees. A player on a stock client just sees the normal short grass.

## The changes

All asserted before writing:

| Target | VA | Change |
|--------|----|--------|
| collection radius | `0x7DEA3C` (.rdata float) | `42.0` to `128.0` |
| fade start | `0x60A45D` (fld operand) | redirect to a shared `64.0` constant |
| fade slope | `0x7DF1BC` (.rdata float) | `1/22` to `1/(128-64)` |
| vertex-buffer budget x4 | `0x5FF963/73/83/93` | `0xFFFF` to `0x3FFFFF` |
| per-frame new-cell bound | hook `0x601BC5` into cave `0x7472D0` | cap new cells at 64 per frame |

The last item is the important stability piece. Extending the radius alone makes a sudden view change (cresting a hill, or the grass cache being cleared) enqueue far more new grass cells in one frame than the slot pool holds, which overflows and crashes. The code cave bounds the number of new cells accepted per frame, so it fills in over a few frames instead.

## Do not

Do not reuse the `.text` tail at `0x794DF0` as a code cave on client builds. Anti-cheat hook DLLs and the [NWU fix](09-nwu-hole-skip.md) live there. This patch uses the `int3` padding at `0x7472D0` instead.

## How to apply

```
python scripts/patch_grass128.py jointops.exe jointops_grass128.exe
```

Base is a stock 1.7.5.7 client with the LAA flag set.

## Anti-cheat note

Only the server can enforce which client build a player runs (for example PunkBuster MD5 tool checks). A player on a stock client is not broken by others running this; they simply see less grass.

## Verification

Applying this to the stock LAA client reproduces the live "v9" grass build byte for byte.
