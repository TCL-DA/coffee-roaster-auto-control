# Agent Instructions - OTL-06ALS CMS

Firmware for an OTL-06ALS coffee roaster on STM32F103RC using PlatformIO and the Arduino framework.

This file is the shared entry point for Codex and other coding agents. Claude-specific workflows remain in `.claude/skills/`; use them as project playbooks when the task matches.

## Must Know

- Target MCU: STM32F103RC, 256 KB Flash, about 20 KB RAM.
- RAM is tight. Avoid new global arrays, large buffers, `String` growth, or speculative abstractions.
- Do not call SD, Modbus, Serial, or other blocking work inside ISR code.
- `timerPoll_1000ms()` must only update counters, flags, and simple safety values.
- Delta HMI addresses are documented as 1-based, while Modbus calls use 0-based addresses, usually `*_W - 1`.
- Temperature values are stored as x10, for example `1850 = 185.0 C`.
- Gas, airflow, and drum values are percentages from `0` to `100`.
- Vacuum pressure is in Pa.

## Build

```bash
pio run -e genericSTM32F103RC
pio run -e genericSTM32F103RC --target size
pio run -e genericSTM32F103RC --target upload
pio device monitor --baud 9600
```

Agent build rule: always try to verify firmware changes with PlatformIO. First try `pio` from PATH. If that fails on this Windows machine, do not stop immediately; use the installed PlatformIO executable directly:

```powershell
& "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe" run -e genericSTM32F103RC
& "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe" run -e genericSTM32F103RC --target size
```

Known local path:

```text
C:\Users\truon\.platformio\penv\Scripts\pio.exe
```

When reporting verification, include whether compile succeeded, RAM/Flash usage, and any meaningful warnings. Current known benign warnings include `ADDREG` redefined from `ModbusESP` and `boolean` deprecated from Arduino/legacy project code. Treat duplicate project macros, linker errors, or memory growth as real issues.

## Source Map

- `src/main.cpp`: setup and loop orchestration.
- `include/Define.h`: global state, pins, Modbus register macros, SD arrays.
- `include/Program.h`: roast state machine, SD profile/logging, warm-up/preheat logic.
- `include/Modbus_Master.h`: HMI, sensors, inverters, IO relay Modbus master.
- `include/Modbus_Slave.h`: Artisan PC Modbus slave interface.
- `include/PID_Airflow.h`: vacuum airflow step controller, FF table, factory tune.
- `include/RoR_Control.h`: RoR gas control overlay.
- `include/MachineStatus.h`: HMI status codes and status queue.
- `include/AnalogConfig.h`: ADC source selection and DAC gas/airflow output.
- `include/IOConfig.h`: relay output mapping.
- `include/ScaleFeeder.h`: Bluetooth scale parser.

## Change Rules

- Make surgical changes only. Do not refactor unrelated code.
- Preserve user edits and dirty worktree changes.
- Match existing style unless the user asks for cleanup.
- Code comments and project documentation added or edited in this project must be Vietnamese with accents.
- Keep source files as UTF-8 so Vietnamese text displays correctly. Do not convert Vietnamese comments to mojibake or no-accent text.
- Keep identifiers, macros, file names, Modbus labels, and debug output strings in English unless the user explicitly asks otherwise.
- Keep debug output strings in English.
- Gate debug output with `if(enDebug)`.
- Prefer fixed-size buffers and integer math where practical.
- After firmware changes, run build and size check when PlatformIO is available.

## Ngôn Ngữ Và Encoding

- Mọi chú thích code, tài liệu cấu hình, và hướng dẫn được thêm/sửa trong dự án này phải dùng tiếng Việt có dấu.
- File chứa tiếng Việt phải lưu UTF-8. Nếu thấy chữ lỗi font như `Äiá»u khiá»ƒn`, `Cáº¥u hÃ¬nh`, phải sửa về tiếng Việt đúng dấu.
- Không đổi tên biến, macro, hằng Modbus, tên file, hoặc chuỗi debug sang tiếng Việt nếu không được yêu cầu.
- Chuỗi debug/runtime in ra Serial vẫn dùng tiếng Anh để dễ đọc log kỹ thuật.

## Release Safety

Before flashing real hardware:

- Confirm `enDebug` default is suitable for production.
- Confirm hardware variant `V300` or `V400` matches the actual board.
- Check RAM and Flash usage.
- Confirm gas safety cutoff is still present.
- Confirm no SD, Modbus, or Serial calls were added inside ISR.
- Confirm PC control does not default to enabled unexpectedly.

## Project Playbooks

The `.claude/skills/` directory is not automatically executed by Codex, but its `SKILL.md` files are useful project-specific workflows:

- `.claude/skills/flash-build/SKILL.md`: build, parse compiler errors, check size.
- `.claude/skills/memory-check/SKILL.md`: RAM/Flash and large array analysis.
- `.claude/skills/release-check/SKILL.md`: pre-flash safety checklist.
- `.claude/skills/modbus-audit/SKILL.md`: Modbus register and timing audit.
- `.claude/skills/state-trace/SKILL.md`: roast state machine trace.
- `.claude/skills/pid-analysis/SKILL.md`: vacuum airflow controller analysis.
- `.claude/skills/profile-analyze/SKILL.md`: roast profile/log analysis.
- `.claude/skills/define-audit/SKILL.md`: `Define.h` audit.
- `.claude/skills/bug-report/SKILL.md`: serial log and runtime bug analysis.
- `.claude/skills/vietnamese-comments/SKILL.md`: Vietnamese comment/documentation style and UTF-8 check.

Use those playbooks when the user asks for the corresponding task.
