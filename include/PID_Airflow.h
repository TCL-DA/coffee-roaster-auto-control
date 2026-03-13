// ============================================================
// PID_Airflow.h  —  Step Controller + FF Table + Factory Auto-Tune
//
// [1] BÌNH THƯỜNG — Step Controller:
//   Mỗi loop: so sánh Diff_Air với setpoint
//   → Vacuum thấp hơn SP > 5Pa: tăng airflow 1%
//   → Vacuum cao hơn SP > 5Pa:  giảm airflow 1%
//   → Trong ±5Pa:               giữ nguyên
//   Khi đổi SP → snap đến Air% đã học từ FF table
//   Tự học và cập nhật FF table khi ổn định 10s
//
// [2] FACTORY AUTO-TUNE — khi bấm AUTO_PID_AIR_TU_R:
//   Máy tự động quét Air% từ 0 → 100%, bước 1%, mỗi bước 3s
//   Ghi lại cặp (Air%, Pa trung bình) vào FF table
//   Sau khi xong → lưu SD, tắt tuning trên HMI
//   Tổng thời gian: ~5 phút
//
// Tích hợp (không thay đổi các file khác):
//   setup()            : pidLoadFromSD()
//   loop()             : pidSelfTuneTask(); pidSDTask();
//   analogIn()         : if (vacuumSetFlag_R==1) pidAirflowUpdate(vacuumSetpoint_R, Diff_Air);
//   timerPoll_1000ms() : selfTuneTickEn = true;
//   rwMemHMI():
//     if (AUTO_PID_AIR_TU_R != AUTO_PID_AIR_TU_R_CP) {
//         AUTO_PID_AIR_TU_R = AUTO_PID_AIR_TU_R_CP;
//         if (AUTO_PID_AIR_TU_R == 1) pidFactoryTuneStart();
//         else                         pidFactoryTuneStop();
//     }
//     if (vacuumSetFlag_R != vacuumSetFlag_R_CP) {
//         vacuumSetFlag_R = vacuumSetFlag_R_CP;
//         if (vacuumSetFlag_R == 1) pidAirflowReset();
//     }
//     if (vacuumSetpoint_R != vacuumSetpoint_R_CP) {
//         vacuumSetpoint_R = vacuumSetpoint_R_CP;
//         if (vacuumSetFlag_R == 1) pidAirflowReset();
//     }
//   rwHMI_2()          : pidShowHMI()
// ============================================================

#ifndef PID_AIRFLOW_H
#define PID_AIRFLOW_H

#include <SD.h>

// ============================================================
// HẰNG SỐ
// ============================================================

const float AIR_DEADBAND    =  5.0f;   // ±5 Pa — vùng không điều chỉnh
const float AIR_STEP        =  1.0f;   // % mỗi bước tăng/giảm
const float AIR_MIN         =  0.0f;
const float AIR_MAX         = 100.0f;

// FF Table
const int   FF_MAX_ENTRIES  = 50;
const float FF_SP_MATCH     =  3.0f;   // 2 SP cách nhau ≤3 Pa → cùng entry
const float FF_DRIFT_THRESH =  3.0f;   // cập nhật khi Air% lệch ≥3%
const char* FF_FILE         = "/pid_ff.txt";

// Factory Auto-Tune
const int   FT_STEP_HOLD_SEC =  2;     // giữ mỗi Air% 2s → 101 bước × 2s = ~3 phút 22s
const int   FT_SETTLE_SEC    =  1;     // đo Pa ở giây cuối sau khi đã settle
const int   FT_AIR_START     =  0;     // bắt đầu từ 0%
const int   FT_AIR_END       = 100;    // kết thúc ở 100%
const int   FT_AIR_STEP      =  1;     // bước tăng


// ============================================================
// CẤU TRÚC DỮ LIỆU
// ============================================================

struct FFEntry {
    float sp;       // Vacuum Pa tương ứng
    float air;      // Air% đã học
    int   count;    // số lần học
};

