// ==========================================================================
// PC_Link_Map.h — SINH TỰ ĐỘNG từ protocol/pc_link.json — ĐỪNG SỬA TAY.
// Sửa JSON rồi chạy: python protocol/gen_pc_link.py
// Bản đồ register dùng chung giữa firmware và app OTL Roast Lab.
// ==========================================================================
#ifndef PC_LINK_MAP_H
#define PC_LINK_MAP_H

#define PCL_VERSION    1

// ── Khối ĐỌC (máy → app) — 100..114 ──
// Máy → app. Cập nhật mỗi vòng loop, app đọc trọn khối trong 1 frame 0x03.
#define PCL_R_BASE     100
#define PCL_R_BT       (PCL_R_BASE + 0 )  // nhiệt hạt [°C] ×10
#define PCL_R_ET       (PCL_R_BASE + 1 )  // nhiệt khí [°C] ×10
#define PCL_R_RORBT    (PCL_R_BASE + 2 )  // RoR hạt [°C/phút] ×100 (có dấu)
#define PCL_R_RORET    (PCL_R_BASE + 3 )  // RoR khí [°C/phút] ×100 (có dấu)
#define PCL_R_RORPRO   (PCL_R_BASE + 4 )  // RoR hồ sơ mẫu tại giây hiện tại [°C/phút] ×100 (có dấu)
#define PCL_R_GAS      (PCL_R_BASE + 5 )  // mức gas [%]
#define PCL_R_AIR      (PCL_R_BASE + 6 )  // mức gió [%]
#define PCL_R_DRUM     (PCL_R_BASE + 7 )  // tốc độ trống [%]
#define PCL_R_SV       (PCL_R_BASE + 8 )  // SV nhiệt hạt [°C] ×10
#define PCL_R_VAC      (PCL_R_BASE + 9 )  // áp hút (âm = hút) [Pa] (có dấu)
#define PCL_R_STEP     (PCL_R_BASE + 10)  // progStep — bước quy trình rang
#define PCL_R_TROAST   (PCL_R_BASE + 11)  // thời gian rang [s]
#define PCL_R_PHASE    (PCL_R_BASE + 12)  // bitmask pha rang
#define PCL_R_FLAGS    (PCL_R_BASE + 13)  // bitmask trạng thái nút/chế độ
#define PCL_R_HB       (PCL_R_BASE + 14)  // heartbeat — tăng mỗi vòng loop, app dò treo
#define PCL_R_COUNT    15

// Bit của phase
#define PCLP_DRY  0x01   // đã qua TP  (progStep >= STP_TP)
#define PCLP_MAI  0x02   // đã qua FCs (progStep >= STP_FCS)
#define PCLP_DEV  0x04   // đã qua DEV (progStep >= STP_DEV)

// Bit của flags
#define PCLF_AUTO     0x01   // START_BTN_R — đang chạy AUTO
#define PCLF_GAS      0x02   // START_GAS_BTN_R — gas đang bật
#define PCLF_CHARGE   0x04   // CHARGE_BTN_R
#define PCLF_DROP     0x08   // DROP_BTN_R
#define PCLF_ESCAPE   0x10   // ESCAPE_BTN_R
#define PCLF_COOL     0x20   // COOLING_BTN_R
#define PCLF_PCCTRL   0x40   // PC_CONTROL_BTN_R — app được phép điều khiển
#define PCLF_FLAME    0x80   // CÓ LỬA THẬT (gasSignal, chân CH1) — khác hẳn 'đã bấm bật gas'
#define PCLF_PCLOST   0x100   // firmware đã tự nhả quyền vì mất app (watchdog)
#define PCLF_FLMFAIL  0x200   // firmware đã tự đóng gas vì mồi hoài không có lửa

// ── Khối GHI (app → máy) — 120..131 ──
// App → máy. CHỈ áp dụng khi PC_CONTROL_BTN_R == 1 (cờ pc_control).
#define PCL_W_BASE     120
#define PCL_W_GAS      (PCL_W_BASE + 0 )  // gas %  [0..100]
#define PCL_W_AIR      (PCL_W_BASE + 1 )  // gió %  [0..100]
#define PCL_W_DRUM     (PCL_W_BASE + 2 )  // trống %  [0..100]
#define PCL_W_SV       (PCL_W_BASE + 3 )  // SV nhiệt hạt ×10  [0..3000]
#define PCL_W_VAC      (PCL_W_BASE + 4 )  // áp hút đặt  [90..250]
#define PCL_W_IGNITE   (PCL_W_BASE + 5 )  // bật/tắt gas (START_GAS)  [0..1]
#define PCL_W_CHARGE   (PCL_W_BASE + 6 )  // nạp hạt  [0..1]
#define PCL_W_DROP     (PCL_W_BASE + 7 )  // xả mẻ  [0..1]
#define PCL_W_ESCAPE   (PCL_W_BASE + 8 )  // thoát  [0..1]
#define PCL_W_COOL     (PCL_W_BASE + 9 )  // làm nguội  [0..1]
#define PCL_W_AUTO     (PCL_W_BASE + 10)  // bật/tắt AUTO (START)  [0..1]
#define PCL_W_HB       (PCL_W_BASE + 11)  // heartbeat app: app tăng mỗi giây; firmware không thấy đổi quá PCL_APP_TMO_S thì nhả quyền  [0..32767]
#define PCL_W_COUNT    12

