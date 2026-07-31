#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <HardwareSerial.h>
#include <ModbusMaster.h>
#include <Adafruit_MCP4725.h>

Adafruit_MCP4725 dac1;
Adafruit_MCP4725 dac2;

HardwareSerial Serial1(USART1);
HardwareSerial Serial3(USART3);
HardwareSerial Serial4(UART4);

#define     CH1_ANALOG      PC3
#define     CH2_ANALOG      PC2
#define     CH3_ANALOG      PC1

#define     CH6_INPUT       PA15
#define     CH5_INPUT       PA8
#define     CH4_INPUT       PB15
#define     CH3_INPUT       PB14
#define     CH2_INPUT       PB13
#define     CH1_INPUT       PB12                              

#define     SWITCH_1        PB4
#define     SWITCH_2        PB3    

#define     CH1_RL          PC13
#define     CH2_RL          PA4
#define     CH3_RL          PD2
#define     CH4_RL          PC12
#define     CH5_RL          PC5  
#define     CH6_RL          PB0 
#define     CH7_RL          PB1
#define     CH8_RL          PB2

#define     ERRO            PA0
#define     BUZZER          PA1
#define     chipSelect      PC4

void Check_OUTPUT(void);
void Check_SERIAL(void);
void Check_INPUT(void);
void Read_TempBT_RS485(void);

float Temperature__BT;
ModbusMaster node1;

void setup() {
  Serial1.begin(9600);              // DB9-RS232 RIGHT
  Serial2.begin(9600);              // DB9-RS232 LEFT
  Serial3.begin(9600);              // Header
  Serial4.begin(38400);              // Modbus RS485
  
  dac1.begin(0x60);
  dac2.begin(0x61);
  dac1.setVoltage(4095, false);
  dac2.setVoltage(4095, false); 

  node1.begin(1, Serial4); // Read RS485 Temperature ET
  
  pinMode(BUZZER, OUTPUT);          // Buzzer
  pinMode(ERRO,   OUTPUT);            // Erro
  pinMode(CH1_RL, OUTPUT);          // Relay 1
  pinMode(CH2_RL, OUTPUT);          // Relay 2
  pinMode(CH3_RL, OUTPUT);          // Relay 3 
  pinMode(CH4_RL, OUTPUT);          // Relay 4 
  pinMode(CH5_RL, OUTPUT);          // Relay 5 
  pinMode(CH6_RL, OUTPUT);          // Relay 6
  pinMode(CH7_RL, OUTPUT);          // Relay 7
  pinMode(CH8_RL, OUTPUT);          // Relay 8

  pinMode(CH1_INPUT, INPUT_PULLUP); // Input 1
  pinMode(CH2_INPUT, INPUT_PULLUP); // Input 2
  pinMode(CH3_INPUT, INPUT_PULLUP); // Input 3
  pinMode(CH4_INPUT, INPUT_PULLUP); // Input 4
  pinMode(CH5_INPUT, INPUT_PULLUP); // Input 5
  pinMode(CH6_INPUT, INPUT_PULLUP); // Input 6
  pinMode(SWITCH_1,  INPUT_PULLUP); // Input SWITCH 1
  pinMode(SWITCH_2,  INPUT_PULLUP); // Input SWITCH 2

  digitalWrite(CH1_RL, LOW);        // OFF
  digitalWrite(CH2_RL, LOW);        // OFF
  digitalWrite(CH3_RL, LOW);        // OFF
  digitalWrite(CH4_RL, LOW);        // OFF 
  digitalWrite(CH5_RL, LOW);        // OFF
  digitalWrite(CH6_RL, LOW);        // OFF 
  digitalWrite(CH7_RL, LOW);        // OFF
  digitalWrite(CH8_RL, LOW);        // OFF

  dac1.setVoltage(4095, false);
  dac2.setVoltage(4095, false); 
    
  pinMode(chipSelect, OUTPUT);
  while (!SD.begin(chipSelect))  
  {
    Serial1.println("Serial 1 - ERRO SD CARD");
    Serial2.println("Serial 2 - ERRO SD CARD");
    digitalWrite(BUZZER, HIGH);
    delay(100); 
    digitalWrite(BUZZER, LOW);
    delay(100);
  }
    Serial1.println("Serial 1 - SD CARD => OK");
    Serial2.println("Serial 2 - SD CARD => OK");
    dac1.setVoltage(0, false);
    dac2.setVoltage(0, false); 
}

