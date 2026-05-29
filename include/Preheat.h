#pragma once
// Preheat.h — Làm nóng máy rang tự động
// State machine: WU_IDLE -> WU_COOLING / WU_IGNITE -> WU_HEATING -> WU_HOLDING
// Gọi từ programScan() mỗi giây khi START_BTN_R == 0

enum WuState    : uint8_t { WU_IDLE=0, WU_COOLING=1, WU_IGNITE=2, WU_HEATING=3, WU_HOLDING=4, WU_PRECISION=5, WU_COAST=6, WU_PRE_IGNITE=7 };
enum WuStartMode: uint8_t { START_COLD=0, START_HOT=1, START_COOL=2 };

static volatile WuState   wuState         = WU_IDLE;
static volatile uint16_t  wuElapsed       = 0;
static uint16_t  wuDeadTimer     = 0;
static int16_t   wuGasPercent    = 0;
static int16_t   wuAirPercent    = 0;
static uint8_t   wuVacFlagSaved  = 0;
static volatile uint16_t  wuIgniteTimer   = 0;
static int16_t   phRorAtStep     = 0;
static uint16_t  phBTNoRiseCount = 0;
static int16_t   phRorPrev       = 0;

// ── Thermal monitor output — cập nhật mỗi giây bởi phThermalMonitor() ────────
static int16_t   phBtCoast      = 0;   // BT sẽ trôi thêm bao nhiêu (×0.1°C) nếu tắt gas ngay
static int16_t   phEtHeatLoad   = 0;   // rorET hiện tại — đại diện nhiệt đang đổ vào trống

static int16_t   phEtRorPrev    = 0;   // rorET giây trước để tính dRorET
static int16_t   phEtAtStep     = 0;   // rorET tại thời điểm recordStep() — baseline ET confirm
static uint8_t   phEtConfirm    = 0;   // giây rorET đã tăng rõ so với baseline sau gas step

// ── FF Table — học gas% theo vùng BT 25°C, lưu /ph_ff.txt ───────────────────
#define PH_FF_ZONES       12
#define PH_FF_ZONE_W      250    // 25°C mỗi vùng (đơn vị 0.1°C)
#define PH_FF_FILE        "/ph_ff.txt"
#define PH_ADAPT_FILE     "/ph_adapt.txt"
#define PH_ADAPT_LOG_FILE "/PHALOG.CSV"

#define WU_HEAT_TIME_SEC  180   // 3 phút để đạt target
#define PH_STABLE_SEC     10    // giây ổn định trước khi học
#define PH_ADAPT_AIR_DEF  20
#define PH_ET_BT_COLD    -30   // gap <= -3°C → trống lạnh
#define PH_ET_BT_HOT      30   // gap >= +3°C → trống nóng
#define PH_GAS_COLD_DEF   65
#define PH_GAS_HOT_DEF    45
#define PH_HEAT_AIR_MAX   80   // gió tối đa khi hãm nhiệt
#define PH_HEAT_AIR_FAR_MAX 20 // gió tối đa khi còn xa target
#define PH_NEAR_TARGET_BAND 300 // 30°C: ngưỡng phanh mạnh
#define PH_APPROACH_BAND  250  // 25°C: bắt đầu hãm
#define PH_CTRL_DEAD_SEC  15   // dead time sau mỗi nấc gas
#define PH_FAR_GAS_FLOOR  65   // lửa nền tối thiểu khi còn xa


static inline uint8_t clampProfilePercent(int v) {
    return (v < 0) ? 0 : (v > 100) ? 100 : (uint8_t)v;
}

struct PhFFEntry {
    int16_t btZoneCenter;
    int16_t gasPercent;
    int16_t gain10;   // delta_rorBT per delta_gas% (×10)
    int16_t coldGas;
    int16_t hotGas;
};

static PhFFEntry phFF[PH_FF_ZONES];
static uint8_t   phStableCount         = 0;
static int16_t   phAdaptGasBoost       = 0;
static int16_t   phAdaptHeatAir        = PH_ADAPT_AIR_DEF;
static int16_t   phAdaptCoastMul       = 10; // hệ số coast × 0.1 (10 = ×1.0), học từ thực tế
static int16_t   phAdaptLossRate10     = 12; // nhiệt tổn thất (°C/min × 10) — học khi gas=floor, ổn định
static int16_t   phAdaptGasGain10      = 30; // °C/min trên 1% gas × 10 — dùng cho PI Kp = 1/gain
static uint16_t  phAdaptRuns           = 0;
static uint16_t  phRunTargetBT10       = 0;
static uint16_t  phRunStartBT10        = 0;
static uint16_t  phRunMaxBT10          = 0;
static uint16_t  phRunSampleCount      = 0;
static uint32_t  phRunGasSum           = 0;
static uint32_t  phRunAirSum           = 0;
static uint16_t  phRunLastSampleElapsed = 65535;
static bool      phRunActive           = false;
static bool      phRunReachedTarget    = false;
static int16_t   phRunPredCoast        = 0;   // phBtCoast tại lúc brake lần cuối
static int16_t   phRunBtAtBrake        = 0;   // BT tại lúc brake lần cuối
static int16_t   phRunBtMaxAfterBrake  = 0;   // BT peak sau lúc brake — dùng để đo actualCoast
static int16_t   phStartGasTarget      = PH_FAR_GAS_FLOOR;
static uint16_t  phCtrlDeadTimer       = 0;
static uint16_t  phCtrlLastDeadElapsed = 65535;
static uint16_t  phHoldLastEvalElapsed = 65535;
static int8_t    phHoldPendingStep     = 0;
static uint8_t   phHoldConfirmSec      = 0;
static int16_t   phGainGasBefore       = 0;
static int16_t   phGainRorBefore       = 0;
static int16_t   phGainBT10            = 0;
static uint8_t   phGainWaiting         = 0;
static uint8_t   phGainWaitCount       = 0;
static bool      phFFSnapDone          = false;
static uint16_t  phCoolDbgTimer        = 0;
static WuStartMode phStartMode         = START_COLD;
static uint32_t  phPreIgniteStartMs    = 0;
static uint8_t   phRecoveryExitCount   = 0;  // đếm giây BT đã về vùng an toàn sau RECOVERY
static uint8_t   phDbgTick             = 0;  // đếm giây để throttle debug 3s/lần
static uint16_t  phCsvLastElapsed      = 65535;
static File      phCsvFile;
static uint8_t   phCsvReason           = 0;  // reason enum cho dòng CSV hiện tại
// Reason enum: 0=NORMAL,1=APPR_BRAKE,2=RECOVERY,3=PI_P,4=PI_I,5=AIR_GUARD,6=SLEW_LIMIT,7=INVARIANT_FIX
static int32_t   phPiIAccum            = 0;   // PI integral accumulator — reset khi đổi target hoặc RECOVERY
static uint16_t  phPiLastElapsed       = 65535;
static int16_t   phPiLastTarget        = 0;   // track target để reset I khi target đổi
static uint32_t  phPiLastUpdateMs      = 0;   // PI update timing dùng millis() — không phụ thuộc loop

// ── PHASE 0: Safety/Fault Layer + rorBT_smooth ──────────────────────────────
static int16_t   rorBT_smooth          = 0;   // EMA filter 5s — dùng cho RECOVERY trigger và predict
static int16_t   phBtHistory[5]        = {0}; // 5 mẫu BT × 1s — phát hiện sensor drop
static int16_t   phEtHistory[5]        = {0}; // 5 mẫu ET × 1s
static uint8_t   phHistIdx             = 0;
static uint16_t  phHistLastSec         = 65535;
static uint8_t   phFaultFlags          = 0;   // bitfield: bit0=SENSOR_DROP, bit1=ROR_EXTREME, bit2=GAS_LOST, bit3=HMI_TIMEOUT, bit4=SD_FAIL
static uint8_t   phGasLostCount        = 0;   // đếm giây gas signal mất khi đang đốt

#define PH_FAULT_SENSOR_DROP  0x01
#define PH_FAULT_ROR_EXTREME  0x02
#define PH_FAULT_GAS_LOST     0x04
#define PH_FAULT_HMI_TIMEOUT  0x08
#define PH_FAULT_SD_FAIL      0x10

// ── Phase 0.1: Cập nhật rorBT_smooth — gọi mỗi giây từ phThermalMonitor() ────
inline void phUpdateRorSmooth() {
    // EMA: alpha = 0.2 → tau ≈ 5s, đủ lọc jitter mà không trễ quá nhiều
    rorBT_smooth = (int16_t)((int32_t)rorBT_smooth * 8 / 10 + (int32_t)rorBT * 2 / 10);
}

// ── Phase 0.2: Sensor drop detection — gọi mỗi giây ─────────────────────────
// Kiểm tra max-min của 5 mẫu gần nhất, nếu chênh > 50°C → sensor lỗi
inline void phCheckSensorDrop() {
    if (phHistLastSec == wuElapsed) return;
    phHistLastSec = wuElapsed;

    phBtHistory[phHistIdx] = (int16_t)Temperature_BT;
    phEtHistory[phHistIdx] = (int16_t)Temperature_ET;
    phHistIdx = (phHistIdx + 1) % 5;

    // Tìm min/max của 5 mẫu BT
    int16_t btMin = phBtHistory[0], btMax = phBtHistory[0];
    int16_t etMin = phEtHistory[0], etMax = phEtHistory[0];
    for (uint8_t i = 1; i < 5; i++) {
        if (phBtHistory[i] < btMin) btMin = phBtHistory[i];
        if (phBtHistory[i] > btMax) btMax = phBtHistory[i];
        if (phEtHistory[i] < etMin) etMin = phEtHistory[i];
        if (phEtHistory[i] > etMax) etMax = phEtHistory[i];
    }
    // Drop bất thường > 50°C trong 5s → fault
    bool btDrop = (btMax - btMin) > 500;
    bool etDrop = (etMax - etMin) > 500;
    if (btDrop || etDrop) {
        if (!(phFaultFlags & PH_FAULT_SENSOR_DROP)) {
            phFaultFlags |= PH_FAULT_SENSOR_DROP;
            setMachineStatus(STT_PREHEAT_SENSOR_DROP);
            if (enDebug) {
                SerialComputer.print("FAULT sensor drop BT=");
                SerialComputer.print(btMax - btMin);
                SerialComputer.print(" ET=");
                SerialComputer.println(etMax - etMin);
            }
        }
    } else {
        phFaultFlags &= ~PH_FAULT_SENSOR_DROP;  // tự clear khi ổn định
    }
}

// ── Phase 0.3: rorBT extreme detection — fire cut ngay ──────────────────────
inline void phCheckRorExtreme() {
    if (rorBT_smooth > 5000) {  // > 500°C/min × 10
        if (!(phFaultFlags & PH_FAULT_ROR_EXTREME)) {
            phFaultFlags |= PH_FAULT_ROR_EXTREME;
            fireCutFlag = true;  // ISR-safe flag, programScan() sẽ xử lý Modbus
            setMachineStatus(STT_ERR_ROR_BT_EXTREME);
            if (enDebug) {
                SerialComputer.print("FAULT RoR extreme="); SerialComputer.println(rorBT_smooth);
            }
        }
    }
}

