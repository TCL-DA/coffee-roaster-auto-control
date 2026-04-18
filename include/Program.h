void loadAllProfileDates(); // forward declaration

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

        //Xử lí dữ liệu khi rang auto
        if(progStatus == STT_PROGRAM_AUTO){
            calibGasProgramEn = 1;
        }
    }

    // Đếm thời gian tuyệt đối từ Start — kích hoạt ghi SD (cả trước và sau CHARGE)
    if(timeAbsoluteEn) {
        timeAbsolute++;
        if(progStatus == STT_PROGRAM_SAVE){
            sdLogDataEn = 1;
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
    strProfileName = String(SELECT_FILE_R) + ".csv";

    // --- HANDLE DEDICATED DELETE REQUEST (from HMI)
    if(sdDeleteProfileEn){
        if(sdLogFile) sdLogFile.close();
        if(sdDeleteProfileIndex > 0 && sdDeleteProfileIndex <= 31){
            String delNameCsv = String(sdDeleteProfileIndex) + ".csv";
            String delNameTxt = String(sdDeleteProfileIndex) + ".txt";
            SD.remove(delNameCsv);
            SD.remove(delNameTxt); // optional: remove .txt too
            SDLogSTEP = "DEL OK";
        } else {
            SDLogSTEP = "DEL IDX ERR";
        }
        // clear request
        sdDeleteProfileEn = 0;
        sdDeleteProfileIndex = -1;
        loadAllProfileDates();  // Cập nhật lại danh sách date trên HMI sau khi xóa
    }

    // Xoá file cũ, mở file mới, ghi header Artisan CSV cố định 110 bytes
    if(sdLogStartEn){
        if(sdLogFile) sdLogFile.close();
        SD.remove(strProfileName);
        sdLogFile = SD.open(strProfileName, FILE_WRITE);
        if(sdLogFile) {
            // Lưu date lúc START trước khi ghi placeholder
            sdStartDD   = (uint8_t)DAY_R;
            sdStartMM   = (uint8_t)MONTH_R;
            sdStartYYYY = (uint16_t)YEAR_R;
            // Placeholder header — độ dài cố định 110 bytes (MM:SS / HH:MM luôn 5 ký tự)
            // Sẽ được overwrite bằng seek(0) khi DROP với milestone thực
            { char datetime[20]; sprintf(datetime, "%02d.%02d.%04d %02d:%02d:%02d",
                (int)sdStartDD, (int)sdStartMM, (int)sdStartYYYY, 0, 0, 0);
            sdLogFile.print("Date:"); sdLogFile.print(datetime);
            sdLogFile.print("\tUnit:C\tCHARGE:00:00\tTP:00:00\tDRYe:00:00\tFCs:00:00\tFCe:\tSCs:\tSCe:\tDROP:00:00\tCOOL:\tTime:00:00\r\n"); }
            // Header cột — Artisan format chuẩn
            sdLogFile.print("Time1\tTime2\tET\tBT\tEvent\tAir(%)\tBurner(%)\tDrum(%)\tVacFlag\tVacSP(Pa)\r\n");
            sdLogFile.flush();
            SDLogSTEP = "OPEN OK";
            // Reset bộ đếm wall time
            timeAbsolute = 0;
            timeChargeAbsolute = 0;
            sdChargeHappened = false;
            sdChargeHH = 0;
            sdChargeMM = 0;
            sdCsvPendingEvent[0] = '\0';
        } else {
            SDLogSTEP = "OPEN FAIL";
        }
        sdLogStartEn = 0;
    }

    if(sdRemoveAll){
        if(sdLogFile) sdLogFile.close();
        for(int i=0;i<31;i++){
            SD.remove(String(i) + ".csv");
            SD.remove(String(i) + ".txt"); // xoá cả file cũ định dạng TXT
        }
        sdRemoveAll = 0;
        loadAllProfileDates();  // Cập nhật lại danh sách date trên HMI sau khi xóa tất cả
    }

    // Ghi dòng dữ liệu CSV — tab-separated, flush sau mỗi giây
    if(sdLogDataEn){
        if(sdLogFile){
            // Sự kiện được set bởi programScan() vào sdCsvPendingEvent, tiêu thụ ở đây
            // Phải copy sang buffer cục bộ — KHÔNG dùng pointer vì clear gốc sẽ xóa luôn
            char evStr[8];
            strncpy(evStr, sdCsvPendingEvent, 7);
            evStr[7] = '\0';
            sdCsvPendingEvent[0] = '\0';

            // Timer ISR tăng timeAbsolute TRƯỚC khi set sdLogDataEn → trừ 1 để row đầu = 00:00
            // Guard chống uint16_t underflow khi timeAbsolute=0 (row rác trước Start button)
            uint16_t t1val = (timeAbsolute > 0) ? (timeAbsolute - 1) : 0;

            // Lưu milestone timestamp tại thời điểm GHI → header khớp với Time1 của row
            if(evStr[0] != '\0') {
                if     (strcmp(evStr, "CHARGE") == 0) timeChargeAbsolute = t1val;
                else if(strcmp(evStr, "TP")     == 0) timeTPAbsolute     = t1val;
                else if(strcmp(evStr, "DRY End") == 0) timeDRYeAbsolute  = t1val;
                else if(strcmp(evStr, "FCs")    == 0) timeFCsAbsolute    = t1val;
                else if(strcmp(evStr, "DROP")   == 0) timeDROPAbsolute   = t1val;
            }

            char t1[6], btbuf[8], etbuf[10];
            sprintf(t1, "%02d:%02d", (int)(t1val/60), (int)(t1val%60));
            dtostrf(Temperature_BT / 10.0f, 1, 1, btbuf);
            dtostrf((float)Airflow_Freq, 1, 1, etbuf);

            sdLogFile.print(t1);                     sdLogFile.print('\t'); // Time1 (wall time)
            if(sdChargeHappened) {
                // CHARGE row: Time2=00:00. Các row sau: tăng dần
                uint16_t t2val = (timeRoast > 0) ? (timeRoast - 1) : 0;
                char t2[6];
                sprintf(t2, "%02d:%02d", (int)(t2val/60), (int)(t2val%60));
                sdLogFile.print(t2);
            }
            sdLogFile.print('\t');                                                    // Time2
            sdLogFile.print(etbuf);                        sdLogFile.print('\t');    // ET
            sdLogFile.print(btbuf);                        sdLogFile.print('\t');    // BT
            sdLogFile.print(evStr);                        sdLogFile.print('\t');    // Event
            sdLogFile.print((float)airflowPercent,   1);   sdLogFile.print('\t');    // Air(%)
            sdLogFile.print((float)gasPercent,       1);   sdLogFile.print('\t');    // Burner(%)
            sdLogFile.print((float)drumPercent,      1);   sdLogFile.print('\t');    // Drum(%)
            sdLogFile.print((int)vacuumSetFlag_R);         sdLogFile.print('\t');    // VacFlag
            sdLogFile.print((int)vacuumSetpoint_R);        sdLogFile.print("\r\n");  // VacSP(Pa)
            sdLogFile.flush();
            SDLogSTEP = "SUCCESS";
        } else {
            SDLogSTEP = "FAIL";
        }
        sdLogDataEn = 0;
    }

    // Overwrite header với milestone thực rồi đóng file
    if(sdLogEndEn){
        // FILE_WRITE dùng O_AT_END (append) — seek(0) không ghi đúng vị trí
        // Phải close rồi mở lại bằng O_READ|O_WRITE (random access, không AT_END)
        if(sdLogFile) sdLogFile.close();

        // If there is a pending event that hasn't been flushed to the arrays yet,
        // record its wall-time into the corresponding absolute time variable so
        // the header will be updated correctly when we overwrite it below.
        if(sdCsvPendingEvent[0] != '\0'){
            uint16_t pendingT = (timeAbsolute > 0) ? (timeAbsolute - 1) : 0;
            if(strcmp(sdCsvPendingEvent, "CHARGE") == 0) timeChargeAbsolute = pendingT;
            else if(strcmp(sdCsvPendingEvent, "TP") == 0)     timeTPAbsolute     = pendingT;
            else if(strcmp(sdCsvPendingEvent, "DRY End") == 0) timeDRYeAbsolute  = pendingT;
            else if(strcmp(sdCsvPendingEvent, "FCs") == 0)    timeFCsAbsolute    = pendingT;
            else if(strcmp(sdCsvPendingEvent, "DROP") == 0)   timeDROPAbsolute   = pendingT;
            sdCsvPendingEvent[0] = '\0';
        }

        sdLogFile = SD.open(strProfileName, O_READ | O_WRITE);
        if(sdLogFile){
            sdLogFile.seek(0);
            char h[6];
            // Ghi date lúc START rang (không phải lúc DROP), giờ lúc CHARGE
            { char datetime[20]; sprintf(datetime, "%02d.%02d.%04d %02d:%02d:%02d",
                (int)sdStartDD, (int)sdStartMM, (int)sdStartYYYY,
                (int)sdChargeHH, (int)sdChargeMM, 0);
            sdLogFile.print("Date:"); sdLogFile.print(datetime); }
            // CHARGE = wall time từ Start; TP/DRYe/FCs/DROP = tính từ CHARGE (= Time2)
            sdLogFile.print("\tUnit:C\tCHARGE:");                         // +15 → 30
            sprintf(h, "%02d:%02d", (int)(timeChargeAbsolute/60), (int)(timeChargeAbsolute%60));
            sdLogFile.print(h);                                            // +5 → 35
            sdLogFile.print("\tTP:");                                      // +4 → 39
            { uint16_t s = (timeTPAbsolute > timeChargeAbsolute) ? timeTPAbsolute - timeChargeAbsolute : 0;
            sprintf(h, "%02d:%02d", (int)(s/60), (int)(s%60)); }
            sdLogFile.print(h);                                            // +5 → 44
            sdLogFile.print("\tDRYe:");                                    // +6 → 50
            { uint16_t s = (timeDRYeAbsolute > timeChargeAbsolute) ? timeDRYeAbsolute - timeChargeAbsolute : 0;
            sprintf(h, "%02d:%02d", (int)(s/60), (int)(s%60)); }
            sdLogFile.print(h);                                            // +5 → 55
            sdLogFile.print("\tFCs:");                                     // +5 → 60
            { uint16_t s = (timeFCsAbsolute > timeChargeAbsolute) ? timeFCsAbsolute - timeChargeAbsolute : 0;
            sprintf(h, "%02d:%02d", (int)(s/60), (int)(s%60)); }
            sdLogFile.print(h);                                            // +5 → 65
            sdLogFile.print("\tFCe:\tSCs:\tSCe:\tDROP:");                 // +21 → 86
            { uint16_t roastSec = (timeDROPAbsolute > timeChargeAbsolute) ? timeDROPAbsolute - timeChargeAbsolute : 0;
            sprintf(h, "%02d:%02d", (int)(roastSec/60), (int)(roastSec%60)); }
            sdLogFile.print(h);                                            // +5 → 91
            sdLogFile.print("\tCOOL:\tTime:");                            // +12 → 103
            { char rtc[6]; sprintf(rtc, "%02d:%02d", (int)sdChargeHH, (int)sdChargeMM);
            sdLogFile.print(rtc); }                                        // +5 → 108
            sdLogFile.print("\r\n");                                       // +2 → 110 ✓
            sdLogFile.close();
            SDLogSTEP = "SUCCESS";
            nodeHMI.writeSingleRegister(DATE_PROFILE_W-1, 1); delay(5);
        } else {
            SDLogSTEP = "FAIL";
        }
        sdLogStartEn = 0;
        sdLogEndEn = 0;
    }
}

// strtok bỏ qua trường rỗng (2 tab liền) → dùng hàm này thay thế
static char* _tsvNext(char** p) {
    if (!*p) return nullptr;
    char* start = *p;
    char* tab   = strchr(*p, '\t');
    if (tab) { *tab = '\0'; *p = tab + 1; }
    else       { *p = nullptr; }
    return start;
}

void sdRead(){
    //Lọc 
    //Lọc data từ profile
    sdReadStt = true;
    if (SELECT_FILE_R < 1 || SELECT_FILE_R > 30) {
        nodeHMI.writeSingleRegister(LOADING_SHOW_W-1, 0); delay(5);
        nodeHMI.writeSingleRegister(FA_SUC_W-1, 0); delay(5);
        return;
    }
    if((SCRNUM_R==6||SCRNUM_R==12||SCRNUM_R==13) && SELECT_FILE_R>0){
        switch(sdReadStep){
            case SD_1:
                sdMillis = millis();
                strProfileName = "";
                // Thử mở .csv trước (format mới), nếu không có thì dùng .txt cũ
                strProfileName = String(SELECT_FILE_R) + ".csv";
                tempFile = SD.open(strProfileName);
                if(!tempFile){
                    strProfileName = String(SELECT_FILE_R) + ".txt";
                    tempFile = SD.open(strProfileName);
                }
                if(tempFile) {
                    SDLogSTEP = "REOK";
                    bool isCsv = strProfileName.endsWith(".csv");

                    if(isCsv) {
                        // ── CSV parser (Artisan format) ──────────────────────────
                        char lineBuf[200];
                        uint16_t csvCHARGE = 0, csvTP = 0, csvDRYe = 0, csvFCs = 0, csvDROP = 0;
                        uint16_t csvDropIdx = 0; // Time2 thực tế của row DROP (index trong sdBT[])

                        percentLoadProfile = 0;
                        nodeHMI.writeSingleRegister(LOADING_SHOW_W-1, percentLoadProfile); delay(5); // % tải profile (100=hợp lệ, 0=lỗi)
                        uint32_t fileSize = tempFile.size();
                        uint8_t lastReportedPct = 255; // giá trị sentinel để in lần đầu
                        uint32_t lastHmiUpdate = millis(); // thời điểm cập nhật HMI lần cuối

                        while(tempFile.available()) {
                            // Đọc từng dòng vào char array (không dùng String để tiết kiệm heap)
                            uint8_t li = 0;
                            while(tempFile.available() && li < 198) {
                                char c = (char)tempFile.read();
                                if(c == '\n') break;
                                if(c == '\r') continue;
                                lineBuf[li++] = c;
                            }
                            lineBuf[li] = '\0';
                            if(li == 0) continue;

                            // Cập nhật tiến độ đọc file (0-99%, 100% dành cho kết quả validate)
                            if(fileSize > 0)
                                percentLoadProfile = (uint8_t)((uint32_t)tempFile.position() * 99UL / fileSize);

                            // Gửi HMI mỗi 100ms
                            if(millis() - lastHmiUpdate >= 50) {
                                lastHmiUpdate = millis();
                                nodeHMI.writeSingleRegister(LOADING_SHOW_W-1, percentLoadProfile); delay(5);
                            }

                            if(strncmp(lineBuf, "Date:", 5) == 0) {
                                // Try to parse full date + time: "Date:DD.MM.YYYY HH:MM:SS\t..."
                                int dd=0, mmth=0, yyyy=0, hh=0, minu=0, sec=0;
                                if (sscanf(lineBuf, "Date:%d.%d.%d %d:%d:%d", &dd, &mmth, &yyyy, &hh, &minu, &sec) >= 5) {
                                    // Store into dAddress[] so macros HOUR_R etc. reflect the values
                                    dAddress[HOUR_W]   = (uint16_t)hh;
                                    dAddress[MINUTE_W] = (uint16_t)minu;
                                    dAddress[SECOND_W] = (uint16_t)sec;
                                    dAddress[DAY_W]    = (uint16_t)dd;
                                    dAddress[MONTH_W]  = (uint16_t)mmth;
                                    dAddress[YEAR_W]   = (uint16_t)yyyy;
                                    // Write back to HMI so it displays the profile datetime immediately
                                }
                                // Parse milestone times từ header
                                char* p; int mm, ss;
                                p = strstr(lineBuf, "CHARGE:"); if(p){ sscanf(p+7, "%d:%d", &mm, &ss); csvCHARGE = mm*60+ss; }
                                p = strstr(lineBuf, "TP:"); if(p){ sscanf(p+3, "%d:%d", &mm, &ss); csvTP   = mm*60+ss; }
                                p = strstr(lineBuf, "DRYe:"); if(p){ sscanf(p+5, "%d:%d", &mm, &ss); csvDRYe = mm*60+ss; }
                                p = strstr(lineBuf, "FCs:"); if(p){ sscanf(p+4, "%d:%d", &mm, &ss); csvFCs  = mm*60+ss; }
                                p = strstr(lineBuf, "DROP:"); if(p){ sscanf(p+5, "%d:%d", &mm, &ss); csvDROP = mm*60+ss; }
                            }
                            else if(strncmp(lineBuf, "Time1", 5) == 0) {
                                // Skip header cột
                            }
                            else if(li > 4 && isdigit((unsigned char)lineBuf[0])) {
                                // Data row — dùng _tsvNext (xử lý đúng trường rỗng, strtok thì không)
                                // Columns: Time1\tTime2\tET\tBT\tEvent\tAir(%)\tBurner(%)\tDrum(%)\tVacFlag\tVacSP(Pa)
                                sdTempVacFlag = 0; sdTempVacSP = 0; sdTempRorBT = 0;
                                char* p = lineBuf;
                                _tsvNext(&p);                               // Time1 (bỏ qua)
                                char* f = _tsvNext(&p);                     // Time2 (roast time — index)
                                if(!f || f[0] == '\0') continue;            // Bỏ qua hàng trước CHARGE (Time2 rỗng)
                                int mm=0, ss=0; sscanf(f, "%d:%d", &mm, &ss);
                                sdTempTi = (uint16_t)(mm*60 + ss);
                                if(sdTempTi >= 1800) continue;

                                f = _tsvNext(&p);                           // ET
                                sdTempET = f ? atoi(f) : 0;
                                f = _tsvNext(&p);                           // BT
                                sdTempBT = f ? (int)(atof(f)*10+0.5f) : 0;
                                char* ev = _tsvNext(&p);                    // Event
                                // Trim leading whitespace in event field to handle variants like '\tDROP' or ' DROP'
                                char* evTrim = ev;
                                if(evTrim){ while(*evTrim==' '||*evTrim=='\t') evTrim++; }
                                // Case-insensitive substring match for "DROP"
                                if(evTrim){
                                    char* q = evTrim;
                                    while(*q){
                                        char c0 = *q;
                                        char c1 = q[1] ? q[1] : '\0';
                                        char c2 = q[2] ? q[2] : '\0';
                                        char c3 = q[3] ? q[3] : '\0';
                                        if( (c0=='D'||c0=='d') && (c1=='R'||c1=='r') && (c2=='O'||c2=='o') && (c3=='P'||c3=='p') ){
                                            csvDropIdx = sdTempTi;
                                            break;
                                        }
                                        q++;
                                    }
                                }
                                f = _tsvNext(&p);                           // Air(%)
                                sdTempAir  = f ? atoi(f) : 0;
                                f = _tsvNext(&p);                           // Burner(%)
                                sdTempGas  = f ? atoi(f) : 0;
                                f = _tsvNext(&p);                           // Drum(%)
                                sdTempDrum = f ? atoi(f) : 0;
                                f = _tsvNext(&p);                           // VacFlag
                                sdTempVacFlag = f ? atoi(f) : 0;
                                f = _tsvNext(&p);                           // VacSP(Pa)
                                sdTempVacSP   = f ? atoi(f) : 0;

                                // Only write into arrays if index within safe bounds
                                if(sdTempTi < 1800) {
                                    sdBT[sdTempTi]             = sdTempBT;
                                    sdET[sdTempTi]             = sdTempET;
                                    sdAirflow[sdTempTi]        = sdTempAir;
                                    sdGas[sdTempTi]            = sdTempGas;
                                    sdDrum[sdTempTi]           = sdTempDrum;
                                    // NOTE: ROR isn't present in the TSV/CSV format used here, keep 0 as placeholder
                                    sdRorBT[sdTempTi]          = sdTempRorBT;
                                    sdVacuumSetFlag[sdTempTi]  = sdTempVacFlag;
                                    sdVacuumSetpoint[sdTempTi] = sdTempVacSP;
                                }
                                SDLogSTEP = "DATA";

                                // DEBUG: in từng row theo cột
                            }
                        }

                        // Gán giá trị milestone từ header và array đã nạp
                        // Các thời gian trong header là Time1 (wall time), cần trừ csvCHARGE để ra roast time (Time2)
                        CHARGE_PRO_R  = sdBT[0];
                        uint16_t rtTP   = (csvTP   > csvCHARGE) ? csvTP   - csvCHARGE : 0;
                        uint16_t rtDRYe = (csvDRYe > csvCHARGE) ? csvDRYe - csvCHARGE : 0;
                        uint16_t rtFCs  = (csvFCs  > csvCHARGE) ? csvFCs  - csvCHARGE : 0;
                        uint16_t rtDROP = (csvDropIdx > 0) ? csvDropIdx :
                                          (csvDROP > csvCHARGE) ? csvDROP - csvCHARGE : 0;
                        TP_PRO_S_R   = rtTP;
                        DE_PRO_S_R   = rtDRYe;
                        FCS_PRO_S_R  = rtFCs;
                        DROP_PRO_S_R = rtDROP;
                        TP_PRO_R   = (rtTP   > 0 && rtTP   < 1800) ? sdBT[rtTP]   : 0;
                        DE_PRO_R   = (rtDRYe > 0 && rtDRYe < 1800) ? sdBT[rtDRYe] : 0;
                        FCS_PRO_R  = (rtFCs  > 0 && rtFCs  < 1800) ? sdBT[rtFCs]  : 0;
                        DROP_PRO_R = (rtDROP > 0 && rtDROP < 1800) ? sdBT[rtDROP] : 0;
                        // Tính DEV: thời gian = DROP - FCs; %DEV = devTime/dropTime*1000 (per mille)
                        { uint16_t devTime = (rtDROP > rtFCs) ? rtDROP - rtFCs : 0;
                          DEV_PRO_M_R = devTime / 60;
                          DEV_PRO_S_R = devTime % 60;
                          DEV_PRO_R   = (rtDROP > 0) ? (uint16_t)((uint32_t)devTime * 1000 / rtDROP) : 0; }
                        // Tách M/S
                        TP_PRO_M_R   = TP_PRO_S_R / 60;  TP_PRO_S_R  %= 60;
                        DE_PRO_M_R   = DE_PRO_S_R / 60;  DE_PRO_S_R  %= 60;
                        FCS_PRO_M_R  = FCS_PRO_S_R / 60; FCS_PRO_S_R %= 60;
                        DROP_PRO_M_R = DROP_PRO_S_R / 60; DROP_PRO_S_R %= 60;
                        SDLogSTEP = "PROPERTIES";

                        // ── Validate profile — kiểm tra đủ điều kiện rang auto ──
                        bool profileOK =
                            (CHARGE_PRO_R > 0)  &&  // BT tại CHARGE hợp lệ (> 0)
                            (rtTP   > 0)        &&  // Có Turning Point
                            (rtDROP >= 60)      &&  // Thời gian rang >= 1 phút
                            (DROP_PRO_R > 0);       // BT tại DROP hợp lệ
                        percentLoadProfile = profileOK ? 100 : 0;
                        nodeHMI.writeSingleRegister(LOADING_SHOW_W-1, percentLoadProfile); delay(5);
                        nodeHMI.writeSingleRegister(FA_SUC_W-1, profileOK ? 1 : 0); delay(5);

                        //Show dữ liệu lên serial monitor để debug


                    } else {
                        // ── TXT parser (format cũ R/P) ───────────────────────────
                        while (tempFile.available()){
                            char inChar  = (char)tempFile.read();

                            if(inChar == 'R')   sDataStr = true;
                            if(sDataStr)    inDataStr += inChar;
                            if(inChar=='E'&&sDataStr){
                                sDataStr = false;
                                if(inDataStr.charAt(0) == 'R'){
                                    int lenDataStr = inDataStr.length();
                                    char inDataCharArray[lenDataStr];
                                    inDataStr.toCharArray(inDataCharArray, lenDataStr);
                                    if(lenDataStr>8){
                                        sdTempVacFlag = 0; sdTempVacSP = 0;
                                        sscanf(inDataCharArray,"R%d,%d,%d,%d,%d,%d,%d,%d,%dE",
                                        &sdTempTi, &sdTempBT, &sdTempET, &sdTempAir,
                                        &sdTempGas, &sdTempDrum, &sdTempRorBT,
                                        &sdTempVacFlag, &sdTempVacSP);
                                        if(sdTempTi < 1800) {
                                            sdBT[sdTempTi]             = sdTempBT;
                                            sdET[sdTempTi]             = sdTempET;
                                            sdAirflow[sdTempTi]        = sdTempAir;
                                            sdGas[sdTempTi]            = sdTempGas;
                                            sdDrum[sdTempTi]           = sdTempDrum;
                                            sdRorBT[sdTempTi]          = sdTempRorBT;
                                            sdVacuumSetFlag[sdTempTi]  = sdTempVacFlag;
                                            sdVacuumSetpoint[sdTempTi] = sdTempVacSP;
                                        }
                                    }
                                    SDLogSTEP = "DATA";
                                }
                                inDataStr = "";
                            }

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
                                        TP_PRO_M_R   = TP_PRO_S_R/60;   TP_PRO_S_R   %= 60;
                                        DE_PRO_M_R   = DE_PRO_S_R/60;   DE_PRO_S_R   %= 60;
                                        FCS_PRO_M_R  = FCS_PRO_S_R/60;  FCS_PRO_S_R  %= 60;
                                        DEV_PRO_M_R  = DEV_PRO_S_R/60;  DEV_PRO_S_R  %= 60;
                                        DROP_PRO_M_R = DROP_PRO_S_R/60; DROP_PRO_S_R %= 60;
                                    }
                                    SDLogSTEP = "PROPERTIES";
                                }
                                inStr = "";
                            }
                        }
                    }

                    tempFile.close();
                    sdReadStep = SD_3;
                }else{
                    sdReadStep = SD_2;
                }
            break;

            case SD_2:
                SDLogSTEP = "READFAIL";
                percentLoadProfile = 0;
                nodeHMI.writeSingleRegister(LOADING_SHOW_W-1, percentLoadProfile); delay(5);
                nodeHMI.writeSingleRegister(FA_SUC_W-1, 0); delay(5);
                CHARGE_PRO_R = 0;
                TP_PRO_R = 0; TP_PRO_M_R = 0; TP_PRO_S_R = 0;
                DE_PRO_R = 0; DE_PRO_M_R = 0; DE_PRO_S_R = 0;
                FCS_PRO_R = 0; FCS_PRO_M_R = 0; FCS_PRO_S_R = 0;
                DEV_PRO_R = 0; DEV_PRO_M_R = 0; DEV_PRO_S_R = 0;
                DROP_PRO_R = 0; DROP_PRO_M_R = 0; DROP_PRO_S_R = 0;
                sdReadStep = SD_3; //Chuyển trạng thái show màn hình
            break;            

            case SD_3:
                nodeHMI.setTransmitBuffer(0,  CHARGE_PRO_R);
                nodeHMI.setTransmitBuffer(1,  TP_PRO_R);
                nodeHMI.setTransmitBuffer(2,  TP_PRO_M_R);
                nodeHMI.setTransmitBuffer(3,  TP_PRO_S_R);
                nodeHMI.setTransmitBuffer(4,  DE_PRO_R);
                nodeHMI.setTransmitBuffer(5,  DE_PRO_M_R);
                nodeHMI.setTransmitBuffer(6,  DE_PRO_S_R);
                nodeHMI.setTransmitBuffer(7,  FCS_PRO_R);
                nodeHMI.setTransmitBuffer(8,  FCS_PRO_M_R);
                nodeHMI.setTransmitBuffer(9,  FCS_PRO_S_R);
                nodeHMI.setTransmitBuffer(10, DEV_PRO_R);
                nodeHMI.setTransmitBuffer(11, DEV_PRO_M_R);
                nodeHMI.setTransmitBuffer(12, DEV_PRO_S_R);
                nodeHMI.setTransmitBuffer(13, DROP_PRO_R);
                nodeHMI.setTransmitBuffer(14, DROP_PRO_M_R);
                nodeHMI.setTransmitBuffer(15, DROP_PRO_S_R);
                nodeHMI.writeMultipleRegisters(CHARGE_PRO_W-1, 16); // reg 103-118, FC10
                delay(20); // Đảm bảo dữ liệu đã được gửi đi trước khi tiếp tục
                nodeHMI.writeSingleRegister(chargeTemp_W+2000,  CHARGE_PRO_R); delay(5); //
                nodeHMI.writeSingleRegister(LOADING_SHOW_W-1,   percentLoadProfile); delay(5);

                sdReadStep = SD_4;
                calSdMillis = millis() - sdMillis;
            break;

            case SD_4:
                //Chờ
                sdReadStt = false; // Tắt flag đọc file để hiển thị tiến độ trong modbusMaster
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
    if (sdVacuumSetFlag[lastTimeSD] == 1) {
        int16_t newSP = (int16_t)sdVacuumSetpoint[lastTimeSD];
        bool changed = (newSP != vacuumSetpoint_R) || (vacuumSetFlag_R != 1);
        vacuumSetFlag_R  = 1;
        vacuumSetpoint_R = newSP;
        if (changed) pidAirflowReset();
    } else {
        vacuumSetFlag_R  = 0;
        airflowPercent   = sdAirflow[lastTimeSD];
    }
    gasPercent  = sdGas[lastTimeSD];   //Gas
    drumPercent = sdDrum[lastTimeSD];  //Trống

    // Cập nhật HMI hiển thị vacuum flag và setpoint trong AUTO mode
    nodeHMI.writeSingleRegister(vacuumSetFlag_W+2000,  vacuumSetFlag_R);
    nodeHMI.writeSingleRegister(vacuumSetpoint_W+2000, vacuumSetpoint_R);


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

// ============================================================
// loadAllProfileDates()
// Đọc header dòng 1 của từng file CSV (slot 1–30),
// parse Date, ChargeTime, và DROP time.
// Ghi 7 registers/slot lên HMI địa chỉ 600–809.
//
// Layout HMI (1-based):
//   base+0 = DD   (ngày)
//   base+1 = MM   (tháng)
//   base+2 = YY   (năm 2 chữ số, 2024→24)
//   base+3 = HH   (giờ lúc charge, từ "Time:HH:MM" cuối header)
//   base+4 = MIN_CHARGE (phút lúc charge)
//   base+5 = roastTimeMin  (phút tổng rang CHARGE→DROP)
//   base+6 = roastTimeSec  (giây tổng rang CHARGE→DROP)
// ============================================================
void loadAllProfileDates() {
    for (int slot = 1; slot <= MAX_PROFILE_SLOTS; slot++) {
        uint16_t base = PROFILE_DATE_BASE_W + (slot - 1) * PROFILE_REGS_PER_SLOT;

        char fname[8];
        sprintf(fname, "%d.csv", slot);

        File f = SD.open(fname);
        if (!f) {
            for (uint8_t r = 0; r < PROFILE_REGS_PER_SLOT; r++) {
                nodeHMI.writeSingleRegister(base + r, 0);
                delay(1);
            }
            continue;
        }

        // Đọc dòng 1 (header milestones), tối đa 120 bytes cố định
        char line[120];
        uint8_t len = 0;
        while (f.available() && len < sizeof(line) - 1) {
            char c = f.read();
            if (c == '\n') break;
            if (c != '\r') line[len++] = c;
        }
        line[len] = '\0';
        f.close();

        // --- Parse Date: "Date:DD.MM.YYYY HH:MM:SS\t..."
        uint8_t dd = 0, mm = 0, yy = 0;
        char* datePtr = strstr(line, "Date:");
        if (datePtr) {
            int d, mo, y;
            if (sscanf(datePtr + 5, "%d.%d.%d", &d, &mo, &y) == 3) {
                dd = (uint8_t)d;
                mm = (uint8_t)mo;
                yy = (uint8_t)(y % 100);
            }
        }

        // --- Parse charge wall-clock time: "Time:HH:MM" at end of header
        uint8_t chHH = 0, chMM = 0;
        char* timePtr = strstr(line, "Time:");
        if (timePtr) {
            int h, mn;
            if (sscanf(timePtr + 5, "%d:%d", &h, &mn) == 2) {
                chHH = (uint8_t)h;
                chMM = (uint8_t)mn;
            }
        }

        // --- Parse CHARGE wall time từ Start: "CHARGE:MM:SS"
        uint16_t chargeSec = 0;
        char* chargePtr = strstr(line, "CHARGE:");
        if (chargePtr) {
            int cm, cs;
            if (sscanf(chargePtr + 7, "%d:%d", &cm, &cs) == 2)
                chargeSec = (uint16_t)(cm * 60 + cs);
        }

        // --- Parse DROP time: "DROP:MM:SS" — lưu trực tiếp, không trừ CHARGE
        uint8_t roastTimeMin = 0, roastTimeSec = 0;
        char* dropPtr = strstr(line, "DROP:");
        if (dropPtr) {
            int dm, ds;
            if (sscanf(dropPtr + 5, "%d:%d", &dm, &ds) == 2) {
                roastTimeMin = (uint8_t)dm;
                roastTimeSec = (uint8_t)ds;
            }
        }

        // --- Ghi 7 registers lên HMI
        nodeHMI.writeSingleRegister(base + 0, dd);           delay(1);
        nodeHMI.writeSingleRegister(base + 1, mm);           delay(1);
        nodeHMI.writeSingleRegister(base + 2, yy);           delay(1);
        nodeHMI.writeSingleRegister(base + 3, chHH);         delay(1);
        nodeHMI.writeSingleRegister(base + 4, chMM);         delay(1);
        nodeHMI.writeSingleRegister(base + 5, roastTimeMin); delay(1);
        nodeHMI.writeSingleRegister(base + 6, roastTimeSec); delay(1);
    }

    // if (enDebug) 
    // SerialComputer.println("=> Profile dates loaded to HMI");
}

// In trạng thái rang auto ra SerialComputer — gọi mỗi giây từ loop()
void debugRoastStatus() {
    if (!enDebug) return;

    // Tên bước
    const char* stepName = "?";
    switch (progStep) {
        case STP_DATA:      stepName = "DATA";     break;
        case STP_COOL_DOWN: stepName = "COOLDOWN"; break;
        case STP_GAS:       stepName = "GAS";      break;
        case STP_CHECK:     stepName = "CHECK";    break;
        case STP_CHARGE:    stepName = "CHARGE";   break;
        case STP_TP:        stepName = "TP";       break;
        case STP_YELLOW:    stepName = "YELLOW";   break;
        case STP_FCS:       stepName = "FCS";      break;
        case STP_DEV:       stepName = "DEV";      break;
        case STP_DROP:      stepName = "DROP";     break;
        case 11:   stepName = "COOLING";  break;
        case STP_ESCAPE:    stepName = "ESCAPE";   break;
    }

    uint16_t tMin = timeRoast / 60;
    uint16_t tSec = timeRoast % 60;

    SerialComputer.print("["); SerialComputer.print(stepName); SerialComputer.print("] ");
    SerialComputer.print("T="); SerialComputer.print(tMin); SerialComputer.print(":");
    if (tSec < 10) SerialComputer.print("0");
    SerialComputer.print(tSec);
    SerialComputer.print(" | BT="); SerialComputer.print(BT_HMI_R / 10.0f, 1);
    SerialComputer.print(" | Gas="); SerialComputer.print(gasPercent); SerialComputer.print("%");
    SerialComputer.print(" | Air="); SerialComputer.print(airflowPercent); SerialComputer.print("%");
    SerialComputer.print(" | Vac="); SerialComputer.print(Diff_Air); SerialComputer.print("Pa");
    SerialComputer.print(" | SP="); SerialComputer.print(vacuumSetpoint_R); SerialComputer.print("Pa");

    // Calib gas info (chỉ sau TP, khi đang chạy auto)
    if (progStep > STP_TP && calibGasProgramEn) {
        int16_t btTarget = sdBT[lastTimeSD];
        int16_t btDiff   = Temperature_BT - btTarget;
        SerialComputer.print(" | CAL BT="); SerialComputer.print(Temperature_BT / 10.0f, 1);
        SerialComputer.print(" TGT=");      SerialComputer.print(btTarget / 10.0f, 1);
        SerialComputer.print(" diff=");     SerialComputer.print(btDiff / 10.0f, 1);
        SerialComputer.print(" step=");     SerialComputer.print(numIncGas);
    }

    SerialComputer.println();
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
                    timeAbsolute = 0;
                    timeAbsoluteEn = 1;
                    sdChargeHappened = false;
                    sdCsvPendingEvent[0] = '\0';
                }

                //Đọc ngày giờ hiện tại từ HMI và ghi vào SD
                updateDateTimeEn = 1;

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
                TIME_YELLOW_MIN_SAVE = TIME_YELLOW_SAVE/60;
                TIME_YELLOW_SEC_SAVE = TIME_YELLOW_SAVE%60;

                TIME_FCS_SAVE = 0;
                TIME_FCS_MIN_SAVE = TIME_FCS_SAVE/60;
                TIME_FCS_SEC_SAVE = TIME_FCS_SAVE%60;

                PER_DEV_SAVE = 0;
                TIME_DEV_MIN_SAVE = 0;
                TIME_DEV_SEC_SAVE = 0;
                
                TIME_DROP_SAVE = 0;
                timeTPAbsolute   = 0;
                timeDRYeAbsolute = 0;
                timeFCsAbsolute  = 0;
                timeDROPAbsolute = 0;

                timeRoast = 0;

                nodeHMI.writeSingleRegister(CLEAR_HIS_CONTROL_W-1, 1);  //Clear trend graph
                nodeHMI.writeSingleCoil(LOCK_BUTTON_W-1, 1);    //Lock các button trên HMI khi rang
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
                    sdChargeHappened = true;           // Bắt đầu ghi Time2 (timestamp lưu khi ghi)
                    sdChargeHH = (uint8_t)HOUR_R;      // Lưu giờ RTC lúc CHARGE
                    sdChargeMM = (uint8_t)MINUTE_R;    // Lưu phút RTC lúc CHARGE
                    strcpy(sdCsvPendingEvent, "CHARGE");
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
                        strcpy(sdCsvPendingEvent, "TP");
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
                    strcpy(sdCsvPendingEvent, "DRY End");
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
                    strcpy(sdCsvPendingEvent, "FCs");
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
                    nodeHMI.writeSingleRegister(warnDeleteProfile-1, 0);  //Turn off start
                    nodeHMI.writeSingleCoil(LOCK_BUTTON_W-1, 0);  //Mở khoá select
                    aLoaderStep = STP_NONE_LOADER; //Trạng thái auto loader về 0
                    progStep = STP_DATA;   //Reset manual save step 
                    STEP_STRING = "NONE";
                }

                //Kiểm tra xem có cần rang tiếp hay không
                if(loop_R <= 1){
                    nodeHMI.writeSingleRegister(START_BTN_W-1, 0);  //Turn off start
                    nodeHMI.writeSingleRegister(warnDeleteProfile-1, 0);  //Turn off start
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
                    nodeHMI.writeSingleRegister(warnDeleteProfile-1, 0);  //Turn off start
                    nodeHMI.writeSingleCoil(LOCK_BUTTON_W-1, 0);  //Mở khoá select
                    sdLogEndEn = 1;//Hoàn tất lưu data phase
                    progStep = 0;   //Reset manual save step
                }
                //Nếu nút auto off gas = 1 thì tắt gas
                if(autoOff_R==1) 
                    nodeHMI.writeSingleRegister(START_GAS_BTN_W-1, 0);  //Turn off gas
                BT_DROP_SAVE = Temperature_BT;
                TIME_DROP_SAVE = timeRoast;
                strcpy(sdCsvPendingEvent, "DROP");
                // Ensure the pending DROP event is flushed to file immediately
                // before we stop wall-time/counting so the row will include Time2
                sdLogDataEn = 1;

                //Trả gió gas trống về biến trở
                naviSourceGAS = SOURCE_AI_VR; //Đổi source sang VR
                naviSourceDRUM = SOURCE_AI_VR;
                naviSourceAIR = SOURCE_AI_VR;

                //Bật cooling&mixer nếu nhập số lớn hơn 0
                if(coolTimer_R>0&&coolStep==0) coolStep = 1; 
                 
                timeRoastEn = 0;

                nodeHMI.writeSingleCoil(SAMPLE_COIL_W-1, 0);  //Turn off trend graph sample
                timeAbsoluteEn = 0; // Dừng đếm wall time

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
            timeAbsoluteEn = 0; //Dừng đếm wall time

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

        if(progStatus == STT_PROGRAM_SAVE){
            loadAllProfileDates(); //Tải lại ngày giờ để chuẩn bị cho mẻ rang tiếp theo
        }
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