# Agent Instructions - OTL-06ALS CMS

## Phân vai GPT và Claude — quy ước lâu dài (08/09/2026)

- Áp dụng mặc định cho mọi phiên và dự án, trừ khi người dùng chỉ đạo khác trong tác vụ hiện tại.
- GPT/Codex phụ trách lập kế hoạch, điều phối, phân tích và review. Claude phụ trách viết/sửa code. Chỉ để Codex viết/sửa code khi người dùng yêu cầu rõ Codex làm; yêu cầu nâng cấp hoặc sửa lỗi chung không tự động đổi phân vai này. Codex vẫn được đọc mã, chạy kiểm tra phù hợp và viết tài liệu/kế hoạch.
- Người dùng cho phép chủ động dùng sub-agent cho nhiệm vụ review/điều phối cụ thể: GPT-6 Astra mức high cho logic phức tạp và task khó; GPT-5.6 Sol mức high cho task thông thường; GPT-5.6 Luna mức high cho review lặp/checklist/hồi quy; GPT-5.6 Luna mức max cho nhiệm vụ cần đào sâu được giao rõ. Tên người dùng gọi “Luma” được hiểu là Luna trong danh sách công cụ hiện tại.
- Chỉ tạo sub-agent khi có nhiệm vụ hữu ích, có phạm vi và đầu ra rõ; không tạo agent chạy chờ. Tuân thủ số slot và model thực sự có trong phiên. Không tự đổi model của agent chính hay giả nhận đang chạy model được mong muốn.
- Giữ quyền phản biện độc lập của phía Claude/Opus (người dùng gọi “Opus 5”): reviewer phải đưa bằng chứng, tác động và tiêu chí chấp nhận; dev được bác bỏ bằng bằng chứng hoặc đề xuất khác.
- Khi review và dev bất đồng sau hai vòng thương lượng mà chưa giải quyết: lập hồ sơ phân xử gồm điểm đồng thuận, điểm bất đồng, bằng chứng, phương án và phép thử phân định. Người dùng muốn phiên tranh luận có “Astra Extra” và “Fable 5.1 Ultracode”. Đây là tên theo yêu cầu người dùng, không phải xác nhận chúng khả dụng; kiểm tra công cụ và hỏi làm rõ mức/model khi cần, không tự ánh xạ “Extra” sang xhigh.
- Kết luận dựa trên bằng chứng, kiểm thử và yêu cầu người dùng, không bỏ phiếu theo số agent. Nếu còn bất đồng không thể phân định, trình người dùng quyết định.
- Chỉ trao đổi trực tiếp với Claude/Opus/Fable khi phiên có công cụ phù hợp và đã có quyền dùng; nếu không, chuẩn bị tài liệu bàn giao để người dùng chuyển. Không tuyên bố đã gọi hoặc đã tranh luận với model không thực sự được gọi.


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

## Quản lý tài sản CAD và EPLAN

- **Quy ước đầy đủ (bản gốc, cho cả Claude lẫn Codex): `F:\Project\112_Quanly\121_Inventor_3D\AGENTS.md`** — đọc file đó trước khi tạo, đổi tên hay di chuyển bất cứ file 3D nào.
- Không lưu mô hình 3D, file Inventor, STEP/STP, macro EPLAN hoặc gói EDZ trong repository firmware này.
- File Inventor và STEP dùng cho EPLAN phải lưu tại `F:\Project\112_Quanly\121_Inventor_3D`; vật tư theo mã đặt trong `03_VatTu_3D_theo_ma\<Hang.Ma>`.
- STEP gốc của hãng đặt trong thư mục `STEP_Hang`; IPT đã xử lý, ảnh xem trước và STEP AP214 cho EPLAN Pro Panel đặt cùng thư mục mã vật tư.
- Macro, dữ liệu part, gói `.edz` và artefact build riêng của EPLAN phải lưu tại `F:\Project\112_Quanly\EDZ`.
- Chỉ dùng thư mục dự án firmware làm nơi tạm trong lúc xử lý khi thật sự cần; phải chuyển kết quả sang `112_Quanly` và dọn bản tạm sau khi hoàn tất.

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
- `.claude/skills/manual-otl/SKILL.md`: build customer manuals as A4 PDF through Illustrator.

Use those playbooks when the user asks for the corresponding task.

### Building a customer manual

Start from `.claude/skills/manual-otl/references/content-mau-toi-thieu.jsx` — a runnable
skeleton with every layout function and a comment on each. Build it with one command:

```bash
python .claude/skills/manual-otl/assets/make.py <content>.jsx
```

or through the `otl-manual` MCP server (`tools/mcp_manual/`), tool `manual_dung`.

Three rules that are not negotiable:

1. **Never claim a document is finished on the strength of `OK pages=N`.** That line says the
   script ran, not that the layout is sound. The machine check only flags pages that are thin
   on text; overlapping text, overflowing frames and a logo touching the title are invisible to
   it. Render the PNGs and look at them.