// Giới hạn kẹp phía firmware — tầng 2 của clamp 2 tầng (app kẹp tầng 1)
static const int16_t PCL_W_MIN[PCL_W_COUNT] = {0, 0, 0, 0, 90, 0, 0, 0, 0, 0, 0, 0};
static const int16_t PCL_W_MAX[PCL_W_COUNT] = {100, 100, 100, 3000, 250, 1, 1, 1, 1, 1, 1, 32767};

// ── Chốt an toàn khi APP là bộ điều khiển ──────────────────────────────
#define PCL_APP_TMO_S    3   // app không nhấp heartbeat quá ngần này giây → nhả quyền về HMI + còi
#define PCL_FLAME_TMO_S  75  // bật gas mà không có lửa quá ngần này giây → firmware TỰ ĐÓNG GAS

// ── Khối tương thích (Modbus_Slave.h) — app đọc/ghi khi máy chưa có PC_Link ──
// Không định nghĩa lại địa chỉ; chỉ ĐỐI CHIẾU để spec không lệch khỏi firmware.
#ifdef BT_show_artisan
static_assert(BT_show_artisan == 0, "pc_link.json lech BT_show_artisan — chay: python protocol/gen_pc_link.py");
static_assert(ET_show_artisan == 1, "pc_link.json lech ET_show_artisan — chay: python protocol/gen_pc_link.py");
static_assert(AIRshow_artisan == 2, "pc_link.json lech AIRshow_artisan — chay: python protocol/gen_pc_link.py");
static_assert(GAS_show_artisan == 3, "pc_link.json lech GAS_show_artisan — chay: python protocol/gen_pc_link.py");
static_assert(DRUM_show_artisan == 4, "pc_link.json lech DRUM_show_artisan — chay: python protocol/gen_pc_link.py");
static_assert(UNDER_show_artisan == 9, "pc_link.json lech UNDER_show_artisan — chay: python protocol/gen_pc_link.py");
static_assert(MI_COOL_artisan_W == 13, "pc_link.json lech MI_COOL_artisan_W — chay: python protocol/gen_pc_link.py");
static_assert(CHARGE_artisan_W == 14, "pc_link.json lech CHARGE_artisan_W — chay: python protocol/gen_pc_link.py");
static_assert(DROP_artisan_W == 15, "pc_link.json lech DROP_artisan_W — chay: python protocol/gen_pc_link.py");
static_assert(ESCAPE_artisan_W == 16, "pc_link.json lech ESCAPE_artisan_W — chay: python protocol/gen_pc_link.py");
static_assert(START_artisan_W == 17, "pc_link.json lech START_artisan_W — chay: python protocol/gen_pc_link.py");
static_assert(SV_show_artisan == 19, "pc_link.json lech SV_show_artisan — chay: python protocol/gen_pc_link.py");
static_assert(GAS_artisan_W == 11, "pc_link.json lech GAS_artisan_W — chay: python protocol/gen_pc_link.py");
static_assert(AIR_artisan_W == 10, "pc_link.json lech AIR_artisan_W — chay: python protocol/gen_pc_link.py");
static_assert(DRUM_artisan_W == 20, "pc_link.json lech DRUM_artisan_W — chay: python protocol/gen_pc_link.py");
static_assert(SV_artisan_W == 18, "pc_link.json lech SV_artisan_W — chay: python protocol/gen_pc_link.py");
static_assert(vacuumC_artisan_W == 22, "pc_link.json lech vacuumC_artisan_W — chay: python protocol/gen_pc_link.py");
static_assert(IGNITION_artisan_W == 12, "pc_link.json lech IGNITION_artisan_W — chay: python protocol/gen_pc_link.py");
static_assert(MI_COOL_artisan_W == 13, "pc_link.json lech MI_COOL_artisan_W — chay: python protocol/gen_pc_link.py");
static_assert(CHARGE_artisan_W == 14, "pc_link.json lech CHARGE_artisan_W — chay: python protocol/gen_pc_link.py");
static_assert(DROP_artisan_W == 15, "pc_link.json lech DROP_artisan_W — chay: python protocol/gen_pc_link.py");
static_assert(ESCAPE_artisan_W == 16, "pc_link.json lech ESCAPE_artisan_W — chay: python protocol/gen_pc_link.py");
static_assert(START_artisan_W == 17, "pc_link.json lech START_artisan_W — chay: python protocol/gen_pc_link.py");
#endif

#endif  // PC_LINK_MAP_H
