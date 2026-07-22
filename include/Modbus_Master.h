#include "MachineStatus.h"

void reportModbusStatus(uint16_t code) {
    static uint16_t lastCode = 0;
    static uint32_t lastMs = 0;
    uint32_t now = millis();

    if (code != lastCode || (uint32_t)(now - lastMs) >= 5000) {
        setMachineStatus(code);
        lastCode = code;
        lastMs = now;
    }
}

enum ModbusFaultDevice {
    MB_DEV_HMI = 0,
    MB_DEV_BT,
    MB_DEV_ET,
    MB_DEV_AIR,
    MB_DEV_DRUM,
    MB_DEV_RELAY,
    MB_DEV_VACUUM,
    MB_DEV_COUNT
};

uint8_t modbusFailCount[MB_DEV_COUNT] = {0};

void forceGasOffForModbusFault(uint16_t statusCode) {
    if (!MACHINE_HAS_GAS_CONTROL) return;

    START_GAS_BTN_R = 0;
    START_GAS_BTN_R_CP = 0;
    burnerValue_R = 0;
    burnerValue_R_CP = 0;
    gasPC = 0;
    gasPercent = 0;
    gasTiEn = 1;
    CH1_RL_OFF;
    nodeHMI.writeSingleRegister(START_GAS_BTN_W - 1, 0);
#if MACHINE_HAS_GAS_CONTROL
    dac_gas.setVoltage(0, false);
#endif

    if (!modbusGasCutoffLatched) {
        modbusGasCutoffLatched = true;
        reportModbusStatus(statusCode);
        setMachineStatus(STT_ERR_GAS_FAULT);
        if (enDebug) SerialComputer.println("MODBUS FAULT: GAS CUT OFF");
    }
}

void modbusNoteSuccess(uint8_t device) {
    if (device < MB_DEV_COUNT) modbusFailCount[device] = 0;
    for (uint8_t i = 0; i < MB_DEV_COUNT; i++) {
        if (modbusFailCount[i] >= MODBUS_GAS_CUTOFF_FAIL_LIMIT) return;
    }
    modbusGasCutoffLatched = false;
}

void modbusNoteFailure(uint8_t device, uint16_t statusCode) {
    if (device < MB_DEV_COUNT && modbusFailCount[device] < 255) {
        modbusFailCount[device]++;
        if (modbusFailCount[device] >= MODBUS_GAS_CUTOFF_FAIL_LIMIT) {
            forceGasOffForModbusFault(statusCode);
        }
    }
    reportModbusStatus(statusCode);
}

void enforceModbusGasCutoff() {
    if (!modbusGasCutoffLatched) return;
    START_GAS_BTN_R = 0;
    START_GAS_BTN_R_CP = 0;
    burnerValue_R = 0;
    burnerValue_R_CP = 0;
    gasPC = 0;
    gasPercent = 0;
    CH1_RL_OFF;
#if MACHINE_HAS_GAS_CONTROL
    dac_gas.setVoltage(0, false);
#endif
}

void reset_update(){
    uint8_t result = 0;
    uint16_t fst_address = 0;
    uint8_t Numaddress = 1;
    result = nodeHMI.readHoldingRegisters(fst_address, Numaddress); //160ms
    if(result == nodeHMI.ku8MBSuccess) {
        modbusNoteSuccess(MB_DEV_HMI);
        for(int i=0;i<20;i++){
            nodeHMI.writeSingleRegister(i, 0);
            delay(1);
        }
        nodeHMI.writeSingleCoil(SAMPLE_COIL_W-1, 0);  //Turn off trend graph sample
        nodeHMI.writeSingleCoil(LOCK_BUTTON_W-1, 0);  //Má»Ÿ khoÃ¡ select
        nodeHMI.writeSingleRegister(GENERAL_CONTROL_W-1, 0);  //Táº¯t chuÃ´ng
        nodeHMI.writeSingleRegister(CLEAR_HIS_CONTROL_W-1, 0);  //Clear trend graph
        nodeHMI.writeSingleRegister(WU_W-1, 0);
        nodeHMI.writeSingleRegister(TUNE_PERCENT_W-1, 0);
        tunePercent = 0;
        //Táº¯t tuning
        nodeHMI.writeSingleRegister(AUTO_PID_AIR_TU_W-1, 0); //Turn off auto tuning
         if(enDebug) SerialComputer.println("RESET HMI TURN OFF SUCCESS");
    }else{
        errorCount++;
        modbusNoteFailure(MB_DEV_HMI, STT_MB_HMI_ERROR);
        if(enDebug) SerialComputer.println("ERRO HMI TURN OFF BUTTON");
        BUZZ_ON; delay(100); BUZZ_OFF;  delay(100);
    }
    delay(5);
    buzzerTimerEn = 0; //Turn off buzzer
    rorBTSamp_1 = 0;
    rorBTSamp_2 = 0;
    SerialComputer.println("=> RESET DATA");
}

void upgradeGraphData(){

}

