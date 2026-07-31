#define     SerialBluetooth Serial3
#define     SerialModbus    Serial4
#define     SerialHmi       Serial1
#define     SerialComputer  Serial2

#define     CH1_ANALOG      PD1
#define     CH2_ANALOG      PB4
#define     CH3_ANALOG      PB5
#define     CH4_ANALOG      PB7

#define     CH1_INPUT_GAS   PA14
#define     CH2_INPUT_ROAST PC9
#define     CH3_INPUT_EXIT  PB15
#define     CH4_INPUT       PB14
#define     CH5_INPUT       PB13
#define     CH6_INPUT       PB12
                                     
#define     CH1_PWM         PC8
#define     CH3_PWM         PC7
#define     CH2_PWM         PC6

#define     CH1_RL_GAS      PC15 //Gas
#define     CH2_RL_XL_1     PD2 //Charge
#define     CH3_RL_XL_2     PC11 //Null
#define     CH4_RL_XL_EN    PB0  //DROP
#define     CH5_DC_COOL     PB1  //COOLING
#define     CH6_RL_XL_3     PB2  //ESCAPE

#define     BUZZER          PA1  //Buzzer
#define     chipSelect      PC4

#define     GAS_ON          digitalWrite(CH1_RL_GAS, HIGH)
#define     GAS_OFF         digitalWrite(CH1_RL_GAS, LOW)

#define     COOl_ON         digitalWrite(CH5_DC_COOL, LOW)
#define     COOl_OFF        digitalWrite(CH5_DC_COOL, HIGH)

#define     BUZZ_ON         digitalWrite(BUZZER, HIGH)
#define     BUZZ_OFF        digitalWrite(BUZZER, LOW)

uint16_t Sec = 0, Min = 0, Total_Sec = 0, Total_Sec_Latter = 0;
uint16_t SAVE_TEMP_MAX = 0, SAVE_TEMP_MIN = 0, SAVE_TEMP_ROAST = 0,SAVE_TEMP_EXIT = 0, VLE_SD_SAVE = 0;
uint16_t Temperature_HMI_BT_DIGITAL, Temperature_HMI_ET_DIGITAL;
uint16_t Ror__BT_DIGITAL, Ror__ET_DIGITAL;
uint16_t M = 0;
uint16_t ModeRun = 0, Mode__Auto = 0;
uint16_t TSec = 0, TSec_Latter = 0;
uint16_t Timer_Xilanh = 0;
uint16_t Timer_Cool = 0;
uint16_t secondCount = 0;


uint32_t startAt = 0;
uint32_t stopAt = 0;

float Temperature__BT, Ror__BT, Ror__BT_Past;
float Temperature__ET, Ror__ET, Ror__ET_Past;

String String_Data_BLE = "";
String Str_Data = "";

boolean trend         = false;
boolean enGraph       = true;
boolean enTime        = true;
boolean enM           = true;
boolean Cold_Roast    = true;
boolean Tick          = false;
boolean PID_SUCCESS   = false;
boolean Manual_VR     = false;
boolean Enable_Timer  = false;
boolean Reset         = false;
boolean EXIT          = false;
boolean Read_Code     = false;
boolean Counter_Xl    = false;
boolean Enable_Cool   = false;
boolean BTN_AUTO      = false;
boolean BTN_MANUAL    = false;
boolean SELECT_PROGRAM= false;
boolean LOADCELL      = false;
boolean SD_SERIAL     = false;
boolean ENABLE_SD_SERIAL = false;
boolean Tick_Timer    = false;
boolean Continue      = false;
boolean enR           = true;

// serialTransmit ESP32Serial;

ModbusMaster node1;
ModbusMaster node2;
ModbusMaster node3;
ModbusMaster node4;

uint16_t valueMemmoryDataHMI[20];
uint16_t Value_Data_Read_HMI[50];
boolean checkStt[16]; //[BT][ET]

#define   BTN_START           Value_Data_Read_HMI[1]
#define   BTN_PID             Value_Data_Read_HMI[2]
#define   BTN_GAS             Value_Data_Read_HMI[3]
#define   BTN_SEND            Value_Data_Read_HMI[4]
#define   VLE_TEMP_MAX        Value_Data_Read_HMI[5]
#define   VLE_TEMP_MIN        Value_Data_Read_HMI[6]
#define   MANUAL_AUTO_SD      Value_Data_Read_HMI[7]
#define   BTN_SD_CARD         Value_Data_Read_HMI[8]
#define   BTN_CHARGE          Value_Data_Read_HMI[10]
#define   BTN_DROP            Value_Data_Read_HMI[11]
#define   VLE_TIME_COOL       Value_Data_Read_HMI[12]