void loop() {
  for(int i = 0; i < 1; i++) Check_OUTPUT();
  for(;;) {
    Read_TempBT_RS485();
    Check_INPUT(); 
    Check_SERIAL();
    Serial1.println();
    Serial2.println();
    Serial3.println();
    delay(100);
  }
}

void Check_OUTPUT(void)
{ digitalWrite(CH1_RL, LOW);  delay(500);
  digitalWrite(CH2_RL, LOW);  delay(500);
  digitalWrite(CH3_RL, LOW);  delay(500);
  digitalWrite(CH4_RL, LOW);  delay(500);
  digitalWrite(CH5_RL, LOW);  delay(500);
  digitalWrite(CH6_RL, LOW);  delay(500);
  digitalWrite(CH7_RL, LOW);  delay(500); 
  digitalWrite(CH8_RL, LOW);  delay(500); 

  digitalWrite(CH1_RL, HIGH); delay(500);
  digitalWrite(CH2_RL, HIGH); delay(500);
  digitalWrite(CH3_RL, HIGH); delay(500);
  digitalWrite(CH4_RL, HIGH); delay(500);
  digitalWrite(CH5_RL, HIGH); delay(500);
  digitalWrite(CH6_RL, HIGH); delay(500);
  digitalWrite(CH7_RL, HIGH); delay(500);
  digitalWrite(CH8_RL, HIGH); delay(500);

  for(int i = 0; i < 2; i++) {
    digitalWrite(CH1_RL, LOW);
    digitalWrite(CH2_RL, LOW); 
    digitalWrite(CH3_RL, LOW);  
    digitalWrite(CH4_RL, LOW);  
    digitalWrite(CH5_RL, LOW);  
    digitalWrite(CH6_RL, LOW);  
    digitalWrite(CH7_RL, LOW);  
    digitalWrite(CH8_RL, LOW);  delay(1000); 

    digitalWrite(CH1_RL, HIGH);
    digitalWrite(CH2_RL, HIGH);
    digitalWrite(CH3_RL, HIGH);
    digitalWrite(CH4_RL, HIGH);
    digitalWrite(CH5_RL, HIGH); 
    digitalWrite(CH6_RL, HIGH); 
    digitalWrite(CH7_RL, HIGH); 
    digitalWrite(CH8_RL, HIGH); delay(1000);
  }
  
  digitalWrite(BUZZER, HIGH);
  digitalWrite(ERRO,   HIGH);
  delay(500);
  digitalWrite(BUZZER, LOW);
  digitalWrite(ERRO,   LOW);
}

void Check_SERIAL(void)
{
  int i_1 = analogRead(CH1_ANALOG);
  int i_2 = analogRead(CH2_ANALOG);
  int i_3 = analogRead(CH3_ANALOG);
  String Str_Data = String(i_1)+" "+String(i_2)+" "+String(i_3);

  Serial1.println("Serial1 => " + Str_Data);
  Serial2.println("Serial2 => " + Str_Data);
  Serial3.println("Serial3 => " + Str_Data);
}