//Read Write $M HMI
void rwMemHMI(){
    uint8_t result = 0;
    uint16_t fst_address = 2001;
    uint8_t Numaddress = 53;
    result = nodeHMI.readHoldingRegisters(fst_address, Numaddress); //160ms
    if(result == nodeHMI.ku8MBSuccess){
        modbusNoteSuccess(MB_DEV_HMI);
        for(int i = 1; i < Numaddress; i++) {
            iMemHMI_CP[i] = nodeHMI.getResponseBuffer(i-1); // náº¡p vao máº£ng array táº¡m
        }

         //Charge duration
        if(chargeDuration_R != chargeDuration_R_CP){
            chargeDuration_R = chargeDuration_R_CP;    
        }

        //Drop duration
        if(dropDuration_R != dropDuration_R_CP){
            dropDuration_R = dropDuration_R_CP;    
        }

        //Escape duration
        if(escapeDuration_R != escapeDuration_R_CP){
            escapeDuration_R = escapeDuration_R_CP;    
        }

        //TP
        if(TpCalib_R != TpCalib_R_CP){
            TpCalib_R = TpCalib_R_CP;    
        }

        //DE
        if(DeCalib_R != DeCalib_R_CP){
            DeCalib_R = DeCalib_R_CP;    
        }

        //Temp controller reg
        if(tempRegister_R != tempRegister_R_CP){
            tempRegister_R = tempRegister_R_CP;    
        }

        //Afterburner set temp
        if(afterburnerSet_R != afterburnerSet_R_CP){
            afterburnerSet_R = afterburnerSet_R_CP;
            afterburnerSet_R_CV = afterburnerSet_R*10;    
        }

        //Pre gas auto set temp
        if(preGas_R != preGas_R_CP){
            preGas_R = preGas_R_CP;    
        }

        //Turn gas point to ignition/BBP
        if(turnGasPoint_R != turnGasPoint_R_CP){
            turnGasPoint_R = turnGasPoint_R_CP;
            turnGasPoint_R_CV = turnGasPoint_R*10;    
        }

        //Deviation temp for charge temp
        if(chTolerange_R != chTolerange_R_CP){
            chTolerange_R = chTolerange_R_CP;
            chTolerange_R_CV = chTolerange_R*10;    
        }

        //Trend graph sample time
        if(loop_R != loop_R_CP){
            loop_R = loop_R_CP;    
        }

        //Modbus ID for Artisan
        if(modbusID_R != modbusID_R_CP){
            modbusID_R = modbusID_R_CP;
            idBaudSetEn = 1; // Cho phÃ©p cáº­p nháº­p
            if (enDebug) { SerialComputer.print("HMI -> modbusID_R = "); SerialComputer.println(modbusID_R); }
        }

        //Modbus baudrate for Artisan
        if(modbusBaud_R != modbusBaud_R_CP){
            modbusBaud_R = modbusBaud_R_CP;
            idBaudSetEn = 1; // Cho phÃ©p cáº­p nháº­p
            if (enDebug) { SerialComputer.print("HMI -> modbusBaud_R = "); SerialComputer.println((uint16_t)modbusBaud_R); }
        }

        //Feeder timer
        if(feederSet_R != feederSet_R_CP){
            feederSet_R = feederSet_R_CP;    
        }

        // //ID Drum
        // if(idDrum_R != idDrum_R_CP){
        //     idDrum_R = idDrum_R_CP;    
        //     //Cáº­p nháº­p
        //     nodeDrum.begin(idDrum_R, SerialModbus);    // Read Drum Inverter
        // }

        //Reg Drum
        if(regDrum_R != regDrum_R_CP){
            regDrum_R = regDrum_R_CP;    
        }

        //Destoner timer
        if(destonerSet_R != destonerSet_R_CP){
            destonerSet_R = destonerSet_R_CP;    
        }

        //Yellow phase temp setup
        if(yellowPhase_R != yellowPhase_R_CP){
            yellowPhase_R = yellowPhase_R_CP;
            yellowPhase_R_CV = yellowPhase_R*10;    
        }

        //FCS phase temp setup
        if(fcsPhase_R != fcsPhase_R_CP){
            fcsPhase_R = fcsPhase_R_CP;
            fcsPhase_R_CV = fcsPhase_R*10;    
        }

        //Cool timer setup
        if(coolTimer_R != coolTimer_R_CP){
            coolTimer_R = coolTimer_R_CP;    
        }

        //Auto charge setup
        if(chargeTemp_R != chargeTemp_R_CP){
            chargeTemp_R = chargeTemp_R_CP;    
            chargeTemp_R_CV = chargeTemp_R;
        }

        //BT set value 
        if(btSV_R != btSV_R_CP){
            btSV_R = btSV_R_CP;
            btSV_R_CV = btSV_R*10;   
            SV_BT = btSV_R_CV;
            svEn = 1; //Set SV
        }

        //BT set value register 
        if(btSVReg_R != btSVReg_R_CP){
            btSVReg_R = btSVReg_R_CP;    
        }

        //Destoner pre start second
        if(destonerPre_R !=destonerPre_R_CP){
            destonerPre_R = destonerPre_R_CP;    
        }

        //Afterburner delay second running
        if(afterburnerNext_R !=afterburnerNext_R_CP){
            afterburnerNext_R = afterburnerNext_R_CP;    
        }

        //Max gas set
        if(maxGasSet_R !=maxGasSet_R_CP){
            maxGasSet_R = maxGasSet_R_CP;
        }
        // Trong rang AUTO: cho HẠ gas, CẤM NÂNG maxGas vượt trần đã lưu trong profile.
        // Chống ai đó phá trần an toàn giữa mẻ. Vượt → kéo về trần + ghi HMI để báo từ chối.
        if(progStatus == STT_PROGRAM_AUTO && progStep > 0 && sdMaxGasLoaded >= 0 && maxGasSet_R > sdMaxGasLoaded){
            maxGasSet_R = sdMaxGasLoaded;
            nodeHMI.writeSingleRegister(maxGasSet_W + 2000, sdMaxGasLoaded);
        }
        if(maxGasSet_R>100) maxGasSet_R=100;
        if(maxGasSet_R<0) maxGasSet_R=0;

        //BÃ¡o type báº¿p
        if(burnerPremix_R !=burnerPremix_R_CP){
            burnerPremix_R = burnerPremix_R_CP;    
        }

        //Khoáº£ng rÆ¡ báº­t gas
        if(preCool_R !=preCool_R_CP){
            preCool_R = preCool_R_CP;   
            preCool_R_CV = preCool_R*10;
        }

        //Fcs
        if(FcsCalib_R !=FcsCalib_R_CP){
            FcsCalib_R = FcsCalib_R_CP;   
        }

        //Lá»‡nh cÃ¢n
        if(netWTG_R != netWTG_R_CP){
            netWTG_R = netWTG_R_CP;   
        }

        //Lá»‡nh cÃ¢n
        if(autoLoader_R != autoLoader_R_CP){
            autoLoader_R = autoLoader_R_CP;   
        }

        if(MACHINE_HAS_DRUM_SPEED_CONTROL && drumSpeed_R != drumSpeed_R_CP){
            drumSpeed_R = drumSpeed_R_CP;
            drumHzTiEn = 1;
            STEP_DRUM_WRITE = "CHANGE DRUM";
        }

        if(airSpeed_R != airSpeed_R_CP){
            airSpeed_R = airSpeed_R_CP;
            airHzTiEn = 1;
        }

        if(MACHINE_HAS_GAS_CONTROL && burnerValue_R != burnerValue_R_CP){
            burnerValue_R = burnerValue_R_CP;
            gasTiEn = 1;
        }

        //BÃ¡o tá»± Ä‘á»™ng ngáº¯t gas
        if(autoOff_R !=autoOff_R_CP){
            autoOff_R = autoOff_R_CP;    
        }

        //Set ngÆ°á»¡ng cÃ¢n cao
        if(wThresholdHigh_R != wThresholdHigh_R_CP){
            wThresholdHigh_R = wThresholdHigh_R_CP;    
        }

        //Set ngÆ°á»¡ng cÃ¢n trung bÃ¬nh
        if(wThresholdMedium_R != wThresholdMedium_R_CP){
            wThresholdMedium_R = wThresholdMedium_R_CP;    
        }

        //Set ngÆ°á»¡ng cÃ¢n tháº¥p
        if(wThresholdLow_R != wThresholdLow_R_CP){
            wThresholdLow_R = wThresholdLow_R_CP;    
        }

        //Set sai sá»‘ cÃ¢n cao
        if(difHigh_R != difHigh_R_CP){
            difHigh_R = difHigh_R_CP;    
        }   

        //Set sai sá»‘ cÃ¢n trung bÃ¬nh
        if(difMedium_R != difMedium_R_CP){
            difMedium_R = difMedium_R_CP;    
        }

        //Set sai sá»‘ cÃ¢n tháº¥p
        if(difLow_R != difLow_R_CP){
            difLow_R = difLow_R_CP;    
        }   

        //Set lá»±c kÃ©o vacuum
        if(vacuumTraction_R != vacuumTraction_R_CP){
            vacuumTraction_R = vacuumTraction_R_CP;    
        }

        //Cá» tá»± Ä‘á»™ng fill cÃ  phÃª tá»« tÃ¡ch Ä‘Ã¡ sang silo
        if(autoFill_R != autoFill_R_CP){
            autoFill_R = autoFill_R_CP;    
        }

        //Thá»i gian tá»± Ä‘á»™ng fill cÃ  phÃª tá»« tÃ¡ch Ä‘Ã¡ sang silo
        if(autoFill_Time_R != autoFill_Time_R_CP){
            autoFill_Time_R = autoFill_Time_R_CP;    
        }

        if(MACHINE_HAS_VACUUM_SENSOR && vacuumSetFlag_R != vacuumSetFlag_R_CP){
            vacuumSetFlag_R = vacuumSetFlag_R_CP;  
        }

        if (MACHINE_HAS_VACUUM_SENSOR && vacuumSetpoint_R != vacuumSetpoint_R_CP) {
            vacuumSetpoint_R = vacuumSetpoint_R_CP;
            pidAirflowReset(); // Reset PID khi setpoint thay Ä‘á»•i
        }

        //Nháº­n khai bÃ¡o min pressure transmitter tá»« HMI
        if(minPT_R != minPT_R_CP){
            minPT_R = minPT_R_CP;  
        }

        //Nháº­n khai bÃ¡o max pressure transmitter tá»« HMI
        if(maxPT_R != maxPT_R_CP){
            maxPT_R = maxPT_R_CP;  
        }

        if(wuTime_R != wuTime_R_CP){
            wuTime_R = wuTime_R_CP;  
        }

        if(wuTemp_R != wuTemp_R_CP){
            wuTemp_R = wuTemp_R_CP;  
        }

    }else{
        errorCount++;
        modbusNoteFailure(MB_DEV_HMI, STT_MB_HMI_ERROR);
        if(enDebug) SerialComputer.println("ERRO HMI INTERNAL MEMORY DELTA");
        BUZZ_ON; delay(100); BUZZ_OFF;  delay(100);
    }
    delay(1);
}