// ── Phase 0.4: Gas signal lost detection — retry ignite ─────────────────────
// Gọi mỗi giây, chỉ khi state đang đốt (HEATING/HOLDING/PRECISION)
inline bool phCheckGasLost() {
    bool isBurningState = (wuState == WU_HEATING || wuState == WU_HOLDING || wuState == WU_PRECISION);
    if (!isBurningState || wuGasPercent <= 5) {
        phGasLostCount = 0;
        return false;
    }
    if (gasSignal == 1) {
        phGasLostCount = 0;
        phFaultFlags &= ~PH_FAULT_GAS_LOST;
        return false;
    }
    // Gas signal = 0 nhưng đang yêu cầu đốt → đếm
    if (++phGasLostCount >= 3) {
        phFaultFlags |= PH_FAULT_GAS_LOST;
        setMachineStatus(STT_PREHEAT_GAS_LOST);
        phGasLostCount = 0;
        if (enDebug) SerialComputer.println("FAULT gas lost — retry ignite");
        return true;  // caller chuyển sang WU_IGNITE
    }
    return false;
}

// ── Phase 0.5: State invariant — gọi cuối preheat() trước khi return ────────
inline bool phValidateInvariant() {
    switch (wuState) {
        case WU_IDLE:        return gasPercent == 0;
        case WU_COOLING:     return gasPercent == 0 && airflowPercent >= 40;
        case WU_COAST:       return gasPercent == 0 && airflowPercent >= 20 && airflowPercent <= 50;
        case WU_PRE_IGNITE:  return gasPercent == 0 && airflowPercent >= 25;
        case WU_IGNITE:      return airflowPercent >= 25 && airflowPercent <= 50;
        case WU_HEATING:     return airflowPercent <= 80;
        case WU_HOLDING:
        case WU_PRECISION:   return airflowPercent <= 40;
        default:             return true;
    }
}

// ── Phase 7: Slew rate limiter — clamp thay đổi gas/air mỗi giây ────────────
// RECOVERY cần allow fast cut → exception param maxRate cao
inline int16_t phSlewLimit(int16_t current, int16_t target, int16_t maxRate) {
    int16_t diff = target - current;
    if      (diff >  maxRate) return current + maxRate;
    else if (diff < -maxRate) return current - maxRate;
    return target;
}

// Áp dụng slew cho output cuối — chống spike từ PI hoặc rule
// gasRate cao trong RECOVERY (cho phép cut nhanh), thấp ở các state khác
static uint16_t phSlewLastSec = 65535;
static int16_t  phSlewLastGas = 0;
static int16_t  phSlewLastAir = 0;
inline void phApplySlewLimit(bool inRecoveryNow) {
    if (phSlewLastSec == wuElapsed) return;
    phSlewLastSec = wuElapsed;

    // PRE_IGNITE/COOLING/COAST cần set air nhanh — không áp slew
    if (wuState == WU_PRE_IGNITE || wuState == WU_COOLING || wuState == WU_COAST) {
        phSlewLastGas = gasPercent;
        phSlewLastAir = airflowPercent;
        return;
    }

    int16_t gasRate = inRecoveryNow ? 30 : 5;
    int16_t airRate = inRecoveryNow ? 10 : 5;  // air 5%/s bình thường, 10%/s recovery

    int16_t newGas = phSlewLimit(phSlewLastGas, gasPercent, gasRate);
    int16_t newAir = phSlewLimit(phSlewLastAir, airflowPercent, airRate);

    gasPercent     = newGas;
    airflowPercent = newAir;
    phSlewLastGas  = newGas;
    phSlewLastAir  = newAir;
}

inline void phEnforceInvariant() {
    if (!phValidateInvariant()) {
        setMachineStatus(STT_PREHEAT_INVARIANT_FAIL);
        // Force về giá trị an toàn — gas=0, air=30 luôn hợp lệ
        gasPercent = 0;
        airflowPercent = 30;
        if (enDebug) {
            SerialComputer.print("INVARIANT FAIL state=");
            SerialComputer.print((int)wuState);
            SerialComputer.print(" gas=");
            SerialComputer.print(gasPercent);
            SerialComputer.print(" air=");
            SerialComputer.println(airflowPercent);
        }
    }
}

// ── CSV log per-5s ───────────────────────────────────────────────────────────
#define PH_CSV_FILE  "/PH5S.CSV"

void phCsvLog(int16_t score10) {
    // Chỉ log mỗi 5 giây, không log khi WU_IDLE hoặc WU_COAST
    if (wuState == WU_IDLE || wuState == WU_COAST) return;
    if (phCsvLastElapsed == wuElapsed) return;
    if (wuElapsed % 5 != 0) return;
    phCsvLastElapsed = wuElapsed;

    // CSV rotation: xóa file cũ sau mỗi 50 run
    if (!phCsvFile) {
        if (phAdaptRuns > 0 && phAdaptRuns % 50 == 0 && SD.exists(PH_CSV_FILE))
            SD.remove(PH_CSV_FILE);
        bool isNew = !SD.exists(PH_CSV_FILE);
        phCsvFile = SD.open(PH_CSV_FILE, FILE_WRITE);
        if (isNew && phCsvFile)
            phCsvFile.println("run,t,bt,et,gas,air,rorBT,rorSmooth,rorET,state,reason,fault,score");
    }
    if (!phCsvFile) {
        phFaultFlags |= PH_FAULT_SD_FAIL;
        return;
    }

    phCsvFile.print(phAdaptRuns);        phCsvFile.print(',');
    phCsvFile.print(wuElapsed);          phCsvFile.print(',');
    phCsvFile.print(Temperature_BT);     phCsvFile.print(',');
    phCsvFile.print(Temperature_ET);     phCsvFile.print(',');
    phCsvFile.print(gasPercent);         phCsvFile.print(',');
    phCsvFile.print(airflowPercent);     phCsvFile.print(',');
    phCsvFile.print(rorBT);              phCsvFile.print(',');
    phCsvFile.print(rorBT_smooth);       phCsvFile.print(',');
    phCsvFile.print(rorET);              phCsvFile.print(',');
    phCsvFile.print((uint8_t)wuState);   phCsvFile.print(',');
    phCsvFile.print(phCsvReason);        phCsvFile.print(',');
    phCsvFile.print(phFaultFlags, HEX);  phCsvFile.print(',');
    phCsvFile.println(score10);          // -1 trong suốt run, giá trị thực ở dòng cuối
    phCsvFile.flush();
    phCsvReason = 0;  // reset reason sau khi log
}

void phCsvClose() {
    if (phCsvFile) { phCsvFile.close(); }
}

// ── Adapt: load/save/log ─────────────────────────────────────────────────────

void phAdaptLoad() {
    phAdaptGasBoost  = 0;
    phAdaptHeatAir   = PH_ADAPT_AIR_DEF;
    phAdaptCoastMul  = burnerPremix_R ? 15 : 10;  // premix: coast dài hơn, bắt đầu từ 15
    phAdaptLossRate10 = 12;
    phAdaptGasGain10  = 30;
    phAdaptRuns      = 0;
    if (!SD.exists(PH_ADAPT_FILE)) return;
    File f = SD.open(PH_ADAPT_FILE, FILE_READ);
    if (!f) return;
    phAdaptGasBoost  = constrain((int16_t)f.parseInt(), -50, 50);
    phAdaptHeatAir   = constrain((int16_t)f.parseInt(),   0, 40);
    phAdaptRuns      = (uint16_t)f.parseInt();
    int16_t cm       = (int16_t)f.parseInt();
    if (cm >= 5 && cm <= 20) phAdaptCoastMul = cm;
    // backward-compat: file cũ không có lossRate/gasGain → parseInt trả 0 → giữ default
    int16_t lr = (int16_t)f.parseInt();
    int16_t gg = (int16_t)f.parseInt();
    if (lr >= 3 && lr <= 50) phAdaptLossRate10 = lr;
    if (gg >= 10 && gg <= 100) phAdaptGasGain10 = gg;
    f.close();
    if (enDebug) {
        SerialComputer.print("ADAPT loaded: boost="); SerialComputer.print(phAdaptGasBoost);
        SerialComputer.print(" air=");                SerialComputer.print(phAdaptHeatAir);
        SerialComputer.print(" runs=");               SerialComputer.print(phAdaptRuns);
        SerialComputer.print(" coastMul=");           SerialComputer.print(phAdaptCoastMul);
        SerialComputer.print(" loss=");               SerialComputer.print(phAdaptLossRate10);
        SerialComputer.print(" gain=");               SerialComputer.println(phAdaptGasGain10);
    }
}

void phAdaptSave() {
    SD.remove(PH_ADAPT_FILE);
    File f = SD.open(PH_ADAPT_FILE, FILE_WRITE);
    if (!f) return;
    f.print(phAdaptGasBoost);  f.print(' ');
    f.print(phAdaptHeatAir);   f.print(' ');
    f.print(phAdaptRuns);      f.print(' ');
    f.print(phAdaptCoastMul);  f.print(' ');
    f.print(phAdaptLossRate10);f.print(' ');
    f.println(phAdaptGasGain10);
    f.close();
    if (enDebug) SerialComputer.println("ADAPT saved");
}

// Học gasGain: khi STABLE có gas step ổn định, gain = |delta_rorBT| / |delta_gas|
// Gọi từ phFFLearnGain hoặc HOLDING STABLE sau dead time
void phLearnGasGain(int16_t gasDelta, int16_t rorBefore, int16_t rorAfter) {
    if (gasDelta == 0) return;
    int16_t newGain = abs((rorAfter - rorBefore) * 10 / gasDelta);  // ×10 unit
    if (newGain < 10 || newGain > 100) return;  // sanity check 1-10°C/min/%
    // EMA 70/30
    phAdaptGasGain10 = (int16_t)((int32_t)phAdaptGasGain10 * 7 / 10 + (int32_t)newGain * 3 / 10);
    if (enDebug) {
        SerialComputer.print("GAIN learn delta_gas="); SerialComputer.print(gasDelta);
        SerialComputer.print(" delta_ror=");           SerialComputer.print(rorAfter - rorBefore);
        SerialComputer.print(" gain10=");              SerialComputer.println(phAdaptGasGain10);
    }
}

// Học lossRate: khi gas = holdGasMin và rorBT âm ổn định → loss = -rorBT
// Gọi từ PRECISION khi STRICT stable đã thỏa
void phLearnLossRate(int16_t rorBtNow) {
    if (rorBtNow > 0 || rorBtNow < -50) return;  // chỉ nhận -5..0°C/min
    int16_t newLoss = -rorBtNow;  // °C/min × 10
    if (newLoss < 5 || newLoss > 30) return;  // physical range 0.5-3°C/min
    // EMA 90/10 — học rất chậm để tránh compound error qua nhiều run
    phAdaptLossRate10 = (int16_t)((int32_t)phAdaptLossRate10 * 9 / 10 + (int32_t)newLoss * 1 / 10);
    if (enDebug) {
        SerialComputer.print("LOSS learn rorBT="); SerialComputer.print(rorBtNow);
        SerialComputer.print(" loss10=");          SerialComputer.println(phAdaptLossRate10);
    }
}

void phAdaptLog(uint16_t runNo, uint16_t targetBT10, uint16_t startBT10, uint16_t endBT10,
                uint16_t maxBT10, uint16_t avgGas, uint16_t avgAir, int16_t score10,
                int16_t oldGasBoost, int16_t newGasBoost, int16_t oldHeatAir, int16_t newHeatAir,
                const char *lesson) {
    bool newFile = !SD.exists(PH_ADAPT_LOG_FILE);
    File f = SD.open(PH_ADAPT_LOG_FILE, FILE_WRITE);
    if (!f) return;
    if (newFile) f.println("run,targetC,startBT,endBT,maxBT,avgGas,avgAir,score10,oldGasBoost,newGasBoost,oldHeatAir,newHeatAir,lesson");
    auto printDec = [&](uint16_t v) { f.print(v/10); f.print('.'); f.print(v%10); f.print(','); };
    f.print(runNo);        f.print(',');
    printDec(targetBT10);  printDec(startBT10); printDec(endBT10); printDec(maxBT10);
    f.print(avgGas);       f.print(',');
    f.print(avgAir);       f.print(',');
    f.print(score10);      f.print(',');
    f.print(oldGasBoost);  f.print(',');
    f.print(newGasBoost);  f.print(',');
    f.print(oldHeatAir);   f.print(',');
    f.print(newHeatAir);   f.print(',');
    f.println(lesson);
    f.close();
}

// ── Run tracking: sample gas/air usage, học adapt sau khi xong ───────────────

void phRunStart(int16_t targetBT10) {
    phRunTargetBT10        = targetBT10;
    phRunStartBT10         = (uint16_t)Temperature_BT;
    phRunMaxBT10           = (uint16_t)Temperature_BT;
    // Init sensor history với nhiệt độ thực để tránh false alarm lúc khởi động
    for (uint8_t i = 0; i < 5; i++) {
        phBtHistory[i] = (int16_t)Temperature_BT;
        phEtHistory[i] = (int16_t)Temperature_ET;
    }
    phFaultFlags &= ~PH_FAULT_SENSOR_DROP;  // clear false alarm từ run trước
    phRunSampleCount       = 0;
    phRunGasSum            = 0;
    phRunAirSum            = 0;
    phRunLastSampleElapsed = 65535;
    phRunActive            = true;
    phRunReachedTarget     = false;
    phRunPredCoast         = 0;
    phRunBtAtBrake         = 0;
    phRunBtMaxAfterBrake   = 0;
}

void phRunSample() {
    if (!phRunActive || phRunLastSampleElapsed == wuElapsed) return;
    phRunLastSampleElapsed = wuElapsed;
    if ((uint16_t)Temperature_BT > phRunMaxBT10) phRunMaxBT10 = (uint16_t)Temperature_BT;
    if (phRunBtAtBrake > 0 && (int16_t)Temperature_BT > phRunBtMaxAfterBrake)
        phRunBtMaxAfterBrake = (int16_t)Temperature_BT;
    if ((int16_t)Temperature_BT >= (int16_t)phRunTargetBT10 - 50) phRunReachedTarget = true;
    phRunGasSum += (uint16_t)constrain(gasPercent, 0, 100);
    phRunAirSum += (uint16_t)constrain(airflowPercent, 0, 100);
    if (phRunSampleCount < 60000) phRunSampleCount++;
    phCsvLog(-1);  // log per-5s với score=-1 (chưa biết score)
}

void phRunLearn(bool normalEnd) {
    if (!phRunActive || phRunSampleCount == 0) { phRunActive = false; return; }

    uint16_t endBT10     = (uint16_t)Temperature_BT;
    int16_t  miss10      = (int16_t)phRunTargetBT10 - (int16_t)phRunMaxBT10;
    int16_t  overshoot10 = (int16_t)phRunMaxBT10 - (int16_t)phRunTargetBT10;
    uint16_t avgGas      = (uint16_t)(phRunGasSum / phRunSampleCount);
    uint16_t avgAir      = (uint16_t)(phRunAirSum / phRunSampleCount);
    int16_t  oldGasBoost = phAdaptGasBoost;
    int16_t  oldHeatAir  = phAdaptHeatAir;
    int16_t  score10     = 10;
    const char *lesson   = "stable_no_change";
    bool changed         = false;

    if (normalEnd) {
        phAdaptRuns++;
        if (!phRunReachedTarget) {
            score10 -= constrain((miss10 + 49) / 50, 0, 8);
            if (avgGas < 60) score10--;
            if (avgAir > 30) score10--;
        } else if (overshoot10 > 0) {
            score10 -= constrain((overshoot10 + 39) / 40, 0, 5);
        }
        score10 = constrain(score10, 0, 10);

        if (score10 < 9 && !phRunReachedTarget && miss10 > 100) {
            phAdaptGasBoost = constrain(phAdaptGasBoost + constrain(miss10/100, 3, 12), -50, 50);
            if (avgAir > 25 || phAdaptHeatAir > 10) phAdaptHeatAir = constrain(phAdaptHeatAir - 5, 0, 40);
            lesson = "miss_target_raise_gas_lower_air"; changed = true;
        } else if (score10 < 9 && phRunReachedTarget && overshoot10 > 80) {
            int16_t gs = constrain((overshoot10 + 39) / 40, 5, 20);
            if (phAdaptHeatAir >= 35) gs = constrain(gs + 5, 5, 25);
            phAdaptGasBoost = constrain(phAdaptGasBoost - gs, -50, 50);
            phAdaptHeatAir  = constrain(phAdaptHeatAir + 5, 0, 40);
            lesson = "overshoot_reduce_gas_raise_air"; changed = true;
        } else if (phRunReachedTarget && overshoot10 > 20) {
            phAdaptGasBoost = constrain(phAdaptGasBoost - 2, -50, 50);
            if (phAdaptHeatAir < 40) phAdaptHeatAir = constrain(phAdaptHeatAir + 5, 0, 40);
            lesson = "small_overshoot_trim_gas"; changed = true;
        } else if (score10 >= 9) {
            lesson = "score_good_keep_settings";
        } else if (phRunReachedTarget && avgGas < 45 && phAdaptGasBoost > 0) {
            phAdaptGasBoost = constrain(phAdaptGasBoost - 2, -50, 50);
            lesson = "reached_with_low_gas_trim_boost"; changed = true;
        }
    }

    // Học coastMul: nếu có dữ liệu brake, so sánh coast dự báo vs BT thực tế peak
    // actualCoast = maxBT - btAtBrake; predCoast = phRunPredCoast
    // Nếu actual >> pred → coastMul cần tăng (bị phanh quá muộn)
    // Nếu actual << pred → coastMul cần giảm (phanh quá sớm)
    if (normalEnd && phRunPredCoast > 0 && phRunBtAtBrake > 0 && phRunBtMaxAfterBrake > phRunBtAtBrake) {
        int16_t actualCoast = phRunBtMaxAfterBrake - phRunBtAtBrake;
        if (actualCoast > 5) {  // chỉ học khi dữ liệu có nghĩa
            // mulNew = coastMul × actualCoast / predCoast, EMA 70/30
            int16_t mulNew = (int16_t)constrain((int32_t)phAdaptCoastMul * actualCoast / phRunPredCoast, 5, 20);
            phAdaptCoastMul = (int16_t)(phAdaptCoastMul * 7 / 10 + mulNew * 3 / 10);
            changed = true;
            if (enDebug) {
                SerialComputer.print("COAST learn pred="); SerialComputer.print(phRunPredCoast/10);
                SerialComputer.print("C actual=");         SerialComputer.print(actualCoast/10);
                SerialComputer.print("C mul=");            SerialComputer.println(phAdaptCoastMul);
            }
        }
        phRunPredCoast = phRunBtAtBrake = 0;
    }

    if (enDebug) {
        SerialComputer.print("ADAPT learn: maxBT="); SerialComputer.print(phRunMaxBT10/10);
        SerialComputer.print(" tgt=");               SerialComputer.print(phRunTargetBT10/10);
        SerialComputer.print(" avgGas=");            SerialComputer.print(avgGas);
        SerialComputer.print(" score=");             SerialComputer.print(score10);
        SerialComputer.print(" boost=");             SerialComputer.println(phAdaptGasBoost);
    }
    // PHASE 5: chỉ save ADAPT khi run thật sự tốt — tránh compound error qua các run
    // Exception: 3 lần đầu (bootstrap) vẫn save để có dữ liệu khởi đầu
    // Exception: có fault flag → không save dù score cao (dữ liệu không đáng tin)
    bool isBootstrap = (phAdaptRuns <= 3);
    bool isGoodRun   = (score10 >= 7);
    bool hadFault    = (phFaultFlags != 0);

    if (changed && (isBootstrap || isGoodRun) && !hadFault) {
        phAdaptSave();
        if (enDebug) {
            SerialComputer.print("ADAPT SAVED (");
            if (isBootstrap)    SerialComputer.println("bootstrap)");
            else if (isGoodRun) SerialComputer.println("good run)");
        }
    } else if (changed) {
        if (enDebug) {
            SerialComputer.print("ADAPT NOT SAVED — score=");
            SerialComputer.print(score10);
            SerialComputer.print(" fault=0x");
            SerialComputer.println(phFaultFlags, HEX);
        }
        // Rollback các thay đổi để giữ params cũ
        phAdaptGasBoost = oldGasBoost;
        phAdaptHeatAir  = oldHeatAir;
    }
    // Luôn log để phân tích, kể cả run xấu
    if (normalEnd) phAdaptLog(phAdaptRuns, phRunTargetBT10, phRunStartBT10, endBT10, phRunMaxBT10,
                              avgGas, avgAir, score10, oldGasBoost, phAdaptGasBoost,
                              oldHeatAir, phAdaptHeatAir, lesson);
    phRunActive = false;
}

// ── FF Table: load/save/lookup/learn ─────────────────────────────────────────

void phFFLoad() {
    for (uint8_t i = 0; i < PH_FF_ZONES; i++) phFF[i] = {0,0,0,0,0};
    phAdaptLoad();
    if (!SD.exists(PH_FF_FILE)) return;
    File f = SD.open(PH_FF_FILE, FILE_READ);
    if (!f) return;
    for (uint8_t i = 0; i < PH_FF_ZONES && f.available(); i++) {
        phFF[i].btZoneCenter = (int16_t)f.parseInt();
        phFF[i].gasPercent   = (int16_t)f.parseInt();
        phFF[i].gain10       = (int16_t)f.parseInt();
        phFF[i].coldGas      = (int16_t)f.parseInt();
        phFF[i].hotGas       = (int16_t)f.parseInt();
    }
    f.close();
    if (enDebug) SerialComputer.println("FF loaded");
}

void phFFSave() {
    SD.remove(PH_FF_FILE);
    File f = SD.open(PH_FF_FILE, FILE_WRITE);
    if (!f) return;
    for (uint8_t i = 0; i < PH_FF_ZONES; i++) {
        if (phFF[i].btZoneCenter == 0) continue;
        f.print(phFF[i].btZoneCenter); f.print(' ');
        f.print(phFF[i].gasPercent);   f.print(' ');
        f.print(phFF[i].gain10);       f.print(' ');
        f.print(phFF[i].coldGas);      f.print(' ');
        f.println(phFF[i].hotGas);
    }
    f.close();
    if (enDebug) SerialComputer.println("FF saved");
}

// Tìm index vùng BT, trả -1 nếu chưa có
int8_t phFFFind(int16_t bt10) {
    int16_t zone = (bt10 / PH_FF_ZONE_W) * PH_FF_ZONE_W + PH_FF_ZONE_W / 2;
    for (uint8_t i = 0; i < PH_FF_ZONES; i++)
        if (phFF[i].btZoneCenter == zone) return (int8_t)i;
    return -1;
}

int16_t phFFLookup(int16_t bt10) {
    int8_t idx = phFFFind(bt10);
    return (idx >= 0) ? phFF[idx].gasPercent : -1;
}


int16_t phFFLookupThermal(int16_t bt10, int16_t etBtGap) {
    int8_t idx = phFFFind(bt10);
    if (etBtGap <= PH_ET_BT_COLD)
        return (idx >= 0 && phFF[idx].coldGas > 0) ? phFF[idx].coldGas : PH_GAS_COLD_DEF;
    if (etBtGap >= PH_ET_BT_HOT)
        return (idx >= 0 && phFF[idx].hotGas > 0)  ? phFF[idx].hotGas  : PH_GAS_HOT_DEF;
    int16_t coldVal = (idx >= 0 && phFF[idx].coldGas > 0) ? phFF[idx].coldGas : PH_GAS_COLD_DEF;
    int16_t hotVal  = (idx >= 0 && phFF[idx].hotGas  > 0) ? phFF[idx].hotGas  : PH_GAS_HOT_DEF;
    return (int16_t)(coldVal + (int32_t)(hotVal - coldVal) * (etBtGap - PH_ET_BT_COLD) / (PH_ET_BT_HOT - PH_ET_BT_COLD));
}