#define   BTN_ESCAPE          Value_Data_Read_HMI[13]
#define   BTN_COOLING         Value_Data_Read_HMI[14]
#define   BTN_XL_DISCHAGRE_1  Value_Data_Read_HMI[15]
#define   BTN_MT_DESTONER     Value_Data_Read_HMI[16]
#define   BTN_XL_DISCHAGRE_2  Value_Data_Read_HMI[17]

#define   BTN_XL_DISCHAGRE_TC Value_Data_Read_HMI[18]
#define   BTN_XL_DROP_TC      Value_Data_Read_HMI[19]
#define   BTN_XL_ESCAPE_TC    Value_Data_Read_HMI[20]
#define   BTN_CONNECT_TEST    Value_Data_Read_HMI[21]

#define   chargeDuration      valueMemmoryDataHMI[1]
#define   dropDuration        valueMemmoryDataHMI[2]
#define   escapeDuration      valueMemmoryDataHMI[3]
#define   incGasSmooth        valueMemmoryDataHMI[4]
#define   decGasSmooth        valueMemmoryDataHMI[5]
#define   tempRegister        valueMemmoryDataHMI[6]

#define   Default_Timer_Cool  node3.writeSingleRegister(12, 0);

#define   BTN_ZERO_LC_ON      node3.writeSingleRegister(13, 1)
#define   BTN_ZERO_LC_OFF     node3.writeSingleRegister(13, 0)

#define   BTN_XL_ROAST_ON     node3.writeSingleRegister(10, 1)
#define   BTN_XL_ROAST_OFF    node3.writeSingleRegister(10, 0)

#define   BTN_XL_EXIT_ON      node3.writeSingleRegister(11, 1)
#define   BTN_XL_EXIT_OFF     node3.writeSingleRegister(11, 0)

#define   LOCK_MANUAL         node3.writeSingleRegister(49, 2)
#define   LOCK_AUTO           node3.writeSingleRegister(49, 3)
#define   LOCK_LOAD           node3.writeSingleRegister(49, 4)

#define   BTN_SEND_ON         node3.writeSingleRegister(4, 1)
#define   BTN_SEND_OFF        node3.writeSingleRegister(4, 0)

#define   BTN_START_ON        node3.writeSingleRegister(1, 1)
#define   BTN_START_OFF       node3.writeSingleRegister(1, 0)

#define   BTN_PID_ON          node3.writeSingleRegister(2, 1)
#define   BTN_PID_OFF         node3.writeSingleRegister(2, 0)

#define   BTN_GAS_ON          node3.writeSingleRegister(3, 1)
#define   BTN_GAS_OFF         node3.writeSingleRegister(3, 0)

#define   LED_GAS_ON          node3.writeSingleRegister(43, 1)
#define   LED_GAS_OFF         node3.writeSingleRegister(43, 0)

#define   LED_CNT_ON          node3.writeSingleRegister(42, 1)
#define   LED_CNT_OFF         node3.writeSingleRegister(42, 0)

#define   EN_GRAPH            node3.writeSingleRegister(51, 0xFFF)
#define   DIS_GRAPH           node3.writeSingleRegister(51, 0)

#define   EN_GRAPH_CURVE      node3.writeSingleRegister(50, 7)
#define   DIS_GRAPH_CURVE     node3.writeSingleRegister(50, 0)

#define   EN_CLEAR_HMI        node3.writeSingleRegister(52, 0xFFF)
#define   DIS_CLEAR_HMI       node3.writeSingleRegister(52, 0)

void Interrupt_Timer_100ms(void);

void setupPin(void){
   
  // pinMode(BUZZER, OUTPUT); //Buzzer
  // pinMode(CH1_RL_GAS,  OUTPUT); //Gas
  // pinMode(CH2_RL_XL_1, OUTPUT); //Charge
  // pinMode(CH3_RL_XL_2, OUTPUT); //Null
  // pinMode(CH4_RL_XL_EN,OUTPUT); //Drop
  // pinMode(CH5_DC_COOL, OUTPUT); //Cooling
  // pinMode(CH6_RL_XL_3, OUTPUT); //Escape

  // pinMode(CH1_INPUT_GAS,   INPUT_PULLUP); // Input phát hiện có lửa
  // pinMode(CH2_INPUT_ROAST, INPUT_PULLUP); // Input phát hiện có cafe vào
  // pinMode(CH3_INPUT_EXIT,  INPUT_PULLUP); // Input thoát chương trình giao tiếp máy tính
  // pinMode(CH4_INPUT,       INPUT_PULLUP); // Input chưa sử dụng
  // pinMode(CH5_INPUT,       INPUT_PULLUP); // Input Test chương trình

  // digitalWrite(CH1_RL_GAS,  LOW);   // OFF
  // digitalWrite(CH2_RL_XL_1, LOW);   // OFF
  // digitalWrite(CH3_RL_XL_2, LOW);   // OFF
  // digitalWrite(CH4_RL_XL_EN,HIGH);  // OFF XI LANH
  // digitalWrite(CH5_DC_COOL, HIGH);  // OFF COOL
  // digitalWrite(CH6_RL_XL_3, HIGH);  // OFF 
  delay(100);
  
  // //Timer
  Timer2.setMode(TIMER_CH1, TIMER_OUTPUTCOMPARE);
  Timer2.setPeriod(1000000);         // in microseconds
  Timer2.setCompare(TIMER_CH1, 1);   // overflow might be small
  Timer2.attachInterrupt(TIMER_CH1,Interrupt_Timer_100ms);

  Default_Timer_Cool; delay(100); //Default cooling time 250s
  SerialComputer.println("=> Setup Pin OK");
}


