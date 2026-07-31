# Delta IA-HMI Lua Quick Reference

Source: DELTA_IA-HMI_LUA_UM_EN_20211208.

## Lua Basics

| Topic | Delta Lua note |
|---|---|
| Comments | `-- single line`, `--[[ multi-line ]]` |
| Scope | Variables are global unless declared `local` |
| Case | Lua is case sensitive |
| Undefined variable | Can terminate the program with `Lua runtime error` |
| String literal | Always quote literal text: `string.upper("Delta")` |
| Main editor | DOPSoft: `Project > Program > Main` |

## Internal Memory `$` With `mem.inter`

| Task | Signature | Notes |
|---|---|---|
| Read word | `v = mem.inter.Read(index, [value_format])` | `index: 0..199999`, optional `"signed"` |
| Read dword | `v = mem.inter.ReadDW(index, [value_format])` | `index: 0..199998`, optional `"signed"` |
| Read float | `v = mem.inter.ReadFloat(index)` | `index: 0..199998` |
| Read bit | `b = mem.inter.ReadBit(index, bit)` | `bit: 0..15`, returns `1` or `0` |
| Read double | `v = mem.inter.ReadDouble(index)` | `index: 0..199996` |
| Read ASCII | `s = mem.inter.ReadAscii(start_index, string_len)` | `string_len` in bytes |
| Write word | `ret = mem.inter.Write(index, value)` | `ret: 1 success, 0 failure` |
| Write dword | `ret = mem.inter.WriteDW(index, value)` | `ret: 1 success, 0 failure` |
| Write float | `ret = mem.inter.WriteFloat(index, float_value)` | `ret: 1 success, 0 failure` |
| Write bit | `ret = mem.inter.WriteBit(index, bit, logic)` | `logic: 1 or 0` |
| Write double | `ret = mem.inter.WriteDouble(index, double_value)` | `ret: 1 success, 0 failure` |
| Write ASCII | `ret = mem.inter.WriteAscii(start_index, ascii_string, string_len)` | Appends `\0`; return is bytes written |

## Static Memory `$M` With `mem.static`

Use the same shape as `mem.inter`:

- `mem.static.Read`, `ReadDW`, `ReadFloat`, `ReadBit`, `ReadDouble`, `ReadAscii`
- `mem.static.Write`, `WriteDW`, `WriteFloat`, `WriteBit`, `WriteDouble`, `WriteAscii`

Static memory is for `$M` addresses.

## External Link Memory With `link`

Address format examples:

- Word/dword/float: `"{Link2}1@D1"`
- Bit: `"{Link2}1@M100"`

| Task | Signature | Notes |
|---|---|---|
| Read word | `v = link.Read(addr, [value_format])` | optional `"signed"` |
| Read dword | `v = link.ReadDW(addr, [value_format])` | optional `"signed"` |
| Read float | `v = link.ReadFloat(addr)` | single precision |
| Read bit | `b = link.ReadBit(addr)` | returns `1` or `0` |
| Read ASCII | `ascii, ret, errMsg = link.ReadAscii(addr, string_len)` | `ret: 1 success, 0 failure` |
| Read double | `v = link.ReadDouble(addr)` | 64-bit floating point |
| Write word | `ret = link.Write(addr, value_word)` | `ret: 1 success, 0 failure` |
| Write dword | `ret = link.WriteDW(addr, value_dword)` | `ret: 1 success, 0 failure` |
| Write float | `ret = link.WriteFloat(addr, value_float)` | `ret: 1 success, 0 failure` |
| Write bit | `ret = link.WriteBit(addr, value_bit)` | `value_bit: 1 or 0` |
| Write ASCII | `ret = link.WriteAscii(addr, ascii, ascii_len)` | UTF-8/ASCII bytes |
| Write double | `ret = link.WriteDouble(addr, value_double)` | 64-bit floating point |
| Copy HMI to PLC | `ret = link.CopyFromInter(addr, interMemIndex, wordLen)` | `$` to external |
| Copy PLC to HMI | `ret = link.CopyToInter(addr, interMemIndex, wordLen)` | external to `$` |
| Copy array | `ret = link.CopyArray(dst_addr, dst_offset, src_addr, src_offset, wordLen)` | addresses can be string or integer |