2. **Never put a partner's name, address or contact details in this repo.** OEM editions are
   *generated* from the OTL master by a script that refuses to write the file while any trace of
   the original brand remains, and the result is checked again against the PDF itself. Per-partner
   branding lives outside the repo.
3. **Do not hand-edit a generated OEM file.** Edit the master, re-run the generator.

## Open Design cho giao diện app

- Yêu cầu ngày 07/09/2026: luôn sử dụng Open Design khi thiết kế, sửa hoặc đánh giá UI/UX của Roast Lab. Bộ nguồn cục bộ: `F:/Project/open-design`. Đọc và áp dụng tài nguyên phù hợp trong `craft/`; nói rõ khi chỉ sử dụng quy tắc thiết kế thay vì chạy ứng dụng/engine. Ưu tiên feedback của người dùng, khả năng đọc và thao tác; chỉ báo cáo bằng chữ.

## Chất lượng ảnh và video trong VS Code/Codex

- Yêu cầu ngày 14/09/2026: khi người dùng yêu cầu tạo hoặc chỉnh ảnh/video trong môi trường VS Code/Codex, chất lượng mục tiêu phải tương đương trải nghiệm ChatGPT trên web hoặc ứng dụng, không xem asset phác thảo, placeholder hay bản dựng kỹ thuật chất lượng thấp là kết quả cuối.
- Với ảnh raster, phải dùng công cụ/model tạo ảnh chuyên dụng khi khả dụng; xem đầy đủ ảnh tham chiếu, giữ đúng tỷ lệ/kích thước/phong cách, kiểm tra trực quan kết quả và lặp chỉnh sửa khi còn lỗi rõ ràng trước khi bàn giao.
- Với video, phải dùng công cụ/model tạo video chuyên dụng khi phiên có hỗ trợ. Nếu phiên không có công cụ video, nói rõ giới hạn ngay từ đầu; có thể chuẩn bị storyboard, shot list, prompt và asset nhưng không được tuyên bố chúng tương đương video thành phẩm.
- Khi yêu cầu chưa phân biệt giữa concept media và giao diện chạy thật, phải xác định đầu ra phù hợp từ ngữ cảnh; không dùng ảnh giả giao diện thay cho UI code nếu mục tiêu là app hoạt động, và không dùng HTML/CSS chụp lại thay cho ảnh sáng tạo nếu mục tiêu là media.
- Giữ vòng chất lượng tối thiểu: xác định mục tiêu và ảnh tham chiếu, tạo bằng pipeline phù hợp, kiểm tra trực quan, sửa lỗi bố cục/chữ/màu/chi tiết, rồi mới tích hợp vào dự án hoặc bàn giao.
- Quy ước này không thay đổi nguyên tắc ngày 06/09/2026: không tự tạo ảnh, GIF hoặc video cho báo cáo/review khi người dùng chưa yêu cầu rõ trong tác vụ hiện tại.

## Bản thiết kế Claude Design và cách Claude + Codex làm chung trên app

**Quy ước gốc cho cả Claude lẫn Codex.** Áp dụng từ 07/09/2026.

### Nguồn thiết kế

**Nguồn để LÀM VIỆC là bản trên đĩa `docs/ui/design-web/`, không phải project trên
mây.** Đây là chốt cố ý (13/09/2026): project Claude Design gắn với **một tài khoản**,
đổi tài khoản hay mất quyền là cả hai bên cùng mù. Bản trên đĩa thì ai mở cũng được —
không mạng, không đăng nhập, không quyền. Mây chỉ là nơi *kéo bản mới về*.

- Bản thiết kế gốc: Claude Design, project `Menu cài đặt nhanh - Lỗi thiết kế`
  (UUID 07/09/2026: `3c3a6a49-faff-4902-a214-f071ccd6006f` — **13/09 trả 404**, phải
  lấy lại UUID từ URL).
- **Bản trên đĩa: `docs/ui/design-web/`** — mở `Rang - Sua lai.dc.html` bằng trình
  duyệt là xem đủ. Codex đọc bản này. Xuất xứ, vân tay md5 và **hai cách làm mới**
  ghi ở `docs/ui/design-web/SOURCE.md`.
- Đặc tả rút gọn (token màu, từng màn, thuật ngữ): **`docs/ui/2026-09-07-design-spec.md`**.
  Đọc file này trước khi sửa giao diện — nhanh hơn đọc bản `.dc.html`.
- Làm mới bản trên đĩa có **hai đường**: `DesignSync` (chỉ Claude Code gọi được, và
  phải đăng nhập đúng tài khoản giữ project), hoặc **tải tay từ trình duyệt** — đường
  này ai mở được design là làm được, không phụ thuộc tài khoản nào. Làm mới xong phải
  cập nhật `SOURCE.md`.
- **Không tự sửa file trong `design-web/`** — đó là bản sao của nguồn, sửa vào đấy sẽ
  bị ghi đè ở lần kéo sau.

