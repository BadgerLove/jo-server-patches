# SYSDUMP crash-dump format

When the server crashes it writes `SYSDUMP.TXT` to the game folder. It is the primary evidence for diagnosing a crash, so it is worth understanding.

## Layout

```
Context dump of Joint Operations: Typhoon Rising (V1.7.5.7) on <date>
Use map file <map>
Memory Usage   Allocated:<hex>h   Used:<hex>h   Pointers:<hex>h   Fragmentation:<hex>h
Execution time minutes: <min>, seconds: <sec>

In game state...
<LAN server | NovaWorld server>
Number of players: <n>, Max players: <n>
Mission: "<name>"
Expansion: "<id>"
Server uptime: <days> <hh:mm:ss>
Mission time: <days> <hh:mm:ss>
Game type: <type>

Last Network Packet : <n> msgs.  <n> bytes.

This program has caused an access violation exception at <addr>h
Attempting to <read from|write to> <addr>h

<register dump: EAX..EDI, EBP, ESP, EIP, EFlags, SegCS, SegSs>

Code bytes before EIP: <bytes>
Code bytes at EIP:     <bytes>

Stack: <raw stack words>
```

## What matters for diagnosis

- **`exception at <addr>`** is the faulting instruction (EIP). This is where the crash happened.
- **`Attempting to read/write <addr>`** is the bad pointer it touched.
- **`Code bytes at EIP`** identifies the exact instruction even without a map, and survives across builds. Keep this: it is the single most useful line.
- **The stack block** contains return addresses. Game-code return addresses (roughly `0x401000`–`0x795000` for a retail-derived build) let you walk back through the callers.
- **EIP inside a system DLL** (for example an address like `0x77xx7d51`) means the fault is in Windows code (often ntdll's heap routines), reached from the game. The DLL base moves per boot due to ASLR, so the same bug shows different absolute addresses across dumps; match on the instruction bytes, not the address.

## Tips

- Capture dumps as **text**, not screenshots. The stack block does not survive a screenshot.
- Note which executable build was live for each dump; the on-screen version string does not change between builds.
- Note whether the machine was minimised or the remote session disconnected at the time. Some crashes (a graphics device-reset fault in `d3d9.dll`) only happen on minimise and are unrelated to server-side bugs.

## See also

- [Empty-server crash: full analysis](empty-server-crash-analysis.md) — a worked example using a set of these dumps.