PLC program/password/station APIs also exist: `link.DownloadPLC`, `link.DownloadEthPLC`, `link.WritePasswordPLC`, `link.SetDefaultStationNo`, `link.SetHMIStationNo`, `link.CODESYSAppDownload`, `link.CODESYSAppUpload`. Search the manual for exact signatures before using them.

## Recipe APIs

| Task | Signature |
|---|---|
| Current recipe number index | `ret, noIdx = recipe.GetCurRcpNoIndex()` |
| Current recipe group index | `ret, gIdx = recipe.GetCurRcpGIndex()` |
| Read normal word | `ret, value = recipe.GetRcpWord(index)` |
| Read normal dword | `ret, value = recipe.GetRcpDWord(index, [value_format])` |
| Read normal float | `ret, value = recipe.GetRcpFloat(index)` |
| Current enhanced number name | `ret, noName = recipe.GetCurEnRcpNoName()` |
| Current enhanced group name | `ret, gName = recipe.GetCurEnRcpGName()` |
| Current enhanced number index | `ret, noIdx = recipe.GetCurEnRcpNoIndex()` |
| Current enhanced group index | `ret, gIdx = recipe.GetCurEnRcpGIndex()` |
| Read enhanced word | `ret, value = recipe.GetEnRcpWord(index)` |
| Read enhanced dword | `ret, value = recipe.GetEnRcpDWord(index, [value_format])` |
| Read enhanced float | `ret, value = recipe.GetEnRcpFloat(index)` |
| Read enhanced ASCII | `ret, str = recipe.GetEnRcpAscii(index)` |
| Read enhanced double | `ret, value = recipe.GetEnRcpDouble(index)` |
| Set normal word | `ret = recipe.SetRcpWord(index, word)` |
| Set normal dword | `ret = recipe.SetRcpDWord(index, dword)` |
| Set normal float | `ret = recipe.SetRcpFloat(index, floatValue)` |
| Set enhanced number name | `ret = recipe.SetCurEnRcpNoName(newName)` |
| Set enhanced group name | `ret = recipe.SetCurEnRcpGName(newName)` |
| Set enhanced word | `ret = recipe.SetEnRcpWord(index, word)` |
| Set enhanced dword | `ret = recipe.SetEnRcpDWord(index, dword)` |
| Set enhanced float | `ret = recipe.SetEnRcpFloat(index, floatValue)` |
| Set enhanced ASCII | `ret = recipe.SetEnRcpAscii(index, str, len)` |
| Set enhanced double | `ret = recipe.SetEnRcpDouble(index, doubleValue)` |
| Change normal recipe number | `ret = recipe.ChangeRcpNoIndex(noIdx)` |
| Change normal recipe group | `ret = recipe.ChangeRcpGIndex(gIdx)` |
| Change enhanced recipe number | `ret = recipe.ChangeEnRcpNoIndex(noIdx)` |
| Change enhanced recipe group | `ret = recipe.ChangeEnRcpGIndex(gIdx)` |

## Screen APIs

| Task | Signature | Notes |
|---|---|---|
| Open screen | `ret = screen.Open(screen_id)` | `screen_id: 1..65535` |
| Close sub screen | `ret = screen.CloseSub(screen_id)` | `screen_id: 1..65535` |
| Is opened | `ret = screen.IsOpened(screen_id)` | `1 open`, `0 not open` |
| Capture | `ret = screen.Capture(disk_ID)` | `2 USB`, `3 SD card` |

## System APIs

| Task | Signature |
|---|---|
| Delay | `sys.Sleep(time_ms)` |
| Uptime | `tick = sys.GetTick()` |
| Internal parameter | `value, ret = sys.GetInterParam("paraName")` |
| Buzzer | `sys.BuzzerOn(buzzerType)` where `0 off`, `1 on`, `2 keep on` |
| Date | `year, month, day, week = sys.GetDate()` |
| Date string | `dateStr = sys.GetDateString()` |
| Days since 1970-01-01 | `days = sys.GetDays(year, month, day)` |
| Seconds since 00:00:00 | `secs = sys.GetSecs(hour, minute, second)` |
| Time | `h, m, s = sys.GetTime()` |
| Convert days to date | `year, month, day = sys.ToDate(days)` |
| Convert seconds to time | `hour, minute, second = sys.ToTime(seconds)` |
| Disk space | `ret, total, free = sys.GetDiskSpace(disk_id)` where `2 USB`, `3 SD` |