### Chống đè file khi hai bên cùng làm
`OTL Roast Lab.html` là **một file duy nhất ~670 KB**. Hai tác nhân sửa song song
là chắc chắn mất việc của nhau. Vì vậy:

1. **Trước khi sửa** `OTL Roast Lab.html` hoặc `tools/test_ui_*`: đọc
   `docs/ui/UI-LOCK.md`. Nếu bên kia đang giữ, **không sửa** — báo người dùng.
2. **Khi nhận việc:** ghi tên mình, thời điểm và phạm vi vào `docs/ui/UI-LOCK.md`.
3. **Sao lưu trước mỗi đợt sửa lớn:** copy sang `docs/ui/backup/` kèm ngày giờ.
4. **Xong việc:** ghi lại đã đổi gì rồi trả khoá (ghi `RẢNH`) trong cùng file.
5. Commit thì **chỉ commit file của mình**, không `git add -A`.

Người dùng có quyền cắt ngang quy tắc này — họ nói ai làm thì người đó làm.

## Phân việc sub-agent và tiết kiệm token — cập nhật 08/09/2026

- Chủ động phân việc cho đúng model khi có nhiệm vụ cụ thể; áp dụng lâu dài cho các phiên và dự án, trừ khi người dùng chỉ đạo khác.
- GPT-6 Astra high: tìm lỗi, xác định nguyên nhân gốc, phân tích logic phức tạp, kiến trúc và review các vấn đề khó hoặc ảnh hưởng an toàn. Việc rà checklist đơn giản giao Luna; khi phát hiện bất thường khó giải thích, chuyển bằng chứng cho Astra.
- GPT-5.6 Sol high: công việc chuyên môn, phân tích thông thường, lập kế hoạch triển khai và công việc lập trình thuộc phạm vi GPT đã được người dùng cho phép. Sau khi Astra xác định lỗi, bàn giao kết luận và tiêu chí chấp nhận cho bên triển khai; không giữ Astra làm mọi bước.
- GPT-5.6 Luna high: checklist, đối chiếu tài liệu, tổng hợp kết quả kiểm thử và review hồi quy có phạm vi rõ. Luna max chỉ dùng cho nhiệm vụ đào sâu được giao rõ.
- Giữ quy ước Claude mặc định viết/sửa code. Phân vai Sol ở trên không tự cấp quyền GPT sửa code; khi người dùng yêu cầu GPT trực tiếp lập trình thì ưu tiên giao Sol.
- Agent chính điều phối và tổng hợp; chuyển việc bằng sub-agent có model chỉ định, không tuyên bố tự đổi model của agent chính. Nếu model cần dùng không khả dụng, báo rõ và đề xuất phương án phù hợp.
- Tiết kiệm token: giao phạm vi hẹp, đầu ra ngắn gồm bằng chứng, kết luận và việc cần làm; chỉ truyền ngữ cảnh/file liên quan thay vì sao chép toàn bộ hội thoại. Tái sử dụng agent cùng vai trò khi còn phù hợp; không tạo agent chạy chờ, không giao trùng việc, không dùng hết slot chỉ vì còn trống.
- Chạy song song các nhiệm vụ độc lập; các bước phụ thuộc phải nhận bàn giao trước. Không để nhiều agent sửa cùng file. Chỉ mở rộng review hoặc lặp kiểm thử khi có thay đổi, lỗi hay nghi vấn cụ thể; kết luận vẫn phải đáp ứng đầy đủ yêu cầu và kiểm tra bắt buộc.

## Kho ảnh dùng chung — `F:\Kho-anh`

Mọi việc Photoshop / thiết kế / manual / banner của O Tesla lấy tài nguyên ảnh từ **`F:\Kho-anh`**
(ảnh máy rang, vật tư, logo, icon HMI, render 3D, ảnh manual, banner — 1.528 ảnh, đã khử trùng lặp).

- Lấy ảnh: các nhóm `01_May-rang` … `09_Thiet-ke-khac`. Không lục lại `F:\Photo`, `F:\File-AI`, `F:\Vat-tu-Otesla`.
- Lưu kết quả Photoshop: `F:\Kho-anh\99_Xuat-Photoshop\<YYMMDD>_<ten-viec>\`.
- Không sửa đè / không xoá bản gốc trong `01_`–`09_`.
- Xuất xong **luôn chép PNG/JPG** vào `F:\Kho-anh\99_Xuat-Photoshop\00_TAT-CA-ANH-XUAT\` tên `<YYMMDD>_<viec>__<file>` — chưa chép là chưa xong.
- Quy ước đầy đủ: `F:\Kho-anh\AGENTS.md`. Tra nguồn gốc từng ảnh: `F:\Kho-anh\_index.csv`.
- Script gom lại khi có ảnh mới: `tools/gom_kho_anh.ps1` (chế độ COPY, không MOVE).
- Repo này PUBLIC — **không commit ảnh từ kho vào repo**.