void rwHMICoil()
{
    const uint16_t fst_address = 0;   // B1
    const uint16_t Numaddress  = 20;  // B1 â†’ B20

    uint8_t result = nodeHMI.readCoils(fst_address, Numaddress);

    if (result == nodeHMI.ku8MBSuccess)
    {
        modbusNoteSuccess(MB_DEV_HMI);
        // SerialComputer.print("B1-B20: ");

        uint16_t currentWord = 0;
        uint16_t prevWordIndex = 0xFFFF;

        for (uint16_t i = 0; i < Numaddress; i++)
        {
            uint16_t wordIndex = i / 16;
            uint8_t  bitIndex  = i % 16;

            if (wordIndex != prevWordIndex)
            {
                currentWord = nodeHMI.getResponseBuffer(wordIndex);
                prevWordIndex = wordIndex;
            }

            uint8_t coilStatus = (currentWord >> bitIndex) & 0x01;

            // SerialComputer.print(coilStatus);
            // SerialComputer.print(" ");
        }

        // SerialComputer.println();
    }
    else
    {
        errorCount++;
        modbusNoteFailure(MB_DEV_HMI, STT_MB_HMI_ERROR);

        if (enDebug)
        {
            SerialComputer.print("ERROR COILS | 0x");
            SerialComputer.println(result, HEX);
        }

        BUZZ_ON; delay(100);
        BUZZ_OFF; delay(100);
    }
}

