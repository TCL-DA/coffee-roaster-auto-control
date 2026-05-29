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
#include "MachineStatus.h"
#include "Program.h"

void debug();

void setup() {
  SerialComputer.begin(DEBUG_SERIAL_BAUD);
  ConfigIO();
  analogConfig();
  ModbusRS485Config();
  configTimer();
  // STT_SYSTEM_BOOT: write direct (HMI not yet confirmed, queue not flushed yet)
  // checkError() will confirm HMI then push individual startup statuses
  checkError();  // pushes 301-320 + STT_SYSTEM_READY at end
  analogCalLoadFromSD();
  rwMemHMI();
  ModbusSlaveConfig();
  pidLoadFromSD();
  phFFLoad();
  setMachineStatus(STT_SD_PID_FF_LOADED);
  reset_update();
  setMachineStatus(STT_PROFILE_SCAN);
  loadAllProfileDates();
  setMachineStatus(STT_SYSTEM_READY);
}

void loop() {
  timeMillis = millis();

  analogIn();
  enforceModbusGasCutoff();
  analogOut();
  readTempET();
  readTempBT();

  if (MACHINE_HAS_DRUM_SPEED_CONTROL && chDrumFlag) {
    readWriteDrumINV();
  }

  if (MACHINE_HAS_VACUUM_SENSOR && chAirFlag) {
    readUnder();
    readWriteAirINV_PID();
  }

  handle_Modbus_Slave();
  if (MACHINE_HAS_SCALE_FEEDER) {
    readScale();
  }
  rwHMICoil();
  rwMemHMI();
  rwHMI_1();
  rwHMI_2();

  if (chIORelayFlag) {
    rwIORelayCoil();
  }

  if(enLoadDateProfile) {
    loadAllProfileDates(); // Load lại ngày táng của tất cả hồ sơ từ SD card vào HMI (sau khi có lệnh từ HMI)
    enLoadDateProfile = false;
  }

  programScan();
  enforceModbusGasCutoff();
  controlIO();

  calTime = millis() - timeMillis;
  if (enDebug) debug();
  errorCount = 0;

  pidSelfTuneTask();   // xử lý self-tune ngoài ISR
  pidSDTask();

  // debugRoastStatus();
}

void debug() {
  // SerialComputer.print("Loop: " + String(calTime) + "ms");
  // if (feederTimerEn)     SerialComputer.print(" | Feeder: "   + String(feederTimer));
  // if (chargeTimerEn)     SerialComputer.print(" | Charge: "   + String(chargeTimer));
  // if (dropTimerEn)       SerialComputer.print(" | Drop: "     + String(dropTimer));
  // if (abTimerEn)         SerialComputer.print(" | AB: "       + String(abTimer));
  // if (coolTimerEn)       SerialComputer.print(" | Cool: "     + String(coolTimer));
  // if (escapeTimerEn)     SerialComputer.print(" | Escape: "   + String(escapeTimer));
  // if (destonerTimerEn)   SerialComputer.print(" | Destoner: " + String(destonerTimer));
  // if (timeRoastEn)       SerialComputer.print(" | Roast: "    + String(timeRoast));
  // if (calSdMillis > 0)   SerialComputer.print(" | CalSD: "    + String(calSdMillis));
  // if (waitDropcloseTiEn) SerialComputer.print(" | WaitDrop: " + String(waitDropcloseTi));
  // if (fillerTiEn)        SerialComputer.print(" | Filler: "   + String(fillerTi));
  // SerialComputer.print(" | airSpeed_R: " + String(airSpeed_R));
  // // SerialComputer.print(" | LOAD_DATE_PROFILE_R: " + String(LOAD_DATE_PROFILE_R));
  // SerialComputer.println();
}