FFEntry  ffMap[FF_MAX_ENTRIES];
int      ffMapSize  = 0;
bool     ffDirty    = false;

// SD task
enum SDCmd : uint8_t { SD_IDLE, SD_LOAD_FF, SD_SAVE_FF };
volatile SDCmd sdPendingCmd = SD_IDLE;

// Tick flag từ ISR
volatile bool selfTuneTickEn = false;

// Trạng thái step controller
float    air_current  = 50.0f;
uint32_t stableTimer  = 0;
uint32_t saveTimer    = 0;

// Factory tune state machine
enum FTState : uint8_t {
    FT_IDLE,        // không chạy
    FT_RUNNING,     // đang quét
    FT_DONE         // xong, chờ lưu SD
};

FTState  ftState      = FT_IDLE;
int      ftCurrentAir = 0;       // Air% đang set trong lúc tune
uint32_t ftTickCount  = 0;       // đếm giây tại mỗi bước
float    ftPaAccum    = 0.0f;    // tổng Pa tích lũy để lấy trung bình
int      ftPaSamples  = 0;       // số mẫu Pa đã lấy


// ============================================================
// FF MAP — TRA CỨU, HỌC, CẬP NHẬT
// ============================================================

int ffFind(float sp) {
    int   best     = -1;
    float bestDist = FF_SP_MATCH + 1.0f;
    for (int i = 0; i < ffMapSize; i++) {
        float d = fabsf(ffMap[i].sp - sp);
        if (d < bestDist) { bestDist = d; best = i; }
    }
    return best;
}

// Tra cứu Air% cho setpoint sp
// Có data → trả về Air% đã học  |  Không có → ước tính tuyến tính
float ffLookup(float sp) {
    int i = ffFind(sp);
    if (i >= 0) return ffMap[i].air;
    return constrain(sp * (100.0f / 120.0f), AIR_MIN, AIR_MAX);
}

// Ghi 1 entry mới hoặc cập nhật entry đã có
// drift ≥ FF_DRIFT_THRESH → hệ thống thay đổi → học lại từ đầu
// drift nhỏ              → moving average bình thường
void ffLearn(float sp, float air) {
    int i = ffFind(sp);

    if (i < 0) {
        if (ffMapSize < FF_MAX_ENTRIES) {
            ffMap[ffMapSize++] = {sp, air, 1};
            ffDirty = true;
            if (enDebug) {
                SerialComputer.print("FF NEW  Pa="); SerialComputer.print(sp, 0);
                SerialComputer.print(" Air=");       SerialComputer.print(air, 1);
                SerialComputer.println("%");
            }
        }
        return;
    }

    float drift = fabsf(ffMap[i].air - air);
    if (drift >= FF_DRIFT_THRESH) {
        // Hệ thống thay đổi (lưới lọc, nhiệt độ...) → học lại
        ffMap[i].air   = (ffMap[i].air + air) / 2.0f;
        ffMap[i].count = 2;
        if (enDebug) {
            SerialComputer.print("FF DRIFT Pa="); SerialComputer.print(sp, 0);
            SerialComputer.print(" drift=");      SerialComputer.print(drift, 1);
            SerialComputer.print(" -> Air=");     SerialComputer.print(ffMap[i].air, 1);
            SerialComputer.println("%");
        }
    } else {
        int cnt = min(ffMap[i].count, 30);
        ffMap[i].air   = (ffMap[i].air * cnt + air) / (cnt + 1);
        ffMap[i].count = cnt + 1;
    }
    ffMap[i].sp = (ffMap[i].sp + sp) / 2.0f;
    ffDirty = true;
}


// ============================================================
// SD — ĐỌC / GHI (1 block, không dùng printf loop)
// ============================================================