//Read 40000 to 40047 HMI
void rwHMI_1(){
    uint8_t result = 0;
    uint16_t fst_address = 0;
    uint8_t Numaddress = 41;
    result = nodeHMI.readHoldingRegisters(fst_address, Numaddress); //160ms
    if(result == nodeHMI.ku8MBSuccess) 
    {
        modbusNoteSuccess(MB_DEV_HMI);
        for(int i = 1; i < Numaddress; i++) {
            dAddress_CP[i] = nodeHMI.getResponseBuffer(i-1); // náº¡p vao máº£ng array
        }
        // Date/time luÃ´n copy â€” khÃ´ng dÃ¹ng if(!=) vÃ¬ giÃ¡ trá»‹ khÃ´ng Ä‘á»•i trong lÃºc rang
        HOUR_R   = HOUR_R_CP;
        MINUTE_R = MINUTE_R_CP;
        DAY_R    = DAY_R_CP;
        MONTH_R  = MONTH_R_CP;
        YEAR_R   = YEAR_R_CP;
        //---------------------------READ HMI

        //Start
        if(START_BTN_R != START_BTN_R_CP){//Kiá»ƒm tra thay Ä‘á»•i cá»§a biáº¿n HMI
            START_BTN_R = START_BTN_R_CP;
        }

        //Gas button
        if(START_GAS_BTN_R != START_GAS_BTN_R_CP){//Kiá»ƒm tra thay Ä‘á»•i cá»§a biáº¿n HMI
            START_GAS_BTN_R = START_GAS_BTN_R_CP;
            mbs.Hreg(IGNITION_artisan_W, START_GAS_BTN_R);  delay(1);
        }

        //Drum/fan button
        if(DRUM_FAN_BTN_R != DRUM_FAN_BTN_R_CP){//Kiá»ƒm tra thay Ä‘á»•i cá»§a biáº¿n HMI
            DRUM_FAN_BTN_R = DRUM_FAN_BTN_R_CP;
            mbs.Hreg(DRUM_FAN_W, DRUM_FAN_BTN_R);     delay(1);
#if MACHINE_HAS_IO_RELAY_MODULE
            nodeIORelay.writeSingleCoil(CH1_IO_RL_W, DRUM_FAN_BTN_R); delay(1); // Relay ngoài 1: drum/fan
#endif
        }

        //Mixer button
        if(MIXER_BTN_R != MIXER_BTN_R_CP){//Kiá»ƒm tra thay Ä‘á»•i cá»§a biáº¿n HMI
            MIXER_BTN_R = MIXER_BTN_R_CP;
            mbs.Hreg(MIXER_W, MIXER_BTN_R);     delay(1);
#if MACHINE_HAS_IO_RELAY_MODULE
            nodeIORelay.writeSingleCoil(CH2_IO_RL_W, MIXER_BTN_R); delay(1); // Relay ngoài 2: mixer
#endif
        }
        
        //Cooling button
        if(COOLING_BTN_R != COOLING_BTN_R_CP){//Kiá»ƒm tra thay Ä‘á»•i cá»§a biáº¿n HMI
            COOLING_BTN_R = COOLING_BTN_R_CP;
            mbs.Hreg(MI_COOL_artisan_W, COOLING_BTN_R);     delay(1);
        }

        //Charge button
        if(CHARGE_BTN_R != CHARGE_BTN_R_CP){//Kiá»ƒm tra thay Ä‘á»•i cá»§a biáº¿n HMI
            CHARGE_BTN_R = CHARGE_BTN_R_CP;
            mbs.Hreg(CHARGE_artisan_W, CHARGE_BTN_R);       delay(1);
        }

        //Drop button
        if(DROP_BTN_R != DROP_BTN_R_CP){//Kiá»ƒm tra thay Ä‘á»•i cá»§a biáº¿n HMI
            DROP_BTN_R = DROP_BTN_R_CP;
            mbs.Hreg(DROP_artisan_W, DROP_BTN_R);
        }

        //Escape button
        if(ESCAPE_BTN_R != ESCAPE_BTN_R_CP){//Kiá»ƒm tra thay Ä‘á»•i cá»§a biáº¿n HMI
            ESCAPE_BTN_R = ESCAPE_BTN_R_CP;
            mbs.Hreg(ESCAPE_artisan_W, ESCAPE_BTN_R);       delay(1);
        }

        //AB button
        if(AB_BTN_R != AB_BTN_R_CP){//Kiá»ƒm tra thay Ä‘á»•i cá»§a biáº¿n HMI
            AB_BTN_R = AB_BTN_R_CP;
        }

        //Destoner button
        if(DESTONER_BTN_R != DESTONER_BTN_R_CP){//Kiá»ƒm tra thay Ä‘á»•i cá»§a biáº¿n HMI
            DESTONER_BTN_R = DESTONER_BTN_R_CP;
        }

        //Feeder button
        if(FEEDER_BTN_R != FEEDER_BTN_R_CP){//Kiá»ƒm tra thay Ä‘á»•i cá»§a biáº¿n HMI
            FEEDER_BTN_R = FEEDER_BTN_R_CP;
        }

        //Save button
        if(SAVE_BTN_R != SAVE_BTN_R_CP){//Kiá»ƒm tra thay Ä‘á»•i cá»§a biáº¿n HMI
            SAVE_BTN_R = SAVE_BTN_R_CP;
        }

        //PC control button
        if(PC_CONTROL_BTN_R != PC_CONTROL_BTN_R_CP){//Kiá»ƒm tra thay Ä‘á»•i cá»§a biáº¿n HMI
            PC_CONTROL_BTN_R = PC_CONTROL_BTN_R_CP;
        }

        //Äá»c slot file Ä‘Æ°á»£c chá»n
        if(SELECT_FILE_R != SELECT_FILE_R_CP){//Kiá»ƒm tra thay Ä‘á»•i cá»§a biáº¿n HMI
            SELECT_FILE_R = SELECT_FILE_R_CP;
            if(SELECT_FILE_R>0){
                sdReadStep = 1;//KÃ­ch hoáº¡t trÃ¬nh Ä‘á»c SD
            }
        }

        //Set date cho profile (Ä‘Ã£ macro trÃªn HMI)
        if(DATE_PROFILE_R != DATE_PROFILE_R_CP){//Kiá»ƒm tra thay Ä‘á»•i cá»§a biáº¿n HMI
            DATE_PROFILE_R = DATE_PROFILE_R_CP;
        }

        //XoÃ¡ 1 profile (káº¿t há»£p macro trÃªn HMI)
        if(DEL_PROFILE_R != DEL_PROFILE_R_CP){//Kiá»ƒm tra thay Ä‘á»•i cá»§a biáº¿n HMI
            DEL_PROFILE_R = DEL_PROFILE_R_CP;
            //XoÃ¡ file chá»‰ Ä‘á»‹nh
            sdLogStartEn = 1;
            nodeHMI.writeSingleRegister(DEL_PROFILE_W-1, 0); delay(1);
        }

        //XoÃ¡ all profile (káº¿t há»£p macro trÃªn HMI)
        if(DEL_ALLPROFILE_R != DEL_ALLPROFILE_R_CP){//Kiá»ƒm tra thay Ä‘á»•i cá»§a biáº¿n HMI
            DEL_ALLPROFILE_R = DEL_ALLPROFILE_R_CP;

            //XoÃ¡ toÃ n bá»™ file
            sdRemoveAll = 1;
            nodeHMI.writeSingleRegister(DEL_ALLPROFILE_W-1, 0); delay(1);
        }
        
        //Auto fill silo button
        if(AUTO_FS_BTN_R != AUTO_FS_BTN_R_CP){//Kiá»ƒm tra thay Ä‘á»•i cá»§a biáº¿n HMI
            AUTO_FS_BTN_R = AUTO_FS_BTN_R_CP;
        }

        //ThÃ´ng bÃ¡o tráº¡ng thÃ¡i Ä‘iá»u hÆ°á»›ng gas
        if(naviSourceGAS != CONTROL_NAVI_R_CP){//Kiá»ƒm tra thay Ä‘á»•i cá»§a biáº¿n HMI
            nodeHMI.writeSingleRegister(CONTROL_NAVI_W-1, naviSourceGAS);
        }

        if(SCRNUM_R != SCRNUM_R_CP){//Kiá»ƒm tra thay Ä‘á»•i cá»§a biáº¿n HMI
            SCRNUM_R = SCRNUM_R_CP;
        }

        if(MANUAL_AUTO_R != MANUAL_AUTO_R_CP){//Kiá»ƒm tra thay Ä‘á»•i cá»§a biáº¿n HMI
            MANUAL_AUTO_R = MANUAL_AUTO_R_CP;
            if(MANUAL_AUTO_R == 0){
                progStatus = STT_PROGRAM_SAVE; //Rang lÆ°u chÆ°Æ¡ng trÃ¬nh
            }
            if(MANUAL_AUTO_R == 1){
                progStatus = STT_PROGRAM_AUTO; //Cháº¡y auto
            }
        }
        
        //---------------------------WRITE HMI
        //Temperature â€” chá»‰ ghi khi thay Ä‘á»•i Ä‘á»ƒ giáº£m Modbus traffic
        if(Temperature_BT != Temperature_BT_CP){
            nodeHMI.writeSingleRegister(BT_HMI_W-1, Temperature_BT);
        }
        if(Temperature_ET != Temperature_ET_CP){
            nodeHMI.writeSingleRegister(ET_HMI_W-1, Temperature_ET);
        }

        if (AUTO_PID_AIR_TU_R != AUTO_PID_AIR_TU_R_CP) {
            AUTO_PID_AIR_TU_R = AUTO_PID_AIR_TU_R_CP;
            if (AUTO_PID_AIR_TU_R == 1) pidFactoryTuneStart();  // báº¥m Báº¬T â†’ báº¯t Ä‘áº§u quÃ©t
            else                         pidFactoryTuneStop();   // báº¥m Táº®T â†’ dá»«ng kháº©n cáº¥p
        }

        if(REFRESH_LOAD_PF_R != REFRESH_LOAD_PF_R_CP){
            REFRESH_LOAD_PF_R = REFRESH_LOAD_PF_R_CP;
            enLoadDateProfile = 1; // KÃ­ch hoáº¡t cá» Ä‘á»ƒ load láº¡i ngÃ y thÃ¡ng cá»§a táº¥t cáº£ há»“ sÆ¡ tá»« SD card vÃ o HMI (sau khi cÃ³ lá»‡nh tá»« HMI)
        }

        //Warm up báº¯t Ä‘áº§u
        if(WU_R != WU_R_CP){
            WU_R = WU_R_CP;
        }

        // //Air Flow Freq
        // if(Airflow_Freq != Airflow_Freq_CP){//Kiá»ƒm tra thay Ä‘á»•i cá»§a biáº¿n HMI
        //     Airflow_Freq = Airflow_Freq_CP;
        //     node3.writeSingleRegister(AIRFLOW_FREQ_HMI, Airflow_Freq);
        // }

        // //Drum Freq
        // if(Drum_Freq != Drum_Freq_CP){//Kiá»ƒm tra thay Ä‘á»•i cá»§a biáº¿n HMI
        //     Drum_Freq = Drum_Freq_CP;
        //     node3.writeSingleRegister(DRUM_FREQ_HMI, Drum_Freq);
        // }

        // //Air underpressure
        // if(airPressure_FB_PLC != airPressure_FB_PLC_CP){//Kiá»ƒm tra thay Ä‘á»•i cá»§a biáº¿n HMI
        //     airPressure_FB_PLC = airPressure_FB_PLC_CP;
        //     node3.writeSingleRegister(AIR_PRESSURE_HMI, airPressure_FB_PLC);
        // }

        //---------------------------END

        //Modbus slave
        mbs.task();
        yield();
        
    }else{
        errorCount++;
        modbusNoteFailure(MB_DEV_HMI, STT_MB_HMI_ERROR);
        if(enDebug) SerialComputer.println("ERRO HMI DELTA 0 46");
        BUZZ_ON; delay(100); BUZZ_OFF;  delay(100);
    }
    delay(10);
}