void Check_INPUT(void)
{
  int State = digitalRead(CH1_INPUT);
  digitalWrite(CH1_RL, !State); 
  if(!State) {
    dac1.setVoltage(4095, false);
    Serial1.println("SR1 INPUT 1 => OK");   // KIỂM TRA INPUT DIGITAL XUÂT CỔNG SERIAL
    Serial2.println("SR2 INPUT 1 => OK");
    Serial3.println("SR3 INPUT 1 => OK");
    delay(100);
  }

  State = digitalRead(CH2_INPUT);
  digitalWrite(CH2_RL, !State); 
  if(!State) {
    dac2.setVoltage(4095, false);
    Serial1.println("SR1 INPUT 2 => OK");   // KIỂM TRA INPUT DIGITAL XUÂT CỔNG SERIAL
    Serial2.println("SR2 INPUT 2 => OK");
    Serial3.println("SR3 INPUT 2 => OK");
    delay(100);
  }

  State = digitalRead(CH3_INPUT);
  digitalWrite(CH3_RL, !State); 
  if(!State) {
    dac1.setVoltage(2047, false);
    Serial1.println("SR1 INPUT 3 => OK");   // KIỂM TRA INPUT DIGITAL XUÂT CỔNG SERIAL
    Serial2.println("SR2 INPUT 3 => OK");
    Serial3.println("SR3 INPUT 3 => OK");
    delay(100);
  }

  State = digitalRead(CH4_INPUT);
  digitalWrite(CH4_RL, !State); 
  if(!State) {
    dac2.setVoltage(2047, false);
    Serial1.println("SR1 INPUT 4 => OK");   // KIỂM TRA INPUT DIGITAL XUÂT CỔNG SERIAL
    Serial2.println("SR2 INPUT 4 => OK");
    Serial3.println("SR3 INPUT 4 => OK");
    delay(100);
  }

  State = digitalRead(CH5_INPUT);
    digitalWrite(CH5_RL, !State); 
    digitalWrite(BUZZER, !State); 
  if(!State) {
    dac1.setVoltage(0, false);
    Serial1.println("SR1 INPUT 5 => OK");   // KIỂM TRA INPUT DIGITAL XUÂT CỔNG SERIAL
    Serial2.println("SR2 INPUT 5 => OK");
    Serial3.println("SR3 INPUT 5 => OK");
    delay(100);
  }

  State = digitalRead(CH6_INPUT);
    digitalWrite(CH6_RL, !State);
  if(!State) { 
    dac2.setVoltage(0, false);
    Serial1.println("SR1 INPUT 6 => OK");   // KIỂM TRA INPUT DIGITAL XUÂT CỔNG SERIAL
    Serial2.println("SR2 INPUT 6 => OK");
    Serial3.println("SR3 INPUT 6 => OK");
    delay(100);
  }

  State = digitalRead(SWITCH_1);
    digitalWrite(CH7_RL, !State);
  if(!State) {
    Serial1.println("SR1 INPUT SWITCH_1 => OK");   // KIỂM TRA INPUT DIGITAL XUÂT CỔNG SERIAL
    Serial2.println("SR2 INPUT SWITCH_1 => OK");
    Serial3.println("SR3 INPUT SWITCH_1 => OK");
    delay(100);
  }

  State = digitalRead(SWITCH_2);
    digitalWrite(CH8_RL, !State);
  if(!State) {
    Serial1.println("SR1 INPUT SWITCH_2 => OK");   // KIỂM TRA INPUT DIGITAL XUÂT CỔNG SERIAL
    Serial2.println("SR2 INPUT SWITCH_2 => OK");
    Serial3.println("SR3 INPUT SWITCH_2 => OK");
    delay(100);
  }

}



void Read_TempBT_RS485(void)
{
  uint8_t   result = 0;

  result = node1.readHoldingRegisters(0x4700, 1);// Data trỏ địa chỉ ở đây theo parem (Địa Chỉ, Chiều Dài)

  if (result == node1.ku8MBSuccess)
  {
    float BT = node1.getResponseBuffer(0);
    Temperature__BT = BT / 10;
    Serial1.print("Serial1 - RS485: ");  Serial1.println(Temperature__BT);  
    Serial2.print("Serial2 - RS485: ");  Serial2.println(Temperature__BT);  
    Serial3.print("Serial3 - RS485: ");  Serial3.println(Temperature__BT);  
  }
  delay(5);
}