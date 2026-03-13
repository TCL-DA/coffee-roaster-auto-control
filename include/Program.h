void timerPoll_1000ms(){
    countTimer++;
    if(countTimer>=10) countTimer = 0;

    // Hàm xử lý bộ đếm thời gian với giới hạn
    auto handleTimer = [](bool &timerEn, auto &timer, int limit) {
        if (timerEn) {
            timer++;
            if (timer > limit) timer = limit; // Giới hạn đếm
        }
    };

    selfTuneTickEn = true;   // ← chỉ set flag

    // Xử lý các bộ đếm thời gian
    handleTimer(chargeTimerEn, chargeTimer, timerLimit);       // Đếm thời gian charge
    handleTimer(dropTimerEn, dropTimer, timerLimit);           // Đếm thời gian drop
    handleTimer(escapeTimerEn, escapeTimer, timerLimit);       // Đếm thời gian escape
    handleTimer(coolTimerEn, coolTimer, timerLimit);           // Đếm thời gian cooling
    handleTimer(abTimerEn, abTimer, timerLimit);               // Đếm thời gian afterburner
    handleTimer(feederTimerEn, feederTimer, timerLimit);       // Đếm thời gian feeder
    handleTimer(destonerTimerEn, destonerTimer, timerLimit);   // Đếm thời gian destoner
    handleTimer(buzzerTimerEn, buzzerTimer, timerLimit);       // Đếm thời gian buzzer
    handleTimer(cleanFeederTiEn, cleanFeederTi, timerLimit);   // Đếm thời gian hút sạch cà phê
    handleTimer(delCyFeederTiEn, delCyFeederTi, timerLimit);   // Đếm thời gian delay xóa cycle feeder
    handleTimer(fillerTiEn, fillerTi, timerLimit);             // Đếm thời gian tự động tắt fill cà phê vào bồn chứa

    if(updateNetWTiEn&&SerialBluetooth.available()==0){
        updateNetWTi++;
        if(updateNetWTi>5) updateNetWTi = 5;
    }else{
        updateNetWTi = 0;    
    }
    if(updateNetWTiEn>timerLimit) updateNetWTiEn=timerLimit;  //Giới hạn đếm

    if(drumHzTiEn) drumHzTimer++;

    if(buzzerTimer>=buzzerTimeOFF){
        buzzerTimer = 0;
        buzzerTimerEn = 0;
    }

    //Xử lí dữ liệu thời gian rang mỗi giây
    if(timeRoastEn) {
        timeRoast++; //Đếm thời gian
        
        if(progStatus == STT_PROGRAM_SAVE){
            //Lưu dữ liệu và ghi vào SD
            sdLogDataEn = 1;
        }

        //Xử lí dữ liệu khi rang auto
        if(progStatus == STT_PROGRAM_AUTO){
            calibGasProgramEn = 1;
        }
    }
    minRoast = timeRoast/60;
    secRoast = timeRoast%60;
    if(minRoast>=60) timeRoast = 0;   

    // enDebug = true;

    if(waitDropcloseTiEn){
        waitDropcloseTi++;
    }


    //Buzzer ON/OFF 
    if(buzzerTimerEn){
        buzzerHMIEn = !buzzerHMIEn;
    }else{
        buzzerHMIEn = false;    
    }


    //Tính toán ror, áp dụng lọc phẳng kalman
    rorCount++; 
    if(rorCount==3){
        raw_rorBT = (Temperature_BT-rorBTSamp_1)*20;
        raw_rorET = (Temperature_ET-rorETSamp_1)*20;

        // old_rorBT = old_rorBT/10;
        // raw_rorBT = (old_rorBT+raw_rorBT)/2;
        rorBT = rorBTKalmanFilter.updateEstimate(raw_rorBT); //Lọc kalman
        rorET = rorETKalmanFilter.updateEstimate(raw_rorET); //Lọc kalman
        // raw_rorBT = raw_rorBT*10;
        if(rorBT>(950)) rorBT = 950;
        if(rorBT<(-950)) rorBT = -950;
        rorBT = rorBT*10;

        if(rorET>(950)) rorET = 950;
        if(rorET<(-950)) rorET = -950;
        rorET = rorET*10;
        //update BT
        // old_rorBT = raw_rorBT;
        rorBTSamp_1 = Temperature_BT;
        rorETSamp_1 = Temperature_ET;
        rorCount = 0; //Reset count    
    }

    //Dự đoán YL
    if(progStep==STP_YELLOW){
        TIME_YEL_SEC_GUE = (yellowPhase_R_CV-Temperature_BT)/(rorBT/10)*60; //Tách lấy số phút, sau đó quy đổi sang giây
        TIME_YEL_SEC_GUE = TIME_YEL_SEC_GUE+(((yellowPhase_R_CV-Temperature_BT)%(rorBT/10))*60)/(rorBT/10); //Tách lấy giây
        TIME_YEL_SEC_GUE = TIME_YEL_SEC_GUE+timeRoast; //Cộng thời gian đang đếm
        TIME_YELLOW_MIN_SAVE = TIME_YEL_SEC_GUE/60;
        TIME_YELLOW_SEC_SAVE = TIME_YEL_SEC_GUE%60;
    }

    //Dự đoán FCS
    if(progStep==STP_FCS){
        TIME_FCS_SEC_GUE = (fcsPhase_R_CV-Temperature_BT)/(rorBT/10)*60; //Tách lấy số phút, sau đó quy đổi sang giây
        TIME_FCS_SEC_GUE = TIME_FCS_SEC_GUE+(((fcsPhase_R_CV-Temperature_BT)%(rorBT/10))*60)/(rorBT/10); //Tách lấy giây
        TIME_FCS_SEC_GUE = TIME_FCS_SEC_GUE+timeRoast; //Cộng thời gian đang đếm
        TIME_FCS_MIN_SAVE = TIME_FCS_SEC_GUE/60;
        TIME_FCS_SEC_SAVE = TIME_FCS_SEC_GUE%60;
    }
}

