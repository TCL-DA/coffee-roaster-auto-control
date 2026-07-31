#include <Adafruit_MCP4725.h>

Adafruit_MCP4725 dac_airflow; // DAC cho lưu lượng không khí
Adafruit_MCP4725 dac_gas;     // DAC cho khí gas

float smoothedAirflowAI = 0;
float smoothedDrumAI = 0;
float smoothedGasAI = 0;

#define DAC_RESOLUTION (8) // Đặt độ phân giải cho DAC (5 đến 9)

// Hệ số lọc lũy thừa, dùng để làm mượt tín hiệu đầu vào (giá trị thấp -> tín hiệu mượt hơn)
const float alpha = 0.5;

void analogConfig() {
    // Địa chỉ cho các module MCP4725
    dac_gas.begin(0x61);      // Cấu hình cho DAC khí gas (địa chỉ 0x61)
    dac_airflow.begin(0x60);  // Cấu hình cho DAC lưu lượng không khí (địa chỉ 0x60)
    SerialComputer.println("=> Analog OK");
}

void analogOut() {
    // Tính toán giá trị DAC cho khí gas dựa trên phần trăm và maxGasSet_R
    int mapDAC_gas = map(gasPercent, 0, 100, 0, (4095 * maxGasSet_R) / 100);
    dac_gas.setVoltage(mapDAC_gas, false); // Gửi giá trị đến DAC cho khí gas

    // Tính toán giá trị DAC cho lưu lượng không khí dựa trên phần trăm
    int mapDAC_airflow = map(airflowPercent, 0, 100, 0, 4095);
    dac_airflow.setVoltage(mapDAC_airflow, false); // Gửi giá trị đến DAC cho lưu lượng không khí
}

void analogIn() {
    // Đọc và làm mượt tín hiệu lưu lượng không khí
    // Đọc và làm mượt tín hiệu lưu lượng không khí
    if (naviSourceAIR == SOURCE_AI_VR) {
        // int rawAirflowAI = analogRead(CH1_ANALOG); // Đọc giá trị tín hiệu thô từ kênh analog CH1
        // smoothedAirflowAI = (alpha * rawAirflowAI) + (1 - alpha) * smoothedAirflowAI; // Làm mượt tín hiệu bằng bộ lọc lũy thừa
        // airflowPercent = constrain(map(smoothedAirflowAI, 0, CH1AInMax, 0, 100), 0, 100); // Chuyển đổi giá trị tín hiệu thành phần trăm và giới hạn trong khoảng 0-100
        airflowPercent = airSpeed_R; //Lấy giá trị phần trăm từ HMI
    } else if (naviSourceAIR == SOURCE_AI_PC) {
        airflowPercent = airflowPC; // Lấy giá trị phần trăm từ nguồn PC
    }

    // Đọc và làm mượt tín hiệu trống
    if (naviSourceDRUM == SOURCE_AI_VR) {
        // int rawDrumAI = analogRead(CH2_ANALOG);
        // smoothedDrumAI = (alpha * rawDrumAI) + (1 - alpha) * smoothedDrumAI;
        // drumPercent = constrain(map(smoothedDrumAI, 0, CH2AInMax, 0, 100), 0, 100);
        drumPercent = drumSpeed_R; // Lấy giá trị phần trăm từ HMI
    } else if (naviSourceDRUM == SOURCE_AI_PC) {
        drumPercent = drumPC;
    }

    // Đọc và làm mượt tín hiệu khí gas
    if (naviSourceGAS == SOURCE_AI_VR) {
        // int rawGasAI = analogRead(CH3_ANALOG);
        // smoothedGasAI = (alpha * rawGasAI) + (1 - alpha) * smoothedGasAI;
        // gasPercent = constrain(map(smoothedGasAI, 0, CH3AInMax, 0, 100), 0, 100);
        gasPercent = burnerValue_R; // Lấy giá trị phần trăm từ HMI
    } else if (naviSourceGAS == SOURCE_AI_PC) {
        gasPercent = gasPC;
    }
}