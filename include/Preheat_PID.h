#pragma once
// Preheat_PID.h — Làm nóng máy rang tự động bằng PID cổ điển (BT → SV).
// Loại preheat thứ 2, chọn bằng PREHEAT_USE_PID=1 trong Config.h.
// Debug preheat: bật/tắt bằng PREHEAT_DEBUG_EN trong Config.h.
#ifndef PREHEAT_DEBUG_EN
#define PREHEAT_DEBUG_EN 1
#endif
#define enPhDebug (enDebug && (PREHEAT_DEBUG_EN))
//
// Triết lý: PID kéo BT về setpoint (SV = wuTemp_R) giống panel Artisan PID Control.
//   out = (kp·e + ki·∫e·dt + kd·de/dt) / 1000     (kp/ki/kd ×1000, không FPU)
//   e = SV − BT (0.1°C).  out > 0 → gas%;  out < 0 → air% để hạ nhiệt.
// kp/ki/kd và chu kỳ tính: xem PH_PID_* trong Config.h.
//
// Dùng CHUNG state machine + lớp an toàn với bản RoR-based:
//   IDLE → COOLING (nếu nóng) → PRE_IGNITE (purge) → IGNITE (mồi) → HEATING/HOLDING.
// Trong HEATING/HOLDING, gas/air do PID lái thay vì forecast.
// An toàn |ET−BT|>160°C → hủy. Gọi từ programScan() mỗi loop, tự throttle 1Hz.

enum WuState : uint8_t {
    WU_IDLE=0, WU_COOLING=1, WU_IGNITE=2, WU_HEATING=3,
    WU_HOLDING=4, WU_PRECISION=5, WU_TUNE=6, WU_PRE_IGNITE=7
};

// ── Trạng thái (tăng bởi ISR timerPoll_1000ms trong Program.h) ──────────────
static volatile WuState   wuState       = WU_IDLE;
static volatile uint16_t  wuElapsed     = 0;   // giây trong HEATING/HOLDING
static volatile uint16_t  wuIgniteTimer = 0;   // giây trong IGNITE

// ── Trạng thái nội bộ ───────────────────────────────────────────────────────
static int16_t  wuGasPercent    = 0;   // gas% hiện tại (mirror ra gasPercent)
static int16_t  wuAirPercent     = 0;  // airflow% hiện tại
static uint16_t wuDeadTimer      = 0;  // hiển thị debug (đếm purge/cooling)
static uint8_t  wuVacFlagSaved   = 0;  // lưu cờ vacuum PID để khôi phục khi xong
static uint8_t  wuIgniteRetry    = 0;  // số lần thử mồi lửa

// Giá trị gas/gió/drum đã đẩy lên HMI lần cuối — chỉ ghi lại khi đổi (change-gated).
// −1 = chưa ghi lần nào → tick đầu chắc chắn ghi.
static int16_t  wuPrevGasHMI     = -1;
static int16_t  wuPrevAirHMI     = -1;
static int16_t  wuPrevDrumHMI    = -1;

// Đẩy gas/gió/drum thực đang lái lên thanh ghi HIỂN THỊ HMI (+2000), chỉ khi đổi.
// Giảm tải Modbus: mỗi giây gọi 1 lần nhưng chỉ ghi register nào có giá trị mới.
static void wuPushIOToHMI() {
    if (gasPercent != wuPrevGasHMI) {
        nodeHMI.writeSingleRegister(burnerValue_W + 2000, gasPercent);
        wuPrevGasHMI = gasPercent;
    }
    if (airflowPercent != wuPrevAirHMI) {
        nodeHMI.writeSingleRegister(airSpeed_W + 2000, airflowPercent);
        wuPrevAirHMI = airflowPercent;
    }
    if (drumPercent != wuPrevDrumHMI) {
        nodeHMI.writeSingleRegister(drumSpeed_W + 2000, drumPercent);
        wuPrevDrumHMI = drumPercent;
    }
}

// ── Hệ số PID runtime (load từ SD, mặc định = Config). Đơn vị ×1000. ────────
// Có 2 bộ: HEATING (đang lên) và HOLDING (giữ target). Artisan gọi là gain scheduling.
// File SD lưu 6 số: kp, ki, kd (HEATING) rồi kp_h, ki_h, kd_h (HOLDING).
static int32_t  phKp             = PH_PID_KP;
static int32_t  phKi             = PH_PID_KI;
static int32_t  phKd             = PH_PID_KD;
static int32_t  phKpH            = PH_PID_KP_HOLD;
static int32_t  phKiH            = PH_PID_KI_HOLD;
static int32_t  phKdH            = PH_PID_KD_HOLD;

// ── Bảng gain scheduling theo SV: mỗi mức nhiệt 1 bộ HEAT gain (kp/ki/kd) ────
// HOLD gains dùng Config chung. Lưu/đọc từ /pid_pre.txt, mỗi dòng "SV,kp,ki,kd".
static int16_t  phSvTab[PH_SV_TABLE_MAX] = {0};   // mức SV (0.1°C)
static int32_t  phKpTab[PH_SV_TABLE_MAX] = {0};
static int32_t  phKiTab[PH_SV_TABLE_MAX] = {0};
static int32_t  phKdTab[PH_SV_TABLE_MAX] = {0};
static uint8_t  phSvCount         = 0;  // số mức đã lưu
static bool     phUsingStored     = false; // run này dùng gain từ bảng (true) hay tune/Config

