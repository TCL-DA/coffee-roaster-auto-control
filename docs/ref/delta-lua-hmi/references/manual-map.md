# Manual Map

Manual file: `DELTA_IA-HMI_LUA_UM_EN_20211208.pdf`.

Full extracted text: `delta-lua-manual.txt`.

## Chapters

| Chapter | Topic | Manual page |
|---|---|---|
| 1 | Introduction to Lua | 2 |
| 2 | Basic Lua programming syntax | 3 |
| 3 | Lua command list | 5 |
| 4.1 | Basic syntax | 13 |
| 4.2 | Internal memory `$` | 31 |
| 4.3 | Static memory `$M` | 36 |
| 4.4 | External link memory | 41 |
| 4.5 | File | 52 |
| 4.6 | FileSlot | 64 |
| 4.7 | FTP Client | 72 |
| 4.8 | Math | 77 |
| 4.9 | Recipe | 84 |
| 4.10 | Screen | 109 |
| 4.11 | String | 113 |
| 4.12 | System library | 119 |
| 4.13 | Serial port COM communication | 123 |
| 4.14 | TCP communication | 130 |
| 4.15 | UDP communication | 138 |
| 4.16 | Text encoding | 149 |
| 4.17 | Utility / CRC | 152 |
| 4.18 | Convert / floating-point conversion | 154 |
| 4.19 | Account | 156 |
| 4.20 | Mail | 163 |
| 4.21 | Draw | 170 |

## Useful Searches

From the skill folder:

```bash
scripts/search-manual.sh "mem.inter.WriteBit"
scripts/search-manual.sh "tcp.Open"
scripts/search-manual.sh "Return value"
scripts/search-manual.sh "Lua runtime error"
```

Prefer exact command names when searching. If the command is not known, search by group: `Recipe`, `COM communication`, `TCP communication`, `External link`, `FileSlot`.