void rwHMI_2(){
    uint8_t cnt_i=0;
    uint8_t result = 0;
    uint16_t fst_address = 59;
    uint8_t Numaddress = 27;
    result = nodeHMI.readHoldingRegisters(fst_address, Numaddress); //160ms
    if(result == nodeHMI.ku8MBSuccess) 
    {
        modbusNoteSuccess(MB_DEV_HMI);
        for(int i = fst_address; i < fst_address+Numaddress; i++) {
            dAddress_CP[i] = nodeHMI.getResponseBuffer(cnt_i-1); // náº¡p vao máº£ng array
            cnt_i++;
        }

        //Write register
        //BÃ¡o gas
        if(gasSignal != GAS_SIGNAL_HMI_R_CP){
            nodeHMI.writeSingleRegister(GAS_SIGNAL_HMI_W-1, gasSignal); 
        }

        //GAS % SHOW
        if(gasPercent*10 != GAS_HMI_R_CP){
            nodeHMI.writeSingleRegister(GAS_HMI_W-1, gasPercent*10); 
        }

        //DRUM % SHOW
        if(drumPercent*10 != DRUM_HMI_R_CP){
            nodeHMI.writeSingleRegister(DRUM_HMI_W-1, drumPercent*10); 
            drumHzTiEn = 1;
            STEP_DRUM_WRITE = "CHANGE DRUM";
        }

        //AIR % SHOW
        if(airflowPercent*10 != AIRFLOW_HMI_R_CP){
            nodeHMI.writeSingleRegister(AIRFLOW_HMI_W-1, airflowPercent*10); 
        }
        
        if(WU_R == 0){
            //Min roast
            if(minRoast != MIN_HMI_R_CP){
                nodeHMI.writeSingleRegister(MIN_HMI_W-1, minRoast);  
            }

            //Sec roast
            if(secRoast != SEC_HMI_R_CP){
                nodeHMI.writeSingleRegister(SEC_HMI_W-1, secRoast);  
            }
        }

        if(rorBT != ROR_BT_HMI_R_CP){
            nodeHMI.writeSingleRegister(ROR_BT_HMI_W-1, rorBT);    
        }

        if(rorET != ROR_ET_HMI_R_CP){
            nodeHMI.writeSingleRegister(ROR_ET_HMI_W-1, rorET);
        }

        // Shared progress bar â€” written here only, set by preheat() or PID_Airflow
        if(tunePercent != TUNE_PERCENT_R_CP){
            nodeHMI.writeSingleRegister(TUNE_PERCENT_W-1, tunePercent);
        }

        //-------------------------------------Roast data show
        //TP temp show HMI
        if(BT_TP_SAVE != TP_HMI_R_CP){
            nodeHMI.writeSingleRegister(TP_HMI_W-1, BT_TP_SAVE);  
        }
        //TP min show HMI
        if(TIME_TP_MIN_SAVE != TP_MIN_HMI_R_CP){
            nodeHMI.writeSingleRegister(TP_MIN_HMI_W-1, TIME_TP_MIN_SAVE);  
        }
        //TP sec show HMI
        if(TIME_TP_SEC_SAVE != TP_SEC_HMI_R_CP){
            nodeHMI.writeSingleRegister(TP_SEC_HMI_W-1, TIME_TP_SEC_SAVE);  
        }

        //YELLOW temp show HMI
        if(BT_YELLOW_SAVE != YELLOW_HMI_R_CP){
            nodeHMI.writeSingleRegister(YELLOW_HMI_W-1, BT_YELLOW_SAVE);  
        }
        //YELLOW min show HMI
        if(TIME_YELLOW_MIN_SAVE != YELLOW_MIN_HMI_R_CP){
            nodeHMI.writeSingleRegister(YELLOW_MIN_HMI_W-1, TIME_YELLOW_MIN_SAVE);  
        }
        //YELLOW sec show HMI
        if(TIME_YELLOW_SEC_SAVE != YELLOW_SEC_HMI_R_CP){
            nodeHMI.writeSingleRegister(YELLOW_SEC_HMI_W-1, TIME_YELLOW_SEC_SAVE);  
        }

        //FCS temp show HMI
        if(BT_FCS_SAVE != FCS_HMI_R_CP){
            nodeHMI.writeSingleRegister(FCS_HMI_W-1, BT_FCS_SAVE);  
        }

        //FCS min show HMI
        if(TIME_FCS_MIN_SAVE != FCS_MIN_HMI_R_CP){
            nodeHMI.writeSingleRegister(FCS_MIN_HMI_W-1, TIME_FCS_MIN_SAVE);  
        }

        //FCS sec show HMI
        if(TIME_FCS_SEC_SAVE != FCS_SEC_HMI_R_CP){
            nodeHMI.writeSingleRegister(FCS_SEC_HMI_W-1, TIME_FCS_SEC_SAVE); 
        }

        //Pháº§n trÄƒm dev show HMI
        if(PER_DEV_SAVE != DEV_HMI_R_CP){
            nodeHMI.writeSingleRegister(DEV_HMI_W-1, PER_DEV_SAVE); 
        }

        //Min dev show HMI
        if(TIME_DEV_MIN_SAVE != DEV_MIN_HMI_R_CP){
            nodeHMI.writeSingleRegister(DEV_MIN_HMI_W-1, TIME_DEV_MIN_SAVE); 
        }

        //Sec dev show HMI
        if(TIME_DEV_SEC_SAVE != DEV_SEC_HMI_R_CP){
            nodeHMI.writeSingleRegister(DEV_SEC_HMI_W-1, TIME_DEV_SEC_SAVE); 
        }

        //Show charge temp khi chÆ°Æ¡ng trÃ¬nh Ä‘ang cháº¡y
        if(BT_CHARGE_SAVE != CHARGE_DATA_HMI_R_CP){
            nodeHMI.writeSingleRegister(CHARGE_DATA_HMI_W-1, BT_CHARGE_SAVE); 
        }

        //Show Drop temp khi chÆ°Æ¡ng trÃ¬nh Ä‘ang cháº¡y
        if(BT_DROP_SAVE != DROP_DATA_HMI_R_CP){
            nodeHMI.writeSingleRegister(DROP_DATA_HMI_W-1, BT_DROP_SAVE); 
        }

        //Show cân — gửi netW100 (×100) để HMI hiển thị đủ 2 số lẻ (cân ≤200kg nên ≤20000, vừa 1 register)
        if(NETW_R_CP != netW100){
            nodeHMI.writeSingleRegister(NETW_W-1, netW100);
        }

        //Show tá»‘c Ä‘á»™ trá»‘ng rang
        if(Drum_Freq != Drum_Freq_CP){
            Drum_Freq = Drum_Freq_CP;
            nodeHMI.writeSingleRegister(DRUM_SPD_W-1, Drum_Freq); 
        }

        if(Diff_Air != DIFF_AIR_R_CP){
            nodeHMI.writeSingleRegister(DIFF_AIR_W-1, Diff_Air);
        }

        //Show PID 0800 setting, 87
        if(PID_0800_R != PID_0800_R_CP){
            nodeHMI.writeSingleRegister(PID_0800_W-1, vacuumSetFlag_R);
        }

        if(rorKG != ROR_KG_R_CP){
            nodeHMI.writeSingleRegister(ROR_KG_W-1, rorKG);
            ROR_KG_R_CP = rorKG;   // reg 91 không nằm trong dải đọc lại nên tự cập nhật _CP
        }

        


        //---------------------------WRITE HMI
        //---------------------------Damper feedback
        //Damper A Feedback
        // if(damper_A_FB_PLC != damper_A_FB_PLC_CP){
        //     damper_A_FB_PLC = damper_A_FB_PLC_CP;//LÆ°u tá»« array táº¡m vÃ o array chÃ­nh
        //     nodeHMI.writeSingleRegister(DAMPER_A_FB_HMI, damper_A_FB_PLC); //Damper A Feedback
        // }
        //---------------------------END


        //---------------------------WRITE COIL PLC
        //Gá»­i giÃ¡ trá»‹ Ä‘iá»u khiá»ƒn Van G
        // if(DAMPER_G_BTN != DAMPER_G_BTN_CP){//Kiá»ƒm tra thay Ä‘á»•i cá»§a biáº¿n HMI
        //     DAMPER_G_BTN = DAMPER_G_BTN_CP;//LÆ°u tá»« array táº¡m vÃ o array chÃ­nh
        //     node10.writeSingleCoil(DAMPER_G_COIL_PLC, DAMPER_G_BTN); //Damper G
        // }
        //---------------------------END

    }else{
        errorCount++;
        modbusNoteFailure(MB_DEV_HMI, STT_MB_HMI_ERROR);
        if(enDebug) SerialComputer.println("ERRO HMI DELTA 140 147");
        BUZZ_ON; delay(100); BUZZ_OFF;  delay(100);
    }
    flushMachineStatus();  // Flush one status code to HMI (queue-based, non-blocking)
    delay(10);
}

