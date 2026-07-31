//Define chip for ISR
#include <Arduino.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <HardwareSerial.h>
#include <ModbusMaster.h>
#include <Wire.h>
#include <Adafruit_MCP4725.h>
#include <ModbusRTU.h>  //Modbus slave ESP MTlab 
#include <SPI.h>
#include <SD.h>

//-------------------------------------------------------Timer
#if !( defined(STM32F0) || defined(STM32F1) || defined(STM32F2) || defined(STM32F3)  ||defined(STM32F4) || defined(STM32F7) || \
       defined(STM32L0) || defined(STM32L1) || defined(STM32L4) || defined(STM32H7)  ||defined(STM32G0) || defined(STM32G4) || \
       defined(STM32WB) || defined(STM32MP1) || defined(STM32L5) )
  #error This code is designed to run on STM32F/L/H/G/WB/MP1 platform! Please check your Tools->Board setting.
#endif

#define TIMER_INTERRUPT_DEBUG         0
#define _TIMERINTERRUPT_LOGLEVEL_     3

#include "STM32TimerInterrupt.h"
#include <SimpleKalmanFilter.h>
//--------------------------------------------------------End 
         

#include "Define.h"
#include "IOConfig.h"
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
  rwMemHMI();   //Đọc setup
  ModbusSlaveConfig();
  reset_update();
  
}

void loop() {
  // Lấy thời gian hiện tại
  timeMillis = millis();

  // Xử lý liên tục
  analogIn();             // Đọc tín hiệu analog
  analogOut();            // Xuất tín hiệu analog
  readTempET();           // Đọc nhiệt độ ET
  readTempBT();           // Đọc nhiệt độ BT
  if(chDrumFlag)
    readWriteDrumINV();     // Điều khiển biến tần trống
  if(chAirFlag)
    readAirflowINV();       // Đọc biến tần luồng khí
  handle_Modbus_Slave();  // Xử lý Modbus slave

  // Xử lý điều kiện
  rwHMICoil();            // Đọc/ghi bit HMI
  rwMemHMI();             // Đọc/ghi biến $M HMI
  rwHMI_1();              // Đọc/ghi biến 4xxxx HMI (40001-40047)
  rwHMI_2();              // Đọc/ghi biến 4xxxx HMI (40060-40085)

  // Xử lý chương trình
  programScan();          // Quét chương trình

  // Điều khiển IO
  controlIO();            // Điều khiển đầu vào/ra

  // Tính thời gian xử lý
  calTime = millis() - timeMillis;

  // Debug nếu được bật
  if (enDebug)
    debug();

  // Đặt lại bộ đếm lỗi
  errorCount = 0;
  // SerialComputer.println("time: " + String(calTime) + " BTN: " + String(WATER_BTN));
}

// Hàm debug - hiển thị thông tin trạng thái hệ thống
void debug() {
  SerialComputer.print("Time xử lý: " + String(calTime) + " ms");

  // Hiển thị trạng thái các timer nếu được kích hoạt
  if (feederTimerEn) SerialComputer.print(" | Feeder: " + String(feederTimer));
  if (chargeTimerEn) SerialComputer.print(" | Charge: " + String(chargeTimer));
  if (dropTimerEn) SerialComputer.print(" | Drop: " + String(dropTimer));
  if (abTimerEn) SerialComputer.print(" | AB: " + String(abTimer));
  if (coolTimerEn) SerialComputer.print(" | Cool: " + String(coolTimer));
  if (escapeTimerEn) SerialComputer.print(" | Escape: " + String(escapeTimer));
  if (destonerTimerEn) SerialComputer.print(" | Destoner: " + String(destonerTimer));
  if (timeRoastEn) SerialComputer.print(" | Roast: " + String(timeRoast));
  if (calSdMillis > 0) SerialComputer.print(" | CalSD: " + String(calSdMillis));
  if (waitDropcloseTiEn > 0) SerialComputer.print(" | WaitDropClose: " + String(waitDropcloseTi));

  // Hiển thị trạng thái các phần trăm điều khiển
  SerialComputer.print(" | Airflow: " + String(airflowPC) + "%");
  SerialComputer.print(" | Gas: " + String(gasPC) + "%");
  SerialComputer.print(" | Drum: " + String(drumPC) + "%");

  SerialComputer.println(); // Xuống dòng
}