void _ffSaveNow() {
    // FIX: STM32 Arduino mặc định KHÔNG hỗ trợ %f trong snprintf
    //      Dùng dtostrf() để convert float → string an toàn
    char buf[FF_MAX_ENTRIES * 24 + 4];
    int pos = 0;
    for (int i = 0; i < ffMapSize; i++) {
        char spStr[10], airStr[10];
        dtostrf(ffMap[i].sp,  1, 1, spStr);
        dtostrf(ffMap[i].air, 1, 2, airStr);
        pos += snprintf(buf + pos, sizeof(buf) - pos,
                        "%s,%s,%d\n", spStr, airStr, ffMap[i].count);
    }
    SD.remove(FF_FILE);
    File f = SD.open(FF_FILE, FILE_WRITE);
    if (!f) { SerialComputer.println("FF SAVE ERR"); return; }
    f.write((const uint8_t*)buf, pos);
    f.close();
    ffDirty = false;
    SerialComputer.print("FF saved: ");
    SerialComputer.print(ffMapSize);
    SerialComputer.println(" entries");
}

void _ffLoadNow() {
    File f = SD.open(FF_FILE, FILE_READ);
    if (!f) { SerialComputer.println("FF: no file on SD"); return; }
    char buf[FF_MAX_ENTRIES * 24 + 4];
    int len = f.read((uint8_t*)buf, sizeof(buf) - 1);
    f.close();
    if (len <= 0) return;
    buf[len] = '\0';

    // FIX: sscanf %f có thể không hoạt động trên STM32
    //      Dùng strtok + atof để parse an toàn
    ffMapSize = 0;
    char* line = strtok(buf, "\n");
    while (line && ffMapSize < FF_MAX_ENTRIES) {
        char* c1 = strchr(line, ',');
        if (!c1) { line = strtok(NULL, "\n"); continue; }
        char* c2 = strchr(c1 + 1, ',');
        if (!c2) { line = strtok(NULL, "\n"); continue; }

        *c1 = '\0';
        *c2 = '\0';

        float sp  = atof(line);
        float air = atof(c1 + 1);
        int   cnt = atoi(c2 + 1);

        if (sp > 0 && air >= 0 && cnt > 0)
            ffMap[ffMapSize++] = {sp, air, cnt};

        line = strtok(NULL, "\n");
    }
    ffDirty = false;
    SerialComputer.print("FF loaded: ");
    SerialComputer.print(ffMapSize);
    SerialComputer.println(" entries");
    if (enDebug) {
        for (int i = 0; i < ffMapSize; i++) {
            SerialComputer.print("  Pa=");  SerialComputer.print(ffMap[i].sp, 0);
            SerialComputer.print(" Air=");  SerialComputer.print(ffMap[i].air, 1);
            SerialComputer.print("% n=");   SerialComputer.println(ffMap[i].count);
        }
    }
}

void pidSDTask() {
    if (sdPendingCmd == SD_IDLE) return;
    SDCmd cmd    = sdPendingCmd;
    sdPendingCmd = SD_IDLE;
    if      (cmd == SD_SAVE_FF) _ffSaveNow();
    else if (cmd == SD_LOAD_FF) _ffLoadNow();
}

void ffRequestSave() { if (ffDirty) sdPendingCmd = SD_SAVE_FF; }


// ============================================================
// FACTORY AUTO-TUNE
// ============================================================
//
// Quy trình mỗi bước Air%:
//   [0 ~ FT_STEP_HOLD_SEC-FT_SETTLE_SEC-1] giây: chờ áp suất ổn định
//   [FT_STEP_HOLD_SEC-FT_SETTLE_SEC .. FT_STEP_HOLD_SEC-1] giây: lấy mẫu Pa
//   Sau FT_STEP_HOLD_SEC giây: ghi entry, tăng Air% lên bước tiếp
//
// VD FT_STEP_HOLD_SEC=3, FT_SETTLE_SEC=2:
//   Giây 0: set Air%, reset tích lũy
//   Giây 1: chờ ổn định (bỏ qua)
//   Giây 2: bắt đầu lấy mẫu Pa
//   Giây 3: kết thúc bước, ghi entry = Pa trung bình của giây 2~3
// ============================================================

void pidFactoryTuneStart() {
    if (ftState == FT_RUNNING) return;

    // Xóa bảng cũ — factory tune ghi đè hoàn toàn
    ffMapSize = 0;
    ffDirty   = false;

    ftCurrentAir = FT_AIR_START;
    ftTickCount  = 0;
    ftPaAccum    = 0.0f;
    ftPaSamples  = 0;
    ftState      = FT_RUNNING;

    // Set airflow về 0 ngay
    air_current    = (float)FT_AIR_START;
    airflowPercent = FT_AIR_START;

    SerialComputer.println("=== FACTORY TUNE START ===");
    SerialComputer.print("Quét Air% ");
    SerialComputer.print(FT_AIR_START);
    SerialComputer.print(" -> ");
    SerialComputer.print(FT_AIR_END);
    SerialComputer.print("%, mỗi bước ");
    SerialComputer.print(FT_STEP_HOLD_SEC);
    SerialComputer.println("s");
}

void pidFactoryTuneStop() {
    if (ftState == FT_IDLE) return;
    ftState        = FT_IDLE;
    air_current    = 50.0f;
    airflowPercent = 50;
    SerialComputer.println("=== FACTORY TUNE ABORTED ===");
}

// Gọi mỗi giây từ pidSelfTuneTask()
void _ftTick() {
    if (ftState != FT_RUNNING) return;

    // Set airflow cho bước hiện tại
    air_current    = (float)ftCurrentAir;
    airflowPercent = ftCurrentAir;

    // Lấy mẫu Pa trong FT_SETTLE_SEC giây cuối của mỗi bước
    int settleStart = FT_STEP_HOLD_SEC - FT_SETTLE_SEC;
    if ((int)ftTickCount >= settleStart) {
        float vac = (float)Diff_Air;
        if (vac > 0) {
            ftPaAccum   += vac;
            ftPaSamples++;
        }
    }

    ftTickCount++;

    // Hết thời gian giữ → ghi entry và chuyển bước tiếp
    if ((int)ftTickCount >= FT_STEP_HOLD_SEC) {
        float avgPa = (ftPaSamples > 0) ? (ftPaAccum / ftPaSamples) : 0.0f;

        if (avgPa > 2.0f) {
            // Chỉ ghi khi Pa đo được có ý nghĩa (>2 Pa)
            ffLearn(avgPa, (float)ftCurrentAir);
            SerialComputer.print("FT Air=");
            SerialComputer.print(ftCurrentAir);
            SerialComputer.print("% -> Pa=");
            SerialComputer.println(avgPa, 1);
        }

        // Reset bộ đếm cho bước tiếp
        ftTickCount = 0;
        ftPaAccum   = 0.0f;
        ftPaSamples = 0;
        ftCurrentAir += FT_AIR_STEP;

        // Kiểm tra kết thúc
        if (ftCurrentAir > FT_AIR_END) {
            ftState = FT_DONE;
            SerialComputer.println("=== FACTORY TUNE DONE ===");
            SerialComputer.print(ffMapSize);
            SerialComputer.println(" entries saved to SD");
            ffDirty = true;
            ffRequestSave();

            // Báo HMI tắt nút tuning
            nodeHMI.writeSingleRegister(AUTO_PID_AIR_TU_W - 1, 0);

            // Trả airflow về 50%
            air_current    = 50.0f;
            airflowPercent = 50;
        }
    }
}


// ============================================================
// SELF-TUNE — học khi ổn định (chỉ chạy khi không factory tune)
// ============================================================

void pidSelfTuneTick() {
    // Factory tune đang chạy → dùng _ftTick() thay thế
    if (ftState == FT_RUNNING) {
        _ftTick();
        return;
    }
    if (ftState == FT_DONE) {
        ftState = FT_IDLE;
        return;
    }

    // Chế độ bình thường: học FF khi ổn định 10s
    if (vacuumSetFlag_R != 1) return;

    float err = fabsf((float)Diff_Air - (float)vacuumSetpoint_R);
    if (err <= AIR_DEADBAND) {
        stableTimer++;
        saveTimer++;
        if (stableTimer == 10)
            ffLearn((float)vacuumSetpoint_R, air_current);
        if (saveTimer >= 60 && ffDirty) {
            ffRequestSave();
            saveTimer = 0;
        }
    } else {
        stableTimer = 0;
    }
}