// Tìm slot (existing > empty > furthest) cho vùng BT
static int8_t phFFFindSlot(int16_t bt10, int16_t zone) {
    int8_t target = -1;
    for (uint8_t i = 0; i < PH_FF_ZONES; i++) {
        if (phFF[i].btZoneCenter == zone)             return (int8_t)i;
        if (phFF[i].btZoneCenter == 0 && target < 0) target = (int8_t)i;
    }
    if (target >= 0) return target;
    int16_t worstDist = 0;
    for (uint8_t i = 0; i < PH_FF_ZONES; i++) {
        int16_t d = abs(phFF[i].btZoneCenter - bt10);
        if (d > worstDist) { worstDist = d; target = (int8_t)i; }
    }
    return target;
}

void phFFLearnThermal(int16_t bt10, int16_t gas, int16_t etBtGap) {
    int16_t zone = (bt10 / PH_FF_ZONE_W) * PH_FF_ZONE_W + PH_FF_ZONE_W / 2;
    int8_t t = phFFFindSlot(bt10, zone);
    phFF[t].btZoneCenter = zone;
    if (etBtGap <= PH_ET_BT_COLD) {
        phFF[t].coldGas = phFF[t].coldGas > 0 ? (int16_t)(phFF[t].coldGas*7/10 + gas*3/10) : gas;
        if (enDebug) { SerialComputer.print("FF COLD BT="); SerialComputer.print(bt10/10); SerialComputer.print("C gas="); SerialComputer.println(phFF[t].coldGas); }
    } else if (etBtGap >= PH_ET_BT_HOT) {
        phFF[t].hotGas  = phFF[t].hotGas  > 0 ? (int16_t)(phFF[t].hotGas *7/10 + gas*3/10) : gas;
        if (enDebug) { SerialComputer.print("FF HOT BT=");  SerialComputer.print(bt10/10); SerialComputer.print("C gas="); SerialComputer.println(phFF[t].hotGas);  }
    }
}

void phFFLearn(int16_t bt10, int16_t gas) {
    int16_t zone = (bt10 / PH_FF_ZONE_W) * PH_FF_ZONE_W + PH_FF_ZONE_W / 2;
    int8_t t = phFFFindSlot(bt10, zone);
    phFF[t].btZoneCenter = zone;
    phFF[t].gasPercent   = gas;
}

void phFFLearnGain(int16_t bt10, int16_t gasDelta, int16_t rorBefore, int16_t rorAfter) {
    if (gasDelta == 0) return;
    int16_t newGain = abs((rorAfter - rorBefore) / gasDelta);
    if (newGain < 1 || newGain > 100) return;
    int16_t zone = (bt10 / PH_FF_ZONE_W) * PH_FF_ZONE_W + PH_FF_ZONE_W / 2;
    for (uint8_t i = 0; i < PH_FF_ZONES; i++) {
        if (phFF[i].btZoneCenter != zone) continue;
        phFF[i].gain10 = phFF[i].gain10 > 0
            ? (int16_t)(phFF[i].gain10*7/10 + newGain*3/10) : newGain;
        if (enDebug) { SerialComputer.print("FF gain BT="); SerialComputer.print(bt10/10); SerialComputer.print("C g="); SerialComputer.println(phFF[i].gain10); }
        return;
    }
}

// ── Thermal monitor — gọi mỗi giây, cập nhật phBtCoast / phEtHeatLoad ───────
// Mô phỏng "cảm giác người rang":
//   phBtCoast   = BT sẽ tăng thêm bao nhiêu nếu tắt gas ngay bây giờ
//                 = rorBT × coast_time (học từ thực tế qua phAdaptCoastMul)
//                 ET đang giảm nhanh → nhiệt vào ít → coast ngắn; ngược lại → coast dài
//   phEtHeatLoad = rorET hiện tại — nhiệt đang đổ vào trống
void phThermalMonitor() {
    // Phase 0: cập nhật rorBT_smooth + safety checks mỗi giây
    phUpdateRorSmooth();
    phCheckSensorDrop();
    phCheckRorExtreme();

    int16_t dRorET = rorET - phEtRorPrev;
    phEtRorPrev  = rorET;
    phEtHeatLoad = rorET;

    // Coast time: thời gian BT còn tăng sau tắt gas, scale bởi phAdaptCoastMul (học từ thực tế)
    // ET đang giảm (dRorET < -10) → nhiệt vào đang yếu dần → base ~8s
    // ET còn cao và ổn định       → nhiệt vào vẫn mạnh    → base ~15s
    int16_t coastBase = (dRorET < -10) ? 2 : 4;
    // Premix burner: buồng trộn thêm lag nhiệt → coast dài hơn 1.5×
    if (burnerPremix_R) coastBase = coastBase * 3 / 2;
    int16_t coastSec  = (int16_t)(coastBase * phAdaptCoastMul / 10);  // scale ×0.1

    // BT coast = rorBT × coastSec / 60 (đổi từ °C/min sang °C trong coastSec giây)
    // Nhân thêm hệ số ET: nếu rorET > rorBT → còn nhiều nhiệt đang đến → coast lớn hơn
    int16_t etBoost = (rorET > rorBT + 20) ? (rorET - rorBT) / 4 : 0;  // max ~25
    phBtCoast = (int16_t)constrain((int32_t)(rorBT + etBoost) * coastSec / 60, 0, 200);

    // ET confirmation: đếm giây rorET đã tăng rõ so với baseline lúc step
    // phEtAtStep = rorET tại lúc recordStep() — so sánh đúng, không bị ghi đè
    if (phGainWaiting && rorET > phEtAtStep + 10) {
        if (phEtConfirm < 20) phEtConfirm++;
    }
}

// ── Burner controller — gọi mỗi giây ────────────────────────────────────────
// mode=0 HEATING: đạt targetBT trong heatDeadlineSec giây
// mode=1 HOLDING: giữ BT ±5°C, xác nhận 20s trước khi bước
// Trả +1/-1 (bước gas 5%), 0 (giữ). Dead time PH_CTRL_DEAD_SEC giữa các bước.