## COM APIs

| Task | Signature |
|---|---|
| Open | `ret = com.Open(com_num, interface, databits, parity, stopbits, baudrate, flowcontrol)` |
| Read | `bytes_read, buffer = com.ReadChars(com_num, len, timeout)` |
| Write | `ret = com.WriteChars(com_num, buffer, len, timeout)` |
| Clear buffer | `ret = com.ClearBuffer(com_num, clear_type)` where `1 read`, `0 write` |
| Station check | `ret = com.StationCheck(com_num, station)` |
| Close | `ret = com.Close(com_num)` |
| Check alive | `ret = com.CheckAlive(modbus_mode, com_num, interface, databits, parity, stopbits, baudrate, flowcontrol, station, timeout)` |
| Station on/off | `ret = com.StationOn(com_num, station)`, `ret = com.StationOff(com_num, station)` |
| Status | `ret = com.GetStatus(com_num)` |

COM parameter values:

- `interface`: `"RS232"`, `"RS422"`, `"RS485"`
- `databits`: `7`, `8`
- `parity`: `"NONE"`, `"ODD"`, `"EVEN"`, `"MARK"`, `"SPACE"`
- `stopbits`: `1`, `2`
- `flowcontrol`: `"OFF"`, `"CTS_RTS"`
- `modbus_mode`: `"MODBUS_ASCII"`, `"MODBUS_RTU"`

## TCP APIs

| Task | Signature |
|---|---|
| Open | `socket = tcp.Open(ip, port)` |
| Read | `bytes_read, buffer = tcp.Read(socket, len, timeout)` |
| Write | `ret = tcp.Write(socket, buffer, len, timeout)` |
| Close | `ret = tcp.Close(socket)` |
| Max sockets | `count = tcp.GetMaxCount()` |
| Running sockets | `count = tcp.GetRunCount()` |
| Status | `status = tcp.GetStatus(socket)` |

Socket numbers are typically `1..8`. `tcp.Open` returns `>0` on success and negative codes on failure.

## UDP APIs

| Task | Signature |
|---|---|
| Open | `socket = udp.Open(ip, port, local_port)` |
| Read | `bytes_read, buffer = udp.Read(socket, len, timeout)` |
| Write | `ret = udp.Write(socket, buffer, len, timeout)` |
| Close | `ret = udp.Close(socket)` |
| Max sockets | `count = udp.GetMaxCount()` |
| Running sockets | `count = udp.GetRunCount()` |
| Status | `status = udp.GetStatus(socket)` |

Manual note: the UDP command-list table shows `udp.GeRunCount`, but the detailed command section uses `udp.GetRunCount()`. Prefer `udp.GetRunCount()`.

## Other Groups

- File: `file.Open`, `file.Read`, `file.ReadLine`, `file.Write`, `file.Length`, `file.GetLineCount`, `file.Seek`, `file.GetPos`, `file.GetError`, `file.Close`, `file.List`, `file.Export`, `file.Delete`, `file.DeleteDir`, `file.ToPDF`, `file.ToPrinter`, `file.ListExternal`, `file.Exist`, `file.PDFToPrinter`, `file.Copy`, `file.Move`.
- FileSlot: `fileslot.Read`, `fileslot.Write`, `fileslot.ReadValue`, `fileslot.WriteValue`, `fileslot.GetLength`, `fileslot.Remove`, `fileslot.Import`, `fileslot.Export`, `fileslot.SetName`, `fileslot.GetName`, `fileslot.GetID`.
- FTP: `ftpc.Download`, `ftpc.Upload`.
- String: `string.len`, `format`, `split`, `find`, `sub`, `rep`, `trim`, `lower`, `upper`, `reverse`, `byte`, `char`, `gsub`, `gmatch`, `match`.
- Utility/convert: `util.Crc16Modbus`, `convert.IntToFloat`, `convert.ToNum`.
- Account/mail/draw APIs exist. Search the manual for exact signatures before using them.
