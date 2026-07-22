#if PREHEAT_USE_PID
#include "Preheat_PID.h"
#else
#include "Preheat.h"
#endif
void loadAllProfileDates(); // forward declaration
#include "RoR_Control.h"

void timerPoll_1000ms(){
    // ── PRIORITY 1: keep drum/fan on while BT or ET is hotter than 80°C ─────
    // ISR context: NO Modbus calls — use flag pattern only
    if (((int16_t)Temperature_BT > 800 ||   // BT > 80.0°C
         (int16_t)Temperature_ET > 800) &&  // ET > 80.0°C
        DRUM_FAN_BTN_R == 0) {
        forceDrumFanOnFlag = true;   // programScan() will execute HMI write
    }
    // ─────────────────────────────────────────────────────────────────────────

    // ── PRIORITY 1: safety cutoff ────────────────────────────────────────────
    // ISR context: NO Modbus calls — use flag pattern only
    if ((int16_t)Temperature_BT > 2500 ||   // BT > 250.0°C
        (int16_t)Temperature_ET > 3500 ||   // ET > 350.0°C
        ((int16_t)Temperature_ET > 3000 && (int16_t)Temperature_BT < 1500)) {  // ET>300°C, BT<150°C
        gasPercent  = 0;      // cut gas via DAC immediately
        fireCutFlag = true;   // programScan() will execute Modbus cutoff
    }
    // ─────────────────────────────────────────────────────────────────────────

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
        if(updateNetWTi>=5) scaleDataValid = false;
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
        if(rorBT>(950)) rorBT = 950;    // trần ±95°C/phút (950 ×10 = 9500 = 95.00)
        if(rorBT<(-950)) rorBT = -950;
        rorBT = rorBT*10;

        if(rorET>(200)) rorET = 200;
        if(rorET<(-200)) rorET = -200;
        rorET = rorET*10;
        //update BT
        // old_rorBT = raw_rorBT;
        rorBTSamp_1 = Temperature_BT;
        rorETSamp_1 = Temperature_ET;

        //RoR của profile mẫu tại thời điểm hiện tại — tính cùng cách rorBT thực
        //(window 3s, *20 rồi *10) để so sánh trực tiếp với rorBT.
        //Không cần Kalman vì sdBT[] mẫu đã mượt sẵn. Chỉ có nghĩa khi rang AUTO.
        if(lastTimeSD>=3){
            int16_t raw_rorBT_pro = ((int16_t)sdBT[lastTimeSD]-(int16_t)sdBT[lastTimeSD-3])*20;
            if(raw_rorBT_pro>950)  raw_rorBT_pro = 950;    // cùng trần ±95°C/phút với rorBT
            if(raw_rorBT_pro<-950) raw_rorBT_pro = -950;
            rorBT_pro = raw_rorBT_pro*10;
        }else{
            rorBT_pro = 0;
        }

        rorCount = 0; //Reset count
    }

    //RoR cân — bộ đếm RIÊNG, cửa sổ 1 giây (bám NHANH cho mẻ ngắn: mẻ nhỏ chỉ chảy ~2-3s), tách khỏi rorBT/rorET (3s).
    //Cùng chiều rorBT: cân TĂNG → dương, cân GIẢM (hút) → âm.
    //Hệ số ×6 cho cửa sổ 1s; clamp ±600 → ×10 = ±6000 = trần 60 kg/phút (1kg/phút=100).
    rorCountKG++;
    if(rorCountKG==1){
        int32_t d = ((int32_t)netW100 - kgSamp_1) * 6;  // int32 tránh tràn khi delta lớn (vd boot: kgSamp_1=0)
        if(d > 600)  d = 600;                            // clamp ±600 = ±60 kg/phút TRƯỚC Kalman (chặn rác vào bộ lọc)
        if(d < -600) d = -600;
        raw_rorKG = (int16_t)d;
        rorKG = rorKGKalmanFilter.updateEstimate(raw_rorKG);
        rorKG = rorKG*10;
        kgSamp_1 = netW100;
        rorCountKG = 0; //Reset count cân
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
    // Preheat timer -- count up every second (no Modbus here, ISR context)
    if (wuState == WU_IGNITE) {
        wuIgniteTimer++;
    } else if (wuState == WU_HEATING || wuState == WU_HOLDING || wuState == WU_PRECISION
#if PREHEAT_USE_PID
               || wuState == WU_TUNE
#endif
              ) {
        wuElapsed++;
    }

}

