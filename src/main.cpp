// Định nghĩa các thư viện cần thiết
#include <Arduino.h>
#include <HardwareSerial.h>
#include <ModbusMaster.h>
#include <Wire.h>
#include <Adafruit_MCP4725.h>
#include <ModbusRTU.h>  // Modbus slave ESP MTlab
#include <SPI.h>
#include <SD.h>
#include "STM32TimerInterrupt.h"
#include <SimpleKalmanFilter.h>

// Kiểm tra nền tảng STM32
#if !( defined(STM32F0) || defined(STM32F1) || defined(STM32F2) || defined(STM32F3)  ||defined(STM32F4) || defined(STM32F7) || \
  defined(STM32L0) || defined(STM32L1) || defined(STM32L4) || defined(STM32H7)  ||defined(STM32G0) || defined(STM32G4) || \
  defined(STM32WB) || defined(STM32MP1) || defined(STM32L5) )
  #error Code này chỉ chạy trên nền tảng STM32! Kiểm tra Tools->Board.
#endif

// Định nghĩa các file header
#include "Define.h"
#include "IOConfig.h"
#include "PID_Airflow.h"
#include "AnalogConfig.h"
#include "ScaleFeeder.h"
#include "Modbus_Slave.h"
#include "Modbus_Master.h"
#include "Program.h"

void debug();

void setup() {
  SerialComputer.begin(9600);
  ConfigIO();
  analogConfig();
  ModbusRS485Config();
  configTimer();
  checkError();
  rwMemHMI();
  ModbusSlaveConfig();
  pidLoadFromSD();
  reset_update();
}

void loop() {
  timeMillis = millis();

  analogIn();
  analogOut();
  readTempET();
  readTempBT();

  if (chDrumFlag) {
    readWriteDrumINV();
  }

  if (chAirFlag) {
    readUnder();
    readWriteAirINV_PID();
  }

  handle_Modbus_Slave();
  readScale();
  rwHMICoil();
  rwMemHMI();
  rwHMI_1();
  rwHMI_2();

  if (chIORelayFlag) {
    rwIORelayCoil();
  }

  programScan();
  controlIO();

  calTime = millis() - timeMillis;
  if (enDebug) debug();
  errorCount = 0;

  pidSelfTuneTask();   // xử lý self-tune ngoài ISR
  pidSDTask();
}

void debug() {
  SerialComputer.print("Loop: " + String(calTime) + "ms");
  if (feederTimerEn)     SerialComputer.print(" | Feeder: "   + String(feederTimer));
  if (chargeTimerEn)     SerialComputer.print(" | Charge: "   + String(chargeTimer));
  if (dropTimerEn)       SerialComputer.print(" | Drop: "     + String(dropTimer));
  if (abTimerEn)         SerialComputer.print(" | AB: "       + String(abTimer));
  if (coolTimerEn)       SerialComputer.print(" | Cool: "     + String(coolTimer));
  if (escapeTimerEn)     SerialComputer.print(" | Escape: "   + String(escapeTimer));
  if (destonerTimerEn)   SerialComputer.print(" | Destoner: " + String(destonerTimer));
  if (timeRoastEn)       SerialComputer.print(" | Roast: "    + String(timeRoast));
  if (calSdMillis > 0)   SerialComputer.print(" | CalSD: "    + String(calSdMillis));
  if (waitDropcloseTiEn) SerialComputer.print(" | WaitDrop: " + String(waitDropcloseTi));
  if (fillerTiEn)        SerialComputer.print(" | Filler: "   + String(fillerTi));
  SerialComputer.println();
}