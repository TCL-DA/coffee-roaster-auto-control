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
#include "PC_Link.h"
#include "Modbus_Master.h"
#include "MachineStatus.h"
#include "Program.h"

void debug();

// ── Đồng hồ bấm giờ vòng loop: đo ms từng tác vụ chặn để tìm khoản chậm ──────
// Cách đo: profTick() ở đầu loop, profTock(i) ngay SAU mỗi tác vụ — tock ghi
// số ms trôi qua rồi tự mốc lại, nên các tác vụ nối đuôi nhau chỉ cần tock.
// profMax giữ ĐỈNH kể từ lần in trước — bắt được cú timeout Modbus 2s hiếm gặp
// mà số đo lần cuối không thấy. In gộp trong debug() mỗi ~2s (cổng debug
// 9600 baud ≈ 1ms/ký tự, in thưa để chính phép đo không làm chậm vòng loop).
#define PROF_N 14
enum { PF_ANA, PF_ET, PF_BT, PF_DRUM, PF_VAC, PF_PCL, PF_SLV,
       PF_COIL, PF_MEM, PF_HMI1, PF_HMI2, PF_IO, PF_PRG, PF_FAST };
static uint32_t profT0;
static uint16_t profMs[PROF_N];    // số đo vòng mới nhất (ms)
static uint16_t profMax[PROF_N];   // đỉnh kể từ lần in trước (ms)
static const char* const profName[PROF_N] = {
  "ANA","ET","BT","DRUM","VAC","PCL","SLV","COIL","MEM","HMI1","HMI2","IO","PRG","FAST"};   // FAST = một lượt rwHMI_Fast()
static inline void profTick(){ profT0 = millis(); }
static inline void profTock(uint8_t i){
  uint16_t d = (uint16_t)(millis() - profT0);
  profMs[i] = d;
  if (d > profMax[i]) profMax[i] = d;
  profT0 = millis();
}

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
  pcLinkInit();          // cấp dãy register liền khối cho app OTL Roast Lab (dùng chung mbs)
  pidLoadFromSD();
  phFFLoad();
#if (MACHINE_HAS_SCALE_FEEDER && FEEDER_ADAPT_EN)
  loaderCfgLoad();   // Nạp bảng dif đã học từ /loadcfg.csv
#endif
  setMachineStatus(STT_SD_PID_FF_LOADED);
  reset_update();
  setMachineStatus(STT_PROFILE_SCAN);
  loadAllProfileDates();
  setMachineStatus(STT_SYSTEM_READY);
}

