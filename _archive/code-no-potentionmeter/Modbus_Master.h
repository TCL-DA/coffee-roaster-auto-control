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
    }else{
        errorCount++;
        if(enDebug) SerialComputer.println("ERRO HMI TURN OFF BUTTON");
        BUZZ_ON; delay(100); BUZZ_OFF;  delay(100);
    }
    delay(5);
    buzzerTimerEn = 0; //Turn off buzzer
    rorBTSamp_1 = 0;
    rorBTSamp_2 = 0;
}

void upgradeGraphData(){

}

//Read Write $M HMI
void rwMemHMI(){
    uint8_t result = 0;
    uint16_t fst_address = 2001;
    uint8_t Numaddress = 38;
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

        // Điều khiển Drum inverter
        if (drumSpeed_R != drumSpeed_R_CP) {
            drumSpeed_R = drumSpeed_R_CP;  // Cập nhật giá trị Drum
            drumHzTiEn = 1;               // Kích hoạt xử lý Drum
            STEP_DRUM_WRITE = "CHANGING DRUM HZ"; // Trạng thái thay đổi Drum
        }

        // Điều khiển Airflow inverter
        if (airSpeed_R != airSpeed_R_CP) {
            airSpeed_R = airSpeed_R_CP;   // Cập nhật giá trị Airflow
            airHzTiEn = 1;                // Kích hoạt xử lý Airflow
            STEP_AIRFLOW_WRITE = "CHANGING AIRFLOW HZ"; // Trạng thái thay đổi Airflow
        }

        // Điều khiển Gas valve
        if (burnerValue_R != burnerValue_R_CP) {
            burnerValue_R = burnerValue_R_CP;  // Cập nhật giá trị Gas              
            STEP_GAS_WRITE = "CHANGING GAS VALVE"; // Trạng thái thay đổi Gas
        }


    }else{
        errorCount++;
        if(enDebug) SerialComputer.println("ERRO HMI INTERNAL MEMORY DELTA");
        BUZZ_ON; delay(100); BUZZ_OFF;  delay(100);
    }
    delay(1);
}

void rwHMICoil(){
    uint8_t result = 0;
    uint16_t fst_address = 0;
    uint8_t Numaddress = 1;
    result = nodeHMI.readCoils(fst_address, Numaddress); //160ms
    if(result == nodeHMI.ku8MBSuccess){
        for(int i = 1; i < Numaddress; i++) {
            cAddress_CP[i] = nodeHMI.getResponseBuffer(i-1);    
            // SerialComputer.print(cAddresss_CP[i]);
            // SerialComputer.print(" ");
        }
        // Serial.println("");

        //Start sample history trend graph
        if(SAMPLE_COIL_R != SAMPLE_COIL_R_CP){
            SAMPLE_COIL_R = SAMPLE_COIL_R_CP;
        }

    }else{
        errorCount++;
        if(enDebug) SerialComputer.println("ERRO COILS DELTA");
        BUZZ_ON; delay(100); BUZZ_OFF;  delay(100);    
    }
    delay(5);
}

//Read 40000 to 40047 HMI
void rwHMI_1(){
    uint8_t result = 0;
    uint16_t fst_address = 0;
    uint8_t Numaddress = 25;
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
            nodeHMI.writeSingleRegister(DEL_PROFILE_W-1, 0);
        }

        //Xoá all profile (kết hợp macro trên HMI)
        if(DEL_ALLPROFILE_R != DEL_ALLPROFILE_R_CP){//Kiểm tra thay đổi của biến HMI
            DEL_ALLPROFILE_R = DEL_ALLPROFILE_R_CP;

            //Xoá toàn bộ file
            sdRemoveAll = 1;
            nodeHMI.writeSingleRegister(DEL_ALLPROFILE_W-1, 0);
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

        // //GAS % SHOW
        // if(gasPercent*10 != GAS_HMI_R_CP){
        //     nodeHMI.writeSingleRegister(GAS_HMI_W-1, gasPercent*10); 
        // }

        // //DRUM % SHOW
        // if(drumPercent*10 != DRUM_HMI_R_CP){
        //     nodeHMI.writeSingleRegister(DRUM_HMI_W-1, drumPercent*10); 
        //     drumHzTiEn = 1;
        //     STEP_DRUM_WRITE = "CHANGE DRUM";
        // }

        // //AIR % SHOW
        // if(airflowPercent*10 != AIRFLOW_HMI_R_CP){
        //     nodeHMI.writeSingleRegister(AIRFLOW_HMI_W-1, airflowPercent*10); 
        // }
        
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
    if (nodeBT.readHoldingRegisters(tempRegister_R, 1) == nodeBT.ku8MBSuccess) {
        Temperature_BT = nodeBT.getResponseBuffer(0);
        if (svEn) {
            nodeBT.writeSingleRegister(btSVReg_R, btSV_R_CV);
            svEn = false;
        }
    } else {
        errorCount++;
        if (enDebug) SerialComputer.println(" ERROR READ BT");
        BUZZ_ON; delay(100); BUZZ_OFF; delay(100);
    }
    delay(10);
}

void readTempET(){
    uint8_t result = nodeET.readHoldingRegisters(tempRegister_R, 1);
    if (result == nodeET.ku8MBSuccess) {
        Temperature_ET = nodeET.getResponseBuffer(0);
    } else {
        errorCount++;
        if (enDebug) SerialComputer.println(" ERROR READ ET");
        BUZZ_ON; delay(100); BUZZ_OFF; delay(100);
    }
    delay(10);
}

void readAirflowINV(){
    // Đọc giá trị từ biến tần trống
    uint8_t result = nodeAir.readHoldingRegisters(8451, 1);
    delay(5);
    if (result == nodeAir.ku8MBSuccess) { // Nếu đọc thành công
        Airflow_Freq_CP = nodeAir.getResponseBuffer(0); // Lưu giá trị tần số trống vào biến tạm
        if (airHzTimer > 1) { // Nếu bộ đếm thời gian lớn hơn 1
            // Ghi giá trị tần số trống mới vào biến tần
            nodeAir.writeSingleRegister(8193, map(airflowPercent, 0, 100, 3000, 6000));
            airHzTiEn = airHzTimer = 0; // Đặt lại bộ đếm và trạng thái
            STEP_AIRFLOW_WRITE = "DONE"; // Cập nhật trạng thái hoàn thành
        }
    } else { // Nếu đọc thất bại
        errorCount++; // Tăng bộ đếm lỗi
        if (enDebug) SerialComputer.println(" ERROR READ AIR INV"); // In thông báo lỗi
        BUZZ_ON; delay(100); BUZZ_OFF; delay(100); // Bật còi báo lỗi
    }
    delay(5); // Đợi một khoảng thời gian ngắn
}

void readWriteDrumINV(){
    // Đọc giá trị từ biến tần trống
    uint8_t result = nodeDrum.readHoldingRegisters(8451, 1);
    delay(5);
    if (result == nodeDrum.ku8MBSuccess) { // Nếu đọc thành công
        Drum_Freq_CP = nodeDrum.getResponseBuffer(0); // Lưu giá trị tần số trống vào biến tạm
        if (drumHzTimer > 1) { // Nếu bộ đếm thời gian lớn hơn 1
            // Ghi giá trị tần số trống mới vào biến tần
            nodeDrum.writeSingleRegister(8193, map(drumPercent, 0, 100, 3000, 5000));
            drumHzTiEn = drumHzTimer = 0; // Đặt lại bộ đếm và trạng thái
            STEP_DRUM_WRITE = "DONE"; // Cập nhật trạng thái hoàn thành
        }
    } else { // Nếu đọc thất bại
        errorCount++; // Tăng bộ đếm lỗi
        if (enDebug) SerialComputer.println(" ERROR READ DRUM INV"); // In thông báo lỗi
        BUZZ_ON; delay(100); BUZZ_OFF; delay(100); // Bật còi báo lỗi
    }
    delay(5); // Đợi một khoảng thời gian ngắn
}

void checkError(){
    uint8_t result = 0;
    uint16_t buzzer_delay = 1000; // Thời gian đợi giữa các lần thử lại

    // Hàm kiểm tra thiết bị
    auto checkDevice = [&](auto& node, const char* name, uint16_t reg, uint8_t retries) {
        while ((result = node.readHoldingRegisters(reg, 1)) != node.ku8MBSuccess) {
            delay(10); // Đợi 10ms trước khi thử lại
            SerialComputer.printf(" CHECK ERROR %s\n", name); // Báo lỗi thiết bị
            for (int j = 0; j < retries; j++) { BUZZ_ON; delay(100); BUZZ_OFF; delay(100); } // Bật còi báo lỗi
            delay(buzzer_delay); // Đợi trước khi thử lại
        }
        SerialComputer.printf(" => %s OK\n", name); // Thiết bị hoạt động bình thường
    };

    // Kiểm tra và đọc/ghi bộ nhớ HMI nếu cờ chHMIFlag được bật
    if (chHMIFlag) checkDevice(nodeHMI, "HMI", 0, 1);   delay(10);
    rwMemHMI();

    // Kiểm tra và đọc/ghi nhiệt độ BT nếu cờ chBTFlag được bật
    if (chBTFlag) checkDevice(nodeBT, "BT", tempRegister_R, 2);     delay(10);

    // Kiểm tra và đọc/ghi nhiệt độ ET nếu cờ chETFlag được bật
    if (chETFlag) checkDevice(nodeET, "ET", tempRegister_R, 3);     delay(10);

    // Kiểm tra và đọc/ghi biến tần luồng khí nếu cờ chAirFlag được bật
    if (chAirFlag) checkDevice(nodeAir, "AIRFLOW INV", 8451, 4);    delay(10);

    // Kiểm tra và đọc/ghi biến tần trống nếu cờ chDrumFlag được bật
    if (chDrumFlag) checkDevice(nodeDrum, "DRUM INV", 8451, 5);     delay(10);

    if(chSDFlag){
        // Kiểm tra và khởi tạo thẻ SD
        while (!SD.begin(chipSelect)) {
            SerialComputer.println(" CHECK ERROR SD"); // Báo lỗi thẻ SD
            for (int j = 0; j < 6; j++) { BUZZ_ON; delay(200); BUZZ_OFF; delay(200); } // Bật còi báo lỗi
            delay(buzzer_delay); // Đợi trước khi thử lại
        }
        SerialComputer.println(" => SD OK"); // Thẻ SD hoạt động bình thường
    }
    BUZZ_ON; delay(500); BUZZ_OFF; // Bật còi báo hiệu hoàn tất
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