// ── Trạng thái PID ──────────────────────────────────────────────────────────
static int32_t  phPidInteg       = 0;  // tích phân ∫e (đã chia về đơn vị output)
static int16_t  phPidPrevBT      = 0;  // BT lần trước (DoM: D tính trên BT)
static int32_t  phEmaD           = 0;  // EMA state cho D term (×100)
static int32_t  phEmaOut         = 0;  // EMA state cho output (×100)
static bool     phEmaInit        = false; // false = chưa khởi tạo EMA lần đầu
static int16_t  phBtStart        = 0;  // BT lúc vào HEATING (gốc đường tiến độ lookahead)
static int16_t  phMaxBT          = -32000; // BT cao nhất trong HEATING/HOLDING (đánh giá vọt)
static int16_t  phHoldMaxDev     = 0;  // độ lệch |BT−SV| lớn nhất khi đang HOLDING (sau settle)
static bool     phReachedHold    = false; // đã từng vào HOLDING chưa (đạt target)
static uint16_t phHoldStartSec   = 0;  // wuElapsed lúc vào HOLDING (để tính grace settle)
static int16_t  phPrevTarget     = 0;  // target lần trước (phát hiện đổi SV giữa chừng)
static uint16_t phTick           = 0;  // giây kể từ khi vào HEATING
static uint16_t phPidEvalTick    = 0;  // tick lần tính PID gần nhất
static uint32_t phLastMillis     = 0;  // throttle 1Hz
static uint32_t phIgniteMs       = 0;  // mốc millis cho purge/ignite

// ── Trạng thái relay autotune ────────────────────────────────────────────────
static const char* PH_PID_FILE   = "/pid_pre.txt";
static int16_t  phTuneSV         = 0;  // SV_tune thực tế (Low PV hoặc SV gốc)
static uint8_t  phTunePeaks      = 0;  // số đỉnh dao động đã ghi
static uint8_t  phTuneRelayHi    = 1;  // 1 = gas đang ở mức HI, 0 = LO
static int16_t  phTuneMax        = -32000; // đỉnh BT trong nửa chu kỳ hiện tại
static int16_t  phTuneMin        =  32000; // đáy BT
static uint16_t phTunePeakTick   = 0;  // tick lần ghi đỉnh gần nhất (đo chu kỳ)
static uint16_t phTunePuSum      = 0;  // tổng chu kỳ Pu (giây) để lấy trung bình
static int32_t  phTuneAmpSum     = 0;  // tổng biên độ (đỉnh−đáy) để lấy trung bình
static uint8_t  phTunePuCount    = 0;  // số chu kỳ đã cộng
static uint16_t phTuneLoSec      = 0;  // số giây liên tục ở trạng thái LO (phát hiện kẹt)
// Lịch sử BT để phát hiện spike nhiễu (discontinuity), giống Artisan pid.py
static int16_t  phBtHist[5]      = {0};
static uint8_t  phBtHistFill     = 0;

// Cập nhật lịch sử BT + trả về true nếu mẫu mới là spike bất thường
// (|ΔBT| hiện tại > 2.5× trung bình các Δ gần & > 1.0°C)
static bool phBtDiscontinuity(int16_t bt10) {
    bool spike = false;
    if (phBtHistFill >= 2) {
        int32_t sum = 0; uint8_t n = phBtHistFill - 1;
        for (uint8_t i = 1; i < phBtHistFill; i++)
            sum += abs(phBtHist[i] - phBtHist[i - 1]);
        int32_t avg = sum / n;
        int32_t cur = abs(bt10 - phBtHist[phBtHistFill - 1]);
        spike = (cur > avg * 5 / 2) && (cur > 10);   // 2.5× trung bình & >1.0°C
    }
    // shift ring giữ 5 mẫu cuối
    if (phBtHistFill < 5) {
        phBtHist[phBtHistFill++] = bt10;
    } else {
        for (uint8_t i = 0; i < 4; i++) phBtHist[i] = phBtHist[i + 1];
        phBtHist[4] = bt10;
    }
    return spike;
}

// ── Helper: kẹp % profile vào 0..100 (Program.h dùng khi đọc/ghi SD) ────────
static inline uint8_t clampProfilePercent(int v) {
    return (v < 0) ? 0 : (v > 100) ? 100 : (uint8_t)v;
}

// ── Lưu toàn bộ bảng gain (mỗi dòng "SV,kp,ki,kd") ra /pid_pre.txt ───────────
static void phPidSave() {
    char buf[PH_SV_TABLE_MAX * 40 + 8];
    int pos = 0;
    for (uint8_t i = 0; i < phSvCount; i++) {
        pos += snprintf(buf + pos, sizeof(buf) - pos, "%d,%ld,%ld,%ld\n",
                        (int)phSvTab[i], (long)phKpTab[i], (long)phKiTab[i], (long)phKdTab[i]);
    }
    SD.remove(PH_PID_FILE);
    File f = SD.open(PH_PID_FILE, FILE_WRITE);
    if (!f) { if (enDebug) SerialComputer.println("PID SAVE ERR"); return; }
    if (pos > 0) f.write((const uint8_t*)buf, pos);
    f.close();
    if (enDebug) { SerialComputer.print("PID table saved, n="); SerialComputer.println(phSvCount); }
}

// ── Tìm mức SV trong bảng (chênh ≤ PH_SV_MATCH) → index, hoặc −1 nếu chưa có ──
static int8_t phSvLookup(int16_t sv) {
    for (uint8_t i = 0; i < phSvCount; i++)
        if (abs(phSvTab[i] - sv) <= PH_SV_MATCH) return (int8_t)i;
    return -1;
}

// ── Thêm/cập nhật bộ gain cho mức SV (upsert) ───────────────────────────────
static void phSvUpsert(int16_t sv, int32_t kp, int32_t ki, int32_t kd) {
    int8_t idx = phSvLookup(sv);
    if (idx < 0) {
        if (phSvCount >= PH_SV_TABLE_MAX) return;   // hết chỗ → bỏ qua
        idx = phSvCount++;
        phSvTab[idx] = sv;
    }
    phKpTab[idx] = kp; phKiTab[idx] = ki; phKdTab[idx] = kd;
    phPidSave();
}

// ── Xoá bộ gain của 1 mức SV (khi tune mức đó cho kết quả tệ) ────────────────
static void phSvRemove(int8_t idx) {
    if (idx < 0 || idx >= phSvCount) return;
    for (uint8_t i = idx; i + 1 < phSvCount; i++) {
        phSvTab[i] = phSvTab[i+1]; phKpTab[i] = phKpTab[i+1];
        phKiTab[i] = phKiTab[i+1]; phKdTab[i] = phKdTab[i+1];
    }
    phSvCount--;
    phPidSave();
}

