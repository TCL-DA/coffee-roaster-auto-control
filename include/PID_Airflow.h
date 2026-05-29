// ============================================================
// PID_Airflow.h  â€”  Step Controller + FF Table + Factory Auto-Tune
//
// [1] BÃŒNH THÆ¯á»œNG â€” Step Controller:
//   Má»—i loop: so sÃ¡nh Diff_Air vá»›i setpoint
//   â†’ Vacuum tháº¥p hÆ¡n SP > 5Pa: tÄƒng airflow 1%
//   â†’ Vacuum cao hÆ¡n SP > 5Pa:  giáº£m airflow 1%
//   â†’ Trong Â±5Pa:               giá»¯ nguyÃªn
//   Khi Ä‘á»•i SP â†’ snap Ä‘áº¿n Air% Ä‘Ã£ há»c tá»« FF table
//   Tá»± há»c vÃ  cáº­p nháº­t FF table khi á»•n Ä‘á»‹nh 10s
//
// [2] FACTORY AUTO-TUNE â€” khi báº¥m AUTO_PID_AIR_TU_R:
//   MÃ¡y tá»± Ä‘á»™ng quÃ©t Air% tá»« 0 â†’ 100%, bÆ°á»›c 1%, má»—i bÆ°á»›c 3s
//   Ghi láº¡i cáº·p (Air%, Pa trung bÃ¬nh) vÃ o FF table
//   Sau khi xong â†’ lÆ°u SD, táº¯t tuning trÃªn HMI
//   Tá»•ng thá»i gian: ~5 phÃºt
//
// TÃ­ch há»£p (khÃ´ng thay Ä‘á»•i cÃ¡c file khÃ¡c):
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
// Háº°NG Sá»
// ============================================================

const float AIR_DEADBAND    =  3.0f;   // Â±5 Pa â€” vÃ¹ng khÃ´ng Ä‘iá»u chá»‰nh
const float AIR_STEP        =  1.0f;   // % má»—i bÆ°á»›c tÄƒng/giáº£m
const uint32_t AIR_COOL_NEAR_MS  = 3000;  // gáº§n setpoint (error nhá») â†’ step cháº­m
const uint32_t AIR_COOL_FAR_MS   = 1500;  // xa setpoint (error lá»›n) â†’ step nhanh
const float    AIR_COOL_FAR_ERR  = 30.0f; // Pa â€” ngÆ°á»¡ng "xa": error â‰¥ nÃ y â†’ dÃ¹ng FAR_MS
const float AIR_MIN         =  0.0f;
const float AIR_MAX         = 100.0f;

// FF Table
const int   FF_MAX_ENTRIES  = 50;
const float FF_SP_MATCH     =  3.0f;   // 2 SP cÃ¡ch nhau â‰¤3 Pa â†’ cÃ¹ng entry
const float FF_DRIFT_THRESH =  3.0f;   // cáº­p nháº­t khi Air% lá»‡ch â‰¥3%
const char* FF_FILE         = "/pid_ff.txt";
const float SNAP_BUF_DEFAULT = 15.0f;  // buffer Air% máº·c Ä‘á»‹nh khi chÆ°a cÃ³ SD data

// Factory Auto-Tune
const int   FT_STEP_HOLD_SEC =  3;     // giá»¯ má»—i Air% 3s â†’ 101 bÆ°á»›c Ã— 3s = ~5 phÃºt 3s
const int   FT_SETTLE_SEC    =  2;     // Ä‘o Pa á»Ÿ 2 giÃ¢y cuá»‘i sau khi Ä‘Ã£ settle
const int   FT_AIR_START     =  0;     // báº¯t Ä‘áº§u tá»« 0%
const int   FT_AIR_END       = 100;    // káº¿t thÃºc á»Ÿ 100%
const int   FT_AIR_STEP      =  1;     // bÆ°á»›c tÄƒng


// ============================================================
// Cáº¤U TRÃšC Dá»® LIá»†U
// ============================================================

struct FFEntry {
    float sp;       // Vacuum Pa tÆ°Æ¡ng á»©ng
    float air;      // Air% Ä‘Ã£ há»c
    int   count;    // sá»‘ láº§n há»c
};

FFEntry  ffMap[FF_MAX_ENTRIES];
int      ffMapSize  = 0;
bool     ffDirty    = false;
float    pidSnapBuffer = SNAP_BUF_DEFAULT;  // Air% buffer: snap Ä‘áº¿n (target Â± buffer)

// SD task
enum SDCmd : uint8_t { SD_IDLE, SD_LOAD_FF, SD_SAVE_FF };
volatile SDCmd sdPendingCmd = SD_IDLE;

