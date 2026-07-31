---
name: delta-lua-hmi
description: Expert support for Delta IA-HMI / DOPSoft Lua programming. Use when writing, reviewing, debugging, or explaining Lua scripts for Delta DOP/IA HMI projects, including mem.inter, mem.static, link external memory, recipes, files, screen control, system functions, COM/TCP/UDP communication, Modbus-style handshakes, HMI runtime errors, and PLC/HMI register access.
---

# Delta IA-HMI Lua

Use this skill as a practical Delta HMI Lua assistant. Prefer code that can be pasted into DOPSoft's Lua editor and tested on an HMI.

## Core Workflow

1. Identify the target task: internal HMI memory, static memory, external PLC link, recipe, file, screen, system, COM, TCP, UDP, account, mail, or drawing.
2. If the exact function signature or return code matters, search the bundled manual before answering:
   - Run `scripts/search-manual.sh "functionName"` from this skill folder, or use `rg` on `references/delta-lua-manual.txt`.
   - Read `references/quick-reference.md` for common signatures and groups.
   - Read `references/patterns.md` for copy-paste script templates and debugging rules.
3. Produce a complete DOPSoft Lua snippet, not pseudocode, unless the user explicitly asks for explanation only.
4. Include the HMI element setup when needed: maintained button trigger bits, numeric/character entry addresses, recipe setup, COM/TCP tool setup, or screen IDs.
5. Add runtime feedback for field work: write return values to unused `$` registers and clear trigger bits after one-shot actions.

## Delta Lua Rules To Preserve

- Delta Lua is case sensitive.
- Variables are global unless declared `local`.
- Undefined variables can stop execution with `Lua runtime error`; quote string literals.
- Use `while true do ... sys.Sleep(ms) ... end` for cyclic logic when the script is intended to keep watching trigger bits.
- Avoid tight infinite loops without `sys.Sleep` unless the manual example clearly does so and the use case is tiny.
- Always use `string.len(str)` for ASCII write length unless the user gives a fixed byte length.
- For write commands, check the return value where possible: usually `1` is success and `0` or a negative value is failure.
- For one-shot maintained-button triggers, clear the source bit after the action, for example `mem.inter.WriteBit(10, 0, 0)`.

## Address Model

- Internal HMI memory `$`: use `mem.inter.*`.
- Static HMI memory `$M`: use `mem.static.*`.
- External PLC/controller memory: use `link.*` with address strings like `"{Link2}1@D1"` or `"{Link2}1@M100"`.
- Recipe addresses: use `RCP`, `RCPNO`, `RCPG`, `ENRCP`, `ENRCPNO`, `ENRCPG`, plus the `recipe.*` API.
- Bit index for word memory is typically `0` to `15`.

## Answer Style

- Match the user's language. If the user writes Vietnamese, answer in Vietnamese.
- Be direct and practical. Show the Lua first, then explain only the parts that matter.
- If a request is ambiguous, state the assumption and make the smallest useful implementation.
- For risky machine actions, include a dry-run or debug-register version first.

## Bundled References

- `references/quick-reference.md`: common function signatures, memory ranges, and API groups.
- `references/patterns.md`: reusable DOPSoft Lua templates.
- `references/manual-map.md`: manual chapter map and search hints.
- `references/delta-lua-manual.txt`: full text extracted from Delta's Lua instruction manual.
- `references/DELTA_IA-HMI_LUA_UM_EN_20211208.pdf`: original attached manual.