void readTempBT(){
    uint8_t   result = 0;
    result = nodeBT.readHoldingRegisters(tempRegister_R, 1);// Data trá» Ä‘á»‹a chá»‰ á»Ÿ Ä‘Ã¢y theo parem (Äá»‹a Chá»‰, Chiá»u DÃ i)
    if (result == nodeBT.ku8MBSuccess){
        modbusNoteSuccess(MB_DEV_BT);
        Temperature_BT = nodeBT.getResponseBuffer(0);// Em láº¥y data ra sÃ i báº±ng máº£ng data[i] vá»›i code hiá»‡n táº¡i thÃ¬ data[0]: Nhiá»‡t Äá»™ (PV) -- data[1]: nhiá»‡t Ä‘á»™ SET (SV)...b
        if(svEn){
            nodeBT.writeSingleRegister(btSVReg_R, btSV_R_CV);
            svEn = false;
        }
    }
    else{
        errorCount++;
        modbusNoteFailure(MB_DEV_BT, STT_MB_BT_ERROR);
        if(enDebug) SerialComputer.println(" ERROR READ BT");
        BUZZ_ON; delay(100); BUZZ_OFF; delay(100);
    }
    delay(10);
}

void readTempET(){
    uint8_t   result = 0;
    result = nodeET.readHoldingRegisters(tempRegister_R, 1);// Data trá» Ä‘á»‹a chá»‰ á»Ÿ Ä‘Ã¢y theo parem (Äá»‹a Chá»‰, Chiá»u DÃ i)
    if (result == nodeET.ku8MBSuccess)
    {
        modbusNoteSuccess(MB_DEV_ET);
        Temperature_ET = nodeET.getResponseBuffer(0);// Em láº¥y data ra sÃ i báº±ng máº£ng data[i] vá»›i code hiá»‡n táº¡i thÃ¬ data[0]: Nhiá»‡t Äá»™ (PV) -- data[1]: nhiá»‡t Ä‘á»™ SET (SV)...b
        // SV_ET = nodeET.getResponseBuffer(1);
        // if(svEn){
        //     nodeET.writeSingleRegister(btSVReg_R, btSV_R_CV);
        //     svEn = false;
        // }
        
    }
    else{
        errorCount++;
        modbusNoteFailure(MB_DEV_ET, STT_MB_ET_ERROR);
        if(enDebug) SerialComputer.println(" ERROR READ ET");
        BUZZ_ON; delay(100); BUZZ_OFF; delay(100);
    }
    delay(10);
}

void readAirflowINV(){
    uint8_t   result = 0;
    result = nodeAir.readHoldingRegisters(AIR_INV_FREQ_READ_REGISTER, 1);// Data trá» Ä‘á»‹a chá»‰ á»Ÿ Ä‘Ã¢y theo parem (Äá»‹a Chá»‰, Chiá»u DÃ i)
    delay(5);
    if (result == nodeAir.ku8MBSuccess)
    {
        modbusNoteSuccess(MB_DEV_AIR);
        Airflow_Freq_CP = nodeAir.getResponseBuffer(0);// Em láº¥y data ra sÃ i báº±ng máº£ng data[i] vá»›i code hiá»‡n táº¡i thÃ¬ data[0]: Nhiá»‡t Äá»™ (PV) -- data[1]: nhiá»‡t Ä‘á»™ SET (SV)... 
    }
    else{
        errorCount++;
        modbusNoteFailure(MB_DEV_AIR, STT_MB_AIR_ERROR);
        if(enDebug) SerialComputer.println(" ERROR READ AIR INV");
        BUZZ_ON; delay(100); BUZZ_OFF; delay(100);
    }
    delay(5);
}

void readWriteDrumINV(){
    uint8_t   result = 0;
    result = nodeDrum.readHoldingRegisters(DRUM_INV_FREQ_READ_REGISTER, 1);// Data trá» Ä‘á»‹a chá»‰ á»Ÿ Ä‘Ã¢y theo parem (Äá»‹a Chá»‰, Chiá»u DÃ i)
    delay(5);
    if (result == nodeDrum.ku8MBSuccess){
        modbusNoteSuccess(MB_DEV_DRUM);
        Drum_Freq_CP = nodeDrum.getResponseBuffer(0);//
        if(drumHzTimer>1){
            drumHz = map(drumPercent,0,100,3000,5000);
            nodeDrum.writeSingleRegister(DRUM_INV_FREQ_WRITE_REGISTER, drumHz);
            drumHzTiEn = 0;   
            drumHzTimer = 0;  
            STEP_DRUM_WRITE = "DONE";
        }
    }
    else{
        errorCount++;
        modbusNoteFailure(MB_DEV_DRUM, STT_MB_DRUM_ERROR);
        if(enDebug) SerialComputer.println(" ERROR READ DRUM INV");
        BUZZ_ON; delay(100); BUZZ_OFF; delay(100);
    }
    delay(5);
}

void readWriteAirINV_PID(){
    uint8_t   result = 0;
    result = nodeAir.readHoldingRegisters(AIR_INV_PID_0800_REGISTER, 1);// Data trá» Ä‘á»‹a chá»‰ á»Ÿ Ä‘Ã¢y theo parem (Äá»‹a Chá»‰, Chiá»u DÃ i)
    delay(5);
    if (result == nodeAir.ku8MBSuccess){
        modbusNoteSuccess(MB_DEV_AIR);
        PID_0800_R_CP = nodeAir.getResponseBuffer(0);//
    }
    else{
        errorCount++;
        modbusNoteFailure(MB_DEV_AIR, STT_MB_AIR_ERROR);
        if(enDebug) SerialComputer.println(" ERROR READ DRUM INV PID");
        BUZZ_ON; delay(100); BUZZ_OFF; delay(100);
    }
    delay(5);
}