// Tick flag tá»« ISR
volatile bool selfTuneTickEn = false;

// Tráº¡ng thÃ¡i step controller
float    air_current    = 50.0f;
float    prevSetpoint   = -1.0f;  // VS cÅ© â€” xÃ¡c Ä‘á»‹nh hÆ°á»›ng snap
uint32_t stableTimer    = 0;
uint32_t saveTimer      = 0;
uint32_t stepCooldownMs = 0;

// Factory tune state machine
enum FTState : uint8_t {
    FT_IDLE,        // khÃ´ng cháº¡y
    FT_WARMUP,      // Ä‘ang Ä‘áº¿m 10s chá» trÆ°á»›c khi báº¯t Ä‘áº§u
    FT_RUNNING,     // Ä‘ang quÃ©t
    FT_DONE         // xong, chá» lÆ°u SD
};

const int FT_WARMUP_SEC = 15;    // delay 15s sau khi báº¥m tune trÆ°á»›c khi báº¯t Ä‘áº§u quÃ©t

FTState  ftState      = FT_IDLE;
int      ftCurrentAir = 0;       // Air% Ä‘ang set trong lÃºc tune
uint32_t ftTickCount  = 0;       // Ä‘áº¿m giÃ¢y táº¡i má»—i bÆ°á»›c
float    ftPaAccum    = 0.0f;    // tá»•ng Pa tÃ­ch lÅ©y Ä‘á»ƒ láº¥y trung bÃ¬nh
int      ftPaSamples  = 0;       // sá»‘ máº«u Pa Ä‘Ã£ láº¥y
int      ftWarmupCount = 0;      // Ä‘áº¿m giÃ¢y warmup


// ============================================================
// FF MAP â€” TRA Cá»¨U, Há»ŒC, Cáº¬P NHáº¬T
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

// Tra cá»©u Air% cho setpoint sp
// CÃ³ data â†’ tráº£ vá» Air% Ä‘Ã£ há»c  |  KhÃ´ng cÃ³ â†’ Æ°á»›c tÃ­nh tuyáº¿n tÃ­nh
float ffLookup(float sp) {
    int i = ffFind(sp);
    if (i >= 0) return ffMap[i].air;
    return constrain(sp * (100.0f / 120.0f), AIR_MIN, AIR_MAX);
}

// Ghi 1 entry má»›i hoáº·c cáº­p nháº­t entry Ä‘Ã£ cÃ³
// drift â‰¥ FF_DRIFT_THRESH â†’ há»‡ thá»‘ng thay Ä‘á»•i â†’ há»c láº¡i tá»« Ä‘áº§u
// drift nhá»              â†’ moving average bÃ¬nh thÆ°á»ng
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
        // Há»‡ thá»‘ng thay Ä‘á»•i (lÆ°á»›i lá»c, nhiá»‡t Ä‘á»™...) â†’ há»c láº¡i
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
// SD â€” Äá»ŒC / GHI (1 block, khÃ´ng dÃ¹ng printf loop)
// ============================================================

void _ffSaveNow() {
    // FIX: STM32 Arduino máº·c Ä‘á»‹nh KHÃ”NG há»— trá»£ %f trong snprintf
    //      DÃ¹ng dtostrf() Ä‘á»ƒ convert float â†’ string an toÃ n
    char buf[FF_MAX_ENTRIES * 24 + 32];
    int pos = 0;

    // DÃ²ng Ä‘áº§u: snap buffer Air% (prefix "SNAPBUF:" Ä‘á»ƒ phÃ¢n biá»‡t vá»›i FF entry)
    char snapStr[10];
    dtostrf(pidSnapBuffer, 1, 2, snapStr);
    pos += snprintf(buf + pos, sizeof(buf) - pos, "SNAPBUF:%s\n", snapStr);

    for (int i = 0; i < ffMapSize; i++) {
        char spStr[10], airStr[10];
        dtostrf(ffMap[i].sp,  1, 1, spStr);
        dtostrf(ffMap[i].air, 1, 2, airStr);
        pos += snprintf(buf + pos, sizeof(buf) - pos,
                        "%s,%s,%d\n", spStr, airStr, ffMap[i].count);
    }
    SD.remove(FF_FILE);
    File f = SD.open(FF_FILE, FILE_WRITE);
    if (!f) { if(enDebug) SerialComputer.println("FF SAVE ERR"); return; }
    f.write((const uint8_t*)buf, pos);
    f.close();
    ffDirty = false;
    if(enDebug) {
        SerialComputer.print("FF saved: "); SerialComputer.print(ffMapSize);
        SerialComputer.print(" entries, snapBuf="); SerialComputer.println(pidSnapBuffer, 2);
    }
}

void _ffLoadNow() {
    File f = SD.open(FF_FILE, FILE_READ);
    if (!f) { if(enDebug) SerialComputer.println("FF: no file on SD"); return; }
    char buf[FF_MAX_ENTRIES * 24 + 4];
    int len = f.read((uint8_t*)buf, sizeof(buf) - 1);
    f.close();
    if (len <= 0) return;
    buf[len] = '\0';

    // FIX: sscanf %f cÃ³ thá»ƒ khÃ´ng hoáº¡t Ä‘á»™ng trÃªn STM32
    //      DÃ¹ng strtok + atof Ä‘á»ƒ parse an toÃ n
    ffMapSize = 0;
    char* line = strtok(buf, "\n");
    while (line && ffMapSize < FF_MAX_ENTRIES) {
        // DÃ²ng snap buffer
        if (strncmp(line, "SNAPBUF:", 8) == 0) {
            float s = atof(line + 8);
            if (s >= 3.0f && s <= 40.0f) pidSnapBuffer = s;
            line = strtok(NULL, "\n");
            continue;
        }

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
    if(enDebug) {
        SerialComputer.print("FF loaded: "); SerialComputer.print(ffMapSize);
        SerialComputer.print(" entries, snapBuf="); SerialComputer.println(pidSnapBuffer, 2);
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


void _ftCalcSnapFactor();  // forward declaration

// ============================================================
// FACTORY AUTO-TUNE
// ============================================================
//
// Quy trÃ¬nh má»—i bÆ°á»›c Air%:
//   [0 ~ FT_STEP_HOLD_SEC-FT_SETTLE_SEC-1] giÃ¢y: chá» Ã¡p suáº¥t á»•n Ä‘á»‹nh
//   [FT_STEP_HOLD_SEC-FT_SETTLE_SEC .. FT_STEP_HOLD_SEC-1] giÃ¢y: láº¥y máº«u Pa
//   Sau FT_STEP_HOLD_SEC giÃ¢y: ghi entry, tÄƒng Air% lÃªn bÆ°á»›c tiáº¿p
//
// VD FT_STEP_HOLD_SEC=3, FT_SETTLE_SEC=2:
//   GiÃ¢y 0: set Air%, reset tÃ­ch lÅ©y
//   GiÃ¢y 1: chá» á»•n Ä‘á»‹nh (bá» qua)
//   GiÃ¢y 2: báº¯t Ä‘áº§u láº¥y máº«u Pa
//   GiÃ¢y 3: káº¿t thÃºc bÆ°á»›c, ghi entry = Pa trung bÃ¬nh cá»§a giÃ¢y 2~3
// ============================================================

void pidFactoryTuneStart() {
    if (ftState == FT_RUNNING || ftState == FT_WARMUP) return;

    // Háº¡ airflow vá» 0 ngay láº­p tá»©c
    air_current    = 0.0f;
    airflowPercent = 0;

    // Reset progress trÃªn HMI
    tunePercent = 0;

    ftWarmupCount = 0;
    ftState       = FT_WARMUP;

    if(enDebug) { SerialComputer.print("=== FACTORY TUNE: air->0%, scan in "); SerialComputer.print(FT_WARMUP_SEC); SerialComputer.println("s ==="); }
}

void pidFactoryTuneStop() {
    if (ftState == FT_IDLE) return;
    ftState        = FT_IDLE;
    ftWarmupCount  = 0;
    air_current    = 50.0f;
    airflowPercent = 50;
    if(enDebug) SerialComputer.println("=== FACTORY TUNE ABORTED ===");
}

// Gá»i má»—i giÃ¢y tá»« pidSelfTuneTask()
void _ftTick() {
    // --- Warmup countdown ---
    if (ftState == FT_WARMUP) {
        ftWarmupCount++;
        if (ftWarmupCount >= FT_WARMUP_SEC) {
            // Háº¿t warmup â†’ báº¯t Ä‘áº§u quÃ©t
            ffMapSize    = 0;
            ffDirty      = false;
            ftCurrentAir = FT_AIR_START;
            ftTickCount  = 0;
            ftPaAccum    = 0.0f;
            ftPaSamples  = 0;
            ftState      = FT_RUNNING;
            air_current    = (float)FT_AIR_START;
            airflowPercent = FT_AIR_START;
        }
        return;
    }

    if (ftState != FT_RUNNING) return;

    // Set airflow cho bÆ°á»›c hiá»‡n táº¡i
    air_current    = (float)ftCurrentAir;
    airflowPercent = ftCurrentAir;

    // Láº¥y máº«u Pa trong FT_SETTLE_SEC giÃ¢y cuá»‘i cá»§a má»—i bÆ°á»›c
    int settleStart = FT_STEP_HOLD_SEC - FT_SETTLE_SEC;
    if ((int)ftTickCount >= settleStart) {
        float vac = (float)Diff_Air;
        if (vac > 0) {
            ftPaAccum   += vac;
            ftPaSamples++;
        }
    }

    ftTickCount++;

    // Háº¿t thá»i gian giá»¯ â†’ ghi entry vÃ  chuyá»ƒn bÆ°á»›c tiáº¿p
    if ((int)ftTickCount >= FT_STEP_HOLD_SEC) {
        float avgPa = (ftPaSamples > 0) ? (ftPaAccum / ftPaSamples) : 0.0f;

        if (avgPa > 2.0f) {
            // Chá»‰ ghi khi Pa Ä‘o Ä‘Æ°á»£c cÃ³ Ã½ nghÄ©a (>2 Pa)
            ffLearn(avgPa, (float)ftCurrentAir);
            if(enDebug) { SerialComputer.print("FT Air="); SerialComputer.print(ftCurrentAir); SerialComputer.print("% -> Pa="); SerialComputer.println(avgPa, 1); }
        }

        // Reset bá»™ Ä‘áº¿m cho bÆ°á»›c tiáº¿p
        ftTickCount = 0;
        ftPaAccum   = 0.0f;
        ftPaSamples = 0;
        ftCurrentAir += FT_AIR_STEP;

        // Cáº­p nháº­t % tiáº¿n trÃ¬nh lÃªn HMI
        { uint16_t pct = (uint16_t)((ftCurrentAir * 100) / FT_AIR_END);
          if (pct > 100) pct = 100;
          tunePercent = pct; }

        // Kiá»ƒm tra káº¿t thÃºc
        if (ftCurrentAir > FT_AIR_END) {
            ftState = FT_DONE;
            _ftCalcSnapFactor();
            ffDirty = true;
            ffRequestSave();

            // BÃ¡o HMI: xong 100%, táº¯t nÃºt tuning
            tunePercent = 100;
            nodeHMI.writeSingleRegister(AUTO_PID_AIR_TU_W - 1, 0);

            // Tráº£ airflow vá» 50%
            air_current    = 50.0f;
            airflowPercent = 50;
        }
    }
}


// TÃ­nh snap buffer (Air%) tá»« FF table sau khi factory tune xong.
// NguyÃªn lÃ½: muá»‘n step controller bÃ¹ khoáº£ng 20 Pa cuá»‘i cÃ¹ng.
// Äá»™ nháº¡y trung bÃ¬nh (Pa/%) = Pa range / Air range tá»« FF table.
// Buffer Air% = 20 Pa / Ä‘á»™ nháº¡y â†’ step controller bÃ¹ Ä‘Ãºng ~20 Pa.
// Clamp trong [8, 25] %.
void _ftCalcSnapFactor() {
    if (ffMapSize < 2) return;

    float airMin = ffMap[0].air, airMax = ffMap[0].air;
    float paMin  = ffMap[0].sp,  paMax  = ffMap[0].sp;
    for (int i = 1; i < ffMapSize; i++) {
        if (ffMap[i].air < airMin) airMin = ffMap[i].air;
        if (ffMap[i].air > airMax) airMax = ffMap[i].air;
        if (ffMap[i].sp  < paMin)  paMin  = ffMap[i].sp;
        if (ffMap[i].sp  > paMax)  paMax  = ffMap[i].sp;
    }
    float airRange = airMax - airMin;
    float paRange  = paMax  - paMin;
    if (airRange < 5.0f || paRange < 10.0f) return;

    // Pa/% sensitivity â†’ Air% buffer tÆ°Æ¡ng á»©ng 20 Pa
    float sensitivity = paRange / airRange;
    float buf = 20.0f / sensitivity;
    if (buf <  8.0f) buf =  8.0f;
    if (buf > 25.0f) buf = 25.0f;
    pidSnapBuffer = buf;

    if(enDebug) {
        SerialComputer.print("Snap calc: sens="); SerialComputer.print(sensitivity, 2);
        SerialComputer.print("Pa/% -> buf=");    SerialComputer.print(buf, 1);
        SerialComputer.println("%");
    }
}

// ============================================================
// SELF-TUNE â€” há»c khi á»•n Ä‘á»‹nh (chá»‰ cháº¡y khi khÃ´ng factory tune)
// ============================================================

void pidSelfTuneTick() {
    // Factory tune warmup hoáº·c Ä‘ang cháº¡y â†’ dÃ¹ng _ftTick()
    if (ftState == FT_WARMUP || ftState == FT_RUNNING) {
        _ftTick();
        return;
    }
    if (ftState == FT_DONE) {
        ftState = FT_IDLE;
        return;
    }

    // Cháº¿ Ä‘á»™ bÃ¬nh thÆ°á»ng: há»c FF khi á»•n Ä‘á»‹nh 10s
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
// CONTROLLER CHÃNH
// ============================================================

void pidLoadFromSD() {
    sdPendingCmd = SD_LOAD_FF;
    air_current  = 50.0f;
    stableTimer  = 0;
    saveTimer    = 0;
    if(enDebug) SerialComputer.println("AirCtrl: loading FF from SD...");
}

// Gá»i khi báº­t PID hoáº·c khi setpoint thay Ä‘á»•i.
// HÆ°á»›ng snap dá»±a trÃªn VS má»›i so vá»›i VS cÅ© (khÃ´ng dÃ¹ng air_current
// vÃ¬ air_current cÃ³ thá»ƒ Ä‘ang lá»‡ch so vá»›i FF â€” gÃ¢y snap sai chiá»u).
void pidAirflowReset() {
    if (ftState == FT_RUNNING) return;
    float sp     = (float)vacuumSetpoint_R;
    float target = constrain(ffLookup(sp), AIR_MIN, AIR_MAX);

    float snapped = air_current;  // máº·c Ä‘á»‹nh: giá»¯ nguyÃªn, step controller tá»± bÃ¹
    float delta = (prevSetpoint >= 0.0f) ? fabsf(sp - prevSetpoint) : 999.0f;

    if (delta > 30.0f) {
        // Thay Ä‘á»•i lá»›n: snap Ä‘á»ƒ tiáº¿t kiá»‡m thá»i gian há»™i tá»¥
        if (sp > prevSetpoint) {
            snapped = target - pidSnapBuffer;
            snapped = constrain(snapped, air_current, air_current + 20.0f);
        } else {
            snapped = target + pidSnapBuffer;
            snapped = constrain(snapped, AIR_MIN, air_current);
        }
    }
    // |delta| <= 30 Pa: khÃ´ng snap, step controller bÃ¹ tá»« tá»«

    prevSetpoint   = sp;
    air_current    = constrain(snapped, AIR_MIN, AIR_MAX);
    airflowPercent = (int)air_current;
    stableTimer    = 0;
}

// Gá»i má»—i loop tá»« analogIn()
// KhÃ´ng cháº¡y khi Ä‘ang factory tune (ftState != FT_IDLE)
void pidAirflowUpdate(float setpoint, float feedback) {
    if (ftState != FT_IDLE) return;  // factory tune tá»± Ä‘iá»u khiá»ƒn airflow

    float error = setpoint - feedback;

    // Cooldown Ä‘á»™ng: error lá»›n â†’ step nhanh, error nhá» â†’ step cháº­m
    // Linear map: |error| tá»« deadbandâ†’FAR_ERR tÆ°Æ¡ng á»©ng NEAR_MSâ†’FAR_MS
    uint32_t now = millis();
    if (now >= stepCooldownMs) {
        if (error > AIR_DEADBAND) {
            float absErr = error < AIR_COOL_FAR_ERR ? error : AIR_COOL_FAR_ERR;
            float t = (absErr - AIR_DEADBAND) / (AIR_COOL_FAR_ERR - AIR_DEADBAND);
            uint32_t cooldown = (uint32_t)(AIR_COOL_NEAR_MS - t * (AIR_COOL_NEAR_MS - AIR_COOL_FAR_MS));
            air_current = constrain(air_current + AIR_STEP, AIR_MIN, AIR_MAX);
            stepCooldownMs = now + cooldown;
        } else if (error < -AIR_DEADBAND) {
            float absErr = -error < AIR_COOL_FAR_ERR ? -error : AIR_COOL_FAR_ERR;
            float t = (absErr - AIR_DEADBAND) / (AIR_COOL_FAR_ERR - AIR_DEADBAND);
            uint32_t cooldown = (uint32_t)(AIR_COOL_NEAR_MS - t * (AIR_COOL_NEAR_MS - AIR_COOL_FAR_MS));
            air_current = constrain(air_current - AIR_STEP, AIR_MIN, AIR_MAX);
            stepCooldownMs = now + cooldown;
        }
    }
    airflowPercent = (int)air_current;
}

void pidShowHMI() { /* step controller â€” khÃ´ng cÃ³ Kp/Ki/Kd */ }

#endif // PID_AIRFLOW_Hâ™¥
