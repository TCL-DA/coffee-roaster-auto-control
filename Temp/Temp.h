void ModbusRS485Config(){
  SerialHmi.begin(115200);      
  SerialModbus.begin(38400); 
  SerialBluetooth.begin(115200); 
  SerialComputer.begin(9600);

  node1.begin(1, SerialModbus); // Read RS485 Temperature ET
  node2.begin(2, SerialModbus); // Read RS485 Temperature BT
  // node4.begin(4, SerialComputer); // Read,Write ESP
  node3.begin(1, SerialHmi);    // HMI
  SerialComputer.println("=> Modbus OK");
}

void readTempET(){
  uint8_t result = 0;

  result = node1.readHoldingRegisters(tempRegister, 1);// Data trỏ địa chỉ ở đây theo parem (Địa Chỉ, Chiều Dài)
  if (result == node1.ku8MBSuccess)
  {
    Temperature__ET = node1.getResponseBuffer(0);// Em lấy data ra sài bằng mảng data[i] với code hiện tại thì data[0]: Nhiệt Độ (PV) -- data[1]: nhiệt độ SET (SV)...
    Temperature_HMI_BT_DIGITAL = (uint16_t)Temperature__BT*10;
    checkStt[1] = 1;
  }
  else
  {
    SerialComputer.print(" ERRO READ ET");
    BUZZ_ON; delay(1500); BUZZ_OFF;  
  }
  delay(5);
}


void Read_TempBT_RS485(void)
{
  uint8_t   result = 0;

  result = node1.readHoldingRegisters(0x4700, 1);// Data trỏ địa chỉ ở đây theo parem (Địa Chỉ, Chiều Dài)

  if (result == node1.ku8MBSuccess)
  {
    float BT = node1.getResponseBuffer(0);
    Temperature__BT = BT / 10;
    // Serial1.print("Serial1 - RS485: ");  Serial1.println(Temperature__BT);  
    // Serial2.print("Serial2 - RS485: ");  Serial2.println(Temperature__BT);  
    // Serial3.print("Serial3 - RS485: ");  Serial3.println(Temperature__BT);  
  }
  delay(5);
}

void Read_TempET_RS485(void)
{
  uint8_t   result = 0;

  result = node2.readHoldingRegisters(0x4700, 1);// Data trỏ địa chỉ ở đây theo parem (Địa Chỉ, Chiều Dài)

  if (result == node2.ku8MBSuccess)
  {
    float ET = node2.getResponseBuffer(0);
    Temperature__ET = ET / 10;
    // Serial1.print("Serial1 - RS485: ");  Serial1.println(Temperature__BT);  
    // Serial2.print("Serial2 - RS485: ");  Serial2.println(Temperature__BT);  
    // Serial3.print("Serial3 - RS485: ");  Serial3.println(Temperature__BT);  
  }
  delay(5);
}