// Äá»c tÃ­n hiá»‡u Ã¡p suáº¥t Ã¢m (underpressure)
// Cáº£m biáº¿n Ä‘Æ°á»£c ná»‘i vÃ o chÃ¢n ACI cá»§a biáº¿n táº§n quáº¡t giÃ³
// TÃ­n hiá»‡u ACI tráº£ vá» dáº£i 0~10000, Ä‘Æ°á»£c quy Ä‘á»•i sang Ä‘Æ¡n vá»‹ thá»±c táº¿ (minPT_R ~ maxPT_R)
void readUnder(){
    uint8_t result = 0;

    // Node đọc vacuum: drum (slave 4) hoặc quạt gió (slave 5) tùy MACHINE_VACUUM_FROM_DRUM
#if MACHINE_VACUUM_FROM_DRUM
    ModbusMaster& nodeVacuum = nodeDrum;
#else
    ModbusMaster& nodeVacuum = nodeAir;
#endif

    // Äá»c thanh ghi 8716 cá»§a biáº¿n táº§n quáº¡t giÃ³ qua Modbus
    // Thanh ghi 8716 chá»©a giÃ¡ trá»‹ tÃ­n hiá»‡u analog ACI (0~10000)
    result = nodeVacuum.readHoldingRegisters(AIR_INV_ACI_RAW_REGISTER, 1);
    delay(5);

    if (result == nodeVacuum.ku8MBSuccess){
        modbusNoteSuccess(MB_DEV_VACUUM);

        // â”€â”€ BÆ°á»›c 1: Láº¥y giÃ¡ trá»‹ thÃ´ tá»« buffer Modbus (0~10000) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        raw_Diff_Air = nodeVacuum.getResponseBuffer(0);

        // â”€â”€ BÆ°á»›c 2: Lá»c Kalman trá»±c tiáº¿p trÃªn raw â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        //
        // PhiÃªn báº£n cÅ© dÃ¹ng 2 táº§ng lá»c chá»“ng nhau:
        //   raw â†’ EMA (al=0.8) â†’ Kalman (e_mea=200, e_est=5, q=0.1) â†’ Diff_Air
        //
        // Váº¥n Ä‘á» cá»§a phiÃªn báº£n cÅ©:
        //   - EMA vÃ  Kalman Ä‘á»u táº¡o ra Ä‘á»™ trá»… riÃªng â†’ cá»™ng dá»“n thÃ nh Ä‘á»™ trá»… kÃ©p
        //   - Kalman cÅ© cÃ³ q=0.1 ráº¥t nhá»: sau vÃ i chu ká»³, Kalman gain há»™i tá»¥ vá»
        //     gáº§n 0, tá»©c bá»™ lá»c gáº§n nhÆ° Bá»Ž QUA phÃ©p Ä‘o má»›i, chá»‰ giá»¯ Æ°á»›c lÆ°á»£ng cÅ©
        //     â†’ Ä‘Ã¢y lÃ  nguyÃªn nhÃ¢n chÃ­nh khiáº¿n Diff_Air pháº£n há»“i ráº¥t cháº­m
        //
        // PhiÃªn báº£n má»›i chá»‰ dÃ¹ng 1 táº§ng Kalman vá»›i tham sá»‘ Ä‘iá»u chá»‰nh láº¡i:
        //   raw â†’ Kalman (e_mea=50, e_est=50, q=1.0) â†’ Diff_Air
        //
        // Ã nghÄ©a tá»«ng tham sá»‘ SimpleKalmanFilter(e_mea, e_est, q):
        //
        //   e_mea = 50  (sai sá»‘ Ä‘o lÆ°á»ng - measurement error)
        //     CÅ© = 200: tin tÆ°á»Ÿng phÃ©p Ä‘o ÃT â†’ bá»™ lá»c kÃ©o ngÆ°á»£c vá» model â†’ cháº­m
        //     Má»›i = 50 : tin tÆ°á»Ÿng phÃ©p Ä‘o NHIá»€U HÆ N â†’ bÃ¡m theo giÃ¡ trá»‹ Ä‘o nhanh hÆ¡n
        //     Giáº£m e_mea â†’ Kalman gain tÄƒng â†’ pháº£n há»“i NHANH hÆ¡n
        //
        //   e_est = 50  (sai sá»‘ Æ°á»›c lÆ°á»£ng ban Ä‘áº§u - estimation error)
        //     CÅ© = 5  : model ban Ä‘áº§u ráº¥t "cháº¯c cháº¯n" â†’ khÃ´ng chá»‹u cáº­p nháº­t nhanh
        //     Má»›i = 50: cÃ¢n báº±ng vá»›i e_mea â†’ Kalman khÃ´ng bá»‹ lá»‡ch vá» phÃ­a model cÅ©
        //
        //   q = 1.0  (process noise - nhiá»…u quÃ¡ trÃ¬nh)
        //     ÄÃ¢y lÃ  tham sá»‘ quan trá»ng nháº¥t Ä‘á»ƒ Ä‘iá»u chá»‰nh tá»‘c Ä‘á»™ pháº£n há»“i:
        //     CÅ© = 0.1: q nhá» â†’ Kalman tin ráº±ng há»‡ thá»‘ng Ã­t thay Ä‘á»•i â†’ gain giáº£m
        //               dáº§n vá» 0 sau vÃ i chu ká»³ â†’ gáº§n nhÆ° khÃ´ng cáº­p nháº­t ná»¯a â†’ CHáº¬M
        //     Má»›i = 1.0: q lá»›n â†’ Kalman tin há»‡ thá»‘ng thay Ä‘á»•i nhanh â†’ duy trÃ¬ gain
        //               á»Ÿ má»©c cao â†’ liÃªn tá»¥c bÃ¡m theo phÃ©p Ä‘o â†’ NHANH gáº¥p Ä‘Ã´i
        //
        // CÃ´ng thá»©c Kalman gain (K) má»—i chu ká»³:
        //   e_est_new = e_est_old + q          â† q lá»›n â†’ e_est tÄƒng nhanh
        //   K = e_est_new / (e_est_new + e_mea) â† e_est lá»›n â†’ K lá»›n â†’ bÃ¡m Ä‘o nhiá»u
        //   estimate = estimate + K * (raw - estimate)
        //   e_est = (1 - K) * e_est_new        â† K lá»›n â†’ e_est giáº£m Ã­t â†’ chu ká»³ sau váº«n nhanh
        //
        // Äiá»u chá»‰nh nhanh/cháº­m chá»‰ cáº§n thay q trong Define.h:
        //   q = 0.5 â†’ mÆ°á»£t hÆ¡n, cháº­m hÆ¡n má»™t chÃºt  (náº¿u nhiá»…u quÃ¡ nhiá»u)
        //   q = 1.0 â†’ cÃ¢n báº±ng nhanh/mÆ°á»£t           (khuyáº¿n nghá»‹)
        //   q = 2.0 â†’ nhanh hÆ¡n ná»¯a, nhiá»…u hÆ¡n      (náº¿u cáº§n pháº£n há»“i tá»©c thÃ¬)
        //
        float filtered = diff_KalmanFilter.updateEstimate(raw_Diff_Air);

        // â”€â”€ BÆ°á»›c 3: Quy Ä‘á»•i tÃ­n hiá»‡u ACI (0~10000) sang Ä‘Æ¡n vá»‹ Ã¡p suáº¥t thá»±c táº¿
        //
        // minPT_R: giÃ¡ trá»‹ Ã¡p suáº¥t tháº¥p nháº¥t cáº£m biáº¿n Ä‘o Ä‘Æ°á»£c (VD: -500 Pa)
        // maxPT_R: giÃ¡ trá»‹ Ã¡p suáº¥t cao nháº¥t cáº£m biáº¿n Ä‘o Ä‘Æ°á»£c  (VD: +500 Pa)
        //
        // CÃ´ng thá»©c ná»™i suy tuyáº¿n tÃ­nh:
        //   Diff_Air = minPT_R + (filtered / 10000) * (maxPT_R - minPT_R)
        //
        // VÃ­ dá»¥ vá»›i minPT_R=-500, maxPT_R=500:
        //   filtered =     0 â†’ Diff_Air = -500  (Ã¡p suáº¥t tháº¥p nháº¥t)
        //   filtered =  5000 â†’ Diff_Air =    0  (giá»¯a dáº£i)
        //   filtered = 10000 â†’ Diff_Air = +500  (Ã¡p suáº¥t cao nháº¥t)
        //
        Diff_Air = minPT_R + (filtered / 10000.0) * (maxPT_R - minPT_R);

    }
    else{
        // Äá»c Modbus tháº¥t báº¡i â†’ tÄƒng bá»™ Ä‘áº¿m lá»—i vÃ  buzz bÃ¡o hiá»‡u
        errorCount++;
        modbusNoteFailure(MB_DEV_VACUUM, STT_MB_VACUUM_ERROR);
        if(enDebug) SerialComputer.println(" ERROR READ UNDER");
        BUZZ_ON; delay(100); BUZZ_OFF; delay(100);
    }
    delay(5);
}

void rwIORelayCoil(){
    uint8_t result = 0;
    uint16_t fst_address = 0;
    uint8_t Numaddress = 1;
    result = nodeIORelay.readCoils(fst_address, Numaddress); //160ms
    if(result == nodeIORelay.ku8MBSuccess){
        modbusNoteSuccess(MB_DEV_RELAY);
        for(int i = 1; i < Numaddress; i++) {
            cAddress_CP[i] = nodeIORelay.getResponseBuffer(i-1);    
        }

    }else{
        errorCount++;
        modbusNoteFailure(MB_DEV_RELAY, STT_MB_RELAY_ERROR);
        if(enDebug) SerialComputer.println("ERRO I/O COILS RELAY MODBUS MODULE");
        BUZZ_ON; delay(100); BUZZ_OFF;  delay(100);    
    }
    delay(5);
}