void Buzzer(uint16_t onTime){
    BUZZ_ON;    delay(onTime);
    BUZZ_OFF;   delay(onTime);
}

//Check connect
void CheckConnect(void){
  uint8_t check;
  pinMode(chipSelect, OUTPUT);
  // CHECK SD CARD
  // while (!SD.begin(chipSelect))  {
  //   SerialComputer.println("ERRO SD CARD");
  //   BUZZ_ON; delay(300); BUZZ_OFF; delay(100);  
  // }
  SerialComputer.println("SD CARD => OK");
  Buzzer(100);  Buzzer(100);

  /*Check HMI*/
  check = node3.readHoldingRegisters(0, 9); delay(50);
  while(check != node3.ku8MBSuccess){
    check = node3.readHoldingRegisters(0, 9); delay(50);
    SerialComputer.println("Error HMI");
    // Buzzer(100,100); 
  } 
  SerialComputer.println("HMI => OK");
  Buzzer(100);  Buzzer(100);
  /*End*/

  // /*Check modbus ET*/
  // check = node1.readHoldingRegisters(0, 1); delay(50);
  // while(check != node1.ku8MBSuccess) {
  //   check = node1.readHoldingRegisters(0, 1); delay(50);
  //   SerialComputer.println("ERRO READ ET");
  //   // BUZZ_ON; delay(300); BUZZ_OFF; delay(100); 
  // }
  //   SerialComputer.println("READ ET => OK");
  //   // Buzzer(100,100);  Buzzer(100,100);
  // /*End*/  

  // /*Check modbus BT*/
  // check = node2.readHoldingRegisters(0, 1); delay(50);
  // while(check != node2.ku8MBSuccess){
  //   check = node2.readHoldingRegisters(0, 1); delay(50);
  //   SerialComputer.println("ERRO READ BT");
  //   // BUZZ_ON; delay(300); BUZZ_OFF; delay(100); 
  // }
  //   SerialComputer.println("READ BT => OK");

  //   // Buzzer(1000,100);
  // /*End*/  

}

//Check Gas
void Check_Start_Gas(void){
  if(BTN_GAS == true){
    GAS_ON;
    if(digitalRead(CH1_INPUT_GAS) == LOW) LED_GAS_ON;
    else LED_GAS_OFF;
  }
  else{ 
    GAS_OFF; 
    LED_GAS_OFF;
  }
}

//Control Xilanh
void Xilanh_Roast_Down(void){
  digitalWrite(CH4_RL_XL_EN, LOW);
  digitalWrite(CH2_RL_XL_1,  LOW);  
}

void Xilanh_Roast_Up(void){
  digitalWrite(CH4_RL_XL_EN, LOW);
  digitalWrite(CH2_RL_XL_1,  HIGH); 
}

void Xilanh_Exit_Down(void){
  digitalWrite(CH4_RL_XL_EN, LOW);
  digitalWrite(CH3_RL_XL_2,  LOW); 
}

void Xilanh_Exit_Up(void){
  digitalWrite(CH4_RL_XL_EN, LOW);
  digitalWrite(CH3_RL_XL_2,  HIGH); 
}

void Xilanh_OUT_COFFEE_UP(void){
  digitalWrite(CH4_RL_XL_EN, LOW);
  digitalWrite(CH6_RL_XL_3,  HIGH); 
}

void Xilanh_OUT_COFFEE_DOWN(void){
  digitalWrite(CH4_RL_XL_EN, LOW);
  digitalWrite(CH6_RL_XL_3,  LOW); 
}

void allXilanhOff(void){
  digitalWrite(CH1_RL_GAS,  LOW);     //Gas   
  digitalWrite(CH2_RL_XL_1,  LOW);    //Charge
  digitalWrite(CH3_RL_XL_2,  LOW);    //Null
  digitalWrite(CH4_RL_XL_EN,  HIGH);  //Drop
  digitalWrite(CH5_DC_COOL, HIGH);    //Cooling
  digitalWrite(CH6_RL_XL_3, HIGH);    //Escape
}