int8_t preheatBurnerControl(uint8_t mode, int16_t targetBT10, uint16_t heatDeadlineSec) {
    int16_t rorNow = rorBT;
    int16_t dRorBT = rorNow - phRorPrev;
    phRorPrev = rorNow;

    // Đo gain 10s sau bước
    if (phGainWaiting && ++phGainWaitCount >= 10) {
        phFFLearnGain(phGainBT10, wuGasPercent - phGainGasBefore, phGainRorBefore, rorNow);
        phGainWaiting = phGainWaitCount = 0;
    }

    if (phCtrlDeadTimer > 0) {
        if (phCtrlLastDeadElapsed != wuElapsed) {
            phCtrlLastDeadElapsed = wuElapsed;
            // ET confirmation: nếu rorET đã phản hồi rõ (>5 đơn vị/giây trong 2 giây liên tiếp)
            // → rút ngắn dead time còn tối thiểu 6s thay vì chờ hết 15s
            if (phEtConfirm >= 2 && phCtrlDeadTimer > 6) phCtrlDeadTimer = 6;
            phCtrlDeadTimer--;
        }
        return 0;
    }

    int16_t btNow   = (int16_t)Temperature_BT;
    int16_t btError = targetBT10 - btNow;
    uint8_t heatAirMax = (mode == 0 && btError > PH_NEAR_TARGET_BAND) ? PH_HEAT_AIR_FAR_MAX : PH_HEAT_AIR_MAX;

    // btIfCutNow: BT sẽ đạt bao nhiêu nếu tắt gas ngay — dùng phBtCoast từ monitor
    int16_t btIfCutNow    = btNow + phBtCoast;
    bool willOvershoot    = (btIfCutNow > targetBT10 + 20);

    // Forecast RoR 15s tới để check stalling / decel — integer only
    int16_t rorFcast      = constrain(rorNow + dRorBT * 15, -500, 3000);
    bool    decelerating  = (dRorBT < -10);
    bool    fcastWillDrop = (rorFcast < rorNow - 50);
    bool    stalling      = (rorNow < 20 && dRorBT <= 0 && btError > 100);

    if (enDebug && (++phDbgTick >= 3)) {
        phDbgTick = 0;
        // Timestamp mm:ss
        uint16_t tMin = wuElapsed / 60, tSec = wuElapsed % 60;
        SerialComputer.print("[");
        SerialComputer.print(tMin); SerialComputer.print(":");
        if (tSec < 10) SerialComputer.print("0");
        SerialComputer.print(tSec); SerialComputer.print("] ");
        // State
        const char* stateStr = "?";
        switch (wuState) {
            case WU_HEATING:   stateStr = "HEAT"; break;
            case WU_HOLDING:   stateStr = "HOLD"; break;
            case WU_PRECISION: stateStr = "PREC"; break;
            default: break;
        }
        SerialComputer.print(stateStr);
        // Target (có thể thay đổi mid-preheat)
        SerialComputer.print(" tgt="); SerialComputer.print((int16_t)wuTemp_R);
        SerialComputer.print("C/");    SerialComputer.print((int16_t)wuTime_R); SerialComputer.print("m");
        // Nhiệt độ
        SerialComputer.print(" BT=");  SerialComputer.print(btNow/10);
        SerialComputer.print(" ET=");  SerialComputer.print((int16_t)Temperature_ET/10);
        // Gas / Air
        SerialComputer.print(" gas="); SerialComputer.print(wuGasPercent);
        SerialComputer.print(" air="); SerialComputer.print(wuAirPercent);
        // RoR
        SerialComputer.print(" RoR="); SerialComputer.print(rorNow/10);  // °C/min thực
        SerialComputer.print(" sm=");  SerialComputer.print(rorBT_smooth/10);
        // Predict / overshoot
        SerialComputer.print(" pred="); SerialComputer.print(btIfCutNow/10);
        SerialComputer.print(" ov=");   SerialComputer.print(willOvershoot ? "Y" : "N");
        // Coast
        SerialComputer.print(" coast="); SerialComputer.print(phBtCoast/10);
        // Fault
        if (phFaultFlags) { SerialComputer.print(" FLT=0x"); SerialComputer.print(phFaultFlags, HEX); }
        SerialComputer.println();
    }

    auto recordStep = [&]() {
        phGainGasBefore = wuGasPercent; phGainRorBefore = rorNow;
        phRorAtStep = rorNow; phGainBT10 = btNow;
        phGainWaiting = 1; phGainWaitCount = 0;
        phEtConfirm   = 0;
        phEtAtStep    = rorET;   // baseline ET để đo phản hồi sau step
        phCtrlDeadTimer = PH_CTRL_DEAD_SEC;
    };

    // ── HEATING ──────────────────────────────────────────────────────────────
    if (mode == 0) {
        if (btError <= 50) return 0;

        int16_t rorNeeded = (heatDeadlineSec > 0)
            ? (int16_t)constrain((int32_t)btError*60/heatDeadlineSec, 0, 3000) : 0;
        int16_t delta       = rorNow - rorNeeded;
        bool farFromTarget  = (btError > PH_NEAR_TARGET_BAND);
        bool approachTarget = (btError <= PH_APPROACH_BAND);

        // Tính gas nền cần đạt khi còn xa target
        // rampCap học từ ADAPT: mỗi lần overshoot → boost giảm → rampCap giảm → ramp thấp hơn
        int16_t rampCap80 = constrain(80 + phAdaptGasBoost, 40, 80);
        int16_t rampCap70 = constrain(70 + phAdaptGasBoost, 35, 70);
        int16_t rampCap90 = constrain(90 + phAdaptGasBoost, 45, 90);
        int16_t rampTarget = phStartGasTarget;
        if (farFromTarget) {
            if (wuElapsed < WU_HEAT_TIME_SEC && btError > 600) rampTarget = max(rampTarget, rampCap80);
            if (heatDeadlineSec < 120 && btError > 600)        rampTarget = max(rampTarget, rampCap70);
            if (heatDeadlineSec <  90 && btError > 450)        rampTarget = max(rampTarget, rampCap80);
            if (heatDeadlineSec <  60 && btError > 300)        rampTarget = max(rampTarget, rampCap90);
        }

        // ET-aware brake: nếu tắt gas ngay sẽ vọt lố → phanh ngay bất kể dead time
        // Ưu tiên cao nhất trong HEATING, kể cả khi còn xa target một chút
        if (willOvershoot && btError <= PH_NEAR_TARGET_BAND) {
            setMachineStatus(STT_PREHEAT_OVERSHOOT);
            if (rorNow > 10) { phRunPredCoast = phBtCoast; phRunBtAtBrake = btNow; }
            if (enDebug) { SerialComputer.print("BC coast brake btIfCut="); SerialComputer.println(btIfCutNow/10); }
            recordStep(); return -1;
        }

        if (approachTarget && (rorNow > 25 || phEtHeatLoad > 40)) {
            if (enDebug) SerialComputer.println("BC approach brake");
            recordStep(); return -1;
        }
        if (farFromTarget && wuGasPercent < rampTarget) {
            if (enDebug) SerialComputer.println("BC ramp to floor");
            recordStep(); return (rampTarget - wuGasPercent >= 10) ? +2 : +1;
        }
        if (decelerating && delta > 0) {
            if (!fcastWillDrop && rorFcast >= rorNeeded - 20) return 0;
            recordStep(); return +1;
        }
        if (stalling) {
            setMachineStatus(STT_ROR_BT_STALL);
            recordStep(); return +1;
        }
        // ET đang dẫn trước BT → chờ BT theo tối đa 15s, không tăng gas vội
        if (rorET > 20 && rorBT < rorET/2 && delta < 0) {
            if (phBTNoRiseCount < 15) { phBTNoRiseCount++; return 0; }
        } else {
            phBTNoRiseCount = 0;
        }

        if (delta < -20) {
            if (wuGasPercent < 100) { recordStep(); return (farFromTarget && delta < -80) ? +2 : +1; }
            if (wuAirPercent > 0) {
                wuAirPercent = constrain(wuAirPercent - 10, 0, heatAirMax);
                airflowPercent = wuAirPercent; phCtrlDeadTimer = PH_CTRL_DEAD_SEC;
                if (enDebug) { SerialComputer.print("BC air-=10 "); SerialComputer.println(wuAirPercent); }
            }
            return 0;
        }
        if (delta > 20) {
            if (farFromTarget) return 0;
            if (wuGasPercent > 0) { recordStep(); return -1; }
            wuAirPercent = constrain(wuAirPercent + 10, 0, heatAirMax);
            airflowPercent = wuAirPercent; phCtrlDeadTimer = PH_CTRL_DEAD_SEC;
            if (enDebug) { SerialComputer.print("BC air+=10 "); SerialComputer.println(wuAirPercent); }
            return 0;
        }
        // RoR trong vùng → từng bước khôi phục gió về 20%
        if      (wuAirPercent > 20) { wuAirPercent = constrain(wuAirPercent - 10, 0, heatAirMax); airflowPercent = wuAirPercent; }
        else if (wuAirPercent < 20) { wuAirPercent = constrain(wuAirPercent + 10, 0, heatAirMax); airflowPercent = wuAirPercent; }
        return 0;
    }

    // ── HOLDING ──────────────────────────────────────────────────────────────
    if (phHoldLastEvalElapsed == wuElapsed) return 0;
    phHoldLastEvalElapsed = wuElapsed;

    int8_t step = 0;
    if      (btError >  50)                          step = +1;
    else if (btError < -30 && rorNow > -50)          step = -1;  // không cắt gas khi BT đang rơi
    else if (rorNow  >  40 && btError <  20)         step = -1;
    else if (rorNow  < -40 && btError > -20)         step = +1;

    // phBtCoast: nếu dự báo vọt lố ngay cả khi BT còn dưới target → giảm gas sớm, bỏ qua confirm
    if (step >= 0 && rorNow > 0 && (btNow + phBtCoast > targetBT10 + 20)) {
        if (rorNow > 10) { phRunPredCoast = phBtCoast; phRunBtAtBrake = btNow; }
        if (enDebug) { SerialComputer.print("HOLD coast brake coast="); SerialComputer.println(phBtCoast/10); }
        phHoldPendingStep = 0; phHoldConfirmSec = 0;
        recordStep(); return -1;
    }

    if (step == 0)                 { phHoldPendingStep = 0; phHoldConfirmSec = 0; return 0; }
    if (step != phHoldPendingStep) { phHoldPendingStep = step; phHoldConfirmSec = 0; }
    // ET đã xác nhận → rút ngắn confirm từ 20s xuống 8s khi cần tăng gas
    uint8_t confirmNeeded = (step > 0 && phEtConfirm >= 3) ? 8 : 20;
    if (phHoldConfirmSec < confirmNeeded) { phHoldConfirmSec++; return 0; }

    phHoldConfirmSec = 0;
    recordStep();
    if (enDebug) {
        SerialComputer.print("BC HOLD step="); SerialComputer.print(step*5);
        SerialComputer.print("% btErr=");      SerialComputer.println(btError);
    }
    return step;
}

// ── wuReset ──────────────────────────────────────────────────────────────────

void wuReset(bool normalEnd = false) {
    phRunLearn(normalEnd);
    phFFSave();
    phCsvClose();  // đóng file CSV khi kết thúc run
    phCsvLastElapsed = 65535;
    phCsvReason = 0;
    wuState               = WU_IDLE;
    wuElapsed             = 0;
    wuDeadTimer           = 0;
    wuGasPercent          = 0;
    phStableCount         = 0;
    phBtCoast             = 0;
    phEtHeatLoad          = 0;
    phEtRorPrev           = 0;
    phEtConfirm           = 0;
    phEtAtStep            = 0;
    phCtrlDeadTimer       = 0;
    phCtrlLastDeadElapsed = 65535;
    phHoldLastEvalElapsed = 65535;
    phHoldPendingStep     = 0;
    phHoldConfirmSec      = 0;
    phGainWaiting         = 0;
    phGainWaitCount       = 0;
    phBTNoRiseCount       = 0;
    phFFSnapDone          = false;
    phCoolDbgTimer        = 0;
    phPiLastElapsed       = 65535;
    phPiLastUpdateMs      = 0;
    // phPiIAccum KHÔNG reset — giữ học từ run trước (quyết định 7)
    // Phase 0: reset sensor history + fault flags
    for (uint8_t i = 0; i < 5; i++) { phBtHistory[i] = 0; phEtHistory[i] = 0; }
    phHistIdx = 0;
    phHistLastSec = 65535;
    phFaultFlags = 0;
    phGasLostCount = 0;
    rorBT_smooth = 0;
    // Phase 7: reset slew state
    phSlewLastSec = 65535;
    phSlewLastGas = 0;
    phSlewLastAir = 0;
    phPreIgniteStartMs = 0;
    phRecoveryExitCount = 0;
    phDbgTick = 0;
    wuIgniteTimer         = 0;
    phRorAtStep = phRorPrev = 0;
    gasPercent = airflowPercent = 0;
    wuAirPercent    = 0;
    naviSourceGAS   = 0;
    naviSourceAIR   = 0;
    vacuumSetFlag_R = wuVacFlagSaved;
    if (vacuumSetFlag_R == 1) pidAirflowReset();
    wuVacFlagSaved = 0;
    nodeHMI.writeSingleRegister(START_GAS_BTN_W - 1, 0);
    tunePercent = 0;
}

// ── Tính progress % hiển thị trên HMI ────────────────────────────────────────
static uint16_t phCalcProgress(int16_t targetBT10) {
    uint16_t timePct = (wuTime_R > 0)
        ? (uint16_t)constrain((int32_t)wuElapsed * 100 / ((uint16_t)wuTime_R * 60), 0, 100) : 0;
    uint16_t btPct = (targetBT10 > 20)
        ? (uint16_t)constrain((int32_t)(int16_t)Temperature_BT * 100 / (targetBT10 - 20), 0, 100) : 0;
    return min(timePct, btPct);
}

// ── preheat() — gọi từ programScan() mỗi loop, tự throttle 1Hz ──────────────

void preheat() {
    static uint32_t phLastMillis = 0;
    uint32_t now = millis();
    if (now - phLastMillis < 1000) {
        // Cập nhật output gas/air liên tục dù chưa đến 1s
        if (wuState == WU_HEATING || wuState == WU_HOLDING || wuState == WU_PRECISION) {
            gasPercent     = constrain(wuGasPercent, 0, 100);
            airflowPercent = constrain(wuAirPercent, 0,
                             (wuState == WU_HEATING) ? 80 : 40);
        }
        return;
    }
    phLastMillis = now;

    if (WU_R == 0 && wuState != WU_IDLE) {
        setMachineStatus(STT_PREHEAT_CANCELLED);
        if (enDebug) SerialComputer.println("PREHEAT: cancelled");
        wuReset(); return;
    }
    if (WU_R == 0) return;

    int16_t targetBT10 = (int16_t)wuTemp_R * 10;

    // Log khi target hoặc thời gian được thay đổi giữa chừng
    static int16_t  phLastLogTarget = 0;
    static uint16_t phLastLogTime   = 0;
    if (enDebug && wuState >= WU_HEATING) {
        if (targetBT10 != phLastLogTarget || (uint16_t)wuTime_R != phLastLogTime) {
            SerialComputer.print("[CHANGE] tgt="); SerialComputer.print(wuTemp_R);
            SerialComputer.print("C time=");       SerialComputer.print(wuTime_R);
            SerialComputer.println("m");
            phLastLogTarget = targetBT10;
            phLastLogTime   = (uint16_t)wuTime_R;
        }
    }

    switch (wuState) {

    case WU_COOLING: {
        if ((int16_t)Temperature_BT > 0)
            tunePercent = (uint16_t)constrain((int32_t)targetBT10 * 99 / (int16_t)Temperature_BT, 0, 99);

        // Khi BT đã vào vùng target ±20°C → chuyển COAST (chờ ET hội tụ)
        // COAST khác COOLING: air vừa phải (35%), không hút nhiệt mạnh nữa
        if ((int16_t)Temperature_BT <= targetBT10 + 200) {
            wuState = WU_COAST;
            wuGasPercent = wuDeadTimer = phCtrlDeadTimer = 0;
            wuAirPercent = 35;
            setMachineStatus(STT_PREHEAT_COAST);
            if (enDebug) SerialComputer.println("COOL: -> COAST");
            break;
        }
        wuGasPercent = 0;
        int16_t btAbove   = (int16_t)Temperature_BT - targetBT10;
        uint8_t airMax    = (btAbove > 200) ? 80 : (btAbove > 50) ? 60 : 40;
        int16_t rorTarget = (btAbove > 200) ? -30 : (btAbove > 50) ? -20 : -10;

        if (wuDeadTimer > 0) { wuDeadTimer--; gasPercent = 0; airflowPercent = constrain(wuAirPercent, 0, airMax); break; }

        int16_t etBtGap  = (int16_t)Temperature_ET - (int16_t)Temperature_BT;
        int8_t  airStep  = 0;
        if      (rorBT > rorTarget + 10 && etBtGap <= 100) airStep = +1;
        else if (rorBT < rorTarget - 30 && etBtGap >= -50) airStep = -1;

        if (enDebug && ++phCoolDbgTimer >= 5) {
            phCoolDbgTimer = 0;
            SerialComputer.print("COOL rorBT="); SerialComputer.print(rorBT);
            SerialComputer.print(" tgt=");       SerialComputer.print(rorTarget);
            SerialComputer.print(" air=");       SerialComputer.println(wuAirPercent);
        }
        if (airStep != 0) {
            wuAirPercent = constrain((int16_t)wuAirPercent + airStep * 10, 0, (int16_t)airMax);
            wuDeadTimer  = 10;
            if (enDebug) { SerialComputer.print("COOL air="); SerialComputer.println(wuAirPercent); }
        }
        gasPercent = 0; airflowPercent = constrain(wuAirPercent, 0, airMax);
    }
    break;

    // ── WU_COAST: sau cooling, chờ ET và BT hội tụ trước khi ignite ──────────
    // Gas = 0, air 35% (vừa phải), chờ |ET-BT| < 5°C và ET trong [target-10, target+10]
    case WU_COAST: {
        if ((int16_t)Temperature_BT > 0)
            tunePercent = (uint16_t)constrain((int32_t)targetBT10 * 99 / (int16_t)Temperature_BT, 0, 99);

        wuGasPercent = 0;
        wuAirPercent = 35;
        gasPercent = 0;
        airflowPercent = 35;

        int16_t etBtGap = (int16_t)Temperature_ET - (int16_t)Temperature_BT;
        bool etConverged = (abs(etBtGap) < 50);
        bool etInRange   = ((int16_t)Temperature_ET >= targetBT10 - 100
                         && (int16_t)Temperature_ET <= targetBT10 + 100);
        bool btSafe      = ((int16_t)Temperature_BT <= targetBT10 + 50);

        if (etConverged && etInRange && btSafe) {
            wuState = WU_IDLE;  // re-classify start mode (sẽ vào HOT path)
            setMachineStatus(STT_PREHEAT_COOLING_DONE);
            if (enDebug) {
                SerialComputer.print("COAST -> IDLE etBtGap=");
                SerialComputer.print(etBtGap);
                SerialComputer.print(" ET=");
                SerialComputer.println(Temperature_ET / 10);
            }
            break;
        }

        // Nếu BT vọt lên lại quá target+30 → quay về COOLING
        if ((int16_t)Temperature_BT > targetBT10 + 300) {
            wuState = WU_COOLING;
            if (enDebug) SerialComputer.println("COAST: BT vọt lại -> COOLING");
        }
    }
    break;

    case WU_IDLE: {
        if ((int16_t)Temperature_BT > targetBT10 + 20) {
            wuState = WU_COOLING;
            naviSourceGAS = SOURCE_AI_AUTO; naviSourceAIR = SOURCE_AI_AUTO;
            wuGasPercent = gasPercent; wuDeadTimer = 0; wuAirPercent = 0;
            wuVacFlagSaved = vacuumSetFlag_R; vacuumSetFlag_R = 0;
            gasPercent = 0;
            nodeHMI.writeSingleRegister(START_GAS_BTN_W - 1, 0);
            if (enDebug) { SerialComputer.print("PREHEAT: BT>target, cooling BT="); SerialComputer.println(Temperature_BT/10); }
            break;
        }
        int16_t etBtGap = (int16_t)Temperature_ET - (int16_t)Temperature_BT;
        int16_t learned = phFFLookup(targetBT10);
        wuGasPercent = (learned >= 0) ? learned : phFFLookupThermal(targetBT10, etBtGap);
        wuGasPercent = constrain(wuGasPercent + phAdaptGasBoost, 5, 100);
        // Gần target rồi → khởi động nhỏ gas để không vọt
        if      ((int16_t)Temperature_BT >= targetBT10 - 50)  wuGasPercent = 0;
        else if ((int16_t)Temperature_BT >= targetBT10 - 100) wuGasPercent = min(wuGasPercent, (int16_t)15);
        else if ((int16_t)Temperature_ET >= targetBT10 && (int16_t)Temperature_BT >= targetBT10 - 150)
                                                               wuGasPercent = min(wuGasPercent, (int16_t)20);
        phStartGasTarget = constrain(wuGasPercent, 5, 100);
        {
            int16_t gap = targetBT10 - (int16_t)Temperature_BT;
            int16_t holdMinCalc = constrain(targetBT10 / 100 + 4, 15, 35);
            if (gap > 0 && gap <= 800) {
                // Gap nhỏ (≤80°C): không ramp, dùng holdMin + nhỏ thêm theo gap
                // Tránh tích nhiệt khi target thấp — BT tự tăng nhẹ
                int16_t softGas = constrain(holdMinCalc + gap / 80, holdMinCalc, holdMinCalc + 10);
                wuGasPercent    = softGas;
                phStartGasTarget = softGas;
            } else if (gap > PH_NEAR_TARGET_BAND) {
                // Gap lớn: gas nền tỉ lệ với gap
                int16_t dynFloor = constrain(gap / 20 + 35, 45, PH_FAR_GAS_FLOOR);
                phStartGasTarget = max(phStartGasTarget, dynFloor);
            }
        }
        wuAirPercent = constrain(phAdaptHeatAir, 0, 40);
        if (enDebug) {
            SerialComputer.print("PREHEAT init gas="); SerialComputer.print(wuGasPercent);
            SerialComputer.print("% ff=");             SerialComputer.print(learned);
            SerialComputer.print(" gap=");             SerialComputer.println(etBtGap/10);
        }
        // Phân loại start mode: COOL (BT > target+20), HOT (gap < 50°C), COLD (còn lại)
        int16_t btGap = targetBT10 - (int16_t)Temperature_BT;
        if ((int16_t)Temperature_BT > targetBT10 + 200)  phStartMode = START_COOL;
        else if (btGap < 500)                              phStartMode = START_HOT;
        else                                               phStartMode = START_COLD;

        wuElapsed = wuDeadTimer = wuIgniteTimer = 0;
        phRorAtStep = phRorPrev = 0;
        phStableCount = 0;
        phRunStart(targetBT10);
        naviSourceGAS = SOURCE_AI_AUTO; naviSourceAIR = SOURCE_AI_AUTO;
        wuVacFlagSaved = vacuumSetFlag_R; vacuumSetFlag_R = 0;
        gasPercent = 0;
        phPreIgniteStartMs = 0;  // sẽ được set khi vào WU_PRE_IGNITE
        wuState = WU_PRE_IGNITE;
        setMachineStatus(STT_PREHEAT_PRE_IGNITE);
        if (enDebug) {
            SerialComputer.print("PREHEAT: pre-ignite mode=");
            SerialComputer.println(phStartMode == START_COLD ? "COLD" : phStartMode == START_HOT ? "HOT" : "COOL");
        }
    }
    break;

    // ── WU_PRE_IGNITE: thổi sạch chamber trước khi mồi lửa ──────────────────
    // COLD: 10s (5s A70 + 5s A30), HOT: 4s (2s A60 + 2s A30)
    // Dùng millis() — không phụ thuộc loop hay throttle 1Hz
    case WU_PRE_IGNITE: {
        uint32_t nowMs = millis();
        if (phPreIgniteStartMs == 0) phPreIgniteStartMs = nowMs;
        uint32_t elapsedMs = nowMs - phPreIgniteStartMs;

        uint32_t totalMs  = (phStartMode == START_HOT) ? 4000UL : 10000UL;
        uint32_t phase1Ms = totalMs / 2;

        if (elapsedMs < phase1Ms) {
            wuAirPercent   = (phStartMode == START_HOT) ? 60 : 70;
        } else if (elapsedMs < totalMs) {
            wuAirPercent   = 30;
        } else {
            // Purge xong → chuyển sang IGNITE
            phPreIgniteStartMs = 0;
            wuState = WU_IGNITE;
            nodeHMI.writeSingleRegister(START_GAS_BTN_W - 1, 1);
            if (enDebug) SerialComputer.println("PRE_IGNITE: done -> IGNITE");
            break;
        }
        gasPercent     = 0;
        airflowPercent = wuAirPercent;
    }
    break;

    case WU_IGNITE: {
        gasPercent = 30;  // mở 30% gas tối thiểu để mồi lửa — relay đã mở, DAC cần đủ áp
        if (gasSignal == 1) {
            setMachineStatus(STT_PREHEAT_IGNITE_OK);
            wuState = WU_HEATING; wuElapsed = 0; wuDeadTimer = 5; wuIgniteTimer = 0;
            phRorAtStep = phRorPrev = 0;
            wuGasPercent   = min((int16_t)30, phStartGasTarget);
            gasPercent     = wuGasPercent;
            airflowPercent = constrain(wuAirPercent, 0, PH_HEAT_AIR_MAX);
            if (enDebug) SerialComputer.println("PREHEAT: gas on");
            break;
        }
        if (wuIgniteTimer >= 60) {
            wuIgniteTimer = phRorAtStep = phRorPrev = 0;
            nodeHMI.writeSingleRegister(START_GAS_BTN_W - 1, 0);
            wuDeadTimer++;
            if (wuDeadTimer >= 3) {
                setMachineStatus(STT_PREHEAT_IGNITE_FAIL);
                if (enDebug) SerialComputer.println("PREHEAT: ignition failed 3x");
                wuReset();
                nodeHMI.writeSingleRegister(WU_W - 1, 0);
                return;
            }
            nodeHMI.writeSingleRegister(START_GAS_BTN_W - 1, 1);
            setMachineStatus(STT_PREHEAT_IGNITE_RETRY);
            if (enDebug) { SerialComputer.print("PREHEAT: retry #"); SerialComputer.println(wuDeadTimer+1); }
        }
    }
    break;

    case WU_HEATING: {
        phThermalMonitor();
        if (enDebug && wuElapsed >= 10 && wuElapsed <= 12 && rorET <= 0)
            SerialComputer.println("PREHEAT WARN: rorET not rising at 10s");
        tunePercent = phCalcProgress(targetBT10);
        nodeHMI.writeSingleRegister(MIN_HMI_W - 1, wuElapsed / 60);
        nodeHMI.writeSingleRegister(SEC_HMI_W - 1, wuElapsed % 60);

        if (wuTime_R > 0 && wuElapsed >= (uint16_t)wuTime_R * 60) {
            setMachineStatus(STT_PREHEAT_TIMEOUT);
            if (enDebug) SerialComputer.println("PREHEAT: timeout");
            phRunSample(); wuReset(true);
            nodeHMI.writeSingleRegister(WU_W - 1, 0); return;
        }

        int16_t btError   = targetBT10 - (int16_t)Temperature_BT;
        uint8_t heatAirMax = (btError > PH_NEAR_TARGET_BAND) ? PH_HEAT_AIR_FAR_MAX : PH_HEAT_AIR_MAX;

        if (btError <= PH_APPROACH_BAND && btError > 50 && wuAirPercent < 30) wuAirPercent = 30;
        if (wuElapsed < WU_HEAT_TIME_SEC && btError > PH_NEAR_TARGET_BAND && wuAirPercent > heatAirMax) wuAirPercent = heatAirMax;
        if (wuElapsed >= WU_HEAT_TIME_SEC && wuElapsed < WU_HEAT_TIME_SEC + 5 && btError > 50) {
            setMachineStatus(STT_PREHEAT_3MIN_WARN);
            if (enDebug) SerialComputer.println("PREHEAT: 3min warn");
        }

        // Chuyển HOLDING khi BT đã vào gần target
        if (btError <= 50) {
            wuState = WU_HOLDING; phStableCount = phCtrlDeadTimer = phGainWaiting = phGainWaitCount = 0;
            phCtrlLastDeadElapsed = phHoldLastEvalElapsed = 65535;
            phHoldPendingStep = phHoldConfirmSec = 0;
            // Clamp gas về holdGasMax (45%) ngay khi vào HOLDING — tránh quán tính từ gas cao
            if (wuGasPercent > 45) { wuGasPercent = 45; phCtrlDeadTimer = PH_CTRL_DEAD_SEC; }
            if (rorBT > 20 || (int16_t)Temperature_ET >= targetBT10) {
                if (wuGasPercent > 0) { wuGasPercent = constrain(wuGasPercent-5, 0, 45); phCtrlDeadTimer = PH_CTRL_DEAD_SEC; }
                gasPercent = wuGasPercent;
                if (wuAirPercent < 30) wuAirPercent = 30;
                airflowPercent = constrain(wuAirPercent, 0, 80);
            }
            if (enDebug) {
                uint16_t tM = wuElapsed/60, tS = wuElapsed%60;
                SerialComputer.print("PREHEAT: -> HOLDING [");
                SerialComputer.print(tM); SerialComputer.print(":");
                if (tS < 10) SerialComputer.print("0");
                SerialComputer.print(tS); SerialComputer.print("] gas=");
                SerialComputer.print(wuGasPercent);
                SerialComputer.print(" BT="); SerialComputer.print((int16_t)Temperature_BT/10);
                SerialComputer.println("C");
            }
            break;
        }

        // ET đã vượt target → hãm lửa sớm, không dùng dead time (quá chậm)
        if (((int16_t)Temperature_ET >= targetBT10 - 50 && btError <= 150) || (btError <= 150 && rorBT_smooth > 30)) {
            int16_t holdMin  = constrain(targetBT10 / 100 + 4, 15, 35);
            int16_t targetGas = holdMin + 5;
            // Cắt gas nhanh về gần holdMin — không dead time
            if      (wuGasPercent > targetGas + 3) wuGasPercent = constrain(wuGasPercent - 8, holdMin, 100);
            else if (wuGasPercent > targetGas)      wuGasPercent = targetGas;
            gasPercent = wuGasPercent;
            if (wuAirPercent < 35) wuAirPercent = 35;
            airflowPercent = constrain(wuAirPercent, 0, PH_HEAT_AIR_MAX);
            phRunSample();
            if (enDebug) SerialComputer.println("PREHEAT: hot approach");
            break;
        }

        // Snap FF khi mới bắt lửa (chỉ một lần, 2s đầu)
        if (!phFFSnapDone && wuElapsed <= 1) {
            phFFSnapDone = true;
            int16_t ff = phFFLookup(targetBT10);
            if (ff >= 0) {
                int16_t ffGas = constrain(ff + phAdaptGasBoost, 5, 100);
                if      (ffGas > wuGasPercent) wuGasPercent = constrain(wuGasPercent + 5, 0, 100);
                else if (ffGas < wuGasPercent && btError <= PH_NEAR_TARGET_BAND) wuGasPercent = constrain(wuGasPercent - 5, 0, 100);
                phCtrlDeadTimer = PH_CTRL_DEAD_SEC;
                if (enDebug) { SerialComputer.print("FF snap gas="); SerialComputer.println(wuGasPercent); }
            }
        }

        // ── APPROACH: phanh chỉ khi RoR đang DƯ so với cần để đạt target đúng hạn ──
        // Nếu đang chậm hơn cần thiết → không phanh, để preheatBurnerControl tăng tốc
        if (btError > 50 && btError <= 600) {
            uint16_t timeLeft = (wuElapsed < WU_HEAT_TIME_SEC) ? WU_HEAT_TIME_SEC - wuElapsed : 1;
            // RoR cần thiết để đạt target trong thời gian còn lại (×10 unit)
            int16_t rorNeeded = (int16_t)constrain((int32_t)btError * 60 / timeLeft, 10, 3000);

            // Nếu RoR hiện tại chậm hơn cần thiết → không vào APPROACH
            // preheatBurnerControl sẽ xử lý và tăng gas nếu cần
            if (rorBT_smooth < rorNeeded - 100) goto skip_approach;

            {
                // Premix: lag dài hơn → predict 45s thay vì 30s
                int16_t btPredict = (int16_t)Temperature_BT + (burnerPremix_R ? rorBT_smooth * 3 / 4 : rorBT_smooth / 2);
                int16_t overrun   = btPredict - targetBT10;
                int16_t holdMin   = constrain(targetBT10 / 100 + 4, 15, 35);
                int16_t targetGas;
                int16_t slewRate;

                if (overrun <= 0) goto skip_approach;  // không vọt → không phanh

                // Phanh tỉ lệ với mức RoR dư
                int16_t excess = rorBT_smooth - rorNeeded;
                if (excess > 1000) { targetGas = holdMin;     slewRate = 20; }
                else if (excess > 500) { targetGas = holdMin + 5;  slewRate = 10; }
                else               { targetGas = holdMin + 10; slewRate = 5; }

                if      (wuGasPercent > targetGas + 2) wuGasPercent = constrain(wuGasPercent - slewRate, holdMin, 100);
                else if (wuGasPercent < targetGas - 2) wuGasPercent = constrain(wuGasPercent + 3, 0, 100);
                else                                    wuGasPercent = targetGas;
                phCtrlDeadTimer = 0;

                int16_t airTarget = (excess > 500) ? 45 : 35;
                if      (wuAirPercent < airTarget - 1) wuAirPercent = constrain(wuAirPercent + 3, 0, 50);
                else if (wuAirPercent > airTarget + 1) wuAirPercent = constrain(wuAirPercent - 2, 0, 50);

                if (enDebug && ++phDbgTick >= 3) {
                    phDbgTick = 0;
                    SerialComputer.print("APPR BT=");    SerialComputer.print((int16_t)Temperature_BT/10);
                    SerialComputer.print(" need=");       SerialComputer.print(rorNeeded/10);
                    SerialComputer.print(" cur=");        SerialComputer.print(rorBT_smooth/10);
                    SerialComputer.print(" over=");       SerialComputer.print(overrun/10);
                    SerialComputer.print("C gas=");       SerialComputer.print(wuGasPercent);
                    SerialComputer.print(" air=");        SerialComputer.println(wuAirPercent);
                }
                gasPercent     = constrain(wuGasPercent, 0, 100);
                airflowPercent = constrain(wuAirPercent, 0, PH_HEAT_AIR_MAX);
                phRunSample();
                break;
            }
            skip_approach:;
        }

        int8_t step = preheatBurnerControl(0, targetBT10, (wuElapsed < WU_HEAT_TIME_SEC) ? WU_HEAT_TIME_SEC - wuElapsed : 1);
        if (step != 0) {
            step = constrain(step, -1, 2);
            int16_t minGas = (step < 0 || btError <= 150) ? 0 : 5;
            wuGasPercent = constrain(wuGasPercent + step * 5, minGas, 100);
        }
        gasPercent     = constrain(wuGasPercent, 0, 100);
        airflowPercent = constrain(wuAirPercent, 0, heatAirMax);
        phRunSample();
    }
    break;

    case WU_HOLDING: {
        phThermalMonitor();
        tunePercent = phCalcProgress(targetBT10);
        nodeHMI.writeSingleRegister(MIN_HMI_W - 1, wuElapsed / 60);
        nodeHMI.writeSingleRegister(SEC_HMI_W - 1, wuElapsed % 60);

        if (wuTime_R > 0 && wuElapsed >= (uint16_t)wuTime_R * 60) {
            setMachineStatus(STT_PREHEAT_DONE);
            if (enDebug) SerialComputer.println("PREHEAT: done");
            phRunSample(); wuReset(true);
            nodeHMI.writeSingleRegister(WU_W - 1, 0); return;
        }

        // Chuyển PRECISION khi đã qua 60% tổng thời gian — chế độ chính xác cuối
        if (wuTime_R > 0 && wuElapsed >= (uint16_t)wuTime_R * 60 * 6 / 10) {
            wuState = WU_PRECISION;
            phPiLastElapsed = 65535;
            if (enDebug) SerialComputer.println("HOLDING -> PRECISION");
            break;
        }

        int16_t holdGasMin = constrain(targetBT10 / 100 + 4, 15, 35);
        const int16_t holdGasMax = 45, holdAirMax = 40, holdAirLow = 20;
        int16_t btHoldErr = targetBT10 - (int16_t)Temperature_BT;

        // ── RECOVERY: BT vọt lố hoặc đang tăng nhanh → gas về sàn ngay, air theo rorBT ──
        // Entry: BT > target+15°C hoặc rorBT_smooth > 40 (nâng ngưỡng tránh kẹt)
        // Exit hysteresis: BT < target+10°C VÀ rorBT_smooth < 80 trong 5s liên tục
        // RoR guard chỉ kích hoạt khi BT đã ở target trở lên — tránh chặn PI khi BT còn thấp
        bool rawRecovery = ((int16_t)Temperature_BT > targetBT10 + 150)
                        || ((int16_t)Temperature_BT >= targetBT10 && rorBT_smooth > 40);
        // BT dưới target → thoát RECOVERY ngay, không check RoR (muốn BT tăng lên target)
        if ((int16_t)Temperature_BT < targetBT10) {
            phRecoveryExitCount = 5;
            rawRecovery = false;
        } else if (!rawRecovery && (int16_t)Temperature_BT < targetBT10 + 100 && rorBT_smooth < 80) {
            if (phRecoveryExitCount < 5) phRecoveryExitCount++;
        } else if (rawRecovery) {
            phRecoveryExitCount = 0;
        }
        bool inRecovery = rawRecovery || (phRecoveryExitCount < 5);
        if (inRecovery) {
            // Gas floor theo mức overshoot (không về 0 để lửa không tắt):
            // BT > target+20°C → 8% (minimum để giữ lửa)
            // BT > target+10°C → 12% (giảm nhiệt, BT tự rơi)
            // BT < target+10°C → holdGasMin (ổn định lại)
            int16_t overBT = (int16_t)Temperature_BT - targetBT10;
            int16_t recFloor = (overBT > 200)       ? 8
                             : (overBT > 100)       ? 12
                             : (rorBT_smooth > 800) ? 8    // RoR >80°C/min gần target → cắt mạnh
                             : (rorBT_smooth > 400) ? 12   // RoR >40°C/min gần target → cắt vừa
                             : holdGasMin;
            if (wuGasPercent > recFloor) {
                wuGasPercent = recFloor;
                phStableCount = 0;
            }
            // Air càng cao càng tốt khi BT còn trên target — scale theo mức vượt
            int16_t airMaxRec = (overBT > 300) ? 100
                              : (overBT > 200) ? 80
                              : (overBT > 100) ? 60
                              : 50;
            if      (rorBT_smooth >  0)  wuAirPercent = constrain(wuAirPercent + 10, 0, airMaxRec);
            else if (rorBT_smooth > -20) wuAirPercent = constrain(wuAirPercent +  5, 0, airMaxRec);
            else                         wuAirPercent = constrain(wuAirPercent - 10, holdAirLow, airMaxRec);
            // 1 dòng mỗi 3s, có đầy đủ BT/ET/gas/air/RoR
            if (enDebug && ++phDbgTick >= 3) {
                phDbgTick = 0;
                uint16_t tMin = wuElapsed / 60, tSec = wuElapsed % 60;
                SerialComputer.print("["); SerialComputer.print(tMin); SerialComputer.print(":");
                if (tSec < 10) SerialComputer.print("0");
                SerialComputer.print(tSec); SerialComputer.print("] ");
                SerialComputer.print("HOLD_REC BT="); SerialComputer.print((int16_t)Temperature_BT/10);
                SerialComputer.print(" ET=");         SerialComputer.print((int16_t)Temperature_ET/10);
                SerialComputer.print(" tgt=");        SerialComputer.print(targetBT10/10);
                SerialComputer.print(" over=");       SerialComputer.print(overBT/10);
                SerialComputer.print("C gas=");       SerialComputer.print(wuGasPercent);
                SerialComputer.print(" air=");        SerialComputer.print(wuAirPercent);
                SerialComputer.print(" RoR=");        SerialComputer.println(rorBT_smooth/10);
            }
        } else {
        // ── STABLE: BT gần target, RoR nhỏ → step ±5% mỗi 20s ──────────────────
            int8_t step = preheatBurnerControl(1, targetBT10, 0);
            if (step != 0) {
                step = constrain(step, -1, 1);
                wuGasPercent = constrain(wuGasPercent + step * 5, holdGasMin, holdGasMax);
                if (step > 0 && wuAirPercent > holdAirLow) {
                    wuAirPercent = constrain(wuAirPercent - 10, holdAirLow, holdAirMax);
                    airflowPercent = wuAirPercent;
                }
                phStableCount = 0;
            } else {
                if (abs(btHoldErr) <= 20 && abs(rorBT) <= 20) {
                    if (++phStableCount >= PH_STABLE_SEC) {
                        phFFLearn((int16_t)Temperature_BT, wuGasPercent);
                        phFFLearnThermal((int16_t)Temperature_BT, wuGasPercent,
                                        (int16_t)Temperature_ET - (int16_t)Temperature_BT);
                        phStableCount = 0;
                        if (enDebug) { SerialComputer.print("FF learn BT="); SerialComputer.print(Temperature_BT/10); SerialComputer.print("C gas="); SerialComputer.println(wuGasPercent); }
                    }
                } else { phStableCount = 0; }
            }
            // Air điều chỉnh nhẹ trong STABLE
            if      (btHoldErr >  50 && wuAirPercent > holdAirLow) wuAirPercent = constrain(wuAirPercent - 10, holdAirLow, holdAirMax);
            else if (btHoldErr >  20 && wuAirPercent > holdAirLow) wuAirPercent = constrain(wuAirPercent -  5, holdAirLow, holdAirMax);
            else if (btHoldErr < -50 && rorBT > 0)                 wuAirPercent = constrain(wuAirPercent +  5,          0, holdAirMax);
        }

        gasPercent     = constrain(wuGasPercent, 0, 100);
        airflowPercent = constrain(wuAirPercent, 0, holdAirMax);
        phRunSample();
    }
    break;

    // ── WU_PRECISION: 40% thời gian cuối — PI nhẹ để khử offset, học FF ─────
    case WU_PRECISION: {
        phThermalMonitor();
        tunePercent = phCalcProgress(targetBT10);
        nodeHMI.writeSingleRegister(MIN_HMI_W - 1, wuElapsed / 60);
        nodeHMI.writeSingleRegister(SEC_HMI_W - 1, wuElapsed % 60);

        if (wuTime_R > 0 && wuElapsed >= (uint16_t)wuTime_R * 60) {
            setMachineStatus(STT_PREHEAT_DONE);
            if (enDebug) SerialComputer.println("PRECISION: done");
            phRunSample(); wuReset(true);
            nodeHMI.writeSingleRegister(WU_W - 1, 0); return;
        }

        // Reset I term khi đổi target — quan trọng để tránh dùng I từ run cũ
        if (targetBT10 != phPiLastTarget) {
            phPiIAccum = 0;
            phPiLastTarget = targetBT10;
            phPiLastUpdateMs = millis();  // reset timer khi đổi target
            if (enDebug) SerialComputer.println("PREC: I reset (target changed)");
        }

        // PI update theo millis() — không phụ thuộc loop, chính xác cả khi SD/Modbus chậm
        uint32_t piNowMs = millis();
        uint32_t piDt    = piNowMs - phPiLastUpdateMs;
        if (piDt < 950) {  // chưa đủ 1s
            gasPercent     = constrain(wuGasPercent, 0, 100);
            airflowPercent = constrain(wuAirPercent, 0, 40);
            break;
        }
        // Cap dt để tránh I term jump lớn khi loop bị treo lâu (>3s)
        if (piDt > 3000) piDt = 3000;
        phPiLastUpdateMs = piNowMs;

        int16_t error    = targetBT10 - (int16_t)Temperature_BT;  // °C × 10
        int16_t holdMin  = constrain(targetBT10 / 100 + 4, 15, 35);
        int16_t baseGas  = holdMin + 5;
        // BT dưới target → không bao giờ RECOVERY (muốn BT tăng lên target)
        // Threshold RoR cao hơn HOLDING: PI xử lý được khi RoR < 30°C/min
        bool    inRecovery = ((int16_t)Temperature_BT >= targetBT10)
                          && (((int16_t)Temperature_BT > targetBT10 + 150)
                           || (rorBT_smooth > 300));

        if (inRecovery) {
            // Không reset I=0 — để I tích lũy qua các chu kỳ, hội tụ về steady-state
            // Chỉ clamp I về 0 nếu đang dương (overshoot → không để I dương góp thêm nhiệt)
            if (phPiIAccum > 0) phPiIAccum = 0;
            int16_t overBT = (int16_t)Temperature_BT - targetBT10;
            int16_t recFloor = (overBT > 200)       ? 8
                             : (overBT > 100)       ? 12
                             : (rorBT_smooth > 800) ? 8    // RoR >80°C/min gần target → cắt mạnh
                             : (rorBT_smooth > 400) ? 12   // RoR >40°C/min gần target → cắt vừa
                             : holdMin;
            wuGasPercent = recFloor;
            int16_t airMaxRec = (overBT > 300) ? 100
                              : (overBT > 200) ? 80
                              : (overBT > 100) ? 60
                              : 50;
            if      (rorBT_smooth >  0)  wuAirPercent = constrain(wuAirPercent + 10, 0, airMaxRec);
            else if (rorBT_smooth > -20) wuAirPercent = constrain(wuAirPercent +  5, 0, airMaxRec);
            else                         wuAirPercent = constrain(wuAirPercent - 10, 20, airMaxRec);
            phStableCount = 0;
            if (enDebug && ++phDbgTick >= 3) {
                phDbgTick = 0;
                uint16_t tMin = wuElapsed / 60, tSec = wuElapsed % 60;
                SerialComputer.print("["); SerialComputer.print(tMin); SerialComputer.print(":");
                if (tSec < 10) SerialComputer.print("0");
                SerialComputer.print(tSec); SerialComputer.print("] ");
                SerialComputer.print("PREC_REC BT="); SerialComputer.print((int16_t)Temperature_BT/10);
                SerialComputer.print(" ET=");          SerialComputer.print((int16_t)Temperature_ET/10);
                SerialComputer.print(" tgt=");         SerialComputer.print(targetBT10/10);
                SerialComputer.print(" over=");        SerialComputer.print(overBT/10);
                SerialComputer.print("C gas=");        SerialComputer.print(wuGasPercent);
                SerialComputer.print(" air=");         SerialComputer.print(wuAirPercent);
                SerialComputer.print(" RoR=");         SerialComputer.println(rorBT_smooth/10);
            }
        } else {
            // PI controller — scaling đúng đơn vị (%/°C trực tiếp)
            // P term: ~0.5% gas trên 1°C error, cap ±5%
            int16_t pTerm = (int16_t)((int32_t)error * 5 / 100);
            pTerm = constrain(pTerm, (int16_t)-5, (int16_t)5);

            // I term: tích lũy scale theo dt thực tế (ms) — chính xác khi loop không đều
            // error °C×10 × dt(ms) / 1000 = error tích lũy °C×10 × giây
            phPiIAccum += (int32_t)error * (int32_t)piDt / 1000;
            phPiIAccum  = constrain(phPiIAccum, (int32_t)-2000, (int32_t)2000);
            int16_t iTerm = (int16_t)(phPiIAccum / 400);

            // Khi BT >= target: cap gas ở holdMin — không thêm nhiệt khi đã vượt target
            int16_t gasMax = ((int16_t)Temperature_BT >= targetBT10) ? holdMin : 45;
            wuGasPercent = constrain(baseGas + pTerm + iTerm, holdMin, gasMax);

            // Air linh hoạt với guard ET/rorBT, slew rate ±2%/s
            int16_t airTarget = 25;
            if (error >  100)                                 airTarget = 22;  // BT thấp, giữ nhiệt
            if (error < -100)                                 airTarget = 30;  // BT cao, thoát nhiệt
            if (rorBT < -50)                                  airTarget = 20;  // BT đang rơi
            if ((int16_t)Temperature_ET > targetBT10 + 150)   airTarget = 35;  // ET cao, pha loãng

            if      (wuAirPercent < airTarget - 1) wuAirPercent = constrain(wuAirPercent + 2, 20, 40);
            else if (wuAirPercent > airTarget + 1) wuAirPercent = constrain(wuAirPercent - 2, 20, 40);

            // ADAPT learning — strict stable detection
            static uint8_t  phStrictStable  = 0;
            static int16_t  phLastGasObs    = 0;
            static int16_t  phLastAirObs    = 0;
            bool isStrictStable =
                abs(error) <= 50 &&
                abs(rorBT_smooth) <= 30 &&   // dùng smooth thay vì raw
                abs(rorET) <= 50 &&
                wuGasPercent == phLastGasObs &&
                wuAirPercent == phLastAirObs &&
                wuElapsed > 60 &&
                phFaultFlags == 0;           // không học khi có fault

            if (isStrictStable) {
                if (++phStrictStable >= 30) {  // 30s strict stable mới học
                    phFFLearn((int16_t)Temperature_BT, wuGasPercent);
                    phFFLearnThermal((int16_t)Temperature_BT, wuGasPercent,
                                     (int16_t)Temperature_ET - (int16_t)Temperature_BT);
                    if (wuGasPercent <= holdMin + 2 && rorBT_smooth < 0) phLearnLossRate(rorBT_smooth);
                    phStrictStable = 0;
                    if (enDebug) {
                        SerialComputer.print("PREC LEARN BT="); SerialComputer.print(Temperature_BT/10);
                        SerialComputer.print("C gas=");          SerialComputer.println(wuGasPercent);
                    }
                }
            } else {
                phStrictStable = 0;
            }
            phLastGasObs = wuGasPercent;
            phLastAirObs = wuAirPercent;

            if (enDebug) {
                SerialComputer.print("PREC err="); SerialComputer.print(error);
                SerialComputer.print(" P=");        SerialComputer.print(pTerm);
                SerialComputer.print(" I=");        SerialComputer.print(iTerm);
                SerialComputer.print(" gas=");      SerialComputer.print(wuGasPercent);
                SerialComputer.print(" air=");      SerialComputer.println(wuAirPercent);
            }
        }

        gasPercent     = constrain(wuGasPercent, 0, 100);
        airflowPercent = constrain(wuAirPercent, 0, 40);
        phRunSample();
    }
    break;

    } // switch

    // ── Phase 0 + 7: gas lost detection + slew rate + state invariant ──────
    if (phCheckGasLost()) {
        // Gas mất giữa state đốt → quay về IGNITE để retry
        wuState = WU_IGNITE;
        wuIgniteTimer = 0;
        nodeHMI.writeSingleRegister(START_GAS_BTN_W - 1, 1);
        gasPercent = 0;
    }
    // Slew limit: cho phép RECOVERY cut nhanh (HOLDING/PRECISION khi BT vọt)
    bool inRecNow = ((wuState == WU_HOLDING || wuState == WU_PRECISION)
                     && ((int16_t)Temperature_BT > (int16_t)wuTemp_R * 10 + 100
                         || rorBT_smooth > 30));
    phApplySlewLimit(inRecNow);
    phEnforceInvariant();
}
