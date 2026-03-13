#include <Adafruit_MCP4725.h>

Adafruit_MCP4725 dac_airflow; // DAC cho lưu lượng không khí
Adafruit_MCP4725 dac_gas;     // DAC cho khí gas

float smoothedAirflowAI = 0;
float smoothedDrumAI = 0;
float smoothedGasAI = 0;


void analogConfig() {
    // Địa chỉ cho các module MCP4725
    dac_gas.begin(0x61);      // Cấu hình cho DAC khí gas (địa chỉ 0x61)
    dac_airflow.begin(0x60);  // Cấu hình cho DAC lưu lượng không khí (địa chỉ 0x60)
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
        float maxDrop = 0.01f * dt;  // giảm tối đa: 100% / 10s
        float maxRise = 0.02f * dt;  // tăng tối đa: 100% / 5s
        if ((float)gasPercent < gasCurrent)
            gasCurrent = max((float)gasPercent, gasCurrent - maxDrop);
        else
            gasCurrent = min((float)gasPercent, gasCurrent + maxRise);
    }

    // Tính toán giá trị DAC cho khí gas dựa trên phần trăm và maxGasSet_R
    int mapDAC_gas = map((int)gasCurrent, 0, 100, 0, (4095 * maxGasSet_R) / 100);
    dac_gas.setVoltage(mapDAC_gas, false); // Gửi giá trị đến DAC cho khí gas

    // Tính toán giá trị DAC cho lưu lượng không khí dựa trên phần trăm
    int mapDAC_airflow = map(airflowPercent, 0, 100, 0, 4095);
    dac_airflow.setVoltage(mapDAC_airflow, false); // Gửi giá trị đến DAC cho lưu lượng không khí
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
        // Chế độ AUTO (rang tự động từ SD profile)
        // autoVacPIDEn/autoVacSP là biến nội bộ — không bị rwMemHMI() ghi đè
        // autoVacPIDEn=true  → PID áp suất với setpoint từ profile SD
        // autoVacPIDEn=false → airflowPercent đã được calibProgram() gán trực tiếp từ SD
        if (autoVacPIDEn) {
            pidAirflowUpdate((float)autoVacSP, Diff_Air);
        }
    } else {
        // Chế độ thủ công (VR hoặc PC): vacuumSetFlag_R từ HMI quyết định
        if (vacuumSetFlag_R == 1) {
            pidAirflowUpdate(vacuumSetpoint_R, Diff_Air);
        } else if (naviSourceAIR == SOURCE_AI_VR) {
            int rawAirflowAI = analogRead(CH1_ANALOG);
            smoothedAirflowAI = (alpha * rawAirflowAI) + (1 - alpha) * smoothedAirflowAI;
            airflowPercent = constrain(map(smoothedAirflowAI, 0, CH1AInMax, 0, 100), 0, 100);
        } else if (naviSourceAIR == SOURCE_AI_PC) {
            airflowPercent = airflowPC;
        }
    }

    // ── Điều khiển tốc độ trống ──────────────────────────────────
    if (naviSourceDRUM == SOURCE_AI_VR) {
        int rawDrumAI = analogRead(CH2_ANALOG);
        smoothedDrumAI = (alpha * rawDrumAI) + (1 - alpha) * smoothedDrumAI;
        drumPercent = constrain(map(smoothedDrumAI, 0, CH2AInMax, 0, 100), 0, 100);
    } else if (naviSourceDRUM == SOURCE_AI_PC) {
        drumPercent = drumPC;
    }

    // ── Điều khiển gas ───────────────────────────────────────────
    if (naviSourceGAS == SOURCE_AI_VR) {
        int rawGasAI = analogRead(CH3_ANALOG);
        smoothedGasAI = (alpha * rawGasAI) + (1 - alpha) * smoothedGasAI;
        gasPercent = constrain(map(smoothedGasAI, 0, CH3AInMax, 0, 100), 0, 100);
    } else if (naviSourceGAS == SOURCE_AI_PC) {
        gasPercent = gasPC;
    }
}