# Delta IA-HMI Lua Patterns

Use these as copy-paste starting points for DOPSoft Lua.

## One-Shot Button Handler

Use maintained buttons as triggers. Clear the bit after the action.

```lua
while true do
    if mem.inter.ReadBit(10, 0) == 1 then
        ret = mem.inter.Write(100, 123)
        mem.inter.Write(101, ret)
        mem.inter.WriteBit(10, 0, 0)
    end

    sys.Sleep(50)
end
```

Element setup:

- Maintained button write address: `$10.0`
- Numeric display for result: `$100`
- Numeric display for return code: `$101`

## Read PLC Register Through Link

```lua
while true do
    if mem.inter.ReadBit(20, 0) == 1 then
        value = link.Read("{Link2}1@D1")
        mem.inter.Write(200, value)
        mem.inter.WriteBit(20, 0, 0)
    end

    sys.Sleep(100)
end
```

Change `"{Link2}1@D1"` to match the DOPSoft link number, station number, and PLC address.

## Write PLC Bit Through Link

```lua
while true do
    if mem.inter.ReadBit(30, 0) == 1 then
        ret = link.WriteBit("{Link2}1@M100", 1)
        mem.inter.Write(300, ret)
        mem.inter.WriteBit(30, 0, 0)
    end

    sys.Sleep(100)
end
```

## Copy PLC Words To HMI Internal Memory

```lua
while true do
    if mem.inter.ReadBit(40, 0) == 1 then
        ret = link.CopyToInter("{Link2}1@D100", 1000, 10)
        mem.inter.Write(1040, ret)
        mem.inter.WriteBit(40, 0, 0)
    end

    sys.Sleep(100)
end
```

This copies 10 words from PLC `D100..D109` to HMI `$1000..$1009`.

## Copy HMI Internal Memory To PLC

```lua
while true do
    if mem.inter.ReadBit(41, 0) == 1 then
        ret = link.CopyFromInter("{Link2}1@D200", 1100, 10)
        mem.inter.Write(1140, ret)
        mem.inter.WriteBit(41, 0, 0)
    end

    sys.Sleep(100)
end
```

This copies 10 words from HMI `$1100..$1109` to PLC `D200..D209`.

## ASCII Read And Write

```lua
while true do
    if mem.inter.ReadBit(50, 0) == 1 then
        name = mem.inter.ReadAscii(1000, 20)
        upper = string.upper(name)
        ret = mem.inter.WriteAscii(1020, upper, string.len(upper))
        mem.inter.Write(1050, ret)
        mem.inter.WriteBit(50, 0, 0)
    end

    sys.Sleep(100)
end
```

Important: quote literal strings. `string.upper(Delta)` is wrong if `Delta` is not a defined variable; use `string.upper("Delta")`.

## Recipe Read

```lua
index = 1

while true do
    if mem.inter.ReadBit(60, 0) == 1 then
        ret, value = recipe.GetRcpWord(index)
        mem.inter.Write(600, ret)
        mem.inter.Write(601, value)
        mem.inter.WriteBit(60, 0, 0)
    end

    sys.Sleep(100)
end
```

Element setup usually includes `RCPNO` and `RCPG` numeric entries when switching normal recipe number/group.

## Enhanced Recipe Write

```lua
while true do
    if mem.inter.ReadBit(61, 0) == 1 then
        index = 4
        ret = recipe.SetEnRcpAscii(index, "PROFILE_A", string.len("PROFILE_A"))
        mem.inter.Write(610, ret)
        mem.inter.WriteBit(61, 0, 0)
    end

    sys.Sleep(100)
end
```

Element setup usually includes `ENRCPNO` and `ENRCPG` numeric entries when switching enhanced recipe number/group.

## Open Screen

```lua
while true do
    if mem.inter.ReadBit(70, 0) == 1 then
        ret = screen.Open(2)
        mem.inter.Write(700, ret)
        mem.inter.WriteBit(70, 0, 0)
    end

    sys.Sleep(50)
end
```

## COM RS485 Send And Receive

```lua
open_ret = com.Open(2, "RS485", 8, "NONE", 1, 9600, "OFF")
mem.inter.Write(800, open_ret)

while true do
    if mem.inter.ReadBit(80, 0) == 1 then
        buffer = mem.inter.ReadAscii(1000, 10)
        ret = com.WriteChars(2, buffer, string.len(buffer), 3000)
        mem.inter.Write(801, ret)
        mem.inter.WriteBit(80, 0, 0)
    end

    if mem.inter.ReadBit(80, 1) == 1 then
        bytes_read, buffer = com.ReadChars(2, 10, 3000)
        mem.inter.Write(802, bytes_read)
        mem.inter.WriteAscii(1010, buffer, string.len(buffer))
        mem.inter.WriteBit(80, 1, 0)
    end

    sys.Sleep(100)
end
```

## TCP Client Send

```lua
socket = -1

while true do
    if mem.inter.ReadBit(90, 0) == 1 then
        socket = tcp.Open("192.168.1.100", 502)
        mem.inter.Write(900, socket)
        mem.inter.WriteBit(90, 0, 0)
    end

    if mem.inter.ReadBit(90, 1) == 1 then
        if socket > 0 then
            buffer = mem.inter.ReadAscii(1100, 10)
            ret = tcp.Write(socket, buffer, string.len(buffer), 1000)
            mem.inter.Write(901, ret)
        else
            mem.inter.Write(901, -999)
        end
        mem.inter.WriteBit(90, 1, 0)
    end

    if mem.inter.ReadBit(90, 2) == 1 then
        if socket > 0 then
            ret = tcp.Close(socket)
            mem.inter.Write(902, ret)
        end
        mem.inter.WriteBit(90, 2, 0)
    end

    sys.Sleep(100)
end
```

## Runtime Debug Checklist

When a script fails on HMI:

1. Check for unquoted strings and misspelled variables.
2. Check capitalization: `mem.inter.WriteBit`, not `mem.Inter.writebit`.
3. Add return-code registers after every external write/read.
4. Clear one-shot trigger bits so the same action does not loop forever.
5. Add `sys.Sleep(50)` or `sys.Sleep(100)` inside cyclic loops.
6. For PLC link failures, verify DOPSoft link number, station number, PLC address syntax, and communication setup.
7. For ASCII, verify byte length and target character entry length.
8. For recipe operations, verify recipe type and that `RCPNO/RCPG` or `ENRCPNO/ENRCPG` elements exist when needed.
9. For COM/TCP, write socket/port status and byte counts to debug `$` registers.
10. If still uncertain, search `references/delta-lua-manual.txt` for the exact command and return code table.