void Read_Drum_RS485(void)
{
  uint16_t   result = 0;

  result = node3.readHoldingRegisters(8193, 1);// Data trỏ địa chỉ ở đây theo parem (Địa Chỉ, Chiều Dài)
  //8451 = Read running Hz in inverter  (range 0-5000)
  //8193 = Write command Hz for inverter (range 0-5000)

  if (result == node3.ku8MBSuccess)
  { 
    uint16_t DrumHz = node3.getResponseBuffer(0);

    uint16_t DrumCommand = 0;
    DrumCommand = random(2000, 3000); //random Hz

    /*
    phai co delay truoc khi thuc hien ham` writeSingleRegister, delay it nhat 5ms
    ku8MBResponseTimedOut = 0xE2;
    */

    delay(10);

    result = node3.writeSingleRegister(8193, DrumCommand);
    
    if(result == 0){
      Serial2.print("Drum Command:" + String(DrumCommand));
      Serial2.println("---------Drum speed:" + String(DrumHz));  
    }else{
      Serial2.print("result ");
      Serial2.println(result,HEX);
    }
    
    // digitalWrite(BUZZER, HIGH);
    // delay(50); //
    // digitalWrite(BUZZER, LOW);
  }else{
    digitalWrite(BUZZER, HIGH);
    delay(1000); //
    digitalWrite(BUZZER, LOW);  
  }
  /* 
  thay doi Hz sau moi 500ms
  */
  delay(500); 
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






void readTempBT(){
  uint8_t   result = 0;
  result = node2.readHoldingRegisters(tempRegister, 1);// Data trỏ địa chỉ ở đây theo parem (Địa Chỉ, Chiều Dài)

  if (result == node2.ku8MBSuccess)
  {
    Temperature__BT = node2.getResponseBuffer(0);// Em lấy data ra sài bằng mảng data[i] với code hiện tại thì data[0]: Nhiệt Độ (PV) -- data[1]: nhiệt độ SET (SV)...
    Temperature_HMI_ET_DIGITAL = (uint16_t)Temperature__ET*10;
    checkStt[0] = 1;
  }
  else{
    SerialComputer.print(" ERRO READ BT");
    BUZZ_ON; delay(500); BUZZ_OFF;
  }
  delay(5);
}

void resetGraph(){
  uint8_t result = 0;
  uint8_t Numaddress = 23;
  result = node3.readHoldingRegisters(0, Numaddress);

  if(result == node3.ku8MBSuccess) {
    EN_CLEAR_HMI; 
    SerialComputer.println("=> Reset Graph");
    delay(1000);
    DIS_CLEAR_HMI;
  }
}

// ESP32 
void commuESP(){
    // SerialComputer.print(" Send data to esp success");
    node4.writeSingleRegister(0, Temperature__BT);  //Send BT temperature value to esp
}

void readMemmoryRegisterHMI(){
  uint8_t result = 0;
  uint8_t mNumaddress = 10;
  result = node3.readHoldingRegisters(2000, mNumaddress); //160ms
  if(result == node3.ku8MBSuccess){
    for(int i=1;i<=mNumaddress;i++){
      valueMemmoryDataHMI[i] = node3.getResponseBuffer(i);
    }
    Serial2.println("chargeDuration: " + String(chargeDuration) + " dropDuration: " + String(dropDuration) + " escapeDuration: " + String(escapeDuration) +
    " gasDecrease: " + String(incGasSmooth) + " gasIncrease: " + String(decGasSmooth) + " tempRegister: " + String(tempRegister));
  }
  delay(5);
}

void Read_Write_HMI_Delta(void)
{
  uint8_t result = 0;
  uint8_t Numaddress = 28;
  

  result = node3.readHoldingRegisters(0, Numaddress); //160ms

  if(result == node3.ku8MBSuccess) 
  {
    for(int i = 0; i < Numaddress; i++) {
      Value_Data_Read_HMI[i] = node3.getResponseBuffer(i); // nạp vao mảng array
      //SerialComputer.print(Value_Data_Read_HMI[i]);
    }
      //SerialComputer.print("\r\n");
      //delay(300);
  
    switch (MANUAL_AUTO_SD)
    {
      case 1:
        SELECT_PROGRAM = true;
        BTN_AUTO = BTN_MANUAL = SD_SERIAL = LOADCELL = false;
        break;
      case 2:
        BTN_MANUAL = true;
        BTN_AUTO = SELECT_PROGRAM = SD_SERIAL = LOADCELL = false;
        break;
      case 3:
        BTN_AUTO = true;
        BTN_MANUAL = SELECT_PROGRAM = SD_SERIAL = LOADCELL = false;
        break;
      case 4:
        LOADCELL = true;
        BTN_AUTO = BTN_MANUAL = SELECT_PROGRAM = SD_SERIAL = false;
        break;
      case 5:
        SD_SERIAL = true;
        BTN_AUTO = BTN_MANUAL = SELECT_PROGRAM = LOADCELL = false;
        break;
    }

    node3.writeSingleRegister(36, Ror__BT_DIGITAL);           
    node3.writeSingleRegister(37, Ror__ET_DIGITAL);  
    // node3.writeSingleRegister(60, (uint16_t)(Temperature__BT+800)/10);      
    node3.writeSingleRegister(60, (uint16_t)fake_BT);        
    node3.writeSingleRegister(61, (uint16_t)(Temperature__ET+1200)/10);      
    node3.writeSingleRegister(62, Min);           
    node3.writeSingleRegister(63, Sec);          
    
    node3.writeSingleRegister(64, random(10,20));                    
    node3.writeSingleRegister(65, random(70,80));  
    
    // node3.writeSingleRegister(32, Temperature_HMI_BT_DIGITAL); 
    // node3.writeSingleRegister(33, Temperature_HMI_ET_DIGITAL);
    node3.writeSingleRegister(32, (uint16_t)fake_BT*10); 
    node3.writeSingleRegister(33, (uint16_t)Temperature__ET+1200); 
    
  }           
  else{
    SerialComputer.println("ERRO HMI DELTA");
    BUZZ_ON; delay(200); BUZZ_OFF;  delay(2000);
  }
  delay(10);
}

void Graph_HMI_Delta(void)
{
    if(Tick)  
    {
      EN_GRAPH; delay(5);
      Tick = false;
    }
    else
    {
      DIS_GRAPH;
    }
}

void Graph_HMI_Delta_1(void)
{
  // if(Tick)  
  // {
  uint8_t result = 0;
  uint8_t Numaddress = 1;
  result = node3.readHoldingRegisters(0, Numaddress); //160ms
  if(result == node3.ku8MBSuccess) 
  {
    if(enGraph){
      EN_GRAPH;
      DIS_GRAPH;
      SerialComputer.println("=> HisGraph sample complete, serial");
      // enGraph = false;
    }
    // if(enGraph){
    //   DIS_GRAPH;
    //   enGraph = false;
    //   SerialComputer.println("=> enGraph = false");
    // }
    // Read_Write_HMI_Delta();
    // Tick = false;
    // }
    delay(10);
  }
}

// void Update_Data_Sd_Card(void)
// {
//     if(Tick_Timer == true)  
//     {
//       txJsonEnvironment();
//       Tick_Timer = false;
//     }
// }