// ── phFFLoad: gọi 1 lần lúc khởi động — load bảng gain từ SD ─────────────────
void phFFLoad() {
    phSvCount = 0;
    File f = SD.open(PH_PID_FILE, FILE_READ);
    if (!f) { if (enDebug) SerialComputer.println("PID: no SD table, use Config"); return; }
    char buf[PH_SV_TABLE_MAX * 40 + 8];
    int len = f.read((uint8_t*)buf, sizeof(buf) - 1);
    f.close();
    if (len <= 0) return;
    buf[len] = '\0';
    char* line = strtok(buf, "\n");
    while (line && phSvCount < PH_SV_TABLE_MAX) {
        // parse "SV,kp,ki,kd"
        char* c1 = strchr(line, ',');     if (!c1) { line = strtok(NULL, "\n"); continue; }
        char* c2 = strchr(c1 + 1, ',');   if (!c2) { line = strtok(NULL, "\n"); continue; }
        char* c3 = strchr(c2 + 1, ',');   if (!c3) { line = strtok(NULL, "\n"); continue; }
        *c1 = *c2 = *c3 = '\0';
        phSvTab[phSvCount] = (int16_t)atoi(line);
        phKpTab[phSvCount] = atol(c1 + 1);
        phKiTab[phSvCount] = atol(c2 + 1);
        phKdTab[phSvCount] = atol(c3 + 1);
        phSvCount++;
        line = strtok(NULL, "\n");
    }
    if (enDebug) { SerialComputer.print("PID table loaded, n="); SerialComputer.println(phSvCount); }
}

// ── wuReset: trả về IDLE, khôi phục vacuum PID, đóng gas ─────────────────────
void wuReset() {
    wuState         = WU_IDLE;
    wuElapsed       = 0;
    wuIgniteTimer   = 0;
    wuDeadTimer     = 0;
    wuGasPercent    = 0;
    wuAirPercent    = 0;
    wuIgniteRetry   = 0;
    phTick          = 0;
    phPidEvalTick   = 0;
    phPidInteg      = 0;
    phPidPrevBT     = 0;
    phEmaD          = 0;
    phEmaOut        = 0;
    phEmaInit       = false;
    phBtStart       = 0;
    phMaxBT         = -32000;
    phHoldMaxDev    = 0;
    phReachedHold   = false;
    phHoldStartSec  = 0;
    phPrevTarget    = 0;
    phBtHistFill    = 0;
    phIgniteMs      = 0;
    gasPercent      = 0;
    airflowPercent  = 0;
    naviSourceGAS   = 0;
    naviSourceAIR   = 0;
    vacuumSetFlag_R = wuVacFlagSaved;
    if (vacuumSetFlag_R == 1) {
        // Khôi phục cả trên HMI để _CP đồng bộ, tránh vòng quét ép tắt lại.
        nodeHMI.writeSingleRegister(vacuumSetFlag_W + 2000, 1);
        pidAirflowReset();
    }
    wuVacFlagSaved  = 0;
    nodeHMI.writeSingleRegister(START_GAS_BTN_W - 1, 0);
    tunePercent     = 0;
    // Xoá mốc HMI để lần preheat sau tick đầu luôn ghi lại gas/gió/drum
    wuPrevGasHMI = wuPrevAirHMI = wuPrevDrumHMI = -1;
}

// ── preheat() — gọi từ programScan() mỗi loop, tự throttle 1Hz ──────────────
void preheat() {
    uint32_t now = millis();
    if (now - phLastMillis < 1000) {
        // Giữ output ổn định giữa các tick 1Hz
        if (wuState == WU_HEATING || wuState == WU_HOLDING) {
            gasPercent     = constrain(wuGasPercent, 0, 100);
            airflowPercent = constrain(wuAirPercent, 0, 100);
        }
        return;
    }
    phLastMillis = now;

    // Hủy khi người dùng tắt preheat từ HMI
    if (WU_R == 0 && wuState != WU_IDLE) {
        setMachineStatus(STT_PREHEAT_CANCELLED);
        if (enPhDebug) SerialComputer.println("PREHEAT-PID: cancelled");
        wuReset();
        return;
    }
    if (WU_R == 0) return;

    int16_t targetBT10 = (int16_t)wuTemp_R * 10;
    int16_t bt10       = (int16_t)Temperature_BT;
    int16_t et10       = (int16_t)Temperature_ET;

    // ── An toàn: ET và BT lệch quá 160°C -> hủy preheat, tắt gas ────────────
    if (wuState != WU_IDLE && abs(et10 - bt10) > PH_DIVERGE_LIMIT) {
        setMachineStatus(STT_TEMP_DIVERGENCE);
        gasPercent = 0;
        nodeHMI.writeSingleRegister(START_GAS_BTN_W - 1, 0);
        if (enPhDebug) {
            SerialComputer.print("PREHEAT-PID ABORT |ET-BT|>160 ET=");
            SerialComputer.print(et10/10); SerialComputer.print(" BT=");
            SerialComputer.println(bt10/10);
        }
        wuReset();
        nodeHMI.writeSingleRegister(WU_W - 1, 0);
        return;
    }

    // ── Trần an toàn riêng PID: BT vượt SV+15°C → cắt gas + gió mạnh ──────────
    // Áp dụng mọi lúc đang đốt (TUNE/HEATING/HOLDING). Chặn vọt lố trước khi
    // tới ngưỡng |ET−BT|>160 hay ISR BT>250. Không hủy preheat, chỉ ghì BT xuống.
    if ((wuState == WU_TUNE || wuState == WU_HEATING || wuState == WU_HOLDING) &&
        bt10 > targetBT10 + PH_PID_OVERHEAT_GUARD) {
        wuGasPercent   = 0;
        wuAirPercent   = PH_TUNE_AIR_LO;   // gió mạnh kéo xuống
        gasPercent     = 0;
        airflowPercent = PH_TUNE_AIR_LO;
        if (enPhDebug) { SerialComputer.print("PID OVERHEAT guard BT="); SerialComputer.println(bt10/10); }
        return;   // bỏ qua tính PID/relay tick này
    }

    switch (wuState) {

    // ── IDLE: nhận quyền điều khiển, chọn đường (cooling nếu đang nóng) ─────
    case WU_IDLE: {
        naviSourceGAS  = SOURCE_AI_AUTO;
        naviSourceAIR  = SOURCE_AI_AUTO;
        wuVacFlagSaved = vacuumSetFlag_R;
        if (vacuumSetFlag_R == 1) {
            // Cưỡng ép TẮT cả trên HMI để _CP đồng bộ về 0, tránh vòng quét HMI
            // (Modbus_Master rwMemHMI) ép vacuumSetFlag_R bật lại giữa preheat —
            // nếu bật lại, analogIn() chạy vacuum PID và tranh quyền gió với preheat.
            vacuumSetFlag_R = 0;           // tắt vacuum PID — preheat tự lái gió
            nodeHMI.writeSingleRegister(vacuumSetFlag_W + 2000, 0);
        }
        gasPercent = 0;
        nodeHMI.writeSingleRegister(START_GAS_BTN_W - 1, 0);

        if (bt10 > targetBT10 + PH_TARGET_BAND) {
            wuState = WU_COOLING;
            wuDeadTimer = 0;
            setMachineStatus(STT_PREHEAT_COOLING);
            if (enPhDebug) { SerialComputer.print("PREHEAT-PID: cooling BT="); SerialComputer.println(bt10/10); }
        } else {
            wuState = WU_PRE_IGNITE;
            phIgniteMs = 0;
            setMachineStatus(STT_PREHEAT_PRE_IGNITE);
            if (enPhDebug) SerialComputer.println("PREHEAT-PID: pre-ignite");
        }
    }
    break;

    // ── COOLING: BT cao hơn target -> gió mạnh hạ nhiệt rồi mới mồi ─────────
    case WU_COOLING: {
        wuGasPercent = 0;
        wuAirPercent = PH_AIR_PURGE;
        gasPercent = 0;
        airflowPercent = PH_AIR_PURGE;
        if (wuDeadTimer < 65535) wuDeadTimer++;
        if (bt10 <= targetBT10) {
            wuState = WU_PRE_IGNITE;
            phIgniteMs = 0; wuDeadTimer = 0;
            setMachineStatus(STT_PREHEAT_COOLING_DONE);
            if (enPhDebug) SerialComputer.println("COOLING -> PRE_IGNITE");
        }
    }
    break;

    // ── PRE_IGNITE: thổi sạch buồng đốt trước khi mở gas ───────────────────
    case WU_PRE_IGNITE: {
        if (phIgniteMs == 0) phIgniteMs = now;
        wuAirPercent = PH_AIR_PURGE;
        gasPercent = 0;
        airflowPercent = PH_AIR_PURGE;
        if (now - phIgniteMs >= PH_PURGE_MS) {
            wuState = WU_IGNITE;
            wuIgniteTimer = 0;
            wuIgniteRetry = 0;
            nodeHMI.writeSingleRegister(START_GAS_BTN_W - 1, 1);  // mở van gas
            if (enPhDebug) SerialComputer.println("PRE_IGNITE: done -> IGNITE");
        }
    }
    break;

    // ── IGNITE: mở 30% gas mồi lửa, chờ gasSignal, thử lại tối đa 3 lần ─────
    case WU_IGNITE: {
        gasPercent     = 30;
        airflowPercent = 30;
        if (gasSignal == 1) {
            // Mồi thành công. Chưa có file SD → relay autotune trước; có rồi → HEATING.
            wuElapsed = 0;
            wuAirPercent = PH_AIR_BASE;
            phTick = phPidEvalTick = 0;
            phPidInteg = 0;
            phPidPrevBT = bt10;
            phEmaD = 0; phEmaOut = 0; phEmaInit = false;
            phBtStart = bt10;   // gốc đường tiến độ cho lookahead
            phBtHistFill = 0;
            // Tính SV_tune để quyết định có tune được không
#if PH_TUNE_LOWPV_EN
            phTuneSV = (int16_t)((int32_t)PH_TUNE_FRL +
                       ((int32_t)(targetBT10 - PH_TUNE_FRL) * 9 / 10));
            if (phTuneSV >= targetBT10) phTuneSV = targetBT10 - 100;
#else
            phTuneSV = targetBT10;
#endif
            // Gain scheduling: tra bảng theo mức SV.
            //   Có gain mức này rồi → dùng luôn, BỎ tune (khách luân phiên không tune lại).
            //   Chưa có + máy đủ nguội (BT<SV_tune) → TUNE mức này.
            //   Chưa có + máy nóng → HEATING với Config (không tune được lúc nóng).
            int8_t svIdx = phSvLookup(targetBT10);
            if (svIdx >= 0) {
                phKp = phKpTab[svIdx]; phKi = phKiTab[svIdx]; phKd = phKdTab[svIdx];
                phUsingStored = true;
                wuState = WU_HEATING;
                wuGasPercent = 30;
                setMachineStatus(STT_PREHEAT_IGNITE_OK);
                if (enPhDebug) {
                    SerialComputer.print("PREHEAT-PID: stored gains SV="); SerialComputer.print(targetBT10/10);
                    SerialComputer.print(" kp="); SerialComputer.print(phKp);
                    SerialComputer.print(" ki="); SerialComputer.print(phKi);
                    SerialComputer.print(" kd="); SerialComputer.println(phKd);
                }
            } else if (bt10 < phTuneSV) {
                phUsingStored = false;
                wuState = WU_TUNE;
                wuGasPercent  = PH_TUNE_GAS_HI;
                wuAirPercent  = PH_TUNE_AIR_HI;
                if (enPhDebug) {
                    SerialComputer.print("TUNE SV_tune="); SerialComputer.print(phTuneSV/10);
                    SerialComputer.println(PH_TUNE_LOWPV_EN ? " (LowPV)" : " (Std)");
                }
                phTunePeaks   = 0;
                phTuneRelayHi = 1;
                phTuneMax     = -32000;
                phTuneMin     =  32000;
                phTunePeakTick = 0;
                phTunePuSum = phTuneAmpSum = phTunePuCount = 0;
                phTuneLoSec   = 0;
                setMachineStatus(STT_PREHEAT_IGNITE_OK);
                if (enPhDebug) SerialComputer.println("PREHEAT-PID: gas on -> TUNE (SV chua co trong bang)");
            } else {
                // Máy nóng, chưa có gain mức này → dùng Config tạm
                phKp = PH_PID_KP; phKi = PH_PID_KI; phKd = PH_PID_KD;
                phUsingStored = false;
                wuState = WU_HEATING;
                wuGasPercent = 30;
                setMachineStatus(STT_PREHEAT_IGNITE_OK);
                if (enPhDebug) SerialComputer.println("PREHEAT-PID: BT>SV_tune, skip tune -> HEATING (Config gains)");
            }
            break;
        }
        if (wuIgniteTimer >= PH_IGNITE_TMO) {
            wuIgniteTimer = 0;
            nodeHMI.writeSingleRegister(START_GAS_BTN_W - 1, 0);
            if (++wuIgniteRetry >= PH_IGNITE_RETRY) {
                setMachineStatus(STT_PREHEAT_IGNITE_FAIL);
                if (enPhDebug) SerialComputer.println("PREHEAT-PID: ignition failed 3x");
                wuReset();
                nodeHMI.writeSingleRegister(WU_W - 1, 0);
                return;
            }
            nodeHMI.writeSingleRegister(START_GAS_BTN_W - 1, 1);
            setMachineStatus(STT_PREHEAT_IGNITE_RETRY);
            if (enPhDebug) { SerialComputer.print("PREHEAT-PID: retry #"); SerialComputer.println(wuIgniteRetry + 1); }
        }
    }
    break;

    // ── TUNE: relay autotune Ziegler-Nichols, đo dao động quanh SV ─────────
    case WU_TUNE: {
        phTick++;
        tunePercent = (uint16_t)((uint32_t)phTunePuCount * 100 / PH_TUNE_CYCLES);
        nodeHMI.writeSingleRegister(MIN_HMI_W - 1, wuElapsed / 60);
        nodeHMI.writeSingleRegister(SEC_HMI_W - 1, wuElapsed % 60);
        wuPushIOToHMI();   // đẩy gas/gió/drum lên HMI, chỉ khi giá trị đổi

        // Quá lâu chưa xong → bỏ tune, dùng hệ số Config
        if (wuElapsed >= PH_TUNE_TIMEOUT_SEC) {
            if (enPhDebug) SerialComputer.println("TUNE timeout -> use Config kp/ki/kd");
            wuState = WU_HEATING;
            wuGasPercent = 30; phTick = phPidEvalTick = 0;
            phPidInteg = 0; phPidPrevBT = bt10;
            phBtStart = bt10;      // reset gốc lookahead theo vị trí BT hiện tại
            phEmaD = 0; phEmaOut = 0; phEmaInit = false;
            break;
        }

        // Relay 2 mức để ép BT dao động quanh SV (đo Ku/Pu):
        //   BT < SV → gas HI + gió nền (đốt nóng lên)
        //   BT > SV → gas 0  + gió mạnh (kéo BT xuống — máy quán tính nhiệt lớn,
        //             nếu không tắt gas + thổi gió thì BT không chịu tụt xuống dưới SV)
        if (bt10 < phTuneSV) {
            if (bt10 < phTuneMin) phTuneMin = bt10;
            if (phTuneRelayHi == 0) {
                // Vừa cắt qua SV_tune xuống dưới → kết thúc 1 nửa chu kỳ (đáy)
                phTuneRelayHi = 1;
                wuGasPercent  = PH_TUNE_GAS_HI;
                wuAirPercent  = PH_TUNE_AIR_HI;
                // Ghi 1 đỉnh dao động (cặp max−min) + đo chu kỳ
                if (phTunePeaks > 0) {
                    phTuneAmpSum += (phTuneMax - phTuneMin);
                    uint16_t pu = phTick - phTunePeakTick;
                    phTunePuSum += pu; phTunePuCount++;
                }
                phTunePeakTick = phTick;
                phTuneMax = -32000; phTuneMin = 32000;
                phTunePeaks++;
                if (enPhDebug) { SerialComputer.print("TUNE peak "); SerialComputer.println(phTunePeaks); }
            }
        } else {
            if (bt10 > phTuneMax) phTuneMax = bt10;
            if (phTuneRelayHi == 1) {
                phTuneRelayHi = 0;
                phTuneLoSec   = 0;                // bắt đầu đếm thời gian ở LO
                wuGasPercent  = PH_TUNE_GAS_LO;   // 0, tắt gas
                wuAirPercent  = PH_TUNE_AIR_LO;   // gió mạnh hạ nhiệt
            }
            phTuneLoSec++;   // mỗi tick (1s) ở LO mà BT vẫn chưa cắt xuống dưới SV_tune
        }

        // KẸT: ở LO quá PH_TUNE_STUCK_SEC mà BT không tụt nổi xuống dưới SV_tune
        // (máy nóng sẵn, nhiệt dư > SV_tune) → bỏ tune, dùng Config gains.
        if (phTuneRelayHi == 0 && phTuneLoSec >= PH_TUNE_STUCK_SEC) {
            if (enPhDebug) SerialComputer.println("TUNE STUCK (BT khong tut duoi SVt, may nong) -> dung Config gains");
            wuState = WU_HEATING;
            wuGasPercent = 30; phTick = phPidEvalTick = 0;
            phPidInteg = 0; phPidPrevBT = bt10;
            phBtStart = bt10; phEmaD = 0; phEmaOut = 0; phEmaInit = false;
            break;
        }

        // Log TUNE mỗi 3 giây — để nhìn thấy relay có dao động không (nếu kẹt
        // thì peak không tăng, BT không cắt qua SV_tune → biết ngay nguyên nhân)
        if (enPhDebug && (wuElapsed % 3 == 0)) {
            uint16_t tM = wuElapsed/60, tS = wuElapsed%60;
            SerialComputer.print("["); SerialComputer.print(tM); SerialComputer.print(":");
            if (tS<10) SerialComputer.print("0");
            SerialComputer.print(tS); SerialComputer.print("] TUNE BT="); SerialComputer.print(bt10/10);
            SerialComputer.print(" SVt="); SerialComputer.print(phTuneSV/10);
            SerialComputer.print(phTuneRelayHi ? " HI" : " LO");
            SerialComputer.print(" gas="); SerialComputer.print(wuGasPercent);
            SerialComputer.print(" air="); SerialComputer.print(wuAirPercent);
            SerialComputer.print(" peak="); SerialComputer.print(phTunePeaks);
            SerialComputer.print(" cyc="); SerialComputer.print(phTunePuCount);
            SerialComputer.println();
        }

        // Đủ số chu kỳ → tính Ziegler-Nichols, lưu SD, vào HEATING
        if (phTunePuCount >= PH_TUNE_CYCLES) {
            int32_t aAvg = phTuneAmpSum / phTunePuCount;       // biên độ đỉnh−đáy (0.1°C)
            int32_t puAvg = phTunePuSum / phTunePuCount;       // chu kỳ (giây)
            int32_t d = (PH_TUNE_GAS_HI - PH_TUNE_GAS_LO) / 2; // biên độ relay (%)
            // Ku = 4·d / (π·a),  a = biên độ BT 1 phía (°C)
            // a_tenthC (0.1°C) → a_C = a_tenthC/10
            // Ku×1000 = 4·d·1000 / (π · a_C) = 4·d·10000 / (π · a_tenthC)
            // π≈3142/1000 → Ku×1000 = 4·d·10000·1000 / (3142 · a_tenthC)
            int32_t a_tenthC = aAvg / 2;                       // biên độ 1 phía (0.1°C)
            int32_t Ku1000 = (a_tenthC > 0)
                ? (4L * d * 10000L * 1000L / (3142L * a_tenthC)) : PH_PID_KP;
            // Kp = 0.6·Ku ; Ki = 2·Kp/Pu ; Kd = 0.125·Kp·Pu  (giữ ×1000)
            phKp = 6 * Ku1000 / 10;
            phKi = (puAvg > 0) ? (2 * phKp / puAvg) : PH_PID_KI;
            phKd = phKp * puAvg / 8;
            // Kẹp an toàn 0.25–4× Config (rộng để autotune thích nghi đầu đốt khác,
            // vẫn chặn số vô lý nếu đo dao động lỗi)
            phKp = constrain(phKp, PH_PID_KP/4, PH_PID_KP*4);
            phKi = constrain(phKi, PH_PID_KI/4, PH_PID_KI*4);
            phKd = constrain(phKd, PH_PID_KD/4, PH_PID_KD*4);
            // Lưu gain vào bảng theo mức SV (targetBT10). HOLD gains giữ Config.
            phSvUpsert(targetBT10, phKp, phKi, phKd);
            phUsingStored = true;
            if (enPhDebug) {
                SerialComputer.print("TUNE done a="); SerialComputer.print(aAvg);
                SerialComputer.print(" Pu="); SerialComputer.print(puAvg);
                SerialComputer.print(" -> kp="); SerialComputer.print(phKp);
                SerialComputer.print(" ki="); SerialComputer.print(phKi);
                SerialComputer.print(" kd="); SerialComputer.println(phKd);
            }
            wuState = WU_HEATING;
            wuGasPercent = 30; phTick = phPidEvalTick = 0;
            phPidInteg = 0; phPidPrevBT = bt10;
            phBtStart = bt10;      // reset gốc lookahead theo BT lúc tune xong
            phEmaD = 0; phEmaOut = 0; phEmaInit = false;
        }

        gasPercent     = constrain(wuGasPercent, 0, 100);
        airflowPercent = constrain(wuAirPercent, 0, 100);
    }
    break;

    // ── HEATING + HOLDING: PID kéo BT về SV ────────────────────────────────
    case WU_HEATING:
    case WU_HOLDING: {
        phTick++;
        // Đổi SV giữa chừng (người dùng chỉnh setpoint) → reset đánh giá ổn định:
        // quay lại HEATING nếu lệch lớn, đo lại từ đầu (transient đổi SV không bị
        // ghi nhầm làm "max dev" → tránh báo BAD oan + tune lại vô ích).
        if (phPrevTarget != 0 && targetBT10 != phPrevTarget) {
            phHoldMaxDev = 0;
            phMaxBT = bt10;
            if (abs(targetBT10 - bt10) > PH_TARGET_BAND) {
                wuState = WU_HEATING;          // SV mới còn xa → đốt/hạ lại
                phBtStart = bt10;              // gốc lookahead mới
            } else {
                phHoldStartSec = wuElapsed;    // SV mới gần → đo lại sau settle
            }
            if (enPhDebug) { SerialComputer.print("SV changed -> "); SerialComputer.println(targetBT10/10); }
        }
        phPrevTarget = targetBT10;
        if (bt10 > phMaxBT) phMaxBT = bt10;   // theo dõi BT cao nhất (đánh giá vọt)
        // Khi đang HOLDING: theo dõi độ lệch |BT−SV| lớn nhất ĐỂ ĐÁNH GIÁ ổn định.
        // Bỏ qua PH_HOLD_SETTLE_SEC giây đầu (giai đoạn chuyển tiếp, BT chưa kịp ổn).
        if (wuState == WU_HOLDING &&
            (uint16_t)(wuElapsed - phHoldStartSec) >= PH_HOLD_SETTLE_SEC) {
            int16_t dev = (int16_t)targetBT10 - bt10; if (dev < 0) dev = -dev;
            if (dev > phHoldMaxDev) phHoldMaxDev = dev;
        }
        tunePercent = (targetBT10 > 200)
            ? (uint16_t)constrain((int32_t)bt10 * 100 / targetBT10, 0, 100) : 0;
        nodeHMI.writeSingleRegister(MIN_HMI_W - 1, wuElapsed / 60);
        nodeHMI.writeSingleRegister(SEC_HMI_W - 1, wuElapsed % 60);
        wuPushIOToHMI();   // đẩy gas/gió/drum lên HMI, chỉ khi giá trị đổi

        // Hết tổng thời gian preheat -> kết thúc + TỰ ĐÁNH GIÁ chất lượng tune.
        // Nếu kết quả TỆ (lệch cuối lớn hoặc vọt nhiều) → xóa /pid_pre.txt để
        // lần preheat sau TỰ TUNE LẠI (1 nút, không cần xóa file tay).
        if (wuTime_R > 0 && wuElapsed >= (uint16_t)wuTime_R * 60) {
            // Tune TỆ nếu: không vào nổi HOLD, hoặc lệch khi HOLD > ±2°C.
            // Đánh giá theo MỨC SV hiện tại (gain scheduling):
            //   TỆ → xoá entry mức này khỏi bảng (chỉ mức này tune lại, mức khác giữ).
            //   TỐT mà chưa có entry → thêm gain hiện tại vào bảng cho mức này.
            bool tuneBad = (!phReachedHold) || (phHoldMaxDev > PH_TUNE_HOLD_DEV);
            int8_t svIdx2 = phSvLookup(targetBT10);
            if (tuneBad) {
                if (svIdx2 >= 0) phSvRemove(svIdx2);   // chỉ xoá mức này
                if (enPhDebug) {
                    SerialComputer.print("PREHEAT-PID: tune BAD SV="); SerialComputer.print(targetBT10/10);
                    SerialComputer.print(" (reachedHold="); SerialComputer.print(phReachedHold);
                    SerialComputer.print(" holdDev="); SerialComputer.print(phHoldMaxDev/10);
                    SerialComputer.println(") -> re-tune mức này lần sau");
                }
            } else {
                if (svIdx2 < 0) phSvUpsert(targetBT10, phKp, phKi, phKd);  // lưu mức mới
                if (enPhDebug) {
                    SerialComputer.print("PREHEAT-PID: tune OK SV="); SerialComputer.print(targetBT10/10);
                    SerialComputer.print(" (holdDev="); SerialComputer.print(phHoldMaxDev/10);
                    SerialComputer.println(") -> keep gains");
                }
            }
            setMachineStatus(STT_PREHEAT_DONE);
            if (enPhDebug) SerialComputer.println("PREHEAT-PID: done (time)");
            wuReset();
            nodeHMI.writeSingleRegister(WU_W - 1, 0);
            return;
        }

        int16_t gap = targetBT10 - bt10;   // dương = BT còn dưới target (= e)

        // Vào HOLDING khi BT lần đầu chạm vùng target ±3°C
        // Chuyển sang bộ hệ số HOLD + reset Iterm (bumpless: tránh giật khi đổi bộ số)
        if (wuState == WU_HEATING && abs(gap) <= PH_TARGET_BAND) {
            wuState = WU_HOLDING;
            phReachedHold = true;   // đã đạt target → bắt đầu đo độ ổn định HOLD
            phHoldStartSec = wuElapsed;   // mốc để bỏ qua giai đoạn chuyển tiếp
            // BUMPLESS TRANSFER đúng nghĩa: KHÔNG reset I=0 (làm gas rớt về 0,
            // gió thổi mạnh → BT tụt → dao động). Thay vào đó nạp lại I sao cho
            // output HOLD ban đầu = output HEATING vừa rồi (gas không nhảy).
            // out = P_hold + I  →  I = out_prev − P_hold. Lưu thang ×100.
            int32_t pHoldNow = phKpH * (((int32_t)PH_PID_BETA * targetBT10 / 100) - bt10) / 10000;
            int32_t outPrev  = constrain(wuGasPercent, 0, 100); // output HEATING vừa rồi (gas%)
            phPidInteg = (outPrev - pHoldNow) * 100;
            phPidInteg = constrain(phPidInteg, -(int32_t)PH_PID_IMAX*100, (int32_t)PH_PID_IMAX*100);
            phEmaInit = false;  // EMA seed lại theo output mới (không reset phEmaD/Out=0 cứng)
            setMachineStatus(STT_PREHEAT_HOLDING);
            if (enPhDebug) SerialComputer.println("HEATING -> HOLDING (bumpless, keep gas)");
        }

        // ── SV hiệu dụng với lookahead (Artisan "Lookahead 6s") ──────────────
        // HEATING: SV_eff = điểm trên đường tiến độ tại (elapsed + lookahead).
        // Đường tiến độ đi từ phBtStart → target trong PH_DEADLINE_SEC (3 phút),
        // KHÔNG dùng toàn bộ Time preheat (Time gồm cả thời gian giữ nhiệt sau đó).
        // Quá mốc 3 phút → svEff = target. PID nhìn trước để phản ứng sớm.
        int16_t svEff = targetBT10;
        if (wuState == WU_HEATING && targetBT10 > phBtStart) {
            int32_t tAhead = (int32_t)wuElapsed + PH_PID_LOOKAHEAD_SEC;
            if (tAhead < PH_DEADLINE_SEC) {
                svEff = phBtStart + (int16_t)((int32_t)(targetBT10 - phBtStart) * tAhead / PH_DEADLINE_SEC);
                if (svEff > targetBT10) svEff = targetBT10;
                if (svEff < phBtStart)  svEff = phBtStart;
            }
            // tAhead ≥ 3 phút → giữ svEff = targetBT10 (đã set mặc định)
        }

        // ── Tính PID mỗi PH_PID_EVAL_SEC giây ──────────────────────────────
        if ((uint16_t)(phTick - phPidEvalTick) >= PH_PID_EVAL_SEC) {
            uint16_t dt = phTick - phPidEvalTick;   // giây trôi qua
            if (dt < 1) dt = 1;                     // chống chia 0 ở D term
            phPidEvalTick = phTick;

            // Chọn bộ hệ số theo giai đoạn (gain scheduling 2 vùng)
            int32_t kp = (wuState == WU_HOLDING) ? phKpH : phKp;
            int32_t ki = (wuState == WU_HOLDING) ? phKiH : phKi;
            int32_t kd = (wuState == WU_HOLDING) ? phKdH : phKd;

            int16_t e = svEff - bt10;                // sai số cho I/D = SV_eff − BT (0.1°C)
            // 2DOF P term: P = Kp × (beta×TARGET − BT).
            // QUAN TRỌNG: beta áp lên TARGET THẬT (targetBT10), KHÔNG lên svEff.
            // Nếu áp lên svEff (sát BT do lookahead) thì beta<1 làm P ÂM dù BT còn
            // thấp hơn target rất nhiều → cắt gas sai (lỗi đã gặp khi test).
            // I và D vẫn dùng e = SV_eff − BT (lookahead) bình thường.
            int32_t pInput = ((int32_t)PH_PID_BETA * targetBT10 / 100) - bt10; // beta×target − BT
            int32_t prop = kp * pInput / 10000;

            // ── Trần tích phân ĐỘNG (port Artisan applyIntegralLimits) ─────────
            // beta<1 làm P âm 1 lượng cố định khi ở target = kp×target×(1−beta).
            // Phải NÂNG trần I thêm đúng lượng đó để I bù được, nếu không BT kẹt
            // dưới target ở SV cao (bug đã gặp ở 230°C: thâm hụt 115 > IMAX 100).
            int32_t iExtra = (int32_t)kp * targetBT10 / 10000 * (100 - PH_PID_BETA) / 100;
            if (iExtra < 0) iExtra = 0;
            int32_t iMax = ((int32_t)PH_PID_IMAX + iExtra) * 100;   // thang ×100
            int32_t iMin = -(int32_t)PH_PID_IMAX * 100;

            // ── Tích phân — LƯU Ở THANG ×100 để không mất phần lẻ khi ki nhỏ.
            int32_t iTermNow = phPidInteg / 100;           // Iterm hiện tại (đơn vị %)
            int32_t outEstimate = prop + iTermNow;         // ước tính trước khi tích
            bool shouldInteg = !((outEstimate >= 100 && e > 0) ||
                                 (outEstimate <= -100 && e < 0));
            if (shouldInteg) {
                phPidInteg += ki * e * dt / 100;           // ×100 thang: /100 thay vì /10000
                phPidInteg = constrain(phPidInteg, iMin, iMax);
            }
            int32_t iTerm = phPidInteg / 100;              // Iterm để cộng vào output

            // ── Vi phân DoM (Artisan): D tính trên delta BT, không trên sai số.
            // Nhân Kd trước rồi mới chia (dt·10000) để giữ độ chính xác số nguyên.
            int32_t dBT = -(int32_t)(bt10 - phPidPrevBT);   // delta BT (0.1°C), đảo dấu
            phPidPrevBT = bt10;
            int32_t deriv = kd * dBT / (10000 * (int32_t)dt);
            // Kẹp D chống giật
            deriv = constrain(deriv, -(int32_t)PH_PID_IMAX, (int32_t)PH_PID_IMAX);
            // Spike nhiễu BT → giảm D còn 30%
            if (phBtDiscontinuity(bt10)) deriv = deriv * 3 / 10;
            // EMA filter cho D term (α=PH_EMA_D_ALPHA/100, Artisan derivative_filter ≈Wn=0.1Hz)
            // Lần đầu: seed bằng giá trị hiện tại để tránh giật cold-start
            if (!phEmaInit) { phEmaD = deriv * 100; }
            else { phEmaD = phEmaD + (int32_t)PH_EMA_D_ALPHA * (deriv * 100 - phEmaD) / 100; }
            deriv = phEmaD / 100;

            int32_t out = prop + iTerm + deriv;        // % (dương = gas, âm = air)

            // EMA filter cho output (α=PH_EMA_OUT_ALPHA/100, Artisan output_filter ≈Wn=0.35Hz)
            if (!phEmaInit) { phEmaOut = out * 100; phEmaInit = true; }
            else { phEmaOut = phEmaOut + (int32_t)PH_EMA_OUT_ALPHA * (out * 100 - phEmaOut) / 100; }
            out = phEmaOut / 100;

            // ── Back-calculation: khi output bị clamp, trừ bớt Iterm theo lượng thừa
            // (Artisan _back_calculate_integral, factor=0.5)
            int32_t outClamped = constrain(out, -100, 100);
            if (outClamped != out) {
                int32_t excess = out - outClamped;
                phPidInteg -= excess * 100 / 2;   // factor 0.5, thang ×100
                phPidInteg = constrain(phPidInteg, iMin, iMax);  // dùng trần động
            }
            out = outClamped;

            if (out >= 0) {
                wuGasPercent = (int16_t)out;            // gas theo output dương
                wuAirPercent = PH_AIR_BASE;             // gió nền
            } else {
                wuGasPercent = 0;                       // output âm → cắt gas
                wuAirPercent = constrain(PH_AIR_BASE - (int16_t)out, 0, 100); // tăng gió hạ nhiệt
            }

            // In log mỗi 3 giây (giảm mật độ 1/3) — PID vẫn tính mỗi giây
            if (enPhDebug && (wuElapsed % 3 == 0)) {
                uint16_t tM = wuElapsed/60, tS = wuElapsed%60;
                SerialComputer.print("["); SerialComputer.print(tM); SerialComputer.print(":");
                if (tS<10) SerialComputer.print("0");
                SerialComputer.print(tS); SerialComputer.print("] ");
                SerialComputer.print(wuState==WU_HOLDING?"HOLD":"HEAT");
                SerialComputer.print(" BT=");  SerialComputer.print(bt10/10);
                SerialComputer.print(" e=");   SerialComputer.print(e);
                SerialComputer.print(wuState==WU_HOLDING?" [HOLD_g]":" [HEAT_g]");
                SerialComputer.print(" P=");    SerialComputer.print(prop);
                SerialComputer.print(" I=");    SerialComputer.print(iTerm);
                SerialComputer.print(" D=");    SerialComputer.print(deriv);
                SerialComputer.print(" dBT=");  SerialComputer.print(dBT);
                SerialComputer.print(" out="); SerialComputer.print(out);
                SerialComputer.print(" gas="); SerialComputer.print(wuGasPercent);
                SerialComputer.print(" air="); SerialComputer.print(wuAirPercent);
                SerialComputer.println();
            }
        }

        gasPercent     = constrain(wuGasPercent, 0, 100);
        airflowPercent = constrain(wuAirPercent, 0, 100);
    }
    break;

    default:
        // WU_PRECISION không dùng trong bản PID
        wuReset();
        break;

    } // switch
}
