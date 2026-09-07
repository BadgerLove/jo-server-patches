# Empty-server crash: full analysis

A worked example of diagnosing the [admin-port crash](../patches/01-admin-port-crash-fix.md) from a collection of SYSDUMPs. This is the reasoning that led to the four-byte fix, kept as a reference for how to approach these.

## The report

A dedicated server crashed and went offline every one to four days. It only happened when the server was **empty**, never when it was full. A monitor archived every SYSDUMP, giving a set spanning several weeks.

## Sorting the dumps

After discarding the dumps taken at 0 to 2 minutes uptime (those were build-swap tests, not real crashes), the real crashes fell into two families:

**Family A — bad pointer in the string formatter.** EIP `0x007773DA`, a byte-scan loop (`cmp byte [eax], 0`). The registers showed a garbage pointer where a string was expected, and the faulting addresses often looked like ASCII fragments. The stack always contained the admin command dispatcher calling `fprintf(log, "User command (%s) - %s", ...)`. So a `%s` argument, the username pointer stored on a client slot, was garbage.

**Family B — heap free of a corrupt block.** EIP inside ntdll (addresses like `0x774A7D51`, `0x772F7D51`, `0x77AF7D51` — the same function, rebased per boot by ASLR). The instruction bytes `80 7F 07 05` (`cmp byte [edi+7], 5`) are a heap-chunk flag check inside the free path. The stack always showed the admin server's disconnect handler calling `free` on a client's receive buffer. So the buffer pointer being freed was garbage.

Two faults, one cause: both dereference a bad pointer that lives on an admin **client slot**.

## Finding the corruption

The client slots are 64 bytes each, in an array that grows as connections are accepted. Disassembling the grow path showed:

```
mov eax, [count]
add eax, 5
imul 0x40             ; allocate (count+5)*64  — correct
call operator_new
...
mov eax, [count]
add eax, eax
add eax, eax          ; eax = count*4          — the bug
push eax              ; memcpy length
call memcpy           ; copies count*4, not count*64
```

The new array is the right size, but only `count*4` bytes are copied in. Every slot past the first fraction is uninitialised heap: a garbage buffer pointer (Family B on disconnect) and a garbage username pointer (Family A on the next logged command).

## Why empty, why days

The table only grows when concurrent connections exceed capacity, which grows in steps of five. The admin tools polling the server leak slots (see [admin protocol](admin-protocol.md): a graceful close is not reaped), so on an idle server the slot count climbs steadily until a growth fires and corrupts the table. On a busy server the box gets cycled long before that, which is why only empty servers died, and only after days.

## The fix

Change the copy length from `count*4` to `count*64`, four bytes:

```
0x4056E6:  03 C0 03 C0   (add eax,eax; add eax,eax)  ->  C1 E0 06 90  (shl eax,6; nop)
```

Applying this reproduces the live server build exactly. With admin tools also closing abortively so the table never grows, the bug cannot trigger even on an unpatched binary.

## Lessons

- Keep crash dumps as text and archive them; a set beats a single dump.
- Match system-DLL crashes on the instruction bytes, not the address (ASLR moves the address).
- Two different-looking faults can be one root cause; look for the common object on the stack.
- Reproduce the fix against the real binary (byte-for-byte) before trusting it.