void sdLogWrite(){
    strProfileName = String(SELECT_FILE_R) + ".txt";

    // Xoá file cũ và mở file mới một lần duy nhất khi bắt đầu rang
    if(sdLogStartEn){
        if(sdLogFile) sdLogFile.close();
        SD.remove(strProfileName);
        sdLogFile = SD.open(strProfileName, FILE_WRITE);
        SDLogSTEP = sdLogFile ? "OPEN OK" : "OPEN FAIL";
        sdLogStartEn = 0;
    }

    if(sdRemoveAll){
        if(sdLogFile) sdLogFile.close();
        for(int i=0;i<16;i++){
            String strReAll = String(i) + ".txt";
            SD.remove(strReAll);
        }
        sdRemoveAll = 0;
    }

    // Ghi dòng R — không open/close, chỉ write+flush vào file đang mở
    // Phải ghi trước P để không bị mất khi cả hai flag cùng bật
    if(sdLogDataEn){
        if(sdLogFile){
            sdLogFile.print('R');
            sdLogFile.print(timeRoast);     sdLogFile.print(',');
            sdLogFile.print(Temperature_BT);  sdLogFile.print(',');
            sdLogFile.print(Temperature_ET);  sdLogFile.print(',');
            sdLogFile.print(airflowPercent);  sdLogFile.print(',');
            sdLogFile.print(gasPercent);      sdLogFile.print(',');
            sdLogFile.print(drumPercent);     sdLogFile.print(',');
            sdLogFile.print(rorBT);           sdLogFile.print(',');
            sdLogFile.print(vacuumSetFlag_R); sdLogFile.print(',');
            sdLogFile.print(vacuumSetpoint_R);
            sdLogFile.println('E');
            sdLogFile.flush(); // đảm bảo dữ liệu ghi xuống thẻ, tránh mất khi mất điện
            SDLogSTEP = "SUCCESS";
        } else {
            SDLogSTEP = "FAIL";
        }
        sdLogDataEn = 0;
    }

    // Ghi dòng P (phase summary) rồi đóng file
    if(sdLogEndEn){
        if(sdLogFile){
            sdLogFile.print('P');
            sdLogFile.print(BT_CHARGE_SAVE);   sdLogFile.print(',');
            sdLogFile.print(BT_TP_SAVE);       sdLogFile.print(',');
            sdLogFile.print(TIME_TP_SAVE);     sdLogFile.print(',');
            sdLogFile.print(BT_YELLOW_SAVE);   sdLogFile.print(',');
            sdLogFile.print(TIME_YELLOW_SAVE); sdLogFile.print(',');
            sdLogFile.print(BT_FCS_SAVE);      sdLogFile.print(',');
            sdLogFile.print(TIME_FCS_SAVE);    sdLogFile.print(',');
            sdLogFile.print(PER_DEV_SAVE);     sdLogFile.print(',');
            sdLogFile.print(TIME_DEV_SAVE);    sdLogFile.print(',');
            sdLogFile.print(BT_DROP_SAVE);     sdLogFile.print(',');
            sdLogFile.print(TIME_DROP_SAVE);
            sdLogFile.println('E');
            sdLogFile.close();
            SDLogSTEP = "SUCCESS";
            nodeHMI.writeSingleRegister(DATE_PROFILE_W-1, 1); //Lưu ngày rang, auto tắt trên HMI
        } else {
            SDLogSTEP = "FAIL";
        }
        sdLogStartEn = 0;
        sdLogEndEn = 0;
    }
}