void sdLogWrite(){
    snprintf(strProfileName, sizeof(strProfileName), "%u.csv", (unsigned)SELECT_FILE_R);

    // --- HANDLE DEDICATED DELETE REQUEST (from HMI)
    if(sdDeleteProfileEn){
        if(sdLogFile) sdLogFile.close();
        if(sdDeleteProfileIndex > 0 && sdDeleteProfileIndex <= 31){
            char delNameCsv[12];
            char delNameTxt[12];
            snprintf(delNameCsv, sizeof(delNameCsv), "%d.csv", sdDeleteProfileIndex);
            snprintf(delNameTxt, sizeof(delNameTxt), "%d.txt", sdDeleteProfileIndex);
            SD.remove(delNameCsv);
            SD.remove(delNameTxt); // optional: remove .txt too
            SDLogSTEP = "DEL OK";
            setMachineStatus(STT_SD_DELETE_OK);
        } else {
            SDLogSTEP = "DEL IDX ERR";
            setMachineStatus(STT_SD_DELETE_FAIL);
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
            sdMaxGasSaved = (uint8_t)constrain((int)maxGasSet_R, 0, 100);  // chốt trần gas lúc START để lưu 1 lần vào header
            // Placeholder header — độ dài cố định 110 bytes (MM:SS / HH:MM luôn 5 ký tự)
            // Sẽ được overwrite bằng seek(0) khi DROP với milestone thực
            { char datetime[20]; sprintf(datetime, "%02d.%02d.%04d %02d:%02d:%02d",
                (int)sdStartDD, (int)sdStartMM, (int)sdStartYYYY, 0, 0, 0);
            sdLogFile.print("Date:"); sdLogFile.print(datetime);
            sdLogFile.print("\tUnit:C\tCHARGE:00:00\tTP:00:00\tDRYe:00:00\tFCs:00:00\tFCe:\tSCs:\tSCe:\tDROP:00:00\tCOOL:\tTime:00:00");
            { char mg[14]; sprintf(mg, "\tMaxGas:%03d\r\n", (int)sdMaxGasSaved); sdLogFile.print(mg); } }
            // Header cột — Artisan format chuẩn
            sdLogFile.print("Time1\tTime2\tET\tBT\tEvent\tAir(%)\tBurner(%)\tDrum(%)\tVacFlag\tVacSP(Pa)\r\n");
            sdLogFile.flush();
            SDLogSTEP = "OPEN OK";
            setMachineStatus(STT_SD_LOG_STARTED);
            // Reset bộ đếm wall time
            timeAbsolute = 0;
            timeChargeAbsolute = 0;
            sdChargeHappened = false;
            sdChargeHH = 0;
            sdChargeMM = 0;
            sdCsvPendingEvent[0] = '\0';
        } else {
            SDLogSTEP = "OPEN FAIL";
            setMachineStatus(STT_SD_SAVE_FAIL);
        }
        sdLogStartEn = 0;
    }

    if(sdRemoveAll){
        setMachineStatus(STT_SD_DELETING_ALL);
        if(sdLogFile) sdLogFile.close();
        for(int i=0;i<31;i++){
            char fileName[12];
            snprintf(fileName, sizeof(fileName), "%d.csv", i);
            SD.remove(fileName);
            snprintf(fileName, sizeof(fileName), "%d.txt", i);
            SD.remove(fileName); // xoá cả file cũ định dạng TXT
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

            char t1[6], btbuf[8];
            sprintf(t1, "%02d:%02d", (int)(t1val/60), (int)(t1val%60));
            dtostrf(Temperature_BT / 10.0f, 1, 1, btbuf);

            sdLogFile.print(t1);                     sdLogFile.print('\t'); // Time1 (wall time)
            if(sdChargeHappened) {
                // CHARGE row: Time2=00:00. Các row sau: tăng dần
                uint16_t t2val = (timeRoast > 0) ? (timeRoast - 1) : 0;
                char t2[6];
                sprintf(t2, "%02d:%02d", (int)(t2val/60), (int)(t2val%60));
                sdLogFile.print(t2);
            }
            sdLogFile.print('\t');                                                    // Time2
            sdLogFile.print(Temperature_ET / 10.0f, 1);   sdLogFile.print('\t');    // ET
            sdLogFile.print(btbuf);                        sdLogFile.print('\t');    // BT
            sdLogFile.print(evStr);                        sdLogFile.print('\t');    // Event
            sdLogFile.print((float)clampProfilePercent(airflowPercent), 1); sdLogFile.print('\t'); // Air(%)
            sdLogFile.print((float)clampProfilePercent(gasPercent),     1); sdLogFile.print('\t'); // Burner(%)
            sdLogFile.print((float)clampProfilePercent(drumPercent),    1); sdLogFile.print('\t'); // Drum(%)
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
            { char mg[12]; sprintf(mg, "\tMaxGas:%03d", (int)sdMaxGasSaved);
            sdLogFile.print(mg); }                                         // +11 → 119
            sdLogFile.print("\r\n");                                       // +2 → 121 ✓
            sdLogFile.close();
            SDLogSTEP = "SUCCESS";
            nodeHMI.writeSingleRegister(DATE_PROFILE_W-1, 1); delay(5);
        } else {
            SDLogSTEP = "FAIL";
        }
        sdLogStartEn = 0;
            setMachineStatus(STT_SD_LOG_ENDED);
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
    static bool sdProfileLoadOK = false;
    static uint16_t sdProfileLoadFailStatus = STT_SD_LOAD_FAIL;
    sdReadStt = true;
    if (SELECT_FILE_R < 1 || SELECT_FILE_R > 30) {
        nodeHMI.writeSingleRegister(LOADING_SHOW_W-1, 0); delay(5);
        nodeHMI.writeSingleRegister(FA_SUC_W-1, 0); delay(5);
        return;
    }
    if((SCRNUM_R==6||SCRNUM_R==12||SCRNUM_R==13) && SELECT_FILE_R>0){
        bool isCsv = true;
        switch(sdReadStep){
            case SD_1:
                sdMillis = millis();
                sdProfileLoadOK = false;
                sdProfileLoadFailStatus = STT_SD_LOAD_FAIL;
                sdMaxGasLoaded = -1;   // reset: profile không có MaxGas thì giữ -1, không áp giá trị cũ
                strProfileName[0] = '\0';
        setMachineStatus(STT_SD_LOADING_PROFILE);
                // Thử mở .csv trước (format mới), nếu không có thì dùng .txt cũ
                snprintf(strProfileName, sizeof(strProfileName), "%u.csv", (unsigned)SELECT_FILE_R);
                tempFile = SD.open(strProfileName);
                isCsv = true;
                if(!tempFile){
                    snprintf(strProfileName, sizeof(strProfileName), "%u.txt", (unsigned)SELECT_FILE_R);
                    tempFile = SD.open(strProfileName);
                    isCsv = false;
                }
                if(tempFile) {
                    SDLogSTEP = "REOK";

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
                                // Lưu trần gas từ profile (chỉ lưu, áp lúc bắt đầu rang AUTO; profile cũ không có field → giữ -1)
                                p = strstr(lineBuf, "MaxGas:"); if(p){ int mg=-1; sscanf(p+7, "%d", &mg); if(mg>=0 && mg<=100) sdMaxGasLoaded = mg; }
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
                                if(sdTempTi >= PROFILE_MAX_SECONDS) continue;

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
                                sdTempAir  = clampProfilePercent(f ? atoi(f) : 0);
                                f = _tsvNext(&p);                           // Burner(%)
                                sdTempGas  = clampProfilePercent(f ? atoi(f) : 0);
                                f = _tsvNext(&p);                           // Drum(%)
                                sdTempDrum = clampProfilePercent(f ? atoi(f) : 0);
                                f = _tsvNext(&p);                           // VacFlag
                                sdTempVacFlag = f ? atoi(f) : 0;
                                f = _tsvNext(&p);                           // VacSP(Pa)
                                sdTempVacSP   = f ? atoi(f) : 0;

                                // Only write into arrays if index within safe bounds
                                if(sdTempTi < PROFILE_MAX_SECONDS) {
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
                        // CHARGE = wall time; TP/DRYe/FCs/DROP = roast time (Time2) — không cần trừ
                        CHARGE_PRO_R  = sdBT[0];
                        uint16_t rtTP   = csvTP;
                        uint16_t rtDRYe = csvDRYe;
                        uint16_t rtFCs  = csvFCs;
                        uint16_t rtDROP = (csvDropIdx > 0) ? csvDropIdx :
                                          (csvDROP > csvCHARGE) ? csvDROP - csvCHARGE : 0;
                        TP_PRO_S_R   = rtTP;
                        DE_PRO_S_R   = rtDRYe;
                        FCS_PRO_S_R  = rtFCs;
                        DROP_PRO_S_R = rtDROP;
                        TP_PRO_R   = (rtTP   > 0 && rtTP   < PROFILE_MAX_SECONDS) ? sdBT[rtTP]   : 0;
                        DE_PRO_R   = (rtDRYe > 0 && rtDRYe < PROFILE_MAX_SECONDS) ? sdBT[rtDRYe] : 0;
                        FCS_PRO_R  = (rtFCs  > 0 && rtFCs  < PROFILE_MAX_SECONDS) ? sdBT[rtFCs]  : 0;
                        DROP_PRO_R = (rtDROP > 0 && rtDROP < PROFILE_MAX_SECONDS) ? sdBT[rtDROP] : 0;
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
                        bool profileOK = true;
                        if (CHARGE_PRO_R <= 0) {
                            profileOK = false;
                            sdProfileLoadFailStatus = STT_SD_LOAD_BAD_CHARGE;
                            SDLogSTEP = "BAD_CHARGE";
                        } else if (rtTP <= 0) {
                            profileOK = false;
                            sdProfileLoadFailStatus = STT_SD_LOAD_BAD_TP;
                            SDLogSTEP = "BAD_TP";
                        } else if (rtDROP < 60) {
                            profileOK = false;
                            sdProfileLoadFailStatus = STT_SD_LOAD_BAD_DROP_TIME;
                            SDLogSTEP = "BAD_DROP_TIME";
                        } else if (DROP_PRO_R <= 0) {
                            profileOK = false;
                            sdProfileLoadFailStatus = STT_SD_LOAD_BAD_DROP_TEMP;
                            SDLogSTEP = "BAD_DROP_TEMP";
                        }
                        percentLoadProfile = profileOK ? 100 : 0;
                        nodeHMI.writeSingleRegister(LOADING_SHOW_W-1, percentLoadProfile); delay(5);
                        nodeHMI.writeSingleRegister(FA_SUC_W-1, profileOK ? 1 : 0); delay(5);
                        sdProfileLoadOK = profileOK;

                        //Show dữ liệu lên serial monitor để debug


                    } else {
                        // ── TXT parser (format cũ R/P) ───────────────────────────
                        char txtDataBuf[160];
                        char txtPropBuf[120];
                        uint8_t txtDataLen = 0;
                        uint8_t txtPropLen = 0;
                        sDataStr = false;
                        sStr = false;
                        while (tempFile.available()){
                            char inChar  = (char)tempFile.read();

                            if(inChar == 'R') {
                                sDataStr = true;
                                txtDataLen = 0;
                            }
                            if(sDataStr) {
                                if(txtDataLen < sizeof(txtDataBuf) - 1) {
                                    txtDataBuf[txtDataLen++] = inChar;
                                } else {
                                    sDataStr = false;
                                    txtDataLen = 0;
                                }
                            }
                            if(inChar=='E'&&sDataStr){
                                sDataStr = false;
                                txtDataBuf[txtDataLen] = '\0';
                                if(txtDataBuf[0] == 'R'){
                                    if(txtDataLen>8){
                                        sdTempVacFlag = 0; sdTempVacSP = 0;
                                        int ti=0, bt=0, et=0, air=0, gas=0, drum=0, ror=0, vacFlag=0, vacSP=0;
                                        int n = sscanf(txtDataBuf,"R%d,%d,%d,%d,%d,%d,%d,%d,%dE",
                                        &ti, &bt, &et, &air, &gas, &drum, &ror, &vacFlag, &vacSP);
                                        if(n >= 7 && ti >= 0 && ti < PROFILE_MAX_SECONDS) {
                                            sdTempTi      = (uint16_t)ti;
                                            sdTempBT      = (uint16_t)max(0, bt);
                                            sdTempET      = (uint16_t)max(0, et);
                                            sdTempAir     = clampProfilePercent(air);
                                            sdTempGas     = clampProfilePercent(gas);
                                            sdTempDrum    = clampProfilePercent(drum);
                                            sdTempRorBT   = (int16_t)ror;
                                            sdTempVacFlag = (vacFlag == 1) ? 1 : 0;
                                            sdTempVacSP   = (uint16_t)max(0, vacSP);
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
                                txtDataLen = 0;
                            }

                            if(inChar == 'P') {
                                sStr = true;
                                txtPropLen = 0;
                            }
                            if(sStr) {
                                if(txtPropLen < sizeof(txtPropBuf) - 1) {
                                    txtPropBuf[txtPropLen++] = inChar;
                                } else {
                                    sStr = false;
                                    txtPropLen = 0;
                                }
                            }
                            if(inChar=='E'&&sStr){
                                sStr = false;
                                txtPropBuf[txtPropLen] = '\0';
                                if(txtPropBuf[0] == 'P'){
                                    if(txtPropLen>8){
                                        sscanf(txtPropBuf,"P%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%dE",
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
                                txtPropLen = 0;
                            }
                        }
                    }

                    if(!isCsv) {
                        sdProfileLoadOK =
                            (CHARGE_PRO_R > 0) &&
                            (DROP_PRO_R > 0) &&
                            ((DROP_PRO_M_R > 0) || (DROP_PRO_S_R > 0));
                        if (!sdProfileLoadOK) {
                            sdProfileLoadFailStatus = STT_SD_LOAD_BAD_TXT;
                            SDLogSTEP = "BAD_TXT";
                        }
                        percentLoadProfile = sdProfileLoadOK ? 100 : 0;
                        nodeHMI.writeSingleRegister(LOADING_SHOW_W-1, percentLoadProfile); delay(5);
                        nodeHMI.writeSingleRegister(FA_SUC_W-1, sdProfileLoadOK ? 1 : 0); delay(5);
                    }

                    tempFile.close();
                    sdReadStep = SD_3;
                }else{
                    sdReadStep = SD_2;
                }
            break;

            case SD_2:
                SDLogSTEP = "READFAIL";
                sdProfileLoadOK = false;
                sdProfileLoadFailStatus = STT_SD_LOAD_NO_FILE;
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
                nodeHMI.writeSingleRegister(chargeTemp_W+2000,  sdProfileLoadOK ? CHARGE_PRO_R : 1800); delay(5); //
                nodeHMI.writeSingleRegister(LOADING_SHOW_W-1,   percentLoadProfile); delay(5);

                rorCtrl_populateSdRorBT(); // Tính sdRorBT[] từ sdBT[] sau khi load xong

                sdReadStep = SD_4;
                setMachineStatus(sdProfileLoadOK ? STT_SD_LOAD_OK : sdProfileLoadFailStatus);
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

// Lưu trạng thái vacuumSetFlag trước khi rang AUTO để khôi phục khi DROP/abort.
// Profile có thể tự bật vacuum PID giữa mẻ; khi xong phải trả về đúng trạng thái ban đầu:
// trước rang TẮT → sau rang tắt lại; trước rang BẬT sẵn → sau rang giữ bật.
static uint8_t roastVacFlagSaved = 0;

void calibProgram(){
    //Cập nhập dữ liệu từ SD mỗi giây
    //Dữ liệu gốc từ SD
    //Gió và trống sẽ được giữ nguyên
    //Dữ liệu chỉ được cập nhật khi thời gian rang bằng thời gian file mẫu
    if(timeRoast<=sdTempTi){
        lastTimeSD = timeRoast;
    }
#if MACHINE_HAS_VACUUM_SENSOR
    if (sdVacuumSetFlag[lastTimeSD] == 1) {
        int16_t newSP = (int16_t)sdVacuumSetpoint[lastTimeSD];
        bool changed = (newSP != vacuumSetpoint_R) || (vacuumSetFlag_R != 1);
        vacuumSetFlag_R  = 1;
        vacuumSetpoint_R = newSP;
        if (changed) pidAirflowReset();
    } else {
        vacuumSetFlag_R  = 0;
        airflowPercent   = sdAirflow[lastTimeSD];
        nodeHMI.writeSingleRegister(airSpeed_W + 2000, airflowPercent);
    }
#else
    vacuumSetFlag_R = 0;
    airflowPercent = sdAirflow[lastTimeSD];
#endif
    gasPercent  = sdGas[lastTimeSD];   //Gas
    drumPercent = sdDrum[lastTimeSD];  //Trống
    nodeHMI.writeSingleRegister(drumSpeed_W + 2000, drumPercent);
    if (!MACHINE_HAS_GAS_CONTROL) gasPercent = 0;
    if (!MACHINE_HAS_DRUM_SPEED_CONTROL) drumPercent = 0;

#if MACHINE_HAS_VACUUM_SENSOR
    // Cập nhật HMI hiển thị vacuum flag và setpoint trong AUTO mode
    nodeHMI.writeSingleRegister(vacuumSetFlag_W+2000,  vacuumSetFlag_R);
    nodeHMI.writeSingleRegister(vacuumSetpoint_W+2000, vacuumSetpoint_R);
#endif


    //Hiệu chỉnh gas theo phase
    //Bắt đầu hiệu chỉnh sau khi TP
    //Auto gas khi temp BT nằm ngoài định mức
    if(progStep>STP_TP){
        //Từ FCS trở đi siết deadband xuống ±0.6°C (=6) để giữ Dev time bám mẫu chặt hơn
        //Trước FCS giữ ±1.0°C (clRangeBt) cho đỡ nhạy nhiễu giai đoạn đầu
        uint16_t clRange = (Temperature_BT>=FCS_PRO_R) ? 6 : clRangeBt;
        if( Temperature_BT>sdBT[lastTimeSD]+clRange
        ||  Temperature_BT<sdBT[lastTimeSD]-clRange){
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
            if(Temperature_BT<(sdBT[lastTimeSD]-clRange))
                gasPercent = gasPercent+numIncGas;

            //BT thực tế cao hơn SD thì giảm gas
            if(Temperature_BT>(sdBT[lastTimeSD]+clRange))
                gasPercent = gasPercent-numIncGas;

            if(gasPercent>100)  gasPercent = 100;
            if(gasPercent<0)  gasPercent = 0;
        }else{
            timeCalibGas = 0;
            numIncGas = 0;
            calibGas = 0;
        }

        // RoR control chỉ dùng cho preheat, không can thiệp gas khi rang auto
    }
    nodeHMI.writeSingleRegister(burnerValue_W + 2000, gasPercent); //cập nhật gas lên HMI
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
        case 11:   stepName = "MIX&COOL"; break;
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

    // preheat info
    if (wuState != WU_IDLE) {
        const char* wuName = "?";
        switch (wuState) {
            case WU_COOLING: wuName = "COOLING"; break;
            case WU_IGNITE:  wuName = "IGNITE";  break;
            case WU_HEATING: wuName = "HEATING"; break;
            case WU_HOLDING: wuName = "HOLDING"; break;
            default: break;
        }
        int16_t targetBT10 = (int16_t)wuTemp_R * 10;
        int16_t btErr = targetBT10 - (int16_t)Temperature_BT;
        uint16_t wMin = wuElapsed / 60;
        uint16_t wSec = wuElapsed % 60;
        SerialComputer.println();
        SerialComputer.print("  PH["); SerialComputer.print(wuName); SerialComputer.print("]");
        SerialComputer.print(" t="); SerialComputer.print(wMin); SerialComputer.print(":");
        if (wSec < 10) SerialComputer.print("0");
        SerialComputer.print(wSec);
        SerialComputer.print(" | BT=");    SerialComputer.print(Temperature_BT / 10.0f, 1);
        SerialComputer.print(" ET=");      SerialComputer.print(Temperature_ET / 10.0f, 1);
        SerialComputer.print(" TGT=");     SerialComputer.print(wuTemp_R);
        SerialComputer.print(" err=");     SerialComputer.print(btErr / 10.0f, 1);
        SerialComputer.print(" | RoRBT="); SerialComputer.print(rorBT / 10.0f, 1);
        SerialComputer.print(" RoRET=");   SerialComputer.print(rorET / 10.0f, 1);
        SerialComputer.print(" | gas=");   SerialComputer.print(wuGasPercent); SerialComputer.print("%");
        SerialComputer.print(" dead=");    SerialComputer.print(wuDeadTimer);  SerialComputer.print("s");
        SerialComputer.print(" prog=");    SerialComputer.print(TUNE_PERCENT_R); SerialComputer.print("%");
    }

    SerialComputer.println();
}

#if (MACHINE_HAS_SCALE_FEEDER && FEEDER_ADAPT_EN)
// Đọc 1 trường số thập phân tới dấu ',' hoặc hết chuỗi; trả về ×10^scale; nhảy *pp qua dấu phẩy.
// Tự parse (không dùng sscanf %f — newlib nano trên STM32 không bật float scanf mặc định).
static int32_t loaderParseScaled(char** pp, uint8_t scale){
    char* s = *pp;
    int32_t whole = 0, frac = 0; uint8_t fdig = 0; bool inFrac = false, neg = false;
    while(*s == ' ') s++;
    if(*s == '-'){ neg = true; s++; }
    for(; *s && *s != ','; s++){
        if(*s == '.'){ inFrac = true; continue; }
        if(*s < '0' || *s > '9') continue;
        if(!inFrac) whole = whole * 10 + (*s - '0');
        else if(fdig < scale){ frac = frac * 10 + (*s - '0'); fdig++; }
    }
    if(*s == ',') s++;
    *pp = s;
    while(fdig < scale){ frac *= 10; fdig++; }
    int32_t mul = 1; for(uint8_t i = 0; i < scale; i++) mul *= 10;
    int32_t v = whole * mul + frac;
    return neg ? -v : v;
}

// Snap cân (×100) và ror (×100) về tâm ô lưới → trả qua *qw (kg), *qr10 (×10 kg/phút).
static void loaderQuantize(int16_t w100, int16_t rorMag, int16_t* qw, int16_t* qr10){
    int16_t wKg = (w100 + 50) / 100;                                       // ×100 → kg (làm tròn)
    *qw   = ((wKg + FEEDER_W_BUCKET / 2) / FEEDER_W_BUCKET) * FEEDER_W_BUCKET;
    int16_t r10 = (rorMag + 5) / 10;                                       // ×100 → ×10 (làm tròn)
    *qr10 = ((r10 + FEEDER_ROR_BUCKET10 / 2) / FEEDER_ROR_BUCKET10) * FEEDER_ROR_BUCKET10;
    if(*qw   < FEEDER_W_BUCKET)     *qw   = FEEDER_W_BUCKET;
    if(*qr10 < FEEDER_ROR_BUCKET10) *qr10 = FEEDER_ROR_BUCKET10;
}

// Tìm ô KHỚP ĐÚNG (qw,qr10). Trả index hoặc -1.
static int16_t loaderCfgFind(int16_t qw, int16_t qr10){
    for(uint8_t i = 0; i < cfgCount; i++)
        if(cfgW[i] == qw && cfgRor10[i] == qr10) return i;
    return -1;
}

// Tìm ô đã học GẦN nhất (khoảng cách tính theo số bước lưới). Trả index hoặc -1 nếu bảng rỗng.
static int16_t loaderCfgNearest(int16_t qw, int16_t qr10){
    int16_t best = -1; int32_t bestD = 0x7fffffff;
    for(uint8_t i = 0; i < cfgCount; i++){
        int32_t dw = (cfgW[i]   - qw)   / FEEDER_W_BUCKET;
        int32_t dr = (cfgRor10[i] - qr10) / FEEDER_ROR_BUCKET10;
        int32_t d  = dw * dw + dr * dr;
        if(d < bestD){ bestD = d; best = i; }
    }
    return best;
}

// Tạo bảng MẶC ĐỊNH khi chưa có file: nội suy dif theo công thức T_kg cho từng ô ror
// (FEEDER_ROR_BUCKET10..30) tại cân tham chiếu FEEDER_SEED_WKG → có sẵn dòng để dùng & sửa.
static void loaderCfgSeed(){
    cfgCount = 0;
    int16_t w100 = (int16_t)FEEDER_SEED_WKG * 100;
    for(int16_t r10 = FEEDER_ROR_BUCKET10; r10 <= 300 && cfgCount < FEEDER_CFG_MAX; r10 += FEEDER_ROR_BUCKET10){
        int16_t rorMag = r10 * 10;                                          // ×10 → ×100
        int32_t dif100 = (int32_t)((int64_t)rorMag * feederTkg * w100 / 60000000LL);
        if(dif100 > FEEDER_DIF_MAX * 10) dif100 = FEEDER_DIF_MAX * 10;
        if(dif100 < 0) dif100 = 0;
        cfgW[cfgCount] = FEEDER_SEED_WKG; cfgRor10[cfgCount] = r10;
        cfgDif100[cfgCount] = (int16_t)dif100; cfgN[cfgCount] = 0;          // n=0: mẫu mặc định (chưa học thật)
        cfgCount++;
    }
}

void loaderCfgSave();   // forward decl: loaderCfgLoad tạo file mới khi thiếu

// Nạp bảng dif đã học từ /loadcfg.csv vào RAM — gọi 1 lần lúc boot (sau SD.begin).
// Tên 8.3 (loadcfg.csv) vì SD@1.2.4 KHÔNG hỗ trợ tên dài >8.3 → tên dài tạo file thất bại âm thầm.
// Không thấy file / file hỏng → tạo file rỗng; bảng rỗng = dùng công thức T_kg default tới khi học được.
void loaderCfgLoad(){
    cfgCount = 0;
    File f = SD.open("loadcfg.csv");
    if(f){
        char line[48];
        bool firstLine = true;
        while(f.available() && cfgCount < FEEDER_CFG_MAX){
            uint8_t len = 0;
            while(f.available()){
                char ch = f.read();
                if(ch == '\n') break;
                if(ch != '\r' && len < sizeof(line) - 1) line[len++] = ch;
            }
            line[len] = 0;
            if(len == 0) continue;
            if(firstLine){ firstLine = false; if(line[0] < '0' || line[0] > '9') continue; }  // bỏ header
            char* p = line;                                  // cột: wKg, rorKgMin, dif, n
            int16_t w    = (int16_t)loaderParseScaled(&p, 0);
            int16_t r10  = (int16_t)loaderParseScaled(&p, 1);
            int16_t d100 = (int16_t)loaderParseScaled(&p, 2);
            int16_t n    = (int16_t)loaderParseScaled(&p, 0);
            if(w > 0 && r10 > 0 && d100 >= 0 && d100 <= FEEDER_DIF_MAX * 10){
                cfgW[cfgCount] = w; cfgRor10[cfgCount] = r10; cfgDif100[cfgCount] = d100;
                cfgN[cfgCount] = (n > 0 && n < 255) ? (uint8_t)n : 1;
                cfgCount++;
            }
        }
        f.close();
    }else{
        loaderCfgSeed();   // chưa có file → nội suy bảng mặc định theo ror (tại cân FEEDER_SEED_WKG)
        loaderCfgSave();   // ghi xuống SD để có sẵn dòng mà dùng & sửa
    }

    // Seed loaderSeq từ STT dòng dữ liệu cuối /loader.csv để đánh số liên tục qua các lần boot.
    // Chỉ seed nếu header đúng định dạng mới (bắt đầu bằng "STT"); file cũ/lạ → bỏ qua (tránh đọc nhầm
    // cột ms thành STT làm số nhảy bậy). Nên xóa file cũ trước khi đổi định dạng cột.
    File c = SD.open("loader.csv");
    if(c && c.peek() != 'S'){ c.close(); }
    else if(c){
        uint16_t lastSeq = 0, cur = 0;
        bool atLineStart = true, lineHasDigit = false;
        while(c.available()){
            char ch = c.read();
            if(ch == '\n'){
                if(lineHasDigit) lastSeq = cur;   // STT của dòng vừa kết thúc
                atLineStart = true; cur = 0; lineHasDigit = false;
            }else if(atLineStart){
                if(ch >= '0' && ch <= '9'){ cur = cur * 10 + (ch - '0'); lineHasDigit = true; }
                else atLineStart = false;         // hết cột STT (header chữ hoặc dấu ',')
            }
        }
        c.close();
        loaderSeq = lastSeq;
    }
}

// Lưu toàn bộ bảng dif ra /loadcfg.csv (ghi đè, ≤FEEDER_CFG_MAX dòng → nhanh).
void loaderCfgSave(){
    SD.remove("loadcfg.csv");
    File f = SD.open("loadcfg.csv", FILE_WRITE);
    if(!f) return;
    f.print("wKg,rorKgMin,dif,n\r\n");
    for(uint8_t i = 0; i < cfgCount; i++){
        f.print(cfgW[i]);                 f.print(',');
        f.print(cfgRor10[i] / 10.0f, 1);  f.print(',');
        f.print(cfgDif100[i] / 100.0f, 2);f.print(',');
        f.print(cfgN[i]);                 f.print("\r\n");
    }
    f.close();
}

// Cắt /loader.csv chỉ giữ LOADER_CSV_MAX dòng dữ liệu gần nhất (luôn giữ header).
// Stream qua /loader.tmp để không phải nạp cả file vào RAM (20KB rất hạn chế).
void loaderLogTrim(){
    File f = SD.open("loader.csv");
    if(!f) return;

    // Đếm số dòng dữ liệu (tổng số '\n' trừ header).
    int32_t dataRows = -1;   // -1 để trừ dòng header
    while(f.available()){ if(f.read() == '\n') dataRows++; }
    if(dataRows <= LOADER_CSV_MAX){ f.close(); return; }

    int32_t skip = dataRows - (LOADER_CSV_MAX - 40);   // cắt dư 40 dòng → chỉ trim mỗi ~40 log, giảm churn ghi thẻ 40×
    f.seek(0);

    SD.remove("loader.tmp");
    File t = SD.open("loader.tmp", FILE_WRITE);
    if(!t){ f.close(); return; }

    // Giữ header (lineIdx 0) và các dòng có lineIdx > skip; bỏ dòng 1..skip.
    int32_t lineIdx = 0;
    while(f.available()){
        char c = f.read();
        if(lineIdx == 0 || lineIdx > skip) t.write(c);
        if(c == '\n') lineIdx++;
    }
    f.close();
    t.close();

    // Thay thế: SD lib này không có rename → copy tmp về csv rồi xoá tmp.
    SD.remove("loader.csv");
    File s = SD.open("loader.tmp");
    File d = SD.open("loader.csv", FILE_WRITE);
    if(s && d){ while(s.available()) d.write(s.read()); }
    if(s) s.close();
    if(d) d.close();
    SD.remove("loader.tmp");
}

// Ghi 1 dòng /loader.csv mỗi lần hút (event-based, không streaming).
// Cột: STT, s(giây kể từ lúc bật máy), wStart(cân đầu), batch(thực tế hút), set(cài đặt), secHut(giây hút), rorKG, dif,
//      offset(lực hút), target(đích), final(thực tế), err(lệch >0=thiếu), score(0-10), result, Told, Tnew.
void loaderLogEvent(int32_t final100, int32_t target100, int32_t err100,
                    int16_t score_x10, const char* result, int16_t difOld100, int16_t difNew100, uint16_t secHut){
    File f = SD.open("loader.csv", FILE_WRITE);
    if(!f){ if(loaderDbgEn) SerialComputer.println("LDR >>> LOG FAIL: SD.open loader.csv FAILED"); return; }
    // Ghi header CHỈ khi file rỗng thật (size 0). Không dùng SD.exists() vì sau chu kỳ
    // remove/recreate của loaderLogTrim() nó hay trả false-negative → chèn header vào giữa.
    if(f.size() == 0) f.print("STT,s,wStart,batch,set,secHut,rorKG,dif,offset,target,final,err,score,result,difOld,difNew\r\n");
    f.print(++loaderSeq);                           f.print(',');  // số thứ tự lần hút
    f.print(millis() / 1000);                       f.print(',');  // thời điểm ghi (giây kể từ lúc bật máy)
    f.print(adaptStartW100 / 100.0f, 2);            f.print(',');  // cân lúc bắt đầu hút (kg)
    f.print((adaptStartW100 - target100) / 100.0f, 2); f.print(','); // batch thực tế hút ra (kg)
    f.print(adaptSet / 10.0f, 1);                   f.print(',');  // set: lượng cài đặt cần hút (kg, chốt lúc cắt)
    f.print(secHut);                                f.print(',');  // thời gian hút (giây)
    f.print(adaptRorMag / 100.0f, 2);               f.print(',');  // tốc độ hút (kg/phút)
    f.print(adaptDif100 / 100.0f, 2);               f.print(',');  // dif đã dùng (kg)
    f.print(suctionOffset100 / 100.0f, 2);          f.print(',');  // offset lực hút đo được (kg)
    f.print(target100 / 100.0f, 2);                 f.print(',');  // đích (kg)
    f.print(final100 / 100.0f, 2);                  f.print(',');  // thực tế (kg)
    f.print(err100 / 100.0f, 2);                    f.print(',');  // lệch (kg, >0=thiếu)
    f.print(score_x10 / 10.0f, 1);                  f.print(',');  // điểm (0.0-10.0)
    f.print(result);                                f.print(',');  // OK / UNDER / OVER
    f.print(difOld100 / 100.0f, 2);                 f.print(',');  // dif ô TRƯỚC học (kg)
    f.print(difNew100 / 100.0f, 2);                 f.print("\r\n");// dif ô SAU học (kg)
    f.close();
    loaderLogTrim();   // giữ tối đa LOADER_CSV_MAX dòng gần nhất
}

// Vòng tự học: sau khi cắt feeder, chờ cân ổn định → chấm điểm → chỉnh dif của Ô (cân,ror) nếu thất bại.
// Điểm = 10.0 − lệch_kg×10 (lệch 0.05kg=9.5đ, 0.10kg=9.0đ). Hút OK = >9.0đ (lệch ≤0.09kg).
// CHỈ sửa dif khi THẤT BẠI (deadband): đạt rồi thì giữ nguyên, tránh giật. THIẾU(dư cà)→dif nhỏ hơn, DƯ→dif lớn hơn.
void loaderAdapt(){
    if(loaderAdaptPhase != 1) return;

    uint32_t elapsed   = millis() - adaptSettleStartMs;
    int16_t  rorMagNow = (rorKG < 0) ? -rorKG : rorKG;

    // Đợi tối thiểu SETTLE_MIN_MS cho cà lắng, RỒI cân ổn định; hoặc hết timeout.
    bool settled = (elapsed >= (uint32_t)FEEDER_SETTLE_MIN_MS) && (rorMagNow <= FEEDER_STABLE_ROR);
    bool timeout = (elapsed >= (uint32_t)FEEDER_SETTLE_TMO * 1000);
    if(!settled && !timeout) return;

    int32_t final100  = netW100;                        // ×100 kg
    int32_t target100 = (int32_t)adaptTarget * 10;      // ×100 kg
    int32_t batch100  = adaptStartW100 - target100;     // ×100 kg, lượng hút mục tiêu

    int32_t err100    = final100 - target100;           // >0 = hút thiếu (dư cà)
    int32_t absErr    = (err100 < 0) ? -err100 : err100;

    // Chấm điểm: mỗi 0.01kg lệch trừ 0.1 điểm. score_x10 đơn vị 0.1 điểm.
    int16_t score_x10 = (int16_t)(100 - absErr);
    if(score_x10 < 0) score_x10 = 0;
    bool ok = (score_x10 >= 91);                        // >9.0đ (lệch ≤0.09kg) = hút OK

    uint16_t secHut = (uint16_t)((adaptSettleStartMs - adaptStartMs) / 1000);
    int16_t  difOld100 = (int16_t)adaptDif100;         // dif đã dùng mẻ này (tham chiếu "trước")
    int16_t  difNew100 = (int16_t)adaptDif100;         // mặc định: không đổi
    const char* result;

    if(batch100 < FEEDER_MIN_BATCH100){
        // Mẻ quá nhỏ (nhiễu cân, không phải mẻ hút thật) → VẪN log để xem, nhưng KHÔNG học.
        // Tránh nhiễu 0.05–0.25kg kéo dif dao động (xem loader.csv mô phỏng 2026-06-22).
        result = "SMALL";
    }else if(ok){
        result = "OK";                                 // đạt → KHÔNG sửa dif (deadband)
    }else{
        result = (err100 > 0) ? "UNDER" : "OVER";      // dư cà(hút thiếu)→dif cần nhỏ hơn ; hút dư→dif cần lớn hơn
        // Học dif cho Ô (cân, ror) của mẻ này. dif lẽ ra đúng = dif đã dùng − err. Cần ror & cân đủ lớn.
        if(adaptRorMag >= 100 && adaptStartW100 >= 100){
            int32_t difReal100 = adaptDif100 - err100;
            if(difReal100 < 0) difReal100 = 0;
            if(difReal100 > FEEDER_DIF_MAX * 10) difReal100 = FEEDER_DIF_MAX * 10;
            int16_t qw, qr10;
            loaderQuantize(adaptStartW100, adaptRorMag, &qw, &qr10);
            int16_t ci = loaderCfgFind(qw, qr10);
            if(ci < 0 && cfgCount < FEEDER_CFG_MAX){    // ô mới → tạo, lấy luôn dif đúng
                ci = cfgCount++;
                cfgW[ci] = qw; cfgRor10[ci] = qr10; cfgDif100[ci] = (int16_t)difReal100; cfgN[ci] = 1;
            }else if(ci < 0){                           // bảng ĐẦY → thay ô ít tin cậy nhất (n nhỏ nhất,
                uint8_t lo = 0;                         // thường là seed/ô rác cũ) → KHÔNG bao giờ ngừng học
                for(uint8_t i = 1; i < cfgCount; i++) if(cfgN[i] < cfgN[lo]) lo = i;
                ci = lo;
                cfgW[ci] = qw; cfgRor10[ci] = qr10; cfgDif100[ci] = (int16_t)difReal100; cfgN[ci] = 1;
            }else{                                      // ô cũ → EMA kéo dần về dif đúng (chống nhiễu 1 mẻ)
                difOld100 = cfgDif100[ci];
                cfgDif100[ci] += (int16_t)((FEEDER_ADAPT_GAIN * (difReal100 - cfgDif100[ci])) / 100);
                if(cfgDif100[ci] < 0) cfgDif100[ci] = 0;
                if(cfgN[ci] < 255) cfgN[ci]++;
            }
            difNew100 = cfgDif100[ci]; loaderCfgSave();  // ci luôn ≥0 giờ → luôn lưu
        }
    }

    loaderLogEvent(final100, target100, err100, score_x10, result, difOld100, difNew100, secHut);
    if(loaderDbgEn){
        SerialComputer.print("LDR >>> LOG: result="); SerialComputer.print(result);
        SerialComputer.print(" score="); SerialComputer.print(score_x10);   // ×10 (98=9.8đ)
        SerialComputer.print(" set="); SerialComputer.print(adaptSet);       // cân cài hút (×10)
        SerialComputer.print(" err="); SerialComputer.print(err100);
        SerialComputer.print(" final="); SerialComputer.print(final100);
        SerialComputer.print(" batch100="); SerialComputer.print(batch100);
        SerialComputer.print(" secHut="); SerialComputer.println(secHut);
    }
    loaderAdaptPhase = 0;
}
#endif

// Cập nhật cờ GIAI ĐOẠN rang lên HMI (Dry / Maillard / DEV) cho thanh phase kiểu Artisan.
// CỘNG DỒN: giai đoạn nào ĐÃ vào thì cờ GIỮ SÁNG tới hết mẻ (giống thanh 3 khúc của Artisan).
//   Dry      : từ CHARGE→DE trở đi (progStep >= STP_TP)
//   Maillard : từ DE→FCs   trở đi (progStep >= STP_FCS)
//   DEV      : từ FCs→DROP  trở đi (progStep >= STP_DEV)
// Hết mẻ / mẻ mới (progStep về STP_DATA hoặc START tắt) → cả 3 = 0.
// Change-gated: chỉ ghi HMI khi tổ hợp cờ ĐỔI, không ghi register liên tục.
void updateRoastPhaseFlags() {
    uint8_t dry = 0, mail = 0, dev = 0;
    if (START_BTN_R == 1) {
        if (progStep >= STP_TP)  dry  = 1;  // đã vào Dry
        if (progStep >= STP_FCS) mail = 1;  // đã vào Maillard
        if (progStep >= STP_DEV) dev  = 1;  // đã vào DEV
    }
    static int8_t last = -1;
    int8_t sig = dry * 4 + mail * 2 + dev;   // gộp 3 cờ thành 1 mã để so đổi
    if (sig == last) return;                 // không đổi → khỏi ghi bus
    last = sig;
    nodeHMI.writeSingleRegister(showPointDry_W      - 1, dry);  delay(1);
    nodeHMI.writeSingleRegister(showPointMaillard_W - 1, mail); delay(1);
    nodeHMI.writeSingleRegister(showPointDEV_W      - 1, dev);  delay(1);
}

void programScan(){
    // PRIORITY 1: keep drum/fan on when BT or ET is hotter than 80C
    if (forceDrumFanOnFlag) {
        if (((int16_t)Temperature_BT > 800 || (int16_t)Temperature_ET > 800) &&
            DRUM_FAN_BTN_R == 0) {
            nodeHMI.writeSingleRegister(DRUM_FAN_BTN_W - 1, 1);
            DRUM_FAN_BTN_R = 1;
            DRUM_FAN_BTN_R_CP = 1;
            #if MACHINE_HAS_IO_RELAY_MODULE
                nodeIORelay.writeSingleCoil(CH1_IO_RL_W, DRUM_FAN_BTN_R); delay(1); // Relay ngoài 1: drum/fan
            #endif
            mbs.Hreg(DRUM_FAN_W, DRUM_FAN_BTN_R);
            if (enDebug) SerialComputer.println("BT/ET > 80C: DRUM/FAN forced ON");
        }
        forceDrumFanOnFlag = false;
    }

    // PRIORITY 1: safety cutoff — ISR flagged it
    if (fireCutFlag) {
        nodeHMI.writeSingleRegister(START_GAS_BTN_W - 1, 0);  // cut gas
        gasPercent = 0;
        // Report specific cause
        if ((int16_t)Temperature_BT > 2500) {
            setMachineStatus(STT_ERR_FIRE_ALARM);       // 401: BT > 250C
            if (enDebug) SerialComputer.println("!!! BT > 250C: GAS CUT OFF !!!");
        } else if ((int16_t)Temperature_ET > 3000 && (int16_t)Temperature_BT < 1500) {
            setMachineStatus(STT_TEMP_DIVERGENCE);      // 267: ET>300C, BT<150C
            if (enDebug) SerialComputer.println("!!! ET>300C BT<150C: EMERGENCY GAS CUT !!!");
        } else {
            setMachineStatus(STT_TEMP_ET_HIGH);         // 264: ET > 350C
            if (enDebug) SerialComputer.println("!!! ET > 350C: GAS CUT OFF !!!");
        }
        fireCutFlag = false;
    }

    // preheat — chạy độc lập, không phụ thuộc AUTO mode
    if (START_BTN_R == 0) {  // only allow preheat when not roasting
        preheat();
    }

    if(calibGasProgramEn){
        calibProgram();
        calibGasProgramEn = false;
    }
    
    //On-off buzzer HMI và tối ưu
    // if(buzzerHMIEn==1 && memBuzzerEn==0){
    //     nodeHMI.writeSingleRegister(GENERAL_CONTROL_W-1, 4);
    //     memBuzzerEn = buzzerHMIEn;
    // }
    // if(buzzerHMIEn==0 && memBuzzerEn==1){
    //     nodeHMI.writeSingleRegister(GENERAL_CONTROL_W-1, 0); 
    //     memBuzzerEn = buzzerHMIEn;
    // }

    //Đọc dữ liệu thẻ nhớ
    sdRead();

    if(START_BTN_R == 1){
        switch(progStep){
            case STP_DATA:
                setMachineStatus(STT_ROAST_INIT);
#if MACHINE_HAS_VACUUM_SENSOR
                roastVacFlagSaved = vacuumSetFlag_R;  // lưu trạng thái vacuum PID trước rang (khôi phục lúc DROP/abort)
#endif
                // Áp trần gas từ profile CHỈ khi rang AUTO (profile không có MaxGas → sdMaxGasLoaded=-1 → bỏ qua)
                if(progStatus == STT_PROGRAM_AUTO && sdMaxGasLoaded >= 0 && sdMaxGasLoaded <= 100){
                    maxGasSet_R = sdMaxGasLoaded;
                    nodeHMI.writeSingleRegister(maxGasSet_W + 2000, sdMaxGasLoaded);
                }
                //Xoá profile đã chọn trên SD, nếu chương trình rang là manual save
                if(progStatus == STT_PROGRAM_SAVE){
                    sdLogStartEn = 1;
                    setMachineStatus(STT_SD_LOG_STARTED);
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
                rorCtrl_reset(); // Reset RoR control state khi bắt đầu mẻ mới
                trendPreStarted = false; // Cho phép bật lại trend sớm ở mẻ mới

                nodeHMI.writeSingleRegister(CLEAR_HIS_CONTROL_W-1, 1);  //Clear trend graph
                nodeHMI.writeSingleCoil(LOCK_BUTTON_W-1, 1);    //Lock các button trên HMI khi rang
                //Debug
                STEP_STRING = "RESET DATA";

                setMachineStatus(STT_ROAST_COOLDOWN); progStep = STP_COOL_DOWN;   //Chuyển trạng thái
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
                        setMachineStatus(STT_ROAST_WAITGAS); progStep = STP_GAS; //Chuyển trạng thái kiểm tra gas 
                        
                    }else{
                        nodeHMI.writeSingleRegister(START_GAS_BTN_W-1, 0);  //Turn off gas    
                    }  
                }else{
                    setMachineStatus(STT_ROAST_WAIT_CHARGE); progStep = STP_CHARGE; //Chuyển trạng thái kiểm tra charge   
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
                        setMachineStatus(STT_ROAST_CHECK); progStep = STP_CHECK; //Chuyển trạng thái
                    }    
                }
                //Nếu là bếp premix thì không cần chờ
                else{
                    naviSourceGAS = SOURCE_AI_AUTO; //Đổi source gas
                    gasPercent = preGas_R; //Set gas charge theo cài đặt
                    setMachineStatus(STT_ROAST_CHECK); progStep = STP_CHECK; //Chuyển trạng thái
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
                    setMachineStatus(STT_EVENT_CHARGE_OPENED);

                    BT_TP_Pre = Temperature_BT; //Lưu biến nhiệt để check TP

                    //Enable record airflow, drum, flame, gas signal

                    nodeHMI.writeSingleCoil(SAMPLE_COIL_W-1, 1);  //Turn on trend graph sample
                    timeRoastEn = 1; //Start roaster time
                    setMachineStatus(STT_EVENT_ROAST_START);
                    sdChargeHappened = true;           // Bắt đầu ghi Time2 (timestamp lưu khi ghi)
                    sdChargeHH = (uint8_t)HOUR_R;      // Lưu giờ RTC lúc CHARGE
                    sdChargeMM = (uint8_t)MINUTE_R;    // Lưu phút RTC lúc CHARGE
                    strcpy(sdCsvPendingEvent, "CHARGE");
                    buzzerTimerEn = 1; //Call buzzer
                    setMachineStatus(STT_ROAST_CATCH_TP); progStep = STP_TP; //Chuyển trạng thái check TP

                }
            break;

            case STP_TP:
                //Condition to TP
                STEP_STRING = "WAIT TP";
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
                        setMachineStatus(STT_EVENT_TP_REACHED);
                        setMachineStatus(STT_ROAST_YELLOW); progStep = STP_YELLOW; // Next to check yellow
                    }
                }
                
                break;

            case STP_YELLOW:
                STEP_STRING = "WAIT YELLOW";
                //Check YL
                if(Temperature_BT>=yellowPhase_R_CV){// đã đạt mốc yellow
                    BT_YELLOW_SAVE = Temperature_BT;
                    TIME_YELLOW_SAVE = timeRoast;
                    TIME_YELLOW_MIN_SAVE = TIME_YELLOW_SAVE/60;
                    TIME_YELLOW_SEC_SAVE = TIME_YELLOW_SAVE%60;
                    strcpy(sdCsvPendingEvent, "DRY End");
                    setMachineStatus(STT_EVENT_YELLOW_REACHED);
                    setMachineStatus(STT_ROAST_FCS); progStep = STP_FCS;       
                }
                break;

            case STP_FCS: //đang chờ từ mốc yellow đến first crack
                STEP_STRING = "WAIT FCS";
                //Check FCS
                if(Temperature_BT>=fcsPhase_R_CV){
                    BT_FCS_SAVE = Temperature_BT;
                    TIME_FCS_SAVE = timeRoast;
                    TIME_FCS_MIN_SAVE = TIME_FCS_SAVE/60;
                    TIME_FCS_SEC_SAVE = TIME_FCS_SAVE%60;
                    strcpy(sdCsvPendingEvent, "FCs");
                    setMachineStatus(STT_EVENT_FCS_REACHED);
                    setMachineStatus(STT_ROAST_DEV); progStep = STP_DEV;       
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
                setMachineStatus(STT_ROAST_LOOP1);
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
                setMachineStatus(STT_ROAST_LOOP2);
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

        //Bật trend SỚM: sau khi bật lửa (gas on), BT tăng dần tới charge —
        //khi còn cách charge TREND_PRECHARGE_BAND (10°C) thì bật sample để ghi cả đoạn tiến tới charge.
        //Chỉ khi có cài charge temp; mỗi mẻ 1 lần (trendPreStarted). Charge-press vẫn bật lại phòng hờ.
        if(chargeTemp_R_CV>0 && progStep>=STP_GAS && progStep<STP_TP && !trendPreStarted
           && Temperature_BT>=(chargeTemp_R_CV-TREND_PRECHARGE_BAND)){
            nodeHMI.writeSingleCoil(SAMPLE_COIL_W-1, 1);  //Turn on trend graph sample sớm
            trendPreStarted = true;
            delay(1);
        }

        //Check auto cân
        //Chỉ cân tự động sau khi DE hoàn thành
        if(progStep==STP_FCS){
            //Xử lí các tình huống trong khi rang auto
            if(progStatus == STT_PROGRAM_AUTO){
                if(autoLoader_R == 1 && aLoaderStep == 0 && loop_R>1){
                    //Chỉ cho auto cân khi phễu nguồn còn ≥ LOADER_MIN_BATCH_PCT% của 1 mẻ (LOADER_MIN_NETW ×10 kg)
                    //Nếu không sẽ auto tắt start
                    if(!scaleDataValid){
                        setMachineStatus(STT_SCALE_DATA_INVALID);
                        setMachineStatus(STT_LOADER_FAIL); aLoaderStep = STP_FAIL_LOADER;
                    }else if(netW < 0){
                        setMachineStatus(STT_SCALE_NEGATIVE);
                        setMachineStatus(STT_LOADER_FAIL); aLoaderStep = STP_FAIL_LOADER;
                    }else if(netW>=LOADER_MIN_NETW){
                        setMachineStatus(STT_LOADER_RUNNING); aLoaderStep = STP_ON_LOADER; //Bắt đầu vào auto loader
                    }else{
                        setMachineStatus(STT_LOADER_FAIL); aLoaderStep = STP_FAIL_LOADER; 
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
                    setMachineStatus(STT_ROAST_DROP); nodeHMI.writeSingleRegister(DROP_BTN_W-1, 1); //Turn on drop    
                }
                //Tự bật cooling trước khi drop
                if(Temperature_BT>=(DROP_PRO_R-preCool_R_CV)&&preCool_R_CV>0){
                    //Bật cooling&mixer nếu nhập số lớn hơn 0
                    if(coolTimer_R>0&&coolStep==0) coolStep = COOL_STEP_COOLING;
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
                    setMachineStatus(STT_EVENT_ROAST_END);
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
#if MACHINE_HAS_VACUUM_SENSOR
                vacuumSetFlag_R = roastVacFlagSaved;  // khôi phục vacuum PID về trạng thái trước rang
                nodeHMI.writeSingleRegister(vacuumSetFlag_W + 2000, vacuumSetFlag_R);
#endif

                //Bật cooling&mixer nếu nhập số lớn hơn 0
                if(coolTimer_R>0&&coolStep==0) coolStep = COOL_STEP_COOLING; 
                 
                timeRoastEn = 0;

                nodeHMI.writeSingleCoil(SAMPLE_COIL_W-1, 0);  //Turn off trend graph sample
                timeAbsoluteEn = 0; // Dừng đếm wall time

                buzzerTimerEn = 1; //Call buzzer
                dropTimerEn = 1; //Enable drop timer auto close
                setMachineStatus(STT_EVENT_DROP_REACHED);
                nodeHMI.writeSingleRegister(DROP_BTN_W-1, 1); //Turn on drop
                setMachineStatus(STT_EVENT_DROP_OPENED);

                STEP_STRING = "DROP";

                if(progStatus == STT_PROGRAM_AUTO && progStep<STP_LOOP_1){
                    setMachineStatus(STT_ROAST_DROP); progStep = STP_LOOP_1; //Chuyển sang trạng thái kiểm tra loop
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
#if MACHINE_HAS_VACUUM_SENSOR
            vacuumSetFlag_R = roastVacFlagSaved;  // khôi phục vacuum PID về trạng thái trước rang
            nodeHMI.writeSingleRegister(vacuumSetFlag_W + 2000, vacuumSetFlag_R);
#endif

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

#if (MACHINE_HAS_SCALE_FEEDER && FEEDER_ADAPT_EN)
    loaderAdapt();   // Vòng tự học dif: chờ cân ổn định sau cắt → chỉnh feederTkg
#endif

    // Tự động cập nhật cân sau 10 giây nếu không có dữ liệu từ Bluetooth
    if (updateNetWTi >= 5 && SerialBluetooth.available() == 0) {
        scaleDataValid = false;
        if(aLoaderStep == STP_WAIT_LOADER){
            nodeHMI.writeSingleRegister(FEEDER_BTN_W-1, 0); // Tắt FEEDER khi mất dữ liệu cân
            setMachineStatus(STT_SCALE_DATA_INVALID);
            setMachineStatus(STT_LOADER_FAIL);
            aLoaderStep = STP_FAIL_LOADER;
            delay(1);
        }
    }

#if MACHINE_HAS_SCALE_FEEDER
    // Bắt đầu mẻ hút bằng LATCH (không dùng sườn 1-vòng): FEEDER_BTN_R đọc từ HMI qua Modbus,
    // đôi khi vòng quét đọc LỠ cạnh 0→1 → mẻ rác (adaptStartMs/wStart cũ). feederWasOff giữ
    // "đã thấy nút nhả" qua nhiều vòng nên dù lỡ cạnh vẫn bắt được mẻ mới. Chỉ bắt khi không ở pha lắng.
    if (FEEDER_BTN_R == 0) feederWasOff = true;
    if (FEEDER_BTN_R == 1 && feederWasOff && loaderAdaptPhase == 0) {
        adaptStartMs       = millis();
        adaptStartW100     = netW100;
        adaptWStartPending = true;
        adaptArmed         = true;   // mẻ hút hợp lệ → cho phép 1 lần vào pha học
        feederWasOff       = false;
    }
    // Phễu đã ổn định sau khi bật hút → đo offset lực hút rồi chốt lại wStart (cà chưa chảy).
    // offset = cân lúc đang hút ổn định (netW100) − cân lúc chưa hút (adaptStartW100 tạm).
    // Kẹp [0, OFFSET_MAX] để mẫu lỗi không phá ngưỡng cắt.
    if (adaptWStartPending && FEEDER_BTN_R == 1
        && (millis() - adaptStartMs >= (uint32_t)FEEDER_WSTART_DELAY_MS)) {
        int16_t off = netW100 - adaptStartW100;
        if (off < 0) off = 0;
        if (off > FEEDER_OFFSET_MAX100) off = FEEDER_OFFSET_MAX100;
        suctionOffset100   = off;
        adaptStartW100     = netW100;
        adaptWStartPending = false;
    }
#endif

    // Tính hiệu số giữa trọng lượng hiện tại và trọng lượng mục tiêu
    if (netW > netWTG_R && FEEDER_BTN_R == 0) {
        difNetW = netW - netWTG_R; // Nếu trọng lượng hiện tại lớn hơn mục tiêu
    } else if (netW <= netWTG_R && FEEDER_BTN_R == 0) {
        difNetW = 0; // Nếu trọng lượng hiện tại nhỏ hơn hoặc bằng mục tiêu
    }

    // Auto-dif: đóng feeder sớm theo lượng cà còn rơi trong lúc xi lanh đóng.
    // Tính & so sánh ở ×100 (0.01kg) để KHÔNG giật bậc 0.1kg.
    // dif100 lấy từ BẢNG đã học: snap (cân, ror) về ô lưới → dùng dif của ô đó; ô trống → ô học
    // gần nhất; bảng rỗng hoàn toàn → công thức T_kg default (|rorKG|×T_kg×wStart/60000000) làm mồi.
    int32_t dif100 = 0;
#if (MACHINE_HAS_SCALE_FEEDER && FEEDER_ADAPT_EN)
    int16_t rorMag = (rorKG < 0) ? -rorKG : rorKG;
    int16_t qw, qr10;
    loaderQuantize(adaptStartW100, rorMag, &qw, &qr10);
    int16_t ci = loaderCfgFind(qw, qr10);
    if (ci < 0) ci = loaderCfgNearest(qw, qr10);
    if (ci >= 0) dif100 = cfgDif100[ci];                                   // dif đã học
    else dif100 = (int32_t)((int64_t)rorMag * feederTkg * adaptStartW100 / 60000000LL);
    if (dif100 > (int32_t)FEEDER_DIF_MAX * 10) dif100 = (int32_t)FEEDER_DIF_MAX * 10;
    if (dif100 < 0) dif100 = 0;
#endif
    dif = (int16_t)(dif100 / 10); // bản ×10 để tham chiếu/hiển thị

    // Tự động tắt feeder dựa trên trọng lượng và trạng thái nút FEEDER
    if (FEEDER_BTN_R == 1 && netWTG_R > 0 && scaleDataValid) { // Nếu nút FEEDER đang bật và có trọng lượng mục tiêu
        // So sánh ở ×100: netW100 vs (đích còn lại ×10 + dif100 + offset). Mượt tới 0.01kg.
        // Cộng suctionOffset100 vào ngưỡng = trừ offset khỏi netW100 (cân đang bị lực hút thổi cao).
        if (netW100 <= ((int32_t)difNetW * 10 + dif100 + suctionOffset100)) { // Đạt ngưỡng cắt
            if (netW100 > (int32_t)vacuumTraction_R * 10) { // Còn đủ lực kéo vacuum
                nodeHMI.writeSingleRegister(FEEDER_BTN_W-1, 0); // Tắt FEEDER
                if(loaderDbgEn) SerialComputer.println("LDR >>> AUTO-CUT (normal path, will settle+log)");
                if(aLoaderStep == STP_WAIT_LOADER){
                    setMachineStatus(STT_LOADER_OK);
                    aLoaderStep = STP_OK_LOADER;
                }
#if (MACHINE_HAS_SCALE_FEEDER && FEEDER_ADAPT_EN)
                // Chốt số liệu lúc cắt → vào pha chờ ổn định để tự học dif.
                // Chỉ khi armed (có sườn hút thật) → tránh cắt lặp/giả ghi dòng rác. Mỗi sườn 1 lần.
                if (adaptArmed) {
                    adaptTarget = difNetW;
                    adaptSet    = netWTG_R;   // chốt set thật của mẻ ngay lúc cắt
                    adaptRorMag = rorMag;
                    adaptDif100 = dif100;
                    adaptSettleStartMs = millis();
                    loaderAdaptPhase = 1;
                    adaptArmed = false;
                }
#endif
                delay(1);
            } else {
                cleanFeederTiEn = 1; // Bật cờ dọn sạch FEEDER
                if(loaderDbgEn) SerialComputer.println("LDR >>> CLEAN-FEEDER (netW100<=vacTr, NO LOG)");
            }
        }
    }

#if (MACHINE_HAS_SCALE_FEEDER && FEEDER_ADAPT_EN)
    // --- Debug loader: tự bật khi bấm loader; tắt 10s sau khi off (và đã ghi log xong); in 1s/lần ---
    if(FEEDER_BTN_R == 1 && enDebug){                   // chỉ bật debug khi enDebug=1 (mặc định TẮT)
        loaderDbgEn = true;
        loaderDbgOffMs = 0;                              // đang chạy → hoãn đếm tắt
    }else if(loaderDbgEn){
        if(loaderDbgOffMs == 0) loaderDbgOffMs = millis();                     // vừa off → bắt đầu đếm
        else if(millis() - loaderDbgOffMs >= 10000 && loaderAdaptPhase == 0)   // đủ 10s & log xong → tắt
            loaderDbgEn = false;
    }
    if(loaderDbgEn && millis() - loaderDbgPrintMs >= 1000){
        loaderDbgPrintMs = millis();
        int32_t thr = (int32_t)difNetW * 10 + dif100 + suctionOffset100;       // ngưỡng cắt (×100)
        SerialComputer.print("LDR t=");    SerialComputer.print((millis() - adaptStartMs) / 1000); // giây kể từ lúc bắt đầu hút
        SerialComputer.print(" btn=");     SerialComputer.print(FEEDER_BTN_R);
        SerialComputer.print(" vld=");     SerialComputer.print(scaleDataValid);
        SerialComputer.print(" w=");       SerialComputer.print(netW100);
        SerialComputer.print(" set=");     SerialComputer.print(netWTG_R);   // cân cài hút (×10)
        SerialComputer.print(" dN=");      SerialComputer.print(difNetW);    // cân đích cuối (×10)
        SerialComputer.print(" raw=");     SerialComputer.print(raw_rorKG * 10); // ror thô trước Kalman (cùng thang ror)
        SerialComputer.print(" ror=");     SerialComputer.print(rorKG);
        SerialComputer.print(" dif=");     SerialComputer.print(dif100);
        SerialComputer.print(" thr=");     SerialComputer.print(thr);
        SerialComputer.print(" wS=");      SerialComputer.print(adaptStartW100);
        SerialComputer.print(" ph=");      SerialComputer.print(loaderAdaptPhase);
        SerialComputer.print(" arm=");     SerialComputer.print(adaptArmed);
        SerialComputer.print(" stp=");     SerialComputer.print(aLoaderStep);
        SerialComputer.print(" cfg=");     SerialComputer.println(cfgCount);
    }
#endif

    //Tự tắt feeder sau 5 giây dọn sạch feeder.
    if(FEEDER_BTN_R == 1 && cleanFeederTi>=10 && cleanFeederTiEn){
        nodeHMI.writeSingleRegister(FEEDER_BTN_W-1, 0);  //Turn off Feeder 
        if(aLoaderStep == STP_WAIT_LOADER){
            setMachineStatus(STT_LOADER_OK);
            aLoaderStep = STP_OK_LOADER;
        }
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
    if(feederTimerEn==1 && feederTimer>=feederSet_R && feederSet_R>0){
        feederTimerEn = 0;
        feederTimer = 0;
        nodeHMI.writeSingleRegister(FEEDER_BTN_W-1, 0);  //Turn off Feeder
        delay(1);
        //Báo lỗi nếu trong chương trình auto
        if(aLoaderStep==STP_WAIT_LOADER){
            setMachineStatus(STT_LOADER_FAIL);
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
        // Reset ca o lenh PC (Hreg 14) — khong thi lenh ke tiep tu app bi coi la "khong doi"
        Charge_btn_PC = 0; mbs.Hreg(CHARGE_artisan_W, 0);
        setMachineStatus(STT_EVENT_CHARGE_CLOSED);
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
        Drop_btn_PC = 0; mbs.Hreg(DROP_artisan_W, 0);   // reset o lenh PC (xem charge)
        setMachineStatus(STT_EVENT_DROP_CLOSED);
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
        setMachineStatus(STT_ACT_AB_OFF); nodeHMI.writeSingleRegister(AB_BTN_W-1, 0);  //Turn off AB
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
#ifdef SOURCE_AI_VR_FROM_HMI
        // Bản tách dây mixer riêng: nếu người dùng hủy cooling thì tắt mixer theo.
        nodeHMI.writeSingleRegister(MIXER_BTN_W-1, 0);
#endif
        coolStep = 0; //Reset quy trình
        coolTimer = 0; //Resetncounter
        coolTimerEn = 0; //Resetncounter
        STEP_COOLING_STRING = "NONE";
    }

    //Auto close destoner
    if(destonerTimerEn==1 && destonerTimer>=destonerSet_R){
        destonerTimerEn = 0;
        destonerTimer = 0;
        setMachineStatus(STT_DESTONER_OFF); nodeHMI.writeSingleRegister(DESTONER_BTN_W-1, 0);  //Turn off Destoner
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
            Escape_btn_PC = 0; mbs.Hreg(ESCAPE_artisan_W, 0);   // reset o lenh PC (xem charge)
            setMachineStatus(STT_EVENT_ESCAPE_CLOSED);
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
    analogCalProcessSD();

//----------------------Chương trình AB tự động
    switch(abStep){
        //Kiểm tra nhiệt độ BT và cài đặt AB
        case STP_ON_AB:
            STEP_AB_STRING = "ONAB";
            setMachineStatus(STT_ACT_AB_ON); nodeHMI.writeSingleRegister(AB_BTN_W-1, 1);  //Turn on AB 
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
        case COOL_STEP_COOLING:
            STEP_COOLING_STRING = "ONCO";
            setMachineStatus(STT_ROAST_COOLING);
            setMachineStatus(STT_ACT_COOLING_ON); nodeHMI.writeSingleRegister(COOLING_BTN_W-1, 1);  // Bật cooling
#ifdef SOURCE_AI_VR_FROM_HMI
            // Bản SOURCE_AI_VR_FROM_HMI tách dây mixer riêng, không đấu chung với cooling.
            nodeHMI.writeSingleRegister(MIXER_BTN_W-1, 1);  // Bật mixer riêng
#else
            // Bản đấu dây cũ: mixer đấu chung với cooling nên cooling bật thì mixer cũng bật.
#endif
            coolTimer = 0;
            coolTimerEn = 1; //Enable drop timer auto close count;
            coolStep = COOL_STEP_ESCAPE_ON; //Next to check escape on
        
        break;  

        case COOL_STEP_ESCAPE_ON:
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
                    setMachineStatus(STT_DESTONER_ON); nodeHMI.writeSingleRegister(DESTONER_BTN_W-1, 1);  //Turn on destoner button
                    delay(1);
                }
            }
            //Wait to cooling complete
            if(coolTimer>=coolTimer_R){
                STEP_COOLING_STRING = "ONES";
                setMachineStatus(STT_ROAST_ESCAPE);
                nodeHMI.writeSingleRegister(ESCAPE_BTN_W-1, 1);  //Turn on escape
                escapeTimerEn = 1;  //Enable escape timer auto close count;
                setMachineStatus(STT_EVENT_ESCAPE_OPENED);
                delay(1);
                coolStep = COOL_STEP_ESCAPE_OFF; //Next to check escape off
            }
            
        break; 
        case COOL_STEP_ESCAPE_OFF:
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
                nodeHMI.writeSingleRegister(COOLING_BTN_W-1, 0);  // Tắt cooling
#ifdef SOURCE_AI_VR_FROM_HMI
                // Bản SOURCE_AI_VR_FROM_HMI tách dây mixer riêng, không đấu chung với cooling.
                nodeHMI.writeSingleRegister(MIXER_BTN_W-1, 0);  // Tắt mixer riêng
#else
                // Bản đấu dây cũ: mixer đấu chung với cooling nên cooling tắt thì mixer cũng tắt.
#endif
                setMachineStatus(STT_EVENT_ESCAPE_CLOSED);
                setMachineStatus(STT_ACT_COOLING_OFF);
                escapeTimerEn = 0; //Turn off escape timer
                escapeTimer = 0;

                coolTimerEn = 0; //Turn off cool timer
                coolTimer = 0;

                buzzerTimerEn = 1; //Call buzzer

                coolStep = 0; //Turn off cooling program
            }
        break;
    }

    //Log đếm cooling: in mỗi giây khi cooling đang chạy — coolTimer (đang đếm) / coolTimer_R (cài đặt)
    static int16_t coolTimerLog = -1;
    if(coolStep>=1){
        if(enDebug && coolTimer!=coolTimerLog){
            SerialComputer.print("Cool count: ");
            SerialComputer.print(coolTimer);
            SerialComputer.print(" / set: ");
            SerialComputer.println(coolTimer_R);
        }
        coolTimerLog = coolTimer;
    }else{
        coolTimerLog = -1;
    }
}


























































