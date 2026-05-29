#include <Adafruit_MCP4725.h>

Adafruit_MCP4725 dac_airflow; // DAC cho lưu lượng không khí
Adafruit_MCP4725 dac_gas;     // DAC cho khí gas

float smoothedAirflowAI = 0;
float smoothedDrumAI = 0;
float smoothedGasAI = 0;

#define AI_CAL_FILE              "/ai_cal.txt"
#define AI_CAL_MIN_RAW           500
#define AI_CAL_MAX_RAW           4095
#define AI_CAL_MIN_SPAN_RAW      80
#define AI_CAL_LOW_PERCENT       8
#define AI_CAL_HIGH_PERCENT      90
#define AI_CAL_STABLE_MS         12000UL
#define AI_CAL_DELTA_RAW         8
#define AI_CAL_MARGIN_RAW        5
#define AI_CAL_SAVE_INTERVAL_MS  30000UL
#define AI_PERCENT_FULL_MARGIN   8
#define AI_PERCENT_FULL_PERCENT  98

static uint16_t aiCalMinRaw[3] = {0, 0, 0};
static uint16_t aiCalStableLowRaw[3] = {0, 0, 0};
static uint16_t aiCalStableHighRaw[3] = {0, 0, 0};
static uint32_t aiCalStableLowMillis[3] = {0, 0, 0};
static uint32_t aiCalStableHighMillis[3] = {0, 0, 0};
static uint32_t aiCalLastSaveMillis = 0;
static bool aiCalSavePending = false;

static bool analogCalValidRange(uint16_t minRaw, uint16_t maxRaw) {
    return maxRaw >= AI_CAL_MIN_RAW && maxRaw <= AI_CAL_MAX_RAW && maxRaw > minRaw && (maxRaw - minRaw) >= AI_CAL_MIN_SPAN_RAW;
}

static int16_t analogPercentFromRaw(uint16_t rawValue, float smoothedRaw, uint16_t minRaw, uint16_t maxRaw) {
    if (!analogCalValidRange(minRaw, maxRaw)) return 0;

    uint16_t span = maxRaw - minRaw;

    // Chốt biên theo raw tức thời để EMA không làm VR max bị kẹt ở 99%.
    if (rawValue <= minRaw + AI_PERCENT_FULL_MARGIN) return 0;
    if (rawValue >= maxRaw) return 100;
    if (rawValue + AI_PERCENT_FULL_MARGIN >= maxRaw) return 100;
    if ((uint32_t)(rawValue - minRaw) * 100UL >= (uint32_t)span * AI_PERCENT_FULL_PERCENT) return 100;
    if (smoothedRaw <= (float)(minRaw + 3)) return 0;

    float adjustedRaw = smoothedRaw - (float)minRaw;
    return constrain((int16_t)((adjustedRaw * 100.0f + ((float)span / 2.0f)) / (float)span), 0, 100);
}

void analogCalLoadFromSD() {
    aiCalMinRaw[0] = 0;
    aiCalMinRaw[1] = 0;
    aiCalMinRaw[2] = 0;
    aiCalStableLowRaw[0] = aiCalStableLowRaw[1] = aiCalStableLowRaw[2] = 0;
    aiCalStableHighRaw[0] = aiCalStableHighRaw[1] = aiCalStableHighRaw[2] = 0;
    aiCalStableLowMillis[0] = aiCalStableLowMillis[1] = aiCalStableLowMillis[2] = 0;
    aiCalStableHighMillis[0] = aiCalStableHighMillis[1] = aiCalStableHighMillis[2] = 0;

    if (!chSDFlag || !SD.exists(AI_CAL_FILE)) return;

    File f = SD.open(AI_CAL_FILE, FILE_READ);
    if (!f) return;

    char line[80];
    size_t len = f.readBytesUntil('\n', line, sizeof(line) - 1);
    line[len] = '\0';
    f.close();

    uint16_t airMin = 0, airMax = 0, drumMin = 0, drumMax = 0, gasMin = 0, gasMax = 0;
    int fields = sscanf(line, "%hu %hu %hu %hu %hu %hu", &airMin, &airMax, &drumMin, &drumMax, &gasMin, &gasMax);

    if (fields == 3) {
        uint16_t oldAirMax = airMin;
        uint16_t oldDrumMax = airMax;
        uint16_t oldGasMax = drumMin;
        airMax = oldAirMax;
        drumMax = oldDrumMax;
        gasMax = oldGasMax;
        airMin = drumMin = gasMin = 0;
    }

    if (fields == 3 || fields == 6) {
        if (analogCalValidRange(airMin, airMax)) {
            aiCalMinRaw[0] = airMin;
            CH1AInMax = airMax;
        }
        if (analogCalValidRange(drumMin, drumMax)) {
            aiCalMinRaw[1] = drumMin;
            CH2AInMax = drumMax;
        }
        if (analogCalValidRange(gasMin, gasMax)) {
            aiCalMinRaw[2] = gasMin;
            CH3AInMax = gasMax;
        }
    }

    if (enDebug) {
        SerialComputer.print("AI CAL loaded: air=");
        SerialComputer.print(aiCalMinRaw[0]);
        SerialComputer.print("-");
        SerialComputer.print(CH1AInMax);
        SerialComputer.print(" drum=");
        SerialComputer.print(aiCalMinRaw[1]);
        SerialComputer.print("-");
        SerialComputer.print(CH2AInMax);
        SerialComputer.print(" gas=");
        SerialComputer.print(aiCalMinRaw[2]);
        SerialComputer.print("-");
        SerialComputer.println(CH3AInMax);
    }
}

static void analogCalTrackRange(uint8_t channel, uint16_t rawValue, uint16_t *maxValue) {
    if (channel >= 3 || !analogCalValidRange(aiCalMinRaw[channel], *maxValue)) return;

    uint32_t now = millis();
    uint16_t *minValue = &aiCalMinRaw[channel];
    uint16_t span = *maxValue - *minValue;
    uint16_t lowRaw = *minValue + (uint16_t)(((uint32_t)span * AI_CAL_LOW_PERCENT) / 100);
    uint16_t highRaw = *minValue + (uint16_t)(((uint32_t)span * AI_CAL_HIGH_PERCENT) / 100);

    if (rawValue <= lowRaw) {
        // Tự học đáy VR khi tín hiệu thấp ổn định, tránh lấy một xung nhiễu làm mốc 0%.
        if (aiCalStableLowMillis[channel] == 0 || abs((int)rawValue - (int)aiCalStableLowRaw[channel]) > 3) {
            aiCalStableLowRaw[channel] = rawValue;
            aiCalStableLowMillis[channel] = now;
        } else if (now - aiCalStableLowMillis[channel] >= AI_CAL_STABLE_MS) {
            uint16_t learnedMin = (aiCalStableLowRaw[channel] > AI_CAL_MARGIN_RAW) ? aiCalStableLowRaw[channel] - AI_CAL_MARGIN_RAW : 0;
            if (learnedMin + AI_CAL_MIN_SPAN_RAW < *maxValue && abs((int)learnedMin - (int)(*minValue)) >= AI_CAL_DELTA_RAW) {
                *minValue = learnedMin;
                aiCalSavePending = true;

                if (enDebug) {
                    SerialComputer.print("AI CAL updated ch");
                    SerialComputer.print(channel + 1);
                    SerialComputer.print(" min=");
                    SerialComputer.println(learnedMin);
                }
            }
            aiCalStableLowMillis[channel] = now;
        }
    }

    if (rawValue < highRaw) return;

    // Tự học đỉnh VR khi tín hiệu cao ổn định, tránh bị một đỉnh nhiễu làm kẹt 100%.
    if (aiCalStableHighMillis[channel] == 0 || abs((int)rawValue - (int)aiCalStableHighRaw[channel]) > 3) {
        aiCalStableHighRaw[channel] = rawValue;
        aiCalStableHighMillis[channel] = now;
        return;
    }

    if (now - aiCalStableHighMillis[channel] < AI_CAL_STABLE_MS) return;

    uint16_t learnedMax = aiCalStableHighRaw[channel] + AI_CAL_MARGIN_RAW;
    if (learnedMax > AI_CAL_MAX_RAW) learnedMax = AI_CAL_MAX_RAW;

    if (learnedMax > *minValue + AI_CAL_MIN_SPAN_RAW && abs((int)learnedMax - (int)(*maxValue)) >= AI_CAL_DELTA_RAW) {
        *maxValue = learnedMax;
        aiCalSavePending = true;
        aiCalStableHighMillis[channel] = now;

        if (enDebug) {
            SerialComputer.print("AI CAL updated ch");
            SerialComputer.print(channel + 1);
            SerialComputer.print(" max=");
            SerialComputer.println(learnedMax);
        }
    }
}

void analogCalProcessSD() {
    if (!aiCalSavePending || !chSDFlag) return;

    uint32_t now = millis();
    if (aiCalLastSaveMillis != 0 && now - aiCalLastSaveMillis < AI_CAL_SAVE_INTERVAL_MS) return;

    SD.remove(AI_CAL_FILE);
    File f = SD.open(AI_CAL_FILE, FILE_WRITE);
    if (!f) return;

    f.print(aiCalMinRaw[0]); f.print(' ');
    f.print(CH1AInMax); f.print(' ');
    f.print(aiCalMinRaw[1]); f.print(' ');
    f.print(CH2AInMax); f.print(' ');
    f.print(aiCalMinRaw[2]); f.print(' ');
    f.println(CH3AInMax);
    f.close();

    aiCalLastSaveMillis = now;
    aiCalSavePending = false;

    if (enDebug) SerialComputer.println("AI CAL saved");
}


void analogConfig() {
    // Địa chỉ cho các module MCP4725
#if MACHINE_HAS_GAS_CONTROL
    dac_gas.begin(0x61);      // Cấu hình cho DAC khí gas (địa chỉ 0x61)

#endif
#if MACHINE_HAS_AIRFLOW_CONTROL
    dac_airflow.begin(0x60);  // Cấu hình cho DAC lưu lượng không khí (địa chỉ 0x60)

#endif
    SerialComputer.println("=> Analog OK");
}

void analogOut() {
    // ── Slew rate limiter cho gas ────────────────────────────────
    static float gasCurrent = 0;
    static bool  gasFirstRun = true;
    static uint32_t lastGasTime = 0;

    // Fix #2: boot init — snap về gasPercent thực tế, tránh ramp từ 0
    if (gasFirstRun) {
        gasCurrent   = (float)gasPercent;
        gasFirstRun  = false;
        lastGasTime  = millis();
    }

    uint32_t now = millis();
    float dt = (float)(now - lastGasTime);
    lastGasTime = now;

    // Fix #1: bypass khi relay gas đóng (START_GAS_BTN_R == 0)
    // → snap ngay về gasPercent, không để state bị stale khi bật lại
    if (START_GAS_BTN_R == 0) {
        gasCurrent = (float)gasPercent;
    } else {
        float maxDrop = 0.02f * dt;      // giảm tối đa: 100% / 5s
        float maxRise = 0.033333f * dt;  // tăng tối đa: 100% / 3s
        if ((float)gasPercent < gasCurrent)
            gasCurrent = max((float)gasPercent, gasCurrent - maxDrop);
        else
            gasCurrent = min((float)gasPercent, gasCurrent + maxRise);
    }
#if MACHINE_HAS_GAS_CONTROL

    // Tính toán giá trị DAC cho khí gas dựa trên phần trăm và maxGasSet_R
    int mapDAC_gas = map((int)gasCurrent, 0, 100, 0, (4095 * maxGasSet_R) / 100);
    dac_gas.setVoltage(mapDAC_gas, false); // Gửi giá trị đến DAC cho khí gas

#else
    gasPercent = 0;
#endif
#if MACHINE_HAS_AIRFLOW_CONTROL

    // Tính toán giá trị DAC cho lưu lượng không khí dựa trên phần trăm
    int mapDAC_airflow = map(airflowPercent, 0, 100, 0, 4095);
    dac_airflow.setVoltage(mapDAC_airflow, false); // Gửi giá trị đến DAC cho lưu lượng không khí

#endif
}

// void analogIn() {
//     // Đọc và làm mượt tín hiệu lưu lượng không khí
//     if (naviSourceAIR == SOURCE_AI_VR) {
//         int rawAirflowAI = analogRead(CH1_ANALOG); 
//         smoothedAirflowAI = (alpha * rawAirflowAI) + (1 - alpha) * smoothedAirflowAI;
//         airflowPercent = constrain(map(smoothedAirflowAI, 0, CH1AInMax, 0, 100), 0, 100);
//     } else if (naviSourceAIR == SOURCE_AI_PC) {
//         airflowPercent = airflowPC;
//     }

//     // Đọc và làm mượt tín hiệu trống
//     if (naviSourceDRUM == SOURCE_AI_VR) {
//         int rawDrumAI = analogRead(CH2_ANALOG);
//         smoothedDrumAI = (alpha * rawDrumAI) + (1 - alpha) * smoothedDrumAI;
//         drumPercent = constrain(map(smoothedDrumAI, 0, CH2AInMax, 0, 100), 0, 100);
//     } else if (naviSourceDRUM == SOURCE_AI_PC) {
//         drumPercent = drumPC;
//     }

//     // Đọc và làm mượt tín hiệu khí gas
//     if (naviSourceGAS == SOURCE_AI_VR) {
//         int rawGasAI = analogRead(CH3_ANALOG);
//         smoothedGasAI = (alpha * rawGasAI) + (1 - alpha) * smoothedGasAI;
//         gasPercent = constrain(map(smoothedGasAI, 0, CH3AInMax, 0, 100), 0, 100);
//     } else if (naviSourceGAS == SOURCE_AI_PC) {
//         gasPercent = gasPC;
//     }
// }

void analogIn() {

    // ── Điều khiển lưu lượng không khí ──────────────────────────
    if (naviSourceAIR == SOURCE_AI_AUTO) {
        // Chế độ AUTO: vacuumSetFlag_R và vacuumSetpoint_R được set bởi calibProgram()
        // vacuumSetFlag_R=1 → PID điều khiển airflow theo setpoint từ SD profile
        // vacuumSetFlag_R=0 → airflowPercent đã được calibProgram() gán trực tiếp từ SD
#if MACHINE_HAS_VACUUM_SENSOR
        if (vacuumSetFlag_R == 1) {
            pidAirflowUpdate((float)vacuumSetpoint_R, (float)Diff_Air);
        }
#endif
    } else {
        // Chế độ thủ công (VR hoặc PC): vacuumSetFlag_R từ HMI quyết định
        if (MACHINE_HAS_VACUUM_SENSOR && vacuumSetFlag_R == 1) {
            pidAirflowUpdate(vacuumSetpoint_R, Diff_Air);
        } else if (naviSourceAIR == SOURCE_AI_VR) {
#ifdef SOURCE_AI_VR_FROM_HMI
            airflowPercent = constrain(airSpeed_R, 0, 100);
#else
            int rawAirflowAI = analogRead(CH1_ANALOG);
            analogCalTrackRange(0, (uint16_t)rawAirflowAI, &CH1AInMax);
            smoothedAirflowAI = (alpha * rawAirflowAI) + (1 - alpha) * smoothedAirflowAI;
            airflowPercent = analogPercentFromRaw((uint16_t)rawAirflowAI, smoothedAirflowAI, aiCalMinRaw[0], CH1AInMax);
#endif
        } else if (naviSourceAIR == SOURCE_AI_PC) {
            airflowPercent = airflowPC;
        }
    }

    // ── Điều khiển tốc độ trống ──────────────────────────────────
    if (!MACHINE_HAS_DRUM_SPEED_CONTROL) {
        drumPercent = 0;
    } else if (naviSourceDRUM == SOURCE_AI_VR) {
#ifdef SOURCE_AI_VR_FROM_HMI
        drumPercent = constrain(drumSpeed_R, 0, 100);
#else
        int rawDrumAI = analogRead(CH2_ANALOG);
        analogCalTrackRange(1, (uint16_t)rawDrumAI, &CH2AInMax);
        smoothedDrumAI = (alpha * rawDrumAI) + (1 - alpha) * smoothedDrumAI;
        drumPercent = analogPercentFromRaw((uint16_t)rawDrumAI, smoothedDrumAI, aiCalMinRaw[1], CH2AInMax);
#endif
    } else if (naviSourceDRUM == SOURCE_AI_PC) {
        drumPercent = drumPC;
    }

    // ── Điều khiển gas ───────────────────────────────────────────
    if (!MACHINE_HAS_GAS_CONTROL) {
        gasPercent = 0;
    } else if (naviSourceGAS == SOURCE_AI_VR) {
#ifdef SOURCE_AI_VR_FROM_HMI
        gasPercent = constrain(burnerValue_R, 0, 100);
#else
        int rawGasAI = analogRead(CH3_ANALOG);
        analogCalTrackRange(2, (uint16_t)rawGasAI, &CH3AInMax);
        smoothedGasAI = (alpha * rawGasAI) + (1 - alpha) * smoothedGasAI;
        gasPercent = analogPercentFromRaw((uint16_t)rawGasAI, smoothedGasAI, aiCalMinRaw[2], CH3AInMax);
#endif
    } else if (naviSourceGAS == SOURCE_AI_PC) {
        gasPercent = gasPC;
    }
}