void sdRead(){
    //Lọc data từ profile
    if(SCRNUM_R==6 && SELECT_FILE_R>0){
        switch(sdReadStep){
            case SD_1:
                sdMillis = millis();
                nodeHMI.writeSingleRegister(LOADING_W-1, 1); //Hiển thị load
                strProfileName ="";
                strProfileName = String(SELECT_FILE_R) + ".txt";
                tempFile = SD.open(strProfileName);
                if(tempFile) {
                    SDLogSTEP = "REOK"; 
                    // read from the file until there's nothing else in it:
                    while (tempFile.available()){
                        // handle_Modbus_Slave();  //Duy trì artisan
                        char inChar  = (char)tempFile.read();

                        //Tách lọc data
                        if(inChar == 'R')   sDataStr = true;
                        if(sDataStr)    inDataStr += inChar;
                        if(inChar=='E'&&sDataStr){
                            sDataStr = false;
                            if(inDataStr.charAt(0) == 'R'){
                                int lenDataStr = inDataStr.length();
                                char inDataCharArray[lenDataStr];
                                inDataStr.toCharArray(inDataCharArray, lenDataStr); 
                                if(lenDataStr>8){
                                    // Reset các field mới về 0 trước khi parse
                                    // (tương thích ngược với file cũ không có 2 field này)
                                    sdTempVacFlag = 0;
                                    sdTempVacSP   = 0;

                                    //Lọc data vào biến tạm
                                    sscanf(inDataCharArray,"R%d,%d,%d,%d,%d,%d,%d,%d,%dE",
                                    &sdTempTi, &sdTempBT, &sdTempET, &sdTempAir,
                                    &sdTempGas, &sdTempDrum, &sdTempRorBT,
                                    &sdTempVacFlag, &sdTempVacSP);

                                    //Gán vào chuỗi
                                    sdBT[sdTempTi]            = sdTempBT;
                                    sdET[sdTempTi]            = sdTempET;
                                    sdAirflow[sdTempTi]       = sdTempAir;
                                    sdGas[sdTempTi]           = sdTempGas;
                                    sdDrum[sdTempTi]          = sdTempDrum;
                                    sdRorBT[sdTempTi]         = sdTempRorBT;
                                    sdVacuumSetFlag[sdTempTi] = sdTempVacFlag;
                                    sdVacuumSetpoint[sdTempTi]= sdTempVacSP;

                                    //Debug
                                    // SerialComputer.print("R");
                                    // SerialComputer.print(sdTempTi); SerialComputer.print(",");
                                    // SerialComputer.print(sdTempBT); SerialComputer.print(",");
                                    // SerialComputer.print(sdTempET); SerialComputer.print(",");
                                    // SerialComputer.print(sdTempAir); SerialComputer.print(",");
                                    // SerialComputer.print(sdTempGas); SerialComputer.print(",");
                                    // SerialComputer.print(sdTempDrum); SerialComputer.print(",");
                                    // SerialComputer.print(sdTempRorBT); SerialComputer.println("E");
                                }
                                 SDLogSTEP = "DATA"; 
                            } 
                            inDataStr = "";
                        }

                        //Tách lọc properties
                        if(inChar == 'P')   sStr = true;
                        if(sStr)    inStr += inChar;
                        if(inChar=='E'&&sStr){
                            sStr = false;
                            if(inStr.charAt(0) == 'P'){
                                int lenStr = inStr.length();
                                char inCharArray[lenStr];
                                inStr.toCharArray(inCharArray, lenStr); 
                                if(lenStr>8){
                                    sscanf(inCharArray,"P%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%dE", 
                                    &CHARGE_PRO_R, &TP_PRO_R, &TP_PRO_S_R, &DE_PRO_R, &DE_PRO_S_R,
                                    &FCS_PRO_R, &FCS_PRO_S_R, &DEV_PRO_R, &DEV_PRO_S_R, 
                                    &DROP_PRO_R, &DROP_PRO_S_R);
                                    //Lọc lấy m và s
                                    //TP
                                    TP_PRO_M_R = TP_PRO_S_R/60;
                                    TP_PRO_S_R = TP_PRO_S_R%60;
                                    //DE
                                    DE_PRO_M_R = DE_PRO_S_R/60;
                                    DE_PRO_S_R = DE_PRO_S_R%60;
                                    //FCS
                                    FCS_PRO_M_R = FCS_PRO_S_R/60;
                                    FCS_PRO_S_R = FCS_PRO_S_R%60;
                                    //DEV
                                    DEV_PRO_M_R = DEV_PRO_S_R/60;
                                    DEV_PRO_S_R = DEV_PRO_S_R%60;
                                    //DROP
                                    DROP_PRO_M_R = DROP_PRO_S_R/60;
                                    DROP_PRO_S_R = DROP_PRO_S_R%60;
                                }
                                SDLogSTEP = "PROPERTIES"; 
                            } 
                            
                            inStr = "";
                        }
                    }
                    //Đóng file
                    tempFile.close();
                    sdReadStep = SD_3;  //chuyển sang stt ghi HMI
                    
                    
                }else{
                    sdReadStep = SD_2;  //chuyển sang stt fail
                }    
            break;

            case SD_2:
                SDLogSTEP = "READFAIL";
                CHARGE_PRO_R = 0;
                TP_PRO_R = 0; TP_PRO_M_R = 0; TP_PRO_S_R = 0;
                DE_PRO_R = 0; DE_PRO_M_R = 0; DE_PRO_S_R = 0;
                FCS_PRO_R = 0; FCS_PRO_M_R = 0; FCS_PRO_S_R = 0;
                DEV_PRO_R = 0; DEV_PRO_M_R = 0; DEV_PRO_S_R = 0;
                DROP_PRO_R = 0; DROP_PRO_M_R = 0; DROP_PRO_S_R = 0;
                sdReadStep = SD_3; //Chuyển trạng thái show màn hình
            break;

            

            case SD_3:
                
                nodeHMI.writeSingleRegister(CHARGE_PRO_W-1, CHARGE_PRO_R);
                nodeHMI.writeSingleRegister(TP_PRO_W-1, TP_PRO_R);
                nodeHMI.writeSingleRegister(TP_PRO_M_W-1, TP_PRO_M_R);
                nodeHMI.writeSingleRegister(TP_PRO_S_W-1, TP_PRO_S_R);

                nodeHMI.writeSingleRegister(DE_PRO_W-1, DE_PRO_R);
                nodeHMI.writeSingleRegister(DE_PRO_M_W-1, DE_PRO_M_R);
                nodeHMI.writeSingleRegister(DE_PRO_S_W-1, DE_PRO_S_R);

                nodeHMI.writeSingleRegister(FCS_PRO_W-1, FCS_PRO_R);
                nodeHMI.writeSingleRegister(FCS_PRO_M_W-1, FCS_PRO_M_R);
                nodeHMI.writeSingleRegister(FCS_PRO_S_W-1, FCS_PRO_S_R);

                nodeHMI.writeSingleRegister(DEV_PRO_W-1, DEV_PRO_R);
                nodeHMI.writeSingleRegister(DEV_PRO_M_W-1, DEV_PRO_M_R);
                nodeHMI.writeSingleRegister(DEV_PRO_S_W-1, DEV_PRO_S_R);

                nodeHMI.writeSingleRegister(DROP_PRO_W-1, DROP_PRO_R);
                nodeHMI.writeSingleRegister(DROP_PRO_M_W-1, DROP_PRO_M_R);
                nodeHMI.writeSingleRegister(DROP_PRO_S_W-1, DROP_PRO_S_R);

                nodeHMI.writeSingleRegister(chargeTemp_W+2000, CHARGE_PRO_R);
                // delay(200);
                nodeHMI.writeSingleRegister(LOADING_W-1, 0); //Tắt Load   
                sdReadStep = SD_4;
                calSdMillis = millis() - sdMillis;
            break;

            case SD_4:
                //Chờ
                sdMillis = 0;
            break;
        }
    }

    //Ngắt đọc file và reset trạng thái khi huỷ lệnh đọc SD
    if(SELECT_FILE_R==0){
        sdReadStep = 0;    
    }
}

void calibProgram(){
    //Cập nhập dữ liệu từ SD mỗi giây
    //Dữ liệu gốc từ SD
    //Gió và trống sẽ được giữ nguyên
    //Dữ liệu chỉ được cập nhật khi thời gian rang bằng thời gian file mẫu
    if(timeRoast<=sdTempTi){
        lastTimeSD = timeRoast;
    }
    // Airflow: tùy theo vacuumSetFlag đã lưu trong profile
    // Dùng biến nội bộ autoVacPIDEn/autoVacSP thay vì vacuumSetFlag_R/vacuumSetpoint_R
    // để tránh xung đột với rwMemHMI() đọc HMI và ghi đè iMemHMI[] mỗi loop
    if (sdVacuumSetFlag[lastTimeSD] == 1) {
        autoVacPIDEn = true;
        autoVacSP    = sdVacuumSetpoint[lastTimeSD];
        // airflowPercent sẽ do pidAirflowUpdate() cập nhật trong analogIn()
    } else {
        autoVacPIDEn = false;
        airflowPercent = sdAirflow[lastTimeSD];
    }

    gasPercent  = sdGas[lastTimeSD];  //Gas
    drumPercent = sdDrum[lastTimeSD]; //Trống

    // Show vacuumSetFlag và vacuumSetpoint hiện tại khi đang rang AUTO
    if ((int16_t)autoVacPIDEn != vacuumSetFlag_R_CP) {
        nodeHMI.writeSingleRegister(vacuumSetFlag_W+2000, (int16_t)autoVacPIDEn);
    }
    if (autoVacSP != vacuumSetpoint_R_CP) {
        nodeHMI.writeSingleRegister(vacuumSetpoint_W+2000, autoVacSP);
    }


    //Hiệu chỉnh gas theo phase
    //Bắt đầu hiệu chỉnh sau khi TP
    //Auto gas khi temp BT nằm ngoài định mức
    if(progStep>STP_TP){
        if( Temperature_BT>sdBT[lastTimeSD]+clRangeBt
        ||  Temperature_BT<sdBT[lastTimeSD]-clRangeBt){
            timeCalibGas++; //Đếm hiệu chỉnh gas
            //Tăng giảm gas theo BT (cách 10s)
            if(timeCalibGas>=10){
                //Tính toán độ lệch nhiệt độ
                //Tính ra bậc tăng gas
                calibGas = abs(Temperature_BT - sdBT[lastTimeSD])/5; 
                
                if(calibGas<=0) calibGas=1;    
            
                //Bước 5% gas
                //Trên bếp NP, bước gas đạt tối thiểu 5% mới có tác dụng
                //Trên bếp premix, bước gas có thể thấp hơn
                //numIncGas = calibGas*Bước;
                numIncGas = calibGas*5;

                //Giới hạn gas, khi rang đang ở giai đoạn DE
                if(Temperature_BT<DE_PRO_R){
                    if(numIncGas>=TpCalib_R){
                        numIncGas =  TpCalib_R;   
                    }
                }

                //Giới hạn gas, khi rang đang ở giai đoạn YEL
                if(Temperature_BT>=DE_PRO_R && Temperature_BT<FCS_PRO_R){
                    if(numIncGas>=DeCalib_R){
                        numIncGas = DeCalib_R;   
                    }
                }

                //Giới hạn gas, khi rang đang ở giai đoạn FCS
                if(Temperature_BT>=FCS_PRO_R){
                    if(numIncGas>=FcsCalib_R){
                        numIncGas =  FcsCalib_R;   
                    }
                }                
                timeCalibGas = 0;
            }

            //BT thực tế thấp hơn SD thì tăng gas
            if(Temperature_BT<(sdBT[lastTimeSD]-clRangeBt))
                gasPercent = gasPercent+numIncGas;

            //BT thực tế cao hơn SD thì giảm gas
            if(Temperature_BT>(sdBT[lastTimeSD]+clRangeBt))
                gasPercent = gasPercent-numIncGas;

            if(gasPercent>100)  gasPercent = 100;
            if(gasPercent<0)  gasPercent = 0;
        }else{
            timeCalibGas = 0; 
        }
    }
}

