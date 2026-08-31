# App rang cà phê — kiến trúc & luồng rang trên OTL Roast Lab

> Quy trình rang **trên app** (khác luồng firmware 11 bước ở [roast-flow.md](roast-flow.md)).
> Chốt chủ máy 2026-07-25. Kế hoạch chi tiết: `docs/plan/plan-rang-loi-firmware.md` (GĐ R).

## Ràng buộc cứng
- **KHÔNG dùng thẻ SD của máy** trên app. Bỏ tính năng "RANG AUTO từ thẻ SD".
- **Hồ sơ = file CSV** (kho chính, không `profiles.json`). CSV đọc được bằng Excel/Artisan.

## Kiến trúc: APP LÁI TOÀN BỘ (hướng A)
App giữ **trọn state machine rang** (vai trò `Program.h` trước đây). Firmware = **tay chân
thuần**: nhận lệnh mức qua khối GHI PC_Link, đóng xi lanh theo timer relay, và giữ **2 chốt
an toàn** (watchdog mất-app 3s → nhả về HMI; mồi-hụt 75s → đóng gas). Bộ tuần tự AUTO cũ
trong `Program.h` (chạy từ SD) **không dùng** ở chế độ app-lái.

App phải **biết mọi timer `$M`** (đọc qua khối config PC_Link, hoặc bảng mặc định theo
model máy) để tự điều phối: `chargeDuration / dropDuration / escapeDuration / preCool /
destonerPre / destonerSet / afterburnerSet / afterburnerNext`.

## ⚠ THỰC THI HIỆN TẠI KHÁC SPEC NÀY (soát 2026-07-30)

Spec dưới đây là **đích**, chưa phải cái đang chạy. Code hiện tại là **"máy chủ nhịp"**:
`OTL Roast Lab.html` (khối `applyMachine`) ghi rõ *"pclink — MÁY chủ: progStep của
firmware là chuẩn, app bám theo"*. App vào/ra mẻ theo `progStep`, không tự giữ chuỗi.

Hệ quả cần biết khi vận hành:
- App **không** tự chạy chuỗi sau xả (làm nguội / tách đá / thoát liệu). `preCool`,
  `destonerPre`, `escapeDuration` chỉ nằm trong bảng tham số ghi xuống máy, không có
  trong logic app. Chuỗi đó do `coolStep` firmware lo, mà `coolStep` **chỉ được kích từ
  trong khối `START_BTN_R == 1`** → không bấm Start trên HMI thì không có làm nguội tự động.
- Vì firmware giữ nhịp, mọi rủi ro kẹt của nó (xem
  [quy-trinh-dieu-khien-may-rang/references/rui-ro-va-de-xuat.md](../../quy-trinh-dieu-khien-may-rang/references/rui-ro-va-de-xuat.md))
  đều lan sang app.

**Chờ chủ máy chốt:** cập nhật spec thành "máy chủ nhịp", hay code tiếp phần app-lái?

## Luồng rang trên app (spec đích)
1. **Đăng nhập** (thợ/khách) → **chọn hồ sơ**.
2. **Nhập kg** mẻ — trống → auto theo **model máy** (máy 5kg → 5kg).
3. **Chọn mức rang** — trống → mặc định *medium*.
4. **Chọn loại cà** — để trống được, chọn sau ở trang Hồ sơ.
5. **Nhập nhiệt charge / nhiệt drop.**
6. **Bấm Play** → tự sang giao diện rang.
7. **Nạp cà lên phễu (loader):** loader có cân → hút theo kg đã cài; không khai báo cân →
   dừng theo timer.
8. **Màn chờ bắt đầu:** hiện bảng thông số mẻ **sửa được tại chỗ** + **đổi hồ sơ** được.
   Hồ sơ đã có CSV (đã rang) → sửa thì **tự tạo hồ sơ MỚI giữ kết cấu CSV cũ** (không đè bản gốc).
9. **Bấm Rang** → app vào state machine:
   - **Chờ nạp:** app **bật/tắt đầu đốt giữ BT bám nhiệt charge** (thấp→bật, cao→tắt).
   - **Charge:** fire charge đúng nhiệt; xi lanh đóng theo `chargeDuration_R`.
   - **Rang:** mỗi giây so BT với **đường mục tiêu** (nội suy từ setpoint hồ sơ) → chỉnh
     gas/gió/trống, **lưu đường gas/gió/trống thực vào CSV**. Chấm **TP → DE → FCs → DEV**.
     - **Auto-loader:** nếu bật option → app tự bật loader ở **TP** (tắt option thì không).
     - **AB:** app bật/tắt afterburner theo `afterburnerSet_R` (nhiệt).
   - **Drop:**
     - *theo nhiệt mục tiêu:* app chạy **mixer+cooling trước** (`preCool_R`) rồi mới fire drop.
     - *thợ bấm kết thúc:* **drop + mixcool CÙNG LÚC.**
     - drop đóng theo `dropDuration_R`.
   - **Sau drop:** AB tiếp theo `afterburnerNext_R` (0 = tắt ngay). mixcool gần xong → app
     fire **destoner trước escape** một khoảng `destonerPre_R`; escape đóng theo
     `escapeDuration_R`; destoner đóng theo `destonerSet_R`.

## Đường mục tiêu & RoR (nền cho nền mờ / đếm ngược / giọng nói)
- Đường BT mục tiêu **nội suy từ setpoint hồ sơ** (`chargeT → DE°C → FCs°C → dropT → time`),
  KHÔNG dùng hằng số demo. Thiếu setpoint → fallback ước lượng, không vẽ đường bịa.
- **RoR mục tiêu tính CÙNG công thức firmware** để khớp thang: mỗi 3 giây
  `RoR = (BT − BT₋₃ₛ) × 20`, lọc Kalman, kẹp ±95 °C/phút (nguồn `Program.h:107`,
  `tools/roast_derive.py`, tham số ở `protocol/pc_link.json` mục `derive`). Đóng gói ×100.

## An toàn (bắt buộc vì app giữ cả chuỗi)
App treo giữa chuỗi drop/escape là nguy hiểm → `failsafe` firmware phải BẬT: watchdog 3s
nhả về HMI, mồi-hụt 75s đóng gas. State machine app viết idempotent — mất nhịp 1-2s không
kẹt cơ cấu.

## Liên quan
- Timer/tham số: [registers-M.md](registers-M.md). Firmware gốc: [program-functions.md](program-functions.md), [roast-flow.md](roast-flow.md).
- Hồ sơ CSV: [profile-format.md](profile-format.md). Kế hoạch: `docs/plan/plan-rang-loi-firmware.md`.