// Ghi STATUS_MC lên HMI CHỈ khi giá trị đổi (0 = not ready, 1 = ready).
// Tránh ghi register liên tục lên bus khi trạng thái không đổi.
void setStatusMC(uint8_t v) {
    static int16_t last = -1;   // -1 = chưa ghi lần nào
    if (v == last) return;
    last = v;
    nodeHMI.writeSingleRegister(STATUS_MC_W - 1, v);
}

// Cập nhật STATUS_MC theo sức khỏe Modbus lúc chạy: thiết bị nào lỗi liên tiếp ≥ ngưỡng
// (cùng ngưỡng cắt gas) → not ready (0); tất cả đọc lại OK → ready (1).
// setStatusMC change-gated nên gọi mỗi vòng loop() vẫn chỉ ghi HMI khi đổi.
void updateStatusMC() {
    for (uint8_t i = 0; i < MB_DEV_COUNT; i++) {
        if (modbusFailCount[i] >= MODBUS_GAS_CUTOFF_FAIL_LIMIT) { setStatusMC(0); return; }
    }
    setStatusMC(1);
}

void checkError() {
    uint8_t result = 0;
    uint16_t buzzer_delay = 1000;

    // Buzz N láº§n vá»›i chu ká»³ ms
    auto buzzN = [](int n, int ms = 100) {
        for (int j = 0; j < n; j++) { BUZZ_ON; delay(ms); BUZZ_OFF; delay(ms); }
    };

    // Chuyá»ƒn mÃ£ lá»—i Modbus sang chuá»—i mÃ´ táº£
    auto errMsg = [](uint8_t code) -> String {
        switch (code) {
            case 0x01: return "Ham khong hop le";
            case 0x02: return "Dia chi du lieu khong hop le";
            case 0x03: return "Gia tri du lieu khong hop le";
            case 0x04: return "Thiet bi slave bi loi";
            case 0xE0: return "Sai ID slave";
            case 0xE1: return "Sai function code";
            case 0xE2: return "Qua thoi gian cho";
            case 0xE3: return "Sai CRC";
            default:   return "Loi khong xac dinh";
        }
    };

    // Kiá»ƒm tra káº¿t ná»‘i Modbus, láº·p vÃ´ háº¡n cho Ä‘áº¿n khi thÃ nh cÃ´ng
    auto checkMB = [&](ModbusMaster& node, uint16_t reg, int buzzCount,
                        bool isCoil, const String& name, uint16_t failStatus,
                        uint8_t device, uint16_t runtimeStatus) {
        result = isCoil ? node.readCoils(reg, 1) : node.readHoldingRegisters(reg, 1);
        while (result != node.ku8MBSuccess) {
            delay(15);  // ThÃªm Ä‘á»™ trá»… nhá» Ä‘á»ƒ trÃ¡nh quÃ¡ táº£i bus
            modbusNoteFailure(device, runtimeStatus);
            if (failStatus > 0) nodeHMI.writeSingleRegister(STT_W - 1, failStatus);
            SerialComputer.println(" LOI " + name + " | 0x" + String(result, HEX) + " - " + errMsg(result));
            buzzN(buzzCount);       // Buzz theo sá»‘ láº§n quy Ä‘á»‹nh cho tá»«ng thiáº¿t bá»‹
            delay(buzzer_delay);    // Chá» trÆ°á»›c khi thá»­ láº¡i
            result = isCoil ? node.readCoils(reg, 1) : node.readHoldingRegisters(reg, 1);
        }
        modbusNoteSuccess(device);
        SerialComputer.println("=> " + name + " OK");
    };

    // Helper: send status to HMI once (HMI must be connected first)
    auto sendSTT = [](uint16_t code) {
        nodeHMI.writeSingleRegister(STT_W - 1, code);
    };

    // Check HMI first — once connected, immediately send BOOT then CHECK_HMI
    if (chHMIFlag) {
        checkMB(nodeHMI, 0, 1, false, "HMI", 0, MB_DEV_HMI, STT_MB_HMI_ERROR);  // block until HMI responds
        sendSTT(STT_SYSTEM_BOOT);               // HMI now connected, announce boot
        setStatusMC(0);                         // not ready: đang dò thiết bị
        delay(600);                             // hold 600ms so HMI can read
        sendSTT(STT_STARTUP_HMI_OK);
        delay(600);
    }

    rwMemHMI();  // read $M registers

    // BT sensor
    if (chBTFlag) {
        sendSTT(STT_STARTUP_CHECK_BT); delay(50);
        checkMB(nodeBT, tempRegister_R, 2, false, "BT", STT_STARTUP_BT_FAIL, MB_DEV_BT, STT_MB_BT_ERROR);
        sendSTT(STT_STARTUP_BT_OK); delay(50);
    }

    // ET sensor
    if (chETFlag) {
        sendSTT(STT_STARTUP_CHECK_ET); delay(50);
        checkMB(nodeET, tempRegister_R, 3, false, "ET", STT_STARTUP_ET_FAIL, MB_DEV_ET, STT_MB_ET_ERROR);
        sendSTT(STT_STARTUP_ET_OK); delay(50);
    }

    // Airflow inverter
    if (chAirFlag) {
        sendSTT(STT_STARTUP_CHECK_AIR);
        checkMB(nodeAir, AIR_INV_FREQ_READ_REGISTER, 4, false, "AIRFLOW INV", STT_STARTUP_AIR_FAIL, MB_DEV_AIR, STT_MB_AIR_ERROR);
        sendSTT(STT_STARTUP_AIR_OK);
    }

    // Drum inverter
    if (chDrumFlag) {
        sendSTT(STT_STARTUP_CHECK_DRUM);
        checkMB(nodeDrum, DRUM_INV_FREQ_READ_REGISTER, 5, false, "DRUM INV", STT_STARTUP_DRUM_FAIL, MB_DEV_DRUM, STT_MB_DRUM_ERROR);
        sendSTT(STT_STARTUP_DRUM_OK);
    }

    // IO relay module
    if (chIORelayFlag) {
        sendSTT(STT_STARTUP_CHECK_RELAY);
        checkMB(nodeIORelay, 0, 2, true, "IO RELAY", STT_STARTUP_RELAY_FAIL, MB_DEV_RELAY, STT_MB_RELAY_ERROR);
        sendSTT(STT_STARTUP_RELAY_OK);
    }

    // SD card
    if (chSDFlag) {
        sendSTT(STT_STARTUP_CHECK_SD);
        while (!SD.begin(chipSelect)) {
            sendSTT(STT_SD_INIT_FAIL);
            SerialComputer.println(" LOI SD");
            buzzN(1, 500);
            delay(buzzer_delay);
        }
        SerialComputer.println("=> SD OK");
        sendSTT(STT_STARTUP_SD_OK);
    }

    // All OK
    sendSTT(STT_SYSTEM_READY);
    setStatusMC(1);                             // ready: tất cả thiết bị OK
    BUZZ_ON; delay(1000); BUZZ_OFF;
}

//BÃ¡o chÃ¡y
// void alarmSignal(){
//     if(
//         Temperature_BT > 3500
//         || Temperature_ET > SV_ET
//         || Temp_Chamber > SV_Chamber
//         || Temp_CylconeAir > SV_CylconeAir
//     ){
//         RED_BUZZER_STM_CP = true;    
//     }else{
//         RED_BUZZER_STM_CP = false;
//         GREEN_YELLOW_STM_CP = true;     
//     }
// }