void loop() {
  timeMillis = millis();
  profTick();

  // mbs.task() rải giữa các giao dịch chặn (2026-07-23): slave app/Artisan được
  // phục vụ nhiều điểm trong vòng thay vì chỉ 2 điểm cũ — khung ghi/đọc của app
  // hết cảnh nằm chờ trọn chu kỳ loop. task() không có khung chờ thì thoát ngay.
  analogIn();
  enforceModbusGasCutoff();
  analogOut();
  profTock(PF_ANA);
  readTempET();
  mbs.task();
  profTock(PF_ET);
  readTempBT();
  mbs.task();
  profTock(PF_BT);

  // Đọc nhanh khối nút lệnh HMI + đổi relay ngay (10/10/2026, xem rwHMI_Fast trong Modbus_Master.h): 3 lượt rải giữa
  // các giao dịch chậm + lượt đọc đủ của rwHMI_1 = nút được soi 4 lần / vòng -> bấm Burner / Charge / Drop / Escape…
  // là relay nhảy gần như tức thì thay vì chờ hết vòng.
  rwHMI_Fast();
  profTock(PF_FAST);

  if (MACHINE_HAS_DRUM_SPEED_CONTROL && chDrumFlag) {
    readWriteDrumINV();
    mbs.task();
    profTock(PF_DRUM);
  }

  if (MACHINE_HAS_VACUUM_SENSOR && chAirFlag) {
    readUnder();
    readWriteAirINV_PID();
    mbs.task();
    profTock(PF_VAC);
  }

  rwHMI_Fast();
  profTock(PF_FAST);

  handle_PC_Link();       // cập nhật khối app OTL trước; mbs.task() cuối handle_Modbus_Slave phục vụ cả 2 map
  profTock(PF_PCL);
  handle_Modbus_Slave();
  profTock(PF_SLV);
  if (MACHINE_HAS_SCALE_FEEDER) {
    readScale();
  }
  rwHMICoil();
  mbs.task();
  profTock(PF_COIL);
  rwMemHMI();
  mbs.task();
  profTock(PF_MEM);
  rwHMI_1();          // đã có mbs.task() bên trong (Modbus_Master.h)
  profTock(PF_HMI1);
  rwHMI_2();
  mbs.task();
  profTock(PF_HMI2);

  if (chIORelayFlag) {
    rwIORelayCoil();
    profTock(PF_IO);
  }

  rwHMI_Fast();           // trước programScan (đoạn dài nhất còn lại của vòng, có khi ghi SD)
  profTock(PF_FAST);

  if(enLoadDateProfile) {
    loadAllProfileDates(); // Load lại ngày táng của tất cả hồ sơ từ SD card vào HMI (sau khi có lệnh từ HMI)
    enLoadDateProfile = false;
  }

  programScan();
  enforceModbusGasCutoff();
  controlIO();
  updateStatusMC();         // cập nhật cờ ready/not-ready theo sức khỏe Modbus runtime
  updateRoastPhaseFlags();  // cập nhật cờ giai đoạn rang (Dry/Maillard/DEV) lên HMI
  roastMarkTask();          // max RoR TP→FCs + đánh dấu mốc cho đồ thị HMI / web PC (không đụng hồ sơ SD)
  mbs.task();               // lúc rang programScan có thể ghi SD lâu — phục vụ app trước khi sang vòng mới
  profTock(PF_PRG);         // gồm cả loadAllProfileDates hiếm gặp ở trên — chấp nhận

  calTime = millis() - timeMillis;
  if (enDebug) debug();
  errorCount = 0;

  sdEnsure();          // thẻ rớt giữa chừng → tự thử khởi tạo lại (tự giãn cách, không chặn)
  pidSelfTuneTask();   // xử lý self-tune ngoài ISR
  pidSDTask();

  // debugRoastStatus();
}

void debug() {
  // Hồ sơ thời gian vòng loop, in mỗi ~2s một dòng dạng:
  //   Loop 320ms | ANA 2 ET 28 BT 29 ... MEM 95/2210 ...
  // Số sau dấu "/" là ĐỈNH kể từ lần in trước (chỉ in khi cao hơn số thường) —
  // thấy /2xxx tức tác vụ đó vừa dính timeout Modbus 2s của thư viện.
  static uint32_t profLastPrint = 0;
  if (millis() - profLastPrint >= 2000) {
    profLastPrint = millis();
    // Ho so thoi gian vong loop — tam TAT de soi rieng preCool. Bo dau // cua
    // khoi duoi de bat lai khi can san loop cham.
    // SerialComputer.print("Loop " + String(calTime) + "ms |");
    // for (uint8_t i = 0; i < PROF_N; i++) {
    //   SerialComputer.print(" " + String(profName[i]) + " " + String(profMs[i]));
    //   if (profMax[i] > profMs[i]) SerialComputer.print("/" + String(profMax[i]));
    // }
    // SerialComputer.println();
    for (uint8_t i = 0; i < PROF_N; i++) profMax[i] = 0;   // van xa dinh moi vong in

    // Soi nhanh $M30 preCool (do sam quat lam mat truoc DROP). Thanh ghi o thang
    // x10, nen in ca so tho lan so do thuc de doi chieu voi o tren HMI.
    SerialComputer.print("preCool_R=");   SerialComputer.print(preCool_R);
    SerialComputer.print(" -> ");         SerialComputer.print(preCool_R_CV / 10.0f, 1);
    SerialComputer.println("C truoc DROP");
  }
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