void programScan(){
    if(calibGasProgramEn){
        calibProgram();
        calibGasProgramEn = false;
    }
    
    //On-off buzzer HMI và tối ưu
    if(buzzerHMIEn==1 && memBuzzerEn==0){
        nodeHMI.writeSingleRegister(GENERAL_CONTROL_W-1, 4);
        memBuzzerEn = buzzerHMIEn;
    }
    if(buzzerHMIEn==0 && memBuzzerEn==1){
        nodeHMI.writeSingleRegister(GENERAL_CONTROL_W-1, 0); 
        memBuzzerEn = buzzerHMIEn;
    }

    //Đọc dữ liệu thẻ nhớ
    sdRead();

    if(START_BTN_R == 1){
        switch(progStep){
            case STP_DATA:
                //Xoá profile đã chọn trên SD, nếu chương trình rang là manual save
                if(progStatus == STT_PROGRAM_SAVE){
                    sdLogStartEn = 1;
                }                

                //Reset data
                BT_CHARGE_SAVE = 0;
                BT_TP_SAVE = 0;
                BT_YELLOW_SAVE = 0;
                BT_FCS_SAVE = 0;
                BT_DROP_SAVE = 0;

                TIME_TP_SAVE = 0;
                TIME_TP_MIN_SAVE = 0;
                TIME_TP_SEC_SAVE = 0;

                TIME_YELLOW_SAVE = 0;
                TIME_YELLOW_MIN_SAVE = 0;
                TIME_YELLOW_SEC_SAVE = 0;

                TIME_FCS_SAVE = 0;
                TIME_FCS_MIN_SAVE = 0;
                TIME_FCS_SEC_SAVE = 0;

                PER_DEV_SAVE = 0;
                TIME_DEV_MIN_SAVE = 0;
                TIME_DEV_SEC_SAVE = 0;
                
                TIME_DROP_SAVE = 0;
            
                timeRoast = 0;

                nodeHMI.writeSingleRegister(CLEAR_HIS_CONTROL_W-1, 1);  //Clear trend graph
                nodeHMI.writeSingleCoil(LOCK_BUTTON_W-1, 1);    //Lock các button trên HMI khi rang
                nodeHMI.writeSingleRegister(CLEAR_HIS_CONTROL_W-1, 0);  //Clear trend graph
                //Debug
                STEP_STRING = "RESET DATA";

                progStep = STP_COOL_DOWN;   //Chuyển trạng thái
            break;

            //Kiểm tra auto charge
            //Nếu có auto charge thì tắt gas và đợi nhiệt giảm
            case STP_COOL_DOWN:
                if(chargeTemp_R_CV>0){
                    //Debug
                    STEP_STRING = "BT COOLS DOWN";
                    if(Temperature_BT<=(chargeTemp_R_CV-turnGasPoint_R_CV)){
                        if(READ_CH1==HIGH){
                            naviSourceGAS = SOURCE_AI_AUTO; //Đổi source gas sang auto
                            gasPercent = 50;
                            nodeHMI.writeSingleRegister(START_GAS_BTN_W-1, 1);  //Turn on gas
                            delay(1);
                        }
                        progStep = STP_GAS; //Chuyển trạng thái kiểm tra gas 
                        
                    }else{
                        nodeHMI.writeSingleRegister(START_GAS_BTN_W-1, 0);  //Turn off gas    
                    }  
                }else{
                    progStep = STP_CHARGE; //Chuyển trạng thái kiểm tra charge   
                }
            break;

            //Kiểm tra bếp
            case STP_GAS:
                //Nếu là bếp NP thì chờ gas on
                if(burnerPremix_R == 0){
                    if(READ_CH1==LOW){
                        naviSourceGAS = SOURCE_AI_AUTO; //Đổi source gas
                        gasPercent = preGas_R; //Set gas charge
                        STEP_STRING = "WAITGAS";
                        progStep = STP_CHECK; //Chuyển trạng thái
                    }    
                }
                //Nếu là bếp premix thì không cần chờ
                else{
                    naviSourceGAS = SOURCE_AI_AUTO; //Đổi source gas
                    gasPercent = preGas_R; //Set gas charge theo cài đặt
                    progStep = STP_CHECK; //Chuyển trạng thái
                }
                
                //Debug
            break;

            case STP_CHECK:
                STEP_STRING = "BT HEATUP";

                //Kiểm tra BT đạt nhiệt charge
                if(Temperature_BT>=(chargeTemp_R_CV-chTolerange_R_CV)&&
                    Temperature_BT<=(chargeTemp_R_CV+chTolerange_R_CV)){
                    nodeHMI.writeSingleRegister(CHARGE_BTN_W-1, 1);  //Turn on charge
                    buzzerTimerEn = 1; //Call buzzer
                    delay(1);
                    progStep = STP_CHARGE; //Chuyển trạng thái        
                }

                //Nhiệt tăng nhanh đến mức không catch auto charge được => reset về bước data
                if(Temperature_BT>chargeTemp_R_CV+(chTolerange_R_CV*5)){
                    nodeHMI.writeSingleRegister(START_GAS_BTN_W-1, 0); //Tắt gas và quay lại bước chờ heat to charge
                    progStep = STP_DATA; //Chuyển trạng thái
                    delay(1);
                }
            break;

            case STP_CHARGE:
                STEP_STRING = "WAIT CHARGE";
                //Quản lí gió, gas trống
                //Chương trình manual save
                if(progStatus == STT_PROGRAM_SAVE){
                    naviSourceGAS = SOURCE_AI_VR; //Đổi source sang VR
                    naviSourceDRUM = SOURCE_AI_VR;
                    naviSourceAIR = SOURCE_AI_VR;
                }
                //Chương trình auto
                if(progStatus == STT_PROGRAM_AUTO){
                    naviSourceGAS = SOURCE_AI_AUTO; //Đổi source sang VR
                    naviSourceDRUM = SOURCE_AI_AUTO;
                    naviSourceAIR = SOURCE_AI_AUTO;
                }
                    
                
                
                //Condition to Charge
                if(CHARGE_BTN_R == 1){ //press charge
                    BT_CHARGE_SAVE = Temperature_BT; //Lưu nhiệt BT charge

                    //Enable auto close charge
                    nodeHMI.writeSingleRegister(CHARGE_BTN_W-1, 1);  //Turn on charge
                    buzzerTimerEn = 1; //Call buzzer
                    chargeTimerEn = 1;

                    BT_TP_Pre = Temperature_BT; //Lưu biến nhiệt để check TP

                    //Enable record airflow, drum, flame, gas signal

                    nodeHMI.writeSingleCoil(SAMPLE_COIL_W-1, 1);  //Turn on trend graph sample
                    timeRoastEn = 1; //Start roaster time
                    buzzerTimerEn = 1; //Call buzzer
                    progStep = STP_TP; //Chuyển trạng thái check TP

                }
            break;

            case STP_TP:
                //Condition to TP
                STEP_STRING = "CATCH TP";
                if(timeRoast>ulimitTPTime && Temperature_BT<ulimitTPTemp){
                    if(Temperature_BT<=BT_TP_Pre){
                        BT_TP_Pre = Temperature_BT; //Lưu biến nhiệt để check TP  
                        STEP_STRING = "CHECK TP";
                        
                    }else{
                        BT_TP_SAVE = BT_TP_Pre; //Set nhiệt TP
                        TIME_TP_SAVE = timeRoast;
                        TIME_TP_MIN_SAVE = TIME_TP_SAVE/60;
                        TIME_TP_SEC_SAVE = TIME_TP_SAVE%60;
                        progStep = STP_YELLOW; // Next to check yellow
                    }
                }
                
                break;

            case STP_YELLOW:
                STEP_STRING = "CATCH YELLOW";
                //Check YL
                if(Temperature_BT>=yellowPhase_R_CV){
                    BT_YELLOW_SAVE = Temperature_BT;
                    TIME_YELLOW_SAVE = timeRoast;
                    TIME_YELLOW_MIN_SAVE = TIME_YELLOW_SAVE/60;
                    TIME_YELLOW_SEC_SAVE = TIME_YELLOW_SAVE%60;
                    progStep = STP_FCS;       
                }
                break;

            case STP_FCS:
                STEP_STRING = "CATCH FCS";
                //Check FCS
                if(Temperature_BT>=fcsPhase_R_CV){
                    BT_FCS_SAVE = Temperature_BT;
                    TIME_FCS_SAVE = timeRoast;
                    TIME_FCS_MIN_SAVE = TIME_FCS_SAVE/60;
                    TIME_FCS_SEC_SAVE = TIME_FCS_SAVE%60;
                    progStep = STP_DEV;       
                }
                break; 

            case STP_DEV:
                STEP_STRING = "DEV";
                //Tính DEV
                TIME_DEV_SAVE = timeRoast-TIME_FCS_SAVE;
                TIME_DEV_MIN_SAVE = TIME_DEV_SAVE/60;
                TIME_DEV_SEC_SAVE = TIME_DEV_SAVE%60;
                PER_DEV_SAVE = (TIME_DEV_SAVE*1000)/timeRoast;
                break; 

            case STP_LOOP_1:
                //Nếu báo lỗi feeder thì huỷ rang
                if(autoLoader_R == 1 && aLoaderStep == STP_FAIL_LOADER){
                    nodeHMI.writeSingleRegister(START_BTN_W-1, 0);  //Turn off start
                    nodeHMI.writeSingleCoil(LOCK_BUTTON_W-1, 0);  //Mở khoá select
                    aLoaderStep = STP_NONE_LOADER; //Trạng thái auto loader về 0
                    progStep = STP_DATA;   //Reset manual save step 
                    STEP_STRING = "NONE";
                }

                //Kiểm tra xem có cần rang tiếp hay không
                if(loop_R <= 1){
                    nodeHMI.writeSingleRegister(START_BTN_W-1, 0);  //Turn off start
                    nodeHMI.writeSingleCoil(LOCK_BUTTON_W-1, 0);  //Mở khoá select
                    progStep = STP_DATA;   //Reset manual save step 
                    STEP_STRING = "NONE";
                }else{
                    //Tiếp tục rang
                    aLoaderStep = STP_NONE_LOADER; //Trạng thái auto loader về 0
                    progStep = STP_LOOP_2; //Chờ drop đóng lại và rang tiếp
                    STEP_STRING = "LOOP";
                }

                //Giảm số mẻ rang 
                if(loop_R>1){
                    loop_R = loop_R-1;
                }
                if(loop_R>=0){
                    nodeHMI.writeSingleRegister(loop_W+2000, loop_R);  //Cập nhập số mẻ
                }
                
                break;

            case STP_LOOP_2:
                if(DROP_BTN_R == 0){
                    //Khởi động trình đếm để chờ drop đóng lại hoàn toàn
                    waitDropcloseTiEn = 1;
                }
                //Trong thời gian này, khách hàng có thể huỷ auto
                STEP_STRING = "WCANCEL";
                
                if(START_BTN_R == 0){
                    nodeHMI.writeSingleCoil(LOCK_BUTTON_W-1, 0);  //Mở khoá select
                    progStep = STP_DATA;   //Reset manual save step
                }
                if(waitDropcloseTi>20){
                    progStep = STP_DATA; //Reset chương trình rang về 0, nó sẽ tự bắt đầu quy trình mới 
                    waitDropcloseTiEn = false;
                    waitDropcloseTi = 0;
                }
                break;
        }

        //Check auto cân
        //Chỉ cân tự động sau khi DE hoàn thành
        if(progStep==STP_FCS){
            //Xử lí các tình huống trong khi rang auto
            if(progStatus == STT_PROGRAM_AUTO){
                if(autoLoader_R == 1 && aLoaderStep == 0 && loop_R>1){
                    //Chỉ cho auto cân khi có trên 7.2kg
                    //Nếu không sẽ auto tắt start
                    if(netW>=72){
                        aLoaderStep = STP_ON_LOADER; //Bắt đầu vào auto loader  
                    }else{
                        aLoaderStep = STP_FAIL_LOADER; 
                    } 
                    
                }
            }
        }

        //Check drop
        if(progStep>=STP_YELLOW){
            //Xử lí các tình huống trong khi rang auto
            if(progStatus == STT_PROGRAM_AUTO){
                //Phát hiện auto drop khi rang auto
                if(Temperature_BT>=DROP_PRO_R && progStep<STP_LOOP_1){
                    nodeHMI.writeSingleRegister(DROP_BTN_W-1, 1); //Turn on drop    
                }
                //Tự bật cooling trước khi drop
                if(Temperature_BT>=(DROP_PRO_R-preCool_R_CV)&&preCool_R_CV>0){
                    //Bật cooling&mixer nếu nhập số lớn hơn 0
                    if(coolTimer_R>0&&coolStep==0) coolStep = 1;
                }
            }

            //Condition to Drop
            if(DROP_BTN_R == 1 && progStep<STP_LOOP_1){ //Press Drop
                //Nếu rang manual save thì tắt start luôn
                if(progStatus == STT_PROGRAM_SAVE){
                    nodeHMI.writeSingleRegister(START_BTN_W-1, 0);  //Turn off start
                    nodeHMI.writeSingleCoil(LOCK_BUTTON_W-1, 0);  //Mở khoá select
                    sdLogEndEn = 1;//Hoàn tất lưu data phase
                    progStep = 0;   //Reset manual save step
                }
                //Nếu nút auto off gas = 1 thì tắt gas
                if(autoOff_R==1) 
                    nodeHMI.writeSingleRegister(START_GAS_BTN_W-1, 0);  //Turn off gas
                BT_DROP_SAVE = Temperature_BT;
                TIME_DROP_SAVE = timeRoast;

                //Trả gió gas trống về biến trở
                naviSourceGAS = SOURCE_AI_VR; //Đổi source sang VR
                naviSourceDRUM = SOURCE_AI_VR;
                naviSourceAIR = SOURCE_AI_VR;

                //Bật cooling&mixer nếu nhập số lớn hơn 0
                if(coolTimer_R>0&&coolStep==0) coolStep = 1; 
                 
                timeRoastEn = 0;

                nodeHMI.writeSingleCoil(SAMPLE_COIL_W-1, 0);  //Turn off trend graph sample
                
                buzzerTimerEn = 1; //Call buzzer
                dropTimerEn = 1; //Enable drop timer auto close
                nodeHMI.writeSingleRegister(DROP_BTN_W-1, 1); //Turn on drop

                STEP_STRING = "DROP";

                if(progStatus == STT_PROGRAM_AUTO && progStep<STP_LOOP_1){
                    progStep = STP_LOOP_1; //Chuyển sang trạng thái kiểm tra loop
                }
                delay(1);
            }
        }
    }
    //Kiểm tra các tình huống trong lúc rang
    if(progStep>=1){
        
        //Tắt chương trình, trả quyền kiểm soát
        if(START_BTN_R == 0){
            //Disable all timer
            timeRoastEn = 0;    //Time roast off

            //Các bước rang về 0
            progStep = 0;       //Program step off
            
            //Trạng thái auto loader về 0
            aLoaderStep = STP_NONE_LOADER;

            //Trả gió gas trống về biến trở
            naviSourceGAS = SOURCE_AI_VR; //Đổi source sang VR
            naviSourceDRUM = SOURCE_AI_VR;
            naviSourceAIR = SOURCE_AI_VR;
            
            nodeHMI.writeSingleCoil(SAMPLE_COIL_W-1, 0);  //Turn off trend graph sample
            nodeHMI.writeSingleCoil(LOCK_BUTTON_W-1, 0);  //Mở khoá select
            STEP_STRING = "NONE";
        }
        //Tự động bật afterburner
        if(afterburnerSet_R_CV>0 && timeRoast>60 && progStep>=STP_TP && progStep<STP_LOOP_1){
            STEP_AB_STRING = "WABHU"; //Wait AB heatup
            //Kiểm tra nhiệt và trạng thái trình tự AB
            if(Temperature_BT>=afterburnerSet_R_CV && abStep==0){
                abStep = STP_ON_AB;
            }    
        }
    }   

    //----------------------Cân
    //Auto loader step
    switch(aLoaderStep){
        case STP_ON_LOADER:
            STEP_LOADER = "ONLOA";
            nodeHMI.writeSingleRegister(FEEDER_BTN_W-1, 1);  //Turn on Feeder 
            delay(1); 
            aLoaderStep = STP_WAIT_LOADER;
        break;

        //Trạng thái chờ drop cà phê
        case STP_WAIT_LOADER:
            STEP_LOADER = "WDO"; //Wait drop on
        break;  

        //Thổi cà thất bại, cà phê ko đưa lên đủ
        case STP_FAIL_LOADER:
            STEP_LOADER = "FLOA"; //Lỗi thổi
        break;   

        //Thổi cà thành công
        case STP_OK_LOADER:
            STEP_LOADER = "OKLOA"; //Thổi ok
        break;    
    }

    // Tự động cập nhật cân sau 10 giây nếu không có dữ liệu từ Bluetooth
    if (updateNetWTi >= 5 && SerialBluetooth.available() == 0) {
        // netW = 0; // Có thể thêm logic cập nhật cân tại đây nếu cần
    }

    // Tính hiệu số giữa trọng lượng hiện tại và trọng lượng mục tiêu
    if (netW > netWTG_R && FEEDER_BTN_R == 0) {
        difNetW = netW - netWTG_R; // Nếu trọng lượng hiện tại lớn hơn mục tiêu
    } else if (netW <= netWTG_R && FEEDER_BTN_R == 0) {
        difNetW = 0; // Nếu trọng lượng hiện tại nhỏ hơn hoặc bằng mục tiêu
    }

    if (netW >= wThresholdHigh_R) {
        dif = difHigh_R; // Trọng lượng lớn hơn hoặc bằng wThresholdHigh_R
    } else if (netW < wThresholdHigh_R && netW >= wThresholdLow_R) {
        dif = difMedium_R; // Trọng lượng từ wThresholdMedium_R đến dưới wThresholdHigh_R
    } else if (netW < wThresholdLow_R) {
        dif = difLow_R; // Trọng lượng nhỏ hơn 5
    }

    // Tự động tắt feeder dựa trên trọng lượng và trạng thái nút FEEDER
    if (FEEDER_BTN_R == 1 && netWTG_R > 0) { // Nếu nút FEEDER đang bật và có trọng lượng mục tiêu
        if (netW <= (difNetW + dif)) { // Kiểm tra nếu trọng lượng hiện tại đạt ngưỡng
            if (netW > vacuumTraction_R) { // Nếu trọng lượng lớn hơn 7
                nodeHMI.writeSingleRegister(FEEDER_BTN_W-1, 0); // Tắt FEEDER
                delay(1);
            } else {
                cleanFeederTiEn = 1; // Bật cờ dọn sạch FEEDER
            }
        }
    }

    //Tự tắt feeder sau 5 giây dọn sạch feeder.
    if(FEEDER_BTN_R == 1 && cleanFeederTi>=10 && cleanFeederTiEn){
        nodeHMI.writeSingleRegister(FEEDER_BTN_W-1, 0);  //Turn off Feeder 
        cleanFeederTiEn = false;  
        cleanFeederTi = 0;
        delay(1);
    }

    //Bật timer feeder
    if(feederTimerEn==0 && FEEDER_BTN_R==1 && feederSet_R>0){
        feederTimerEn = 1;  //Bật timer
    }

    //Bật timer filler
    if(fillerTiEn==0 && AUTO_FS_BTN_R==1 && autoFill_Time_R>0){
        fillerTiEn = 1;  //Bật timer
    }

    //Auto close filler
    if(fillerTiEn==1 && fillerTi>=autoFill_Time_R){
        fillerTiEn = 0;
        fillerTi = 0;
        nodeHMI.writeSingleRegister(AUTO_FS_BTN_W-1, 0);  //Turn off Auto filler
        delay(1);
    }

    //Hủy auto close filler
    if(fillerTiEn==1 && AUTO_FS_BTN_R==0 && fillerTi>=1){
        fillerTiEn = 0; //Tắt timer
        fillerTi = 0;   //Reset counter 
    }

    //Auto close feeder - timer
    if(feederTimerEn==1 && feederTimer>=feederSet_R && feederSet_R>=10){
        feederTimerEn = 0;
        feederTimer = 0;
        nodeHMI.writeSingleRegister(FEEDER_BTN_W-1, 0);  //Turn off Feeder
        delay(1);
        //Báo lỗi nếu trong chương trình auto
        if(aLoaderStep==2){
            aLoaderStep = STP_FAIL_LOADER;
        }
    }
    //Huỷ auto close feeder
    if(feederTimerEn==1 && FEEDER_BTN_R==0 && feederTimer>=1){
        feederTimerEn = 0; //Tắt timer
        feederTimer = 0;   //Reset counter 
    }
    //----------------------End cân

    //----------------------Auto close charge
    //Auto close charge
    if(chargeTimerEn==1 && chargeTimer>=chargeDuration_R){
        chargeTimerEn = 0;
        chargeTimer = 0;
        nodeHMI.writeSingleRegister(CHARGE_BTN_W-1, 0);  //Turn off charge
        buzzerTimerEn = 1; //Call buzzer
        delay(1);
    }
    //Huỷ auto close charge
    if(chargeTimerEn==1 && CHARGE_BTN_R==0 && chargeTimer>=1){
        chargeTimerEn = 0; //Tắt timer
        chargeTimer = 0;   //Reset counter 
    }
    //----------------------End charge

    //----------------------Auto close drop
    //Auto close drop
    if(dropTimerEn==1 && dropTimer>=dropDuration_R){
        dropTimerEn = 0;
        dropTimer = 0;
        nodeHMI.writeSingleRegister(DROP_BTN_W-1, 0);  //Turn off Drop
        buzzerTimerEn = 1; //Call buzzer
        STEP_STRING = "NONE";
        delay(1);
    }
    //Huỷ auto close drop
    if(dropTimerEn==1 && DROP_BTN_R==0 && dropTimer>=1){
        STEP_STRING = "NONE";
        dropTimerEn = 0; //Tắt timer
        dropTimer = 0;   //Reset counter     
    }
    //----------------------End drop

    //----------------------Auto close AB
    //Auto close ab
    if(abTimerEn==1 && abTimer>=afterburnerNext_R){
        abTimerEn = 0;
        abTimer = 0;
        nodeHMI.writeSingleRegister(AB_BTN_W-1, 0);  //Turn off AB
        abStep = 0; //Tắt ab step
        STEP_AB_STRING = "NONE";
        delay(1);
    }
    //Huỷ auto close ab
    if(abTimerEn==1 && AB_BTN_R==0 && abTimer>=1){
        abStep = 0; //Tắt ab step
        abTimerEn = 0; //Tắt timer
        abTimer = 0;   //Reset counter     
        STEP_AB_STRING = "NONE";
    }
    //----------------------End close

    //Huỷ quy trình cooling
    if(coolStep>=1 && COOLING_BTN_R==0 && coolTimer>=1){
        coolStep = 0; //Reset quy trình
        coolTimer = 0; //Resetncounter
        coolTimerEn = 0; //Resetncounter
        STEP_COOLING_STRING = "NONE";
    }

    //Auto close destoner
    if(destonerTimerEn==1 && destonerTimer>=destonerSet_R){
        destonerTimerEn = 0;
        destonerTimer = 0;
        nodeHMI.writeSingleRegister(DESTONER_BTN_W-1, 0);  //Turn off Destoner
        if(autoFill_R==1){
            //Nếu cờ auto fill được bật thì bật nút auto fill, kích hoạt chế độ timer auto fill
            nodeHMI.writeSingleRegister(AUTO_FS_BTN_W-1, 1);
            delay(1);
        }
        delay(1);
    }

    //Huỷ auto close destoner
    if(destonerTimerEn>=1 && DESTONER_BTN_R==0 && destonerTimer>=1){
        destonerTimer = 0; //Resetncounter
        destonerTimerEn = 0; //Resetncounter
    }

    if(PC_CONTROL_BTN_R==1){
        //Huỷ auto close escape
        if(escapeTimerEn>=1 && ESCAPE_BTN_R==0 && escapeTimer>=1){
            STEP_COOLING_STRING = "OFFESC";
            escapeTimer = 0; //Reset counter
            escapeTimerEn = 0; //Reset counter
            buzzerTimerEn = 1; //Call buzzer
        }
        
        //Auto close escape
        if(escapeTimer>=escapeDuration_R){
            STEP_COOLING_STRING = "OFFESC";
            nodeHMI.writeSingleRegister(ESCAPE_BTN_W-1, 0);  //Turn off escape
            escapeTimerEn = 0; //Turn off escape timer
            escapeTimer = 0;
            buzzerTimerEn = 1; //Call buzzer
        }     
    }

    //Điều hướng gas analog source control
    if(naviSourceGAS!=SOURCE_AI_AUTO){
        if(PC_CONTROL_BTN_R==1){
            naviSourceGAS = SOURCE_AI_PC;//Khiển bằng PC    
        }else{
            naviSourceGAS = SOURCE_AI_VR;//Khiển bằng VR    
        }
    }

    //Điều hướng airflow analog source control
    if(naviSourceAIR!=SOURCE_AI_AUTO){
        if(PC_CONTROL_BTN_R==1){
            naviSourceAIR = SOURCE_AI_PC;//Khiển bằng PC    
        }else{
            naviSourceAIR = SOURCE_AI_VR;//Khiển bằng VR    
        }
    }

    //Điều hướng drum analog source control
    if(naviSourceDRUM!=SOURCE_AI_AUTO){
        if(PC_CONTROL_BTN_R==1){
            naviSourceDRUM = SOURCE_AI_PC;//Khiển bằng PC    
        }else{
            naviSourceDRUM = SOURCE_AI_VR;//Khiển bằng VR    
        }
    }

    sdLogWrite();   //Trình lưu file

//----------------------Chương trình AB tự động
    switch(abStep){
        //Kiểm tra nhiệt độ BT và cài đặt AB
        case STP_ON_AB:
            STEP_AB_STRING = "ONAB";
            nodeHMI.writeSingleRegister(AB_BTN_W-1, 1);  //Turn on AB 
            delay(1); 
            abStep = STP_WAIT_AB;
        break;

        //Trạng thái chờ drop cà phê
        case STP_WAIT_AB:
            STEP_AB_STRING = "WDO"; //Wait drop on
            //Huỷ AB step trước khi nó tự tắt
            if(AB_BTN_R == 0&&dropTimerEn==1){
                abTimerEn = 0; //Tắt timer
                abTimer = 0;   //Reset counter 
                abStep = 0; //Reset bước
                STEP_AB_STRING = "NONE";
            }

             //Tự tắt AB khi "drop bật"
            if(DROP_BTN_R == 1&&abTimerEn==0){
                if(afterburnerNext_R>0&&AB_BTN_R==1){
                    abTimerEn = 1;  // Cho phép đếm
                }else{
                    nodeHMI.writeSingleRegister(AB_BTN_W-1, 0);  //Turn tắt AB ngay lập tức 
                    abStep = 0; //Tắt ab step  
                }
                STEP_AB_STRING = "CACAB"; //Cancel auto close ab
            }
        break;        
    }

//----------------------Chương trình cooling tự động
//----------------------Đã bao gồm tự động bật escape, bật destoner
    switch(coolStep){
        case STP_COOLING:
            STEP_COOLING_STRING = "ONCO";
            nodeHMI.writeSingleRegister(COOLING_BTN_W-1, 1);  //Turn on cool
            coolTimer = 0;
            coolTimerEn = 1; //Enable drop timer auto close count;
            coolStep = STP_ESCAPE_ON; //Next to check escape on
        
        break;  

        case STP_ESCAPE_ON:
            STEP_COOLING_STRING = "WAESCAPE";
            //Call buzzer before escape run
            if(coolTimer>=(coolTimer_R-5)){
                buzzerTimerEn = 1; //Call buzzer
            }
            //Bật trước destoner
            if(destonerSet_R>0){
                STEP_COOLING_STRING = "WAESDES";
                if(coolTimer>=(coolTimer_R-destonerPre_R)){
                    destonerTimerEn = 1; //Turn on destoner timer
                    nodeHMI.writeSingleRegister(DESTONER_BTN_W-1, 1);  //Turn on destoner button
                    delay(1);
                }
            }
            //Wait to cooling complete
            if(coolTimer>=coolTimer_R){
                STEP_COOLING_STRING = "ONES";
                nodeHMI.writeSingleRegister(ESCAPE_BTN_W-1, 1);  //Turn on escape
                escapeTimerEn = 1;  //Enable escape timer auto close count;
                delay(1);
                coolStep = STP_ESCAPE_OFF; //Next to check escape off
            }
            
        break; 
        case STP_ESCAPE_OFF:
            //Wait to cooling complete
            STEP_COOLING_STRING = "WAESCOFF";

            //Call buzzer before escape run
            if(escapeTimer>=(escapeDuration_R-5)){
                buzzerTimerEn = 1; //Call buzzer
            }

            //Huỷ auto close escape
            //Huỷ auto close destoner
            if(escapeTimerEn>=1 && ESCAPE_BTN_R==0 && escapeTimer>=1){
                STEP_COOLING_STRING = "OFFESC";
                escapeTimer = 0; //Reset counter
                escapeTimerEn = 0; //Reset counter

                coolTimerEn = 0; //Turn off cool timer
                coolTimer = 0;

                buzzerTimerEn = 1; //Call buzzer

                coolStep = 0; //Turn off cooling programm
            }

            if(escapeTimer>=escapeDuration_R||ESCAPE_BTN_R==0){
                STEP_COOLING_STRING = "OFFESC";
                nodeHMI.writeSingleRegister(ESCAPE_BTN_W-1, 0);  //Turn off escape
                nodeHMI.writeSingleRegister(COOLING_BTN_W-1, 0);  //Turn off cool
                escapeTimerEn = 0; //Turn off escape timer
                escapeTimer = 0;

                coolTimerEn = 0; //Turn off cool timer
                coolTimer = 0;

                buzzerTimerEn = 1; //Call buzzer

                coolStep = 0; //Turn off cooling program
            }        
        break; 
    }
}