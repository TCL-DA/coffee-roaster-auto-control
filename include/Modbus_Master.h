void reset_update(){
    uint8_t result = 0;
    uint16_t fst_address = 0;
    uint8_t Numaddress = 1;
    result = nodeHMI.readHoldingRegisters(fst_address, Numaddress); //160ms
    if(result == nodeHMI.ku8MBSuccess) {
        for(int i=0;i<20;i++){
            nodeHMI.writeSingleRegister(i, 0);
            delay(1);
        }
        nodeHMI.writeSingleCoil(SAMPLE_COIL_W-1, 0);  //Turn off trend graph sample
        nodeHMI.writeSingleCoil(LOCK_BUTTON_W-1, 0);  //Mở khoá select
        nodeHMI.writeSingleRegister(GENERAL_CONTROL_W-1, 0);  //Tắt chuông
        nodeHMI.writeSingleRegister(CLEAR_HIS_CONTROL_W-1, 0);  //Clear trend graph
        //Tắt tuning
        nodeHMI.writeSingleRegister(AUTO_PID_AIR_TU_W-1, 0); //Turn off auto tuning
         if(enDebug) SerialComputer.println("RESET HMI TURN OFF SUCCESS");
    }else{
        errorCount++;
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
    uint8_t Numaddress = 51;
    result = nodeHMI.readHoldingRegisters(fst_address, Numaddress); //160ms
    if(result == nodeHMI.ku8MBSuccess){
        for(int i = 1; i < Numaddress; i++) {
            iMemHMI_CP[i] = nodeHMI.getResponseBuffer(i-1); // nạp vao mảng array tạm
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
            idBaudSetEn = 1; // Cho phép cập nhập   
        }

        //Modbus baudrate for Artisan
        if(modbusBaud_R != modbusBaud_R_CP){
            modbusBaud_R = modbusBaud_R_CP;   
            idBaudSetEn = 1; // Cho phép cập nhập  
        }

        //Feeder timer
        if(feederSet_R != feederSet_R_CP){
            feederSet_R = feederSet_R_CP;    
        }

        // //ID Drum
        // if(idDrum_R != idDrum_R_CP){
        //     idDrum_R = idDrum_R_CP;    
        //     //Cập nhập
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
        if(maxGasSet_R>100) maxGasSet_R=100;
        if(maxGasSet_R<0) maxGasSet_R=0;

        //Báo type bếp
        if(burnerPremix_R !=burnerPremix_R_CP){
            burnerPremix_R = burnerPremix_R_CP;    
        }

        //Khoảng rơ bật gas
        if(preCool_R !=preCool_R_CP){
            preCool_R = preCool_R_CP;   
            preCool_R_CV = preCool_R*10;
        }

        //Fcs
        if(FcsCalib_R !=FcsCalib_R_CP){
            FcsCalib_R = FcsCalib_R_CP;   
        }

        //Lệnh cân
        if(netWTG_R != netWTG_R_CP){
            netWTG_R = netWTG_R_CP;   
        }

        //Lệnh cân
        if(autoLoader_R != autoLoader_R_CP){
            autoLoader_R = autoLoader_R_CP;   
        }

        //Báo tự động ngắt gas
        if(autoOff_R !=autoOff_R_CP){
            autoOff_R = autoOff_R_CP;    
        }

        //Set ngưỡng cân cao
        if(wThresholdHigh_R != wThresholdHigh_R_CP){
            wThresholdHigh_R = wThresholdHigh_R_CP;    
        }

        //Set ngưỡng cân trung bình
        if(wThresholdMedium_R != wThresholdMedium_R_CP){
            wThresholdMedium_R = wThresholdMedium_R_CP;    
        }

        //Set ngưỡng cân thấp
        if(wThresholdLow_R != wThresholdLow_R_CP){
            wThresholdLow_R = wThresholdLow_R_CP;    
        }

        //Set sai số cân cao
        if(difHigh_R != difHigh_R_CP){
            difHigh_R = difHigh_R_CP;    
        }   

        //Set sai số cân trung bình
        if(difMedium_R != difMedium_R_CP){
            difMedium_R = difMedium_R_CP;    
        }

        //Set sai số cân thấp
        if(difLow_R != difLow_R_CP){
            difLow_R = difLow_R_CP;    
        }   

        //Set lực kéo vacuum
        if(vacuumTraction_R != vacuumTraction_R_CP){
            vacuumTraction_R = vacuumTraction_R_CP;    
        }

        //Cờ tự động fill cà phê từ tách đá sang silo
        if(autoFill_R != autoFill_R_CP){
            autoFill_R = autoFill_R_CP;    
        }

        //Thời gian tự động fill cà phê từ tách đá sang silo
        if(autoFill_Time_R != autoFill_Time_R_CP){
            autoFill_Time_R = autoFill_Time_R_CP;    
        }

        if(vacuumSetFlag_R != vacuumSetFlag_R_CP){
            vacuumSetFlag_R = vacuumSetFlag_R_CP;  
        }

        if (vacuumSetpoint_R != vacuumSetpoint_R_CP) {
            vacuumSetpoint_R = vacuumSetpoint_R_CP;
            pidAirflowReset(); // Reset PID khi setpoint thay đổi
        }

        //Nhận khai báo min pressure transmitter từ HMI
        if(minPT_R != minPT_R_CP){
            minPT_R = minPT_R_CP;  
        }

        //Nhận khai báo max pressure transmitter từ HMI
        if(maxPT_R != maxPT_R_CP){
            maxPT_R = maxPT_R_CP;  
        }

    }else{
        errorCount++;
        if(enDebug) SerialComputer.println("ERRO HMI INTERNAL MEMORY DELTA");
        BUZZ_ON; delay(100); BUZZ_OFF;  delay(100);
    }
    delay(1);
}

void rwHMICoil()
{
    const uint16_t fst_address = 0;   // B1
    const uint16_t Numaddress  = 20;  // B1 → B20

    uint8_t result = nodeHMI.readCoils(fst_address, Numaddress);

    if (result == nodeHMI.ku8MBSuccess)
    {
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
    uint8_t Numaddress = 33;
    result = nodeHMI.readHoldingRegisters(fst_address, Numaddress); //160ms
    if(result == nodeHMI.ku8MBSuccess) 
    {
        for(int i = 1; i < Numaddress; i++) {
            dAddress_CP[i] = nodeHMI.getResponseBuffer(i-1); // nạp vao mảng array
        }
        //---------------------------READ HMI

        //Start
        if(START_BTN_R != START_BTN_R_CP){//Kiểm tra thay đổi của biến HMI
            START_BTN_R = START_BTN_R_CP;
        }

        //Gas button
        if(START_GAS_BTN_R != START_GAS_BTN_R_CP){//Kiểm tra thay đổi của biến HMI
            START_GAS_BTN_R = START_GAS_BTN_R_CP;
            mbs.Hreg(IGNITION_artisan_W, START_GAS_BTN_R);  delay(1);
        }

        //Cooling button
        if(COOLING_BTN_R != COOLING_BTN_R_CP){//Kiểm tra thay đổi của biến HMI
            COOLING_BTN_R = COOLING_BTN_R_CP;
            mbs.Hreg(MI_COOL_artisan_W, COOLING_BTN_R);     delay(1);
        }

        //Charge button
        if(CHARGE_BTN_R != CHARGE_BTN_R_CP){//Kiểm tra thay đổi của biến HMI
            CHARGE_BTN_R = CHARGE_BTN_R_CP;
            mbs.Hreg(CHARGE_artisan_W, CHARGE_BTN_R);       delay(1);
        }

        //Drop button
        if(DROP_BTN_R != DROP_BTN_R_CP){//Kiểm tra thay đổi của biến HMI
            DROP_BTN_R = DROP_BTN_R_CP;
            mbs.Hreg(DROP_artisan_W, DROP_BTN_R);
        }

        //Escape button
        if(ESCAPE_BTN_R != ESCAPE_BTN_R_CP){//Kiểm tra thay đổi của biến HMI
            ESCAPE_BTN_R = ESCAPE_BTN_R_CP;
            mbs.Hreg(ESCAPE_artisan_W, ESCAPE_BTN_R);       delay(1);
        }

        //AB button
        if(AB_BTN_R != AB_BTN_R_CP){//Kiểm tra thay đổi của biến HMI
            AB_BTN_R = AB_BTN_R_CP;
        }

        //Destoner button
        if(DESTONER_BTN_R != DESTONER_BTN_R_CP){//Kiểm tra thay đổi của biến HMI
            DESTONER_BTN_R = DESTONER_BTN_R_CP;
        }

        //Feeder button
        if(FEEDER_BTN_R != FEEDER_BTN_R_CP){//Kiểm tra thay đổi của biến HMI
            FEEDER_BTN_R = FEEDER_BTN_R_CP;
        }

        //Save button
        if(SAVE_BTN_R != SAVE_BTN_R_CP){//Kiểm tra thay đổi của biến HMI
            SAVE_BTN_R = SAVE_BTN_R_CP;
        }

        //PC control button
        if(PC_CONTROL_BTN_R != PC_CONTROL_BTN_R_CP){//Kiểm tra thay đổi của biến HMI
            PC_CONTROL_BTN_R = PC_CONTROL_BTN_R_CP;
        }

        //Đọc slot file được chọn
        if(SELECT_FILE_R != SELECT_FILE_R_CP){//Kiểm tra thay đổi của biến HMI
            SELECT_FILE_R = SELECT_FILE_R_CP;
            if(SELECT_FILE_R>0){
                sdReadStep = 1;//Kích hoạt trình đọc SD
            }
        }

        //Set date cho profile (đã macro trên HMI)
        if(DATE_PROFILE_R != DATE_PROFILE_R_CP){//Kiểm tra thay đổi của biến HMI
            DATE_PROFILE_R = DATE_PROFILE_R_CP;
        }

        //Xoá 1 profile (kết hợp macro trên HMI)
        if(DEL_PROFILE_R != DEL_PROFILE_R_CP){//Kiểm tra thay đổi của biến HMI
            DEL_PROFILE_R = DEL_PROFILE_R_CP;
            //Xoá file chỉ định
            sdLogStartEn = 1;
            nodeHMI.writeSingleRegister(DEL_PROFILE_W-1, 0); delay(1);
        }

        //Xoá all profile (kết hợp macro trên HMI)
        if(DEL_ALLPROFILE_R != DEL_ALLPROFILE_R_CP){//Kiểm tra thay đổi của biến HMI
            DEL_ALLPROFILE_R = DEL_ALLPROFILE_R_CP;

            //Xoá toàn bộ file
            sdRemoveAll = 1;
            nodeHMI.writeSingleRegister(DEL_ALLPROFILE_W-1, 0); delay(1);
        }
        
        //Auto fill silo button
        if(AUTO_FS_BTN_R != AUTO_FS_BTN_R_CP){//Kiểm tra thay đổi của biến HMI
            AUTO_FS_BTN_R = AUTO_FS_BTN_R_CP;
            nodeIORelay.writeSingleCoil(CH1_IO_RL_W, AUTO_FS_BTN_R); delay(1);
        }

        //Thông báo trạng thái điều hướng gas
        if(naviSourceGAS != CONTROL_NAVI_R_CP){//Kiểm tra thay đổi của biến HMI
            nodeHMI.writeSingleRegister(CONTROL_NAVI_W-1, naviSourceGAS);
        }

        if(SCRNUM_R != SCRNUM_R_CP){//Kiểm tra thay đổi của biến HMI
            SCRNUM_R = SCRNUM_R_CP;
            if(SCRNUM_R == 2){
                progStatus = STT_PROGRAM_SAVE; //Rang lưu chương trình
            }
            if(SCRNUM_R == 3){
                progStatus = STT_PROGRAM_AUTO; //Chạy auto
            }
        }
        
        //---------------------------WRITE HMI
        //Temperature
        nodeHMI.writeSingleRegister(BT_HMI_W-1, Temperature_BT); //BT
        nodeHMI.writeSingleRegister(ET_HMI_W-1, Temperature_ET); //ET

        if (AUTO_PID_AIR_TU_R != AUTO_PID_AIR_TU_R_CP) {
            AUTO_PID_AIR_TU_R = AUTO_PID_AIR_TU_R_CP;
            if (AUTO_PID_AIR_TU_R == 1) pidFactoryTuneStart();  // bấm BẬT → bắt đầu quét
            else                         pidFactoryTuneStop();   // bấm TẮT → dừng khẩn cấp
        }
        
        // //Air Flow Freq
        // if(Airflow_Freq != Airflow_Freq_CP){//Kiểm tra thay đổi của biến HMI
        //     Airflow_Freq = Airflow_Freq_CP;
        //     node3.writeSingleRegister(AIRFLOW_FREQ_HMI, Airflow_Freq);
        // }

        // //Drum Freq
        // if(Drum_Freq != Drum_Freq_CP){//Kiểm tra thay đổi của biến HMI
        //     Drum_Freq = Drum_Freq_CP;
        //     node3.writeSingleRegister(DRUM_FREQ_HMI, Drum_Freq);
        // }

        // //Air underpressure
        // if(airPressure_FB_PLC != airPressure_FB_PLC_CP){//Kiểm tra thay đổi của biến HMI
        //     airPressure_FB_PLC = airPressure_FB_PLC_CP;
        //     node3.writeSingleRegister(AIR_PRESSURE_HMI, airPressure_FB_PLC);
        // }

        //---------------------------END

        //Modbus slave
        mbs.task();
        yield();
        
    }else{
        errorCount++;
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
        for(int i = fst_address; i < fst_address+Numaddress; i++) {
            dAddress_CP[i] = nodeHMI.getResponseBuffer(cnt_i-1); // nạp vao mảng array
            cnt_i++;
        }

        //Write register
        //Báo gas
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
        
        //Min roast
        if(minRoast != MIN_HMI_R_CP){
            nodeHMI.writeSingleRegister(MIN_HMI_W-1, minRoast);  
        }

        //Sec roast
        if(secRoast != SEC_HMI_R_CP){
            nodeHMI.writeSingleRegister(SEC_HMI_W-1, secRoast);  
        }

        if(rorBT != ROR_BT_HMI_R_CP){
            nodeHMI.writeSingleRegister(ROR_BT_HMI_W-1, rorBT);    
        }

        if(rorET != ROR_ET_HMI_R_CP){
            nodeHMI.writeSingleRegister(ROR_ET_HMI_W-1, rorET);    
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

        //Phần trăm dev show HMI
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

        //Show charge temp khi chương trình đang chạy
        if(BT_CHARGE_SAVE != CHARGE_DATA_HMI_R_CP){
            nodeHMI.writeSingleRegister(CHARGE_DATA_HMI_W-1, BT_CHARGE_SAVE); 
        }

        //Show Drop temp khi chương trình đang chạy
        if(BT_DROP_SAVE != DROP_DATA_HMI_R_CP){
            nodeHMI.writeSingleRegister(DROP_DATA_HMI_W-1, BT_DROP_SAVE); 
        }

        //Show cân
        if(NETW_R_CP != netW){
            nodeHMI.writeSingleRegister(NETW_W-1, netW); 
        }

        //Show tốc độ trống rang
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

        


        //---------------------------WRITE HMI
        //---------------------------Damper feedback
        //Damper A Feedback
        // if(damper_A_FB_PLC != damper_A_FB_PLC_CP){
        //     damper_A_FB_PLC = damper_A_FB_PLC_CP;//Lưu từ array tạm vào array chính
        //     nodeHMI.writeSingleRegister(DAMPER_A_FB_HMI, damper_A_FB_PLC); //Damper A Feedback
        // }
        //---------------------------END


        //---------------------------WRITE COIL PLC
        //Gửi giá trị điều khiển Van G
        // if(DAMPER_G_BTN != DAMPER_G_BTN_CP){//Kiểm tra thay đổi của biến HMI
        //     DAMPER_G_BTN = DAMPER_G_BTN_CP;//Lưu từ array tạm vào array chính
        //     node10.writeSingleCoil(DAMPER_G_COIL_PLC, DAMPER_G_BTN); //Damper G
        // }
        //---------------------------END

    }else{
        errorCount++;
        if(enDebug) SerialComputer.println("ERRO HMI DELTA 140 147");
        BUZZ_ON; delay(100); BUZZ_OFF;  delay(100);
    }
    delay(10);
}

void readTempBT(){
    uint8_t   result = 0;
    result = nodeBT.readHoldingRegisters(tempRegister_R, 1);// Data trỏ địa chỉ ở đây theo parem (Địa Chỉ, Chiều Dài)
    if (result == nodeBT.ku8MBSuccess){
        Temperature_BT = nodeBT.getResponseBuffer(0);// Em lấy data ra sài bằng mảng data[i] với code hiện tại thì data[0]: Nhiệt Độ (PV) -- data[1]: nhiệt độ SET (SV)...b
        if(svEn){
            nodeBT.writeSingleRegister(btSVReg_R, btSV_R_CV);
            svEn = false;
        }
    }
    else{
        errorCount++;
        if(enDebug) SerialComputer.println(" ERROR READ BT");
        BUZZ_ON; delay(100); BUZZ_OFF; delay(100);
    }
    delay(10);
}

void readTempET(){
    uint8_t   result = 0;
    result = nodeET.readHoldingRegisters(tempRegister_R, 1);// Data trỏ địa chỉ ở đây theo parem (Địa Chỉ, Chiều Dài)
    if (result == nodeET.ku8MBSuccess)
    {
        Temperature_ET = nodeET.getResponseBuffer(0);// Em lấy data ra sài bằng mảng data[i] với code hiện tại thì data[0]: Nhiệt Độ (PV) -- data[1]: nhiệt độ SET (SV)...b
        // SV_ET = nodeET.getResponseBuffer(1);
        // if(svEn){
        //     nodeET.writeSingleRegister(btSVReg_R, btSV_R_CV);
        //     svEn = false;
        // }
        
    }
    else{
        errorCount++;
        if(enDebug) SerialComputer.println(" ERROR READ ET");
        BUZZ_ON; delay(100); BUZZ_OFF; delay(100);
    }
    delay(10);
}

void readAirflowINV(){
    uint8_t   result = 0;
    result = nodeAir.readHoldingRegisters(8451, 1);// Data trỏ địa chỉ ở đây theo parem (Địa Chỉ, Chiều Dài)
    delay(5);
    if (result == nodeAir.ku8MBSuccess)
    {
        Airflow_Freq_CP = nodeAir.getResponseBuffer(0);// Em lấy data ra sài bằng mảng data[i] với code hiện tại thì data[0]: Nhiệt Độ (PV) -- data[1]: nhiệt độ SET (SV)... 
    }
    else{
        errorCount++;
        if(enDebug) SerialComputer.println(" ERROR READ AIR INV");
        BUZZ_ON; delay(100); BUZZ_OFF; delay(100);
    }
    delay(5);
}

void readWriteDrumINV(){
    uint8_t   result = 0;
    result = nodeDrum.readHoldingRegisters(8451, 1);// Data trỏ địa chỉ ở đây theo parem (Địa Chỉ, Chiều Dài)
    delay(5);
    if (result == nodeDrum.ku8MBSuccess){
        Drum_Freq_CP = nodeDrum.getResponseBuffer(0);//
        if(drumHzTimer>1){
            drumHz = map(drumPercent,0,100,3000,5000);
            nodeDrum.writeSingleRegister(8193, drumHz);
            drumHzTiEn = 0;   
            drumHzTimer = 0;  
            STEP_DRUM_WRITE = "DONE";
        }
    }
    else{
        errorCount++;
        if(enDebug) SerialComputer.println(" ERROR READ DRUM INV");
        BUZZ_ON; delay(100); BUZZ_OFF; delay(100);
    }
    delay(5);
}

void readWriteAirINV_PID(){
    uint8_t   result = 0;
    result = nodeAir.readHoldingRegisters(2048, 1);// Data trỏ địa chỉ ở đây theo parem (Địa Chỉ, Chiều Dài)
    delay(5);
    if (result == nodeAir.ku8MBSuccess){
        PID_0800_R_CP = nodeAir.getResponseBuffer(0);//
    }
    else{
        errorCount++;
        if(enDebug) SerialComputer.println(" ERROR READ DRUM INV PID");
        BUZZ_ON; delay(100); BUZZ_OFF; delay(100);
    }
    delay(5);
}

// Đọc tín hiệu áp suất âm (underpressure)
// Cảm biến được nối vào chân ACI của biến tần quạt gió
// Tín hiệu ACI trả về dải 0~10000, được quy đổi sang đơn vị thực tế (minPT_R ~ maxPT_R)
void readUnder(){
    uint8_t result = 0;

    // Đọc thanh ghi 8716 của biến tần quạt gió qua Modbus
    // Thanh ghi 8716 chứa giá trị tín hiệu analog ACI (0~10000)
    result = nodeAir.readHoldingRegisters(8716, 1);
    delay(5);

    if (result == nodeAir.ku8MBSuccess){

        // ── Bước 1: Lấy giá trị thô từ buffer Modbus (0~10000) ──────────────
        raw_Diff_Air = nodeAir.getResponseBuffer(0);

        // ── Bước 2: Lọc Kalman trực tiếp trên raw ───────────────────────────
        //
        // Phiên bản cũ dùng 2 tầng lọc chồng nhau:
        //   raw → EMA (al=0.8) → Kalman (e_mea=200, e_est=5, q=0.1) → Diff_Air
        //
        // Vấn đề của phiên bản cũ:
        //   - EMA và Kalman đều tạo ra độ trễ riêng → cộng dồn thành độ trễ kép
        //   - Kalman cũ có q=0.1 rất nhỏ: sau vài chu kỳ, Kalman gain hội tụ về
        //     gần 0, tức bộ lọc gần như BỎ QUA phép đo mới, chỉ giữ ước lượng cũ
        //     → đây là nguyên nhân chính khiến Diff_Air phản hồi rất chậm
        //
        // Phiên bản mới chỉ dùng 1 tầng Kalman với tham số điều chỉnh lại:
        //   raw → Kalman (e_mea=50, e_est=50, q=1.0) → Diff_Air
        //
        // Ý nghĩa từng tham số SimpleKalmanFilter(e_mea, e_est, q):
        //
        //   e_mea = 50  (sai số đo lường - measurement error)
        //     Cũ = 200: tin tưởng phép đo ÍT → bộ lọc kéo ngược về model → chậm
        //     Mới = 50 : tin tưởng phép đo NHIỀU HƠN → bám theo giá trị đo nhanh hơn
        //     Giảm e_mea → Kalman gain tăng → phản hồi NHANH hơn
        //
        //   e_est = 50  (sai số ước lượng ban đầu - estimation error)
        //     Cũ = 5  : model ban đầu rất "chắc chắn" → không chịu cập nhật nhanh
        //     Mới = 50: cân bằng với e_mea → Kalman không bị lệch về phía model cũ
        //
        //   q = 1.0  (process noise - nhiễu quá trình)
        //     Đây là tham số quan trọng nhất để điều chỉnh tốc độ phản hồi:
        //     Cũ = 0.1: q nhỏ → Kalman tin rằng hệ thống ít thay đổi → gain giảm
        //               dần về 0 sau vài chu kỳ → gần như không cập nhật nữa → CHẬM
        //     Mới = 1.0: q lớn → Kalman tin hệ thống thay đổi nhanh → duy trì gain
        //               ở mức cao → liên tục bám theo phép đo → NHANH gấp đôi
        //
        // Công thức Kalman gain (K) mỗi chu kỳ:
        //   e_est_new = e_est_old + q          ← q lớn → e_est tăng nhanh
        //   K = e_est_new / (e_est_new + e_mea) ← e_est lớn → K lớn → bám đo nhiều
        //   estimate = estimate + K * (raw - estimate)
        //   e_est = (1 - K) * e_est_new        ← K lớn → e_est giảm ít → chu kỳ sau vẫn nhanh
        //
        // Điều chỉnh nhanh/chậm chỉ cần thay q trong Define.h:
        //   q = 0.5 → mượt hơn, chậm hơn một chút  (nếu nhiễu quá nhiều)
        //   q = 1.0 → cân bằng nhanh/mượt           (khuyến nghị)
        //   q = 2.0 → nhanh hơn nữa, nhiễu hơn      (nếu cần phản hồi tức thì)
        //
        float filtered = diff_KalmanFilter.updateEstimate(raw_Diff_Air);

        // ── Bước 3: Quy đổi tín hiệu ACI (0~10000) sang đơn vị áp suất thực tế
        //
        // minPT_R: giá trị áp suất thấp nhất cảm biến đo được (VD: -500 Pa)
        // maxPT_R: giá trị áp suất cao nhất cảm biến đo được  (VD: +500 Pa)
        //
        // Công thức nội suy tuyến tính:
        //   Diff_Air = minPT_R + (filtered / 10000) * (maxPT_R - minPT_R)
        //
        // Ví dụ với minPT_R=-500, maxPT_R=500:
        //   filtered =     0 → Diff_Air = -500  (áp suất thấp nhất)
        //   filtered =  5000 → Diff_Air =    0  (giữa dải)
        //   filtered = 10000 → Diff_Air = +500  (áp suất cao nhất)
        //
        Diff_Air = minPT_R + (filtered / 10000.0) * (maxPT_R - minPT_R);

    }
    else{
        // Đọc Modbus thất bại → tăng bộ đếm lỗi và buzz báo hiệu
        errorCount++;
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
        for(int i = 1; i < Numaddress; i++) {
            cAddress_CP[i] = nodeIORelay.getResponseBuffer(i-1);    
        }

    }else{
        errorCount++;
        if(enDebug) SerialComputer.println("ERRO I/O COILS RELAY MODBUS MODULE");
        BUZZ_ON; delay(100); BUZZ_OFF;  delay(100);    
    }
    delay(5);
}

void checkError() {
    uint8_t result = 0;
    uint16_t buzzer_delay = 1000;

    // Buzz N lần với chu kỳ ms
    auto buzzN = [](int n, int ms = 100) {
        for (int j = 0; j < n; j++) { BUZZ_ON; delay(ms); BUZZ_OFF; delay(ms); }
    };

    // Chuyển mã lỗi Modbus sang chuỗi mô tả
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

    // Kiểm tra kết nối Modbus, lặp vô hạn cho đến khi thành công
    auto checkMB = [&](ModbusMaster& node, uint16_t reg, int buzzCount,
                        bool isCoil, const String& name) {
        result = isCoil ? node.readCoils(reg, 1) : node.readHoldingRegisters(reg, 1);
        while (result != node.ku8MBSuccess) {
            delay(15);  // Thêm độ trễ nhỏ để tránh quá tải bus
            SerialComputer.println(" LOI " + name + " | 0x" + String(result, HEX) + " - " + errMsg(result));
            buzzN(buzzCount);       // Buzz theo số lần quy định cho từng thiết bị
            delay(buzzer_delay);    // Chờ trước khi thử lại
            result = isCoil ? node.readCoils(reg, 1) : node.readHoldingRegisters(reg, 1);
        }
        SerialComputer.println("=> " + name + " OK");
    };

    // Kiểm tra lần lượt từng thiết bị
    if (chHMIFlag)     checkMB(nodeHMI,     0,              1, false, "HMI");
    rwMemHMI();        // Đọc ghi biến $M HMI
    if (chBTFlag)      checkMB(nodeBT,      tempRegister_R, 2, false, "BT");
    if (chETFlag)      checkMB(nodeET,      tempRegister_R, 3, false, "ET");
    if (chAirFlag)     checkMB(nodeAir,     8451,           4, false, "AIRFLOW INV");
    if (chDrumFlag)    checkMB(nodeDrum,    8451,           5, false, "DRUM INV");
    if (chIORelayFlag) checkMB(nodeIORelay, 0,              2, true,  "IO RELAY");

    // Kiểm tra thẻ SD, lặp vô hạn cho đến khi đọc được
    if (chSDFlag) {
        while (!SD.begin(chipSelect)) {
            SerialComputer.println(" LOI SD");
            buzzN(1, 500);
            delay(buzzer_delay);
        }
        SerialComputer.println("=> SD OK");
    }

    // Tất cả thiết bị OK => buzz báo hiệu
    BUZZ_ON; delay(1000); BUZZ_OFF;
}

//Báo cháy
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