void pidSelfTuneTask() {
    if (!selfTuneTickEn) return;
    selfTuneTickEn = false;
    pidSelfTuneTick();
}


// ============================================================
// CONTROLLER CHÍNH
// ============================================================

void pidLoadFromSD() {
    sdPendingCmd = SD_LOAD_FF;
    air_current  = 50.0f;
    stableTimer  = 0;
    saveTimer    = 0;
    SerialComputer.println("AirCtrl: loading FF from SD...");
}

// Gọi khi bật PID hoặc khi setpoint thay đổi
// Snap đến gần Air% đã học, để step controller bù phần còn lại
// Tránh vọt lố do thay đổi Air% quá đột ngột
void pidAirflowReset() {
    if (ftState == FT_RUNNING) return;  // không reset khi đang factory tune
    float ff       = ffLookup((float)vacuumSetpoint_R);
    float target   = constrain(ff, AIR_MIN, AIR_MAX);

    // Chỉ snap 40% khoảng cách → giảm overshoot
    // Step controller sẽ bù 60% còn lại từ từ (±1%/loop)
    // Tune: 0.4 = ít vọt, settle chậm | 0.7 = cân bằng | 0.9 = nhanh hơn, vọt nhiều hơn
    air_current    = air_current + 0.4f * (target - air_current);
    air_current    = constrain(air_current, AIR_MIN, AIR_MAX);
    airflowPercent = (int)air_current;
    stableTimer    = 0;

    SerialComputer.print("AirCtrl SP=");
    SerialComputer.print(vacuumSetpoint_R);
    SerialComputer.print(" -> Air=");
    SerialComputer.print(air_current, 1);
    int idx = ffFind((float)vacuumSetpoint_R);
    SerialComputer.print("% (");
    SerialComputer.print(idx >= 0 ? "learned" : "estimated");
    SerialComputer.println(")");
}

// Gọi mỗi loop từ analogIn()
// Không chạy khi đang factory tune (ftState != FT_IDLE)
void pidAirflowUpdate(float setpoint, float feedback) {
    if (ftState != FT_IDLE) return;  // factory tune tự điều khiển airflow

    float error = setpoint - feedback;

    // ── Damping: không bước thêm khi vacuum đang tự hướng về SP ──
    // Sau khi snap FF, vacuum có quán tính — nếu đang di chuyển
    // đúng hướng thì đứng yên chờ, không đẩy thêm → giảm vọt lố
    static float prev_error = 0;
    bool approaching = (error > 0 && error < prev_error) ||   // vacuum đang tăng về SP
                       (error < 0 && error > prev_error);     // vacuum đang giảm về SP
    prev_error = error;

    if (!approaching) {
        if (error > AIR_DEADBAND) {
            air_current = constrain(air_current + AIR_STEP, AIR_MIN, AIR_MAX);
        } else if (error < -AIR_DEADBAND) {
            air_current = constrain(air_current - AIR_STEP, AIR_MIN, AIR_MAX);
        }
    }
    airflowPercent = (int)air_current;

    if (enDebug) {
        SerialComputer.print("AC SP=");  SerialComputer.print(setpoint, 0);
        SerialComputer.print(" V=");     SerialComputer.print(feedback, 0);
        SerialComputer.print(" e=");     SerialComputer.print(error, 0);
        SerialComputer.print(" A=");     SerialComputer.print(airflowPercent);
        SerialComputer.println("%");
    }
}

void pidShowHMI() { /* step controller — không có Kp/Ki/Kd */ }

#endif // PID_AIRFLOW_H♥