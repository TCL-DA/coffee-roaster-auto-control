#ifndef PC_LINK_H
#define PC_LINK_H
// ============================================================================
// PC_Link.h — Cầu nối tốc-độ-cao cho app "OTL Roast Lab" (PC ↔ máy rang)
// ----------------------------------------------------------------------------
// VÌ SAO CÓ FILE NÀY (đọc trước khi sửa):
//   • 4 UART đã dùng hết: Serial1=HMI, Serial2=SerialComputer(FT232/MAX3232→PC),
//     Serial3=Bluetooth(cân), Serial4=RS485. App OTL cắm vào FT232 = Serial2 —
//     CÙNG cổng với Artisan. KHÔNG mở được 2 slave Modbus trên 1 UART.
//   • Nên PC_Link DÙNG CHUNG đúng con `mbs` (ModbusRTU) đang chạy trong
//     Modbus_Slave.h, chỉ CẤP THÊM một DÃY REGISTER LIỀN KHỐI riêng cho app OTL.
//     → App đọc toàn bộ dữ liệu live trong 1 frame (func 0x03) = tối ưu tốc độ.
//     → Artisan giữ nguyên map cũ (reg 0–26). Hai map sống song song; mỗi lúc chỉ
//       1 app cắm vào FT232, đổi app không cần build lại.
//
// KHÔNG XUNG ĐỘT với handle_Modbus_Slave():
//   Khi PC_Link áp setpoint xuống máy, nó cập nhật LUÔN *_R / *_R_CP / *Percent
//   (đúng như nhánh PC của Modbus_Slave.h). Handler Artisan so sánh thấy "không
//   đổi" → im, không ghi đè. Các nút ảo của Artisan (reg 12–17) app OTL không đụng
//   nên giữ 0 == 0 → SYNC_BTN cũng im.
//
// CƠ CHẾ:
//   • Khối ĐỌC (máy→app): cập nhật MỖI vòng loop, không cần bật gì.
//   • Khối GHI (app→máy): CHỈ áp dụng khi PC_CONTROL_BTN_R == 1 (nút "PC control"
//     trên HMI). Tắt → app chỉ xem, khối ghi phản chiếu setpoint hiện tại của máy
//     để giao diện app khớp số thực.
//
// WIRING (đã thêm ở main.cpp):
//   #include "PC_Link.h"     // sau Modbus_Slave.h
//   pcLinkInit();            // trong setup(), sau ModbusSlaveConfig()
//   handle_PC_Link();        // trong loop(), NGAY TRƯỚC handle_Modbus_Slave()
//                            //   (mbs.task() ở cuối handle_Modbus_Slave phục vụ cả 2 map)
//
// ĐƠN VỊ (app tự quy đổi):
//   BT/ET/SV ×10 (2153 = 215.3°C) · rorBT/rorET ×100 (1°C/min = 100) ·
//   gas/air/drum = %  · Diff_Air = Pa (âm=hút, số có dấu) · SV ghi ×10 (≤3000).
// ============================================================================

#ifndef PC_LINK_EN
#define PC_LINK_EN 1          // đặt 0 để loại hẳn PC_Link khỏi build
#endif

#if PC_LINK_EN

// ── Bản đồ register: DÙNG CHUNG với app (protocol/pc_link.json) ─────────────
// Địa chỉ, bit cờ, giới hạn kẹp đều nằm ở PC_Link_Map.h — file SINH TỰ ĐỘNG.
// Muốn thêm/sửa register: sửa protocol/pc_link.json rồi chạy
//     python protocol/gen_pc_link.py
// để firmware, tool Python và giao diện cùng đổi một lượt (không lệch nhau).
#include "PC_Link_Map.h"

static int16_t pclLastW[PCL_W_COUNT];     // giá trị khối ghi vòng trước (edge-gate)
static bool    pclInited = false;

// Nạp register vào slave `mbs` (khai báo trong Modbus_Slave.h, include trước file này)
void pcLinkInit(){
    for (int i = 0; i < PCL_R_COUNT; i++) mbs.addHreg(PCL_R_BASE + i);
    for (int i = 0; i < PCL_W_COUNT; i++) mbs.addHreg(PCL_W_BASE + i);
    SerialComputer.println("=> PC_Link OK (reg 100-130)");
}

// ── Khối GHI: đọc 1 ô, nếu app đổi thì trả về true (kèm giá trị đã kẹp) ──────
// Giới hạn lấy từ PCL_W_MIN/MAX (bản đồ dùng chung) — app kẹp tầng 1, đây tầng 2.
static inline bool pclChanged(uint8_t idx, int16_t &out){
    const int16_t lo = PCL_W_MIN[idx], hi = PCL_W_MAX[idx];
    int16_t v = (int16_t)mbs.Hreg(PCL_W_BASE + idx);
    if (v < lo) v = lo; else if (v > hi) v = hi;
    if (v == pclLastW[idx]) return false;
    pclLastW[idx] = v;
    out = v;
    return true;
}

// ════════════════════════════════════════════════════════════════════════════
// CHỐT AN TOÀN — bắt buộc vì APP LÀ BỘ ĐIỀU KHIỂN (app tự mồi lửa, tự charge,
// tự chỉnh gas). Không có 2 chốt này thì app treo giữa mẻ = máy chạy tiếp với
// setpoint cuối cùng vô thời hạn, hoặc xả gas sống vào buồng đốt khi mồi hụt.
//
//  1) WATCHDOG APP — app phải nhấp PCL_W_HB mỗi giây. Quá PCL_APP_TMO_S giây
//     không thấy đổi → NHẢ PC control về HMI + kêu còi gọi thợ.
//     GIỮ NGUYÊN gas/gió (chủ máy chọn): mẻ đang rang không hỏng, thợ tới bấm tay.
//  2) MỒI HỤT — app bật gas mà quá PCL_FLAME_TMO_S giây vẫn không có gasSignal
//     → TỰ ĐÓNG GAS. Chốt này chạy BẤT KỂ app còn sống hay không.
// ════════════════════════════════════════════════════════════════════════════
static bool     pclAppLost    = false;   // đã nhả quyền vì mất app
static bool     pclFlameFail  = false;   // đã đóng gas vì mồi hụt
static uint16_t pclLastAppHb  = 0;
static uint32_t pclAppSeenMs  = 0;       // lần cuối thấy app nhấp heartbeat
static uint32_t pclGasOnMs    = 0;       // lúc gas được bật mà chưa có lửa

static void pclSafety(){
    const uint32_t now = millis();

    // ── 1) Watchdog app ────────────────────────────────────────────────────
    const uint16_t appHb = mbs.Hreg(PCL_W_HB);
    if (appHb != pclLastAppHb) {          // app còn sống
        pclLastAppHb = appHb;
        pclAppSeenMs = now;
        pclAppLost   = false;
    }
#if PCL_APP_WATCHDOG_EN
    if (PC_CONTROL_BTN_R == 1) {
        if (pclAppSeenMs == 0) pclAppSeenMs = now;   // vừa bật PC control, cho app 1 nhịp
        if (!pclAppLost && (now - pclAppSeenMs) > (uint32_t)PCL_APP_TMO_S * 1000UL) {
            pclAppLost = true;
            nodeHMI.writeSingleRegister(PC_CONTROL_BTN_W - 1, 0);   // trả quyền cho HMI
            buzzerTimerEn = 1;                                      // gọi thợ
            SerialComputer.println("=> PC_Link: mat app -> nha quyen ve HMI");
        }
    } else {
        pclAppSeenMs = 0;
    }
#else
    (void)now;   // watchdog TẮT theo Config.h — PC control không bao giờ tự nhả
#endif

    // ── 2) Mồi hụt → đóng gas ──────────────────────────────────────────────
    if (START_GAS_BTN_R == 1 && gasSignal == 0) {
        if (pclGasOnMs == 0) pclGasOnMs = now;
        if (!pclFlameFail && (now - pclGasOnMs) > (uint32_t)PCL_FLAME_TMO_S * 1000UL) {
            pclFlameFail = true;
            nodeHMI.writeSingleRegister(START_GAS_BTN_W - 1, 0);    // ĐÓNG GAS
            buzzerTimerEn = 1;
            SerialComputer.println("=> PC_Link: moi hut -> dong gas");
        }
    } else {
        pclGasOnMs = 0;
        if (gasSignal == 1) pclFlameFail = false;   // có lửa rồi thì xoá cờ
    }
}

void handle_PC_Link(){
    // ── 1) Khối ĐỌC — luôn cập nhật để app vẽ curve ─────────────────────────
    static uint16_t hb = 0;
    mbs.Hreg(PCL_R_BT,     Temperature_BT);
    mbs.Hreg(PCL_R_ET,     Temperature_ET);
    mbs.Hreg(PCL_R_RORBT,  (uint16_t)rorBT);
    mbs.Hreg(PCL_R_RORET,  (uint16_t)rorET);
    mbs.Hreg(PCL_R_RORPRO, (uint16_t)rorBT_pro);
    mbs.Hreg(PCL_R_GAS,    (uint16_t)gasPercent);
    mbs.Hreg(PCL_R_AIR,    (uint16_t)airflowPercent);
    mbs.Hreg(PCL_R_DRUM,   (uint16_t)drumPercent);
    mbs.Hreg(PCL_R_SV,     SV_BT);
    mbs.Hreg(PCL_R_VAC,    (uint16_t)Diff_Air);
    mbs.Hreg(PCL_R_STEP,   progStep);
    mbs.Hreg(PCL_R_TROAST, timeRoast);
    mbs.Hreg(PCL_R_DRUMHZ, (uint16_t)Drum_Freq_CP);   // tần số thật biến tần trống (0.01Hz)

    uint16_t ph = 0;
    if (START_BTN_R == 1) {
        if (progStep >= STP_TP)  ph |= PCLP_DRY;
        if (progStep >= STP_FCS) ph |= PCLP_MAI;
        if (progStep >= STP_DEV) ph |= PCLP_DEV;
    }
    mbs.Hreg(PCL_R_PHASE, ph);

    uint16_t fl = 0;
    if (START_BTN_R == 1)       fl |= PCLF_AUTO;
    if (START_GAS_BTN_R == 1)   fl |= PCLF_GAS;
    if (CHARGE_BTN_R == 1)      fl |= PCLF_CHARGE;
    if (DROP_BTN_R == 1)        fl |= PCLF_DROP;
    if (ESCAPE_BTN_R == 1)      fl |= PCLF_ESCAPE;
    if (COOLING_BTN_R == 1)     fl |= PCLF_COOL;
    if (PC_CONTROL_BTN_R == 1)  fl |= PCLF_PCCTRL;
    if (gasSignal == 1)         fl |= PCLF_FLAME;    // CÓ LỬA THẬT (chân CH1)
    if (pclAppLost)             fl |= PCLF_PCLOST;
    if (pclFlameFail)           fl |= PCLF_FLMFAIL;
    if (DRUM_FAN_BTN_R == 1)    fl |= PCLF_DRUMFAN;
    if (MIXER_BTN_R == 1)       fl |= PCLF_MIXER;
    if (AB_BTN_R == 1)          fl |= PCLF_AB;
    if (FEEDER_BTN_R == 1)      fl |= PCLF_LOADER;
    if (DESTONER_BTN_R == 1)    fl |= PCLF_DESTONER;
    mbs.Hreg(PCL_R_FLAGS, fl);
    mbs.Hreg(PCL_R_HB, ++hb);

    pclSafety();   // 2 chốt an toàn — chạy MỌI vòng, kể cả khi app đã im

    // ── 2) Khối GHI — chỉ khi bật nút PC control ────────────────────────────
    // Khi TẮT: phản chiếu setpoint máy vào khối ghi + chốt pclLastW để lúc bật
    //          control không bắn lệnh cũ. App vẫn thấy đúng số thực.
    if (PC_CONTROL_BTN_R != 1) {
        int16_t sp[PCL_W_COUNT] = {
            (int16_t)gasPercent, (int16_t)airflowPercent, (int16_t)drumPercent,
            svPC, vacuumSetpoint_R,
            START_GAS_BTN_R, CHARGE_BTN_R, DROP_BTN_R, ESCAPE_BTN_R, COOLING_BTN_R,
            START_BTN_R,
            0,                     // PCL_W_HB — heartbeat app, không phải setpoint
            DRUM_FAN_BTN_R, MIXER_BTN_R, AB_BTN_R, FEEDER_BTN_R, DESTONER_BTN_R
        };
        for (int i = 0; i < PCL_W_COUNT; i++) {
            mbs.Hreg(PCL_W_BASE + i, (uint16_t)sp[i]);
            pclLastW[i] = sp[i];
        }
        pclInited = true;
        return;
    }
    if (!pclInited) {   // an toàn: nếu boot đã ở chế độ PC control, seed 1 lần
        int16_t sp[PCL_W_COUNT] = {
            (int16_t)gasPercent, (int16_t)airflowPercent, (int16_t)drumPercent,
            svPC, vacuumSetpoint_R,
            START_GAS_BTN_R, CHARGE_BTN_R, DROP_BTN_R, ESCAPE_BTN_R, COOLING_BTN_R,
            START_BTN_R,
            0,                     // PCL_W_HB — heartbeat app, không phải setpoint
            DRUM_FAN_BTN_R, MIXER_BTN_R, AB_BTN_R, FEEDER_BTN_R, DESTONER_BTN_R
        };
        for (int i = 0; i < PCL_W_COUNT; i++) {
            mbs.Hreg(PCL_W_BASE + i, (uint16_t)sp[i]);
            pclLastW[i] = sp[i];
        }
        pclInited = true;
        return;
    }

    // — Nút do MÁY tự đổi (timer tự đóng charge/drop/escape, hoặc thợ bấm trên HMI):
    //   phản chiếu ngược vào khối ghi. Không có đoạn này thì sau khi firmware tự
    //   đóng xi lanh, ô lệnh của app vẫn treo ở 1 → lần bấm sau không tạo được
    //   cạnh đổi, nút chết cứng cho tới khi khởi động lại app.
    {
        const int16_t cur[5] = { START_GAS_BTN_R, CHARGE_BTN_R, DROP_BTN_R,
                                 ESCAPE_BTN_R, COOLING_BTN_R };
        for (uint8_t i = 0; i < 5; i++) {
            const uint8_t idx = 5 + i;              // PCL_W_IGNITE..PCL_W_COOL
            if (cur[i] != pclLastW[idx] &&
                (int16_t)mbs.Hreg(PCL_W_BASE + idx) == pclLastW[idx]) {
                pclLastW[idx] = cur[i];             // app chưa ra lệnh mới → máy thắng
                mbs.Hreg(PCL_W_BASE + idx, (uint16_t)cur[i]);
            }
        }
        // Thiết bị phụ (ô 12-16): cùng luật phản chiếu khi máy/thợ HMI tự đổi
        const int16_t cur2[5] = { DRUM_FAN_BTN_R, MIXER_BTN_R, AB_BTN_R,
                                  FEEDER_BTN_R, DESTONER_BTN_R };
        for (uint8_t i = 0; i < 5; i++) {
            const uint8_t idx = 12 + i;             // PCL_W_DRUMFAN..PCL_W_DESTONER
            if (cur2[i] != pclLastW[idx] &&
                (int16_t)mbs.Hreg(PCL_W_BASE + idx) == pclLastW[idx]) {
                pclLastW[idx] = cur2[i];
                mbs.Hreg(PCL_W_BASE + idx, (uint16_t)cur2[i]);
            }
        }
    }

    int16_t v;
    // — Setpoint: ghi HMI + cập nhật *_R/_R_CP/*Percent (giữ handler Artisan im).
    //   PHẢI đồng bộ cả Ô ARTISAN (reg 10/11/18/20/22): khi PC control bật, khối
    //   tương thích ngừng phản chiếu các ô đó (naviSource = AI_PC) nên chúng đứng
    //   im ở số cũ; handler của nó thấy lệch *_R_CP là kéo setpoint NGƯỢC về số
    //   cũ mỗi vòng — app chỉnh gas/gió/trống mà máy không đổi là vì vậy. —
    if (pclChanged(0, v) && MACHINE_HAS_GAS_CONTROL) {
        gasPercent = v; burnerValue_R = v; burnerValue_R_CP = v;
        mbs.Hreg(GAS_artisan_W, (uint16_t)v);
        nodeHMI.writeSingleRegister(burnerValue_W + 2000, v);
    }
    if (pclChanged(1, v)) {
        airflowPercent = v; airSpeed_R = v; airSpeed_R_CP = v;
        mbs.Hreg(AIR_artisan_W, (uint16_t)v);
        nodeHMI.writeSingleRegister(airSpeed_W + 2000, v);
    }
    if (pclChanged(2, v) && MACHINE_HAS_DRUM_SPEED_CONTROL) {
        drumPercent = v; drumSpeed_R = v; drumSpeed_R_CP = v;
        mbs.Hreg(DRUM_artisan_W, (uint16_t)v);
        nodeHMI.writeSingleRegister(drumSpeed_W + 2000, v);
    }
    if (pclChanged(3, v)) {
        svPC = v;
        mbs.Hreg(SV_artisan_W, (uint16_t)v);
        nodeHMI.writeSingleRegister(btSV_W + 2000, v / 10);
    }
    if (pclChanged(4, v) && MACHINE_HAS_VACUUM_SENSOR) {
        vacuumSetpoint_R = v; vacuumSetpoint_R_CP = v;
        mbs.Hreg(vacuumC_artisan_W, (uint16_t)v);
        nodeHMI.writeSingleRegister(vacuumSetpoint_W + 2000, v);
        pidAirflowReset();
    }

    // — Nút ảo: ghi coil HMI (charge/drop/escape kèm timer tự đóng + buzzer) —
    if (pclChanged(5, v))
        nodeHMI.writeSingleRegister(START_GAS_BTN_W - 1, v);
    if (pclChanged(6, v)) {
        nodeHMI.writeSingleRegister(CHARGE_BTN_W - 1, v);
        chargeTimerEn = 1; buzzerTimerEn = 1;
    }
    if (pclChanged(7, v)) {
        nodeHMI.writeSingleRegister(DROP_BTN_W - 1, v);
        dropTimerEn = 1; buzzerTimerEn = 1;
    }
    if (pclChanged(8, v)) {
        nodeHMI.writeSingleRegister(ESCAPE_BTN_W - 1, v);
        escapeTimerEn = 1; buzzerTimerEn = 1;
    }
    if (pclChanged(9, v))
        nodeHMI.writeSingleRegister(COOLING_BTN_W - 1, v);
    if (pclChanged(10, v))
        nodeHMI.writeSingleRegister(START_BTN_W - 1, v);

    // — Thiết bị phụ: mức BẬT/TẮT thuần, ghi coil HMI, relay theo IOConfig.h —
    if (pclChanged(12, v))
        nodeHMI.writeSingleRegister(DRUM_FAN_BTN_W - 1, v);
    if (pclChanged(13, v))
        nodeHMI.writeSingleRegister(MIXER_BTN_W - 1, v);
    if (pclChanged(14, v))
        nodeHMI.writeSingleRegister(AB_BTN_W - 1, v);
    if (pclChanged(15, v))
        nodeHMI.writeSingleRegister(FEEDER_BTN_W - 1, v);
    if (pclChanged(16, v))
        nodeHMI.writeSingleRegister(DESTONER_BTN_W - 1, v);
}

#else   // PC_LINK_EN == 0 — vô hiệu, không tốn gì
inline void pcLinkInit(){}
inline void handle_PC_Link(){}
#endif  // PC_LINK_EN

#endif  // PC_LINK_H
