// RoR_Control.h
// Burner control module: dùng RoR_ET làm early warning, kiểm soát RoR_BT và BT
// Tách biệt hoàn toàn khỏi calibProgram()
// Chỉ gọi sau STP_TP, mỗi 3 giây (cùng chu kỳ với rorCount)
//
// Chuỗi nhân quả (từ analysis-roaster-thermal.md):
//   Gas → [lag 3-6s] → RoR_ET → [lag 3-5s] → RoR_BT → [∫dt] → BT
//   RoR_ET correlation với RoR_BT tại lag=0 (r=0.77) — early warning
//   Gain: ~1.5 °C/min per %Gas (vùng BT 180-240°C, không tải)
//   Dead time: ~15s sau khi thay đổi gas mới ổn định

#pragma once
#include "Define.h"

// ─── Tham số điều chỉnh ──────────────────────────────────────────────────────

// Deadband RoR — không can thiệp khi sai lệch nhỏ hơn ngưỡng này (đơn vị 0.1°C/min)
#define ROR_CTRL_DEADBAND_ROR       15    // ±1.5°C/min
#define ROR_CTRL_DEADBAND_BT        10    // ±1.0°C (đơn vị 0.1°C)

// Gain: mỗi 1.5°C/min sai lệch RoR → 1% gas correction
// Từ phân tích: gain thực tế ~1.5°C/min per %Gas (không tải)
// Khi có tải gain thấp hơn → dùng divisor lớn hơn cho an toàn
#define ROR_CTRL_GAIN_DIVISOR       20    // rorError/20 = gas% (đơn vị 0.1°C/min / 20 ≈ %gas)

// Giới hạn correction mỗi lần gọi (3 giây)
#define ROR_CTRL_MAX_CORRECTION     5     // ±5% gas mỗi bước
#define ROR_CTRL_MAX_TOTAL_OFFSET   15    // tổng offset tích lũy không vượt ±15%

// Early warning từ RoR_ET: nếu dRoR_ET lớn → dampen gas proactively
// dRoR_ET = rorET_now - rorET_prev (đơn vị 0.1°C/min)
#define ROR_CTRL_ET_WARN_THRESHOLD  30    // 3.0°C/min thay đổi RoR_ET → cảnh báo
#define ROR_CTRL_ET_DAMP_STEP       2     // giảm/tăng thêm 2% gas khi có early warning

// Dead time: không điều chỉnh lại trong N giây sau lần chỉnh trước
#define ROR_CTRL_DEAD_TIME_SEC      15    // 15 giây

// ─── State variables ─────────────────────────────────────────────────────────

static int16_t  rorCtrl_gasOffset    = 0;   // tổng offset tích lũy so với sdGas[t]
static int16_t  rorCtrl_prevRorET    = 0;   // RoR_ET lần trước để tính dRoR_ET
static uint16_t rorCtrl_deadTimer    = 0;   // đếm giây kể từ lần điều chỉnh cuối
static bool     rorCtrl_initialized  = false;

// ─── Hàm tiện ích ─────────────────────────────────────────────────────────────

// Populate sdRorBT[] từ sdBT[] — gọi một lần sau khi load profile xong
// Tính đạo hàm sdBT theo thời gian, đơn vị 0.1°C/min
// Window 10s để tránh nhiễu từ profile thô
void rorCtrl_populateSdRorBT() {
    const uint8_t WINDOW = 10; // giây
    for (uint16_t t = 0; t < sdTempTi; t++) {
        if (t < WINDOW) {
            sdRorBT[t] = 0;
            continue;
        }
        // (sdBT[t] - sdBT[t-WINDOW]) / WINDOW * 60  → °C/min × 10 = 0.1°C/min
        int32_t delta = (int32_t)sdBT[t] - (int32_t)sdBT[t - WINDOW];
        sdRorBT[t] = (int16_t)(delta * 6); // delta/10 * 60 = delta*6 (units stay in 0.1°C/min)
    }
}

// Reset state — gọi khi bắt đầu AUTO hoặc sau khi thoát AUTO
void rorCtrl_reset() {
    rorCtrl_gasOffset   = 0;
    rorCtrl_prevRorET   = rorET;
    rorCtrl_deadTimer   = 0;
    rorCtrl_initialized = false;
}

// ─── Hàm chính ───────────────────────────────────────────────────────────────
//
// Gọi trong calibProgram() sau khi đã set gasPercent = sdGas[lastTimeSD]
// Chỉ gọi khi: progStep > STP_TP && rorCount == 0 (mỗi 3 giây, ngay sau khi RoR được cập nhật)
//
// gasPercent phải đã được set = sdGas[lastTimeSD] trước khi gọi hàm này
// Hàm này chỉ thêm/bớt offset, không override hoàn toàn

void rorCtrl_update() {

    // ── Khởi tạo lần đầu ────────────────────────────────────────────────────
    if (!rorCtrl_initialized) {
        rorCtrl_prevRorET   = rorET;
        rorCtrl_gasOffset   = 0;
        rorCtrl_deadTimer   = 0;
        rorCtrl_initialized = true;
        return;
    }

    // ── Dead time — chờ hệ thống ổn định sau lần chỉnh trước ────────────────
    if (rorCtrl_deadTimer > 0) {
        rorCtrl_deadTimer--;
        // Vẫn apply offset cũ trong lúc chờ
        int16_t applied = gasPercent + rorCtrl_gasOffset;
        gasPercent = constrain(applied, 0, 100);
        return;
    }

    // ── Tính sai lệch RoR BT ────────────────────────────────────────────────
    // sdRorBT[t] và rorBT đều đơn vị 0.1°C/min
    int16_t rorTarget  = sdRorBT[lastTimeSD];
    int16_t rorError   = rorTarget - rorBT;     // dương = RoR thực thấp hơn target → cần tăng gas

    // ── Tính sai lệch BT ────────────────────────────────────────────────────
    // sdBT[t] và Temperature_BT đều đơn vị 0.1°C
    int16_t btTarget = (int16_t)sdBT[lastTimeSD];
    int16_t btError  = btTarget - (int16_t)Temperature_BT; // dương = BT thực thấp hơn → cần tăng gas

    // ── Early warning từ RoR_ET ─────────────────────────────────────────────
    int16_t dRorET = rorET - rorCtrl_prevRorET; // dương = RoR_ET đang tăng → BT sắp tăng nhanh hơn
    rorCtrl_prevRorET = rorET;

    // ── Quyết định correction ────────────────────────────────────────────────
    int16_t correction = 0;

    // 1. RoR correction (ưu tiên cao nhất)
    if (abs(rorError) > ROR_CTRL_DEADBAND_ROR) {
        correction = rorError / ROR_CTRL_GAIN_DIVISOR;
        correction = constrain(correction, -ROR_CTRL_MAX_CORRECTION, ROR_CTRL_MAX_CORRECTION);
    }

    // 2. BT correction (bổ sung nhỏ khi RoR đúng nhưng BT vẫn lệch)
    if (correction == 0 && abs(btError) > ROR_CTRL_DEADBAND_BT) {
        // Chỉ can thiệp nhỏ — BT là hệ quả của RoR, không override mạnh
        int16_t btCorr = btError / 50; // rất nhỏ: 5°C lệch → 0.1% gas
        correction = constrain(btCorr, -2, 2);
    }

    // 3. Early warning từ RoR_ET — dampen khi RoR_ET đang thay đổi mạnh
    if (abs(dRorET) > ROR_CTRL_ET_WARN_THRESHOLD) {
        if (dRorET > 0) {
            // RoR_ET tăng nhanh → BT sắp tăng → giảm gas phòng ngừa
            correction -= ROR_CTRL_ET_DAMP_STEP;
        } else {
            // RoR_ET giảm nhanh → BT sắp giảm → tăng gas phòng ngừa
            correction += ROR_CTRL_ET_DAMP_STEP;
        }
    }

    // ── Không làm gì nếu correction = 0 ────────────────────────────────────
    if (correction == 0) {
        int16_t applied = gasPercent + rorCtrl_gasOffset;
        gasPercent = constrain(applied, 0, 100);
        return;
    }

    // ── Tích lũy offset ─────────────────────────────────────────────────────
    rorCtrl_gasOffset += correction;
    rorCtrl_gasOffset  = constrain(rorCtrl_gasOffset,
                                   -ROR_CTRL_MAX_TOTAL_OFFSET,
                                    ROR_CTRL_MAX_TOTAL_OFFSET);

    // ── Apply giới hạn theo phase (tái dùng limits của calibProgram) ─────────
    int16_t maxStep = 100; // fallback
    if ((int16_t)Temperature_BT < DE_PRO_R)                                   maxStep = TpCalib_R;
    else if ((int16_t)Temperature_BT < FCS_PRO_R)                             maxStep = DeCalib_R;
    else                                                                        maxStep = FcsCalib_R;

    rorCtrl_gasOffset = constrain(rorCtrl_gasOffset, -maxStep, maxStep);

    // ── Apply offset vào gasPercent ──────────────────────────────────────────
    int16_t applied = gasPercent + rorCtrl_gasOffset;
    gasPercent = constrain(applied, 0, 100);

    // ── Bắt đầu dead time ───────────────────────────────────────────────────
    rorCtrl_deadTimer = ROR_CTRL_DEAD_TIME_SEC / 3; // chia 3 vì gọi mỗi 3 giây

    // ── Debug output ─────────────────────────────────────────────────────────
    if (enDebug) {
        SerialComputer.print("RoR_CTRL: rorErr=");   SerialComputer.print(rorError);
        SerialComputer.print(" btErr=");              SerialComputer.print(btError);
        SerialComputer.print(" dRorET=");             SerialComputer.print(dRorET);
        SerialComputer.print(" corr=");               SerialComputer.print(correction);
        SerialComputer.print(" offset=");             SerialComputer.print(rorCtrl_gasOffset);
        SerialComputer.print(" gas=");                SerialComputer.println(gasPercent);
    }
}
