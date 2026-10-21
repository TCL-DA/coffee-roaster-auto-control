#if PREHEAT_USE_PID
#include "Preheat_PID.h"
#else
#include "Preheat.h"
#endif
void loadAllProfileDates(); // forward declaration
#include "RoR_Control.h"

// ─── RoR kiểu Artisan (chế độ đang rang) ────────────────────────────────────────
// Giá trị ở tuổi a (0 = mới nhất) trong đệm vòng, iNext = ô ghi kế tiếp.
static inline int32_t rorAge(const int32_t *buf, uint8_t size, uint8_t iNext, uint8_t age){
    int16_t k = (int16_t)iNext - 1 - (int16_t)age;
    while(k < 0) k += size;
    return buf[k];
}
// Delta Span: (5·st mới nhất − Σ5 st quanh điểm trái) → RoR °C/phút ×100 (compute_ror_simple).
static inline int32_t rorSpan(int32_t stNew, int32_t left5){
    int32_t r = (5*stNew - left5) * 120 / ((int32_t)ROR_WCF * (ROR_L-1) * ROR_SAMPLE_SEC);
    if(r > 100000)  r = 100000;           //chặn rác trước Smoothing (±1000 °C/phút)
    if(r < -100000) r = -100000;
    return r;
}
// Một nhịp RoR cho 1 kênh (BT hoặc ET). Trả RoR °C/phút ×100 đã qua Smoothing.
static int32_t rorArtisanStep(RorArtisanCh &c, int16_t temp){
    if(!c.primed){
        if(temp == 0) return 0;           //chưa đọc được nhiệt — chờ, đừng nạp đệm bằng 0
        for(uint8_t i = 0; i < ROR_NCF; i++) c.raw[i] = temp;
        for(uint8_t i = 0; i < ROR_NST; i++) c.st[i]  = (int32_t)temp * ROR_WCF;
        for(uint8_t i = 0; i < ROR_NR;  i++) c.ror[i] = 0;
        c.iRaw = c.iSt = c.iRor = 0;
        c.primed = true;
    }
    //1. Smooth Curves — trọng số 1..NCF, mẫu mới nhất nặng nhất
    c.raw[c.iRaw] = temp; if(++c.iRaw >= ROR_NCF) c.iRaw = 0;
    int32_t st = 0;
    for(uint8_t a = 0; a < ROR_NCF; a++) st += (int32_t)(ROR_NCF - a) * rorAge(c.raw, ROR_NCF, c.iRaw, a);
    c.st[c.iSt] = st; if(++c.iSt >= ROR_NST) c.iSt = 0;
    //2. Delta Span — điểm trái lấy TB 5 mẫu quanh nó (tuổi L-3..L+1), điểm phải là mẫu mới nhất
    int32_t left = 0;
    for(uint8_t a = ROR_L-3; a <= ROR_L+1; a++) left += rorAge(c.st, ROR_NST, c.iSt, a);
    c.ror[c.iRor] = rorSpan(st, left); if(++c.iRor >= ROR_NR) c.iRor = 0;
    //3. Smoothing — trọng số 1..NR trên NR giá trị RoR gần nhất
    int32_t acc = 0;
    for(uint8_t a = 0; a < ROR_NR; a++) acc += (int32_t)(ROR_NR - a) * rorAge(c.ror, ROR_NR, c.iRor, a);
    return acc / ROR_WNR;
}
// Cùng chuỗi đó chạy trên hồ sơ mẫu sdBT[] (1 phần tử/giây) tại giây t — không trạng thái.
// Trước giây 0 coi như bằng sdBT[0]. Để rorBT_pro trễ ĐÚNG như rorBT, hai đường so thẳng được.
static int32_t rorArtisanProfile(int32_t t){
    int32_t stv[ROR_NR + ROR_L + 2];      //st ở tuổi m = 0..NR+L+1 (bước ROR_SAMPLE_SEC)
    for(uint8_t m = 0; m < ROR_NR + ROR_L + 2; m++){
        int32_t sum = 0;
        for(uint8_t a = 0; a < ROR_NCF; a++){
            int32_t idx = t - (int32_t)(m + a) * ROR_SAMPLE_SEC;
            if(idx < 0) idx = 0;
            sum += (int32_t)(ROR_NCF - a) * (int16_t)sdBT[idx];
        }
        stv[m] = sum;
    }
    int32_t acc = 0;
    for(uint8_t k = 0; k < ROR_NR; k++){
        int32_t left = 0;
        for(uint8_t a = ROR_L-3; a <= ROR_L+1; a++) left += stv[k + a];
        acc += (int32_t)(ROR_NR - k) * rorSpan(stv[k], left);
    }
    return acc / ROR_WNR;
}
// Làm tròn RoR ×100 về bội số 10 (giữ độ phân giải 0.1 °C/phút như bản cũ) rồi kẹp trần.
static inline int16_t rorOut(int32_t r, int32_t lim){
    r = (r >= 0) ? (r + 5) / 10 * 10 : (r - 5) / 10 * 10;
    if(r > lim)  r = lim;
    if(r < -lim) r = -lim;
    return (int16_t)r;
}

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
    handleTimer(gasWaitTiEn, gasWaitTi, timerLimit);           // Đếm giây chờ lửa bắt (STP_GAS)
    handleTimer(loop2TiEn, loop2Ti, timerLimit);               // Đếm giây đứng ở STP_LOOP_2

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


    //RoR cho Preheat — GIỮ ĐÚNG cách tính cũ (≤ v3.11.0), từng phép một: hiệu 3 giây + Kalman,
    //trần BT ±95, ET ±20. Ép int16 như bản cũ (raw_rorBT là int16_t) để hành vi preheat không đổi.
    rorPhCount++;
    if(rorPhCount == 3){
        int16_t rawB = (Temperature_BT - rorPhSampBT) * 20;
        int16_t rawE = (Temperature_ET - rorPhSampET) * 20;
        int16_t rB = rorBTphKalman.updateEstimate(rawB);
        int16_t rE = rorETphKalman.updateEstimate(rawE);
        if(rB > 950)  rB = 950;
        if(rB < -950) rB = -950;
        if(rE > 200)  rE = 200;
        if(rE < -200) rE = -200;
        rorBT_ph = rB * 10;
        rorET_ph = rE * 10;
        rorPhSampBT = Temperature_BT;
        rorPhSampET = Temperature_ET;
        rorPhCount = 0;
    }

    //RoR BT / ET — chuỗi y hệt Artisan lúc đang rang, mỗi ROR_SAMPLE_SEC giây (tham số ở Config.h).
    //Trần ±95 °C/phút cho cả BT và ET (ET trước đây ±20 — kẹp phẳng đầu khi đổi gas mạnh).
    //rorBT_pro dùng CÙNG chuỗi để so thẳng với rorBT.
    rorCount++;
    if(rorCount >= ROR_SAMPLE_SEC){
        rorCount = 0;
        rorBT = rorOut(rorArtisanStep(rorBTCh, Temperature_BT), 9500);
        rorET = rorOut(rorArtisanStep(rorETCh, Temperature_ET), 9500);
        rorBT_pro = (lastTimeSD >= 1) ? rorOut(rorArtisanProfile(lastTimeSD), 9500) : 0;
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

/* Thẻ SD hỏng lúc chạy → thử khởi tạo lại, giãn cách SD_RETRY_MS (không chặn vòng quét).
   Trả về true nếu thẻ dùng được. Mọi thao tác thẻ nên hỏi hàm này trước, đừng gọi thẳng
   SD.open khi sdOK=false — thẻ lỗi làm thư viện chờ timeout, vòng quét khựng theo. */
bool sdEnsure(){
    if(sdOK) return true;
    // 09/10/2026 đo trên bàn thử (không có thẻ SD): SD.begin() chờ timeout ~2 s -> vòng quét khựng, giây rang đứng 2–3 s mỗi
    // SD_RETRY_MS (10 s), HMI báo giả "mất kết nối board". Đang rang / làm nóng thì KHÔNG thử khởi tạo lại; máy rảnh mới thử.
    if(START_BTN_R == 1 || timeRoastEn == 1 || WU_R == 1) return false;
    if(millis() - sdRetryMs < SD_RETRY_MS) return false;
    sdRetryMs = millis();
    sdOK = SD.begin(chipSelect);
    if(sdOK && enDebug) SerialComputer.println("SD: card back online");
    return sdOK;
}

// Đóng mọi tệp của mẻ lưu (tệp đang ghi + tệp hồ sơ đang chép), về trạng thái không ghi
static void sdRecCloseAll(){
    if(sdLogFile) sdLogFile.close();
    if(sdRecSlot) sdRecSlot.close();
    sdLogFile = File();
    sdRecSlot = File();
    sdRecMode = SD_REC_NONE;
}

// Chép tệp tạm sang tệp hồ sơ, SD_REC_CHUNK byte mỗi lần (hetMot = true: chép tới hết ngay).
// Chép xong: tệp hồ sơ thành tệp ghi tiếp, xoá tệp tạm. Mẻ vẫn ghi dòng mới vào tệp tạm trong lúc chép (O_APPEND
// tự nhảy về cuối khi ghi) nên vòng chép đuổi theo cuối tệp — ~60 byte/giây ghi so với ~1 KB/giây chép.
static void sdRecCopyStep(bool hetMot){
    uint8_t buf[SD_REC_CHUNK];
    do {
        if(!sdLogFile || !sdRecSlot){
            SDLogSTEP = "COPY FAIL";
            setMachineStatus(STT_SD_SAVE_FAIL);
            sdRecCloseAll();
            return;
        }
        const uint32_t size = sdLogFile.size();
        if(sdRecCopyPos >= size){
            sdRecSlot.flush();
            sdLogFile.close();
            SD.remove(SD_REC_TMP);
            sdLogFile = sdRecSlot;            // từ đây ghi thẳng tệp hồ sơ
            sdRecSlot = File();
            sdRecMode = SD_REC_SLOT;
            SDLogSTEP = "COPY OK";
            return;
        }
        uint32_t n = size - sdRecCopyPos;
        if(n > SD_REC_CHUNK) n = SD_REC_CHUNK;
        sdLogFile.seek(sdRecCopyPos);
        const int doc = sdLogFile.read(buf, (uint16_t)n);
        if(doc <= 0 || sdRecSlot.write(buf, (size_t)doc) != (size_t)doc){
            SDLogSTEP = "COPY IO FAIL";
            setMachineStatus(STT_SD_SAVE_FAIL);
            sdRecCloseAll();
            return;
        }
        sdRecCopyPos += (uint32_t)doc;
    } while(hetMot);
}

void sdLogWrite(){
    snprintf(strProfileName, sizeof(strProfileName), "%u.csv", (unsigned)SELECT_FILE_R);

    // --- HANDLE DEDICATED DELETE REQUEST (from HMI)
    if(sdDeleteProfileEn){
        sdRecCloseAll();
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

    // Start mẻ lưu: mở TỆP TẠM, ghi header Artisan CSV cố định 110 bytes. Tệp hồ sơ của ô chưa bị đụng tới nạp hạt.
    if(sdRecStartEn){
        sdRecCloseAll();
        SD.remove(SD_REC_TMP);
        sdLogFile = SD.open(SD_REC_TMP, FILE_WRITE);
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
            sdRecMode = SD_REC_TEMP;
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
        sdRecStartEn = 0;
    }

    // Huỷ mẻ: chưa nạp hạt -> bỏ tệp tạm, hồ sơ cũ còn nguyên. Đã nạp -> chép nốt rồi đóng (giữ phần đã rang như trước).
    if(sdRecCancelEn){
        if(sdRecMode == SD_REC_TEMP){
            sdRecCloseAll();
            SD.remove(SD_REC_TMP);
            SDLogSTEP = "CANCEL TMP";
        } else {
            if(sdRecMode == SD_REC_COPY) sdRecCopyStep(true);
            sdRecCloseAll();
        }
        sdRecCancelEn = 0;
    }

    // Đã nạp hạt: bắt đầu chép tệp tạm sang tệp hồ sơ (xoá tệp hồ sơ cũ ĐÚNG lúc này), mỗi vòng một đoạn
    if(sdRecMode == SD_REC_TEMP && sdChargeHappened){
        SD.remove(strProfileName);
        sdRecSlot = SD.open(strProfileName, FILE_WRITE);
        sdRecCopyPos = 0;
        if(sdRecSlot){
            sdRecMode = SD_REC_COPY;
        } else {
            SDLogSTEP = "SLOT OPEN FAIL";
            setMachineStatus(STT_SD_SAVE_FAIL);
            sdRecMode = SD_REC_NONE;      // ghi tiếp vào tệp tạm cũng vô ích: không có tệp hồ sơ để thay
        }
    }
    if(sdRecMode == SD_REC_COPY) sdRecCopyStep(false);

    if(sdRemoveAll){
        setMachineStatus(STT_SD_DELETING_ALL);
        sdRecCloseAll();
        SD.remove(SD_REC_TMP);
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
    if(sdLogEndEn && sdRecMode == SD_REC_COPY) sdRecCopyStep(true);   // mẻ ngắn: chép nốt trước khi ghi đè header
    if(sdLogEndEn && sdRecMode != SD_REC_SLOT){                        // chưa nạp hạt (hoặc mở tệp hồ sơ hỏng): không đụng hồ sơ
        sdRecCloseAll();
        SD.remove(SD_REC_TMP);
        sdCsvPendingEvent[0] = '\0';
        SDLogSTEP = "END NO CHARGE";
        sdLogEndEn = 0;
    }
    if(sdLogEndEn){
        // FILE_WRITE dùng O_AT_END (append) — seek(0) không ghi đúng vị trí
        // Phải close rồi mở lại bằng O_READ|O_WRITE (random access, không AT_END)
        sdRecCloseAll();

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
    static bool sdShowCleared = false;   // đã xoá LOADING_SHOW/FA_SUC trên HMI chưa
    sdReadStt = true;
    if (SELECT_FILE_R < 1 || SELECT_FILE_R > 30) {
        // Change-gate (2026-07-23): trước đây ghi 2 reg này + 2×delay(5) MỖI vòng
        // loop khi chưa chọn slot (trạng thái thường trực) → ~24ms rác/vòng, đo
        // được bằng profiler loop. Chỉ ghi 1 lần khi vừa mất slot hợp lệ.
        if (!sdShowCleared) {
            nodeHMI.writeSingleRegister(LOADING_SHOW_W-1, 0); delay(1);
            nodeHMI.writeSingleRegister(FA_SUC_W-1, 0); delay(1);
            sdShowCleared = true;
        }
        return;
    }
    sdShowCleared = false;   // slot hợp lệ — lần sau mất slot sẽ xoá màn hình lại
    //pclSdReadReq: app chọn profile qua PC_Link — không bắt HMI phải đứng màn 6/12/13
    if((SCRNUM_R==6||SCRNUM_R==12||SCRNUM_R==13||pclSdReadReq) && SELECT_FILE_R>0){
        bool isCsv = true;
        switch(sdReadStep){
            case SD_1:
                sdMillis = millis();
                sdProfileLoadOK = false;
                pclProfOk = 0;   //PC_Link: đang nạp, app chờ prof_ok
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
                                // Gán vào biến tạm rồi mới kiểm dải: gán thẳng vào sdTempTi
                                // thì dòng vượt dải tuy bị bỏ qua nhưng sdTempTi vẫn GIỮ số rác.
                                // Nếu đó là dòng cuối file, sdTempTi > PROFILE_MAX_SECONDS làm
                                // lastTimeSD vượt biên → sdBT[lastTimeSD] đọc ra ngoài mảng.
                                uint16_t tiTmp = (uint16_t)(mm*60 + ss);
                                if(tiTmp >= PROFILE_MAX_SECONDS) continue;
                                sdTempTi = tiTmp;

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
                        // Chốt điểm cuối hồ sơ = giây XẢ, không phải giây cuối file.
                        // Dùng rtDROP vì nó đã hợp nhất 2 nguồn (event DROP trên dòng và
                        // "DROP:" ở header) nên vẫn chạy được với file thợ quên bấm event.
                        sdProfileEndTi = (rtDROP > 0 && rtDROP < PROFILE_MAX_SECONDS) ? rtDROP : sdTempTi;
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
                                        // Chốt điểm cuối hồ sơ TRƯỚC khi tách M/S — lúc này
                                        // DROP_PRO_S_R còn là TỔNG GIÂY, sau dòng dưới thì không.
                                        sdProfileEndTi = (DROP_PRO_S_R > 0 && DROP_PRO_S_R < PROFILE_MAX_SECONDS)
                                                       ? (uint16_t)DROP_PRO_S_R : sdTempTi;
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
                sdProfileEndTi = 0;
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


                sdReadStep = SD_4;
                setMachineStatus(sdProfileLoadOK ? STT_SD_LOAD_OK : sdProfileLoadFailStatus);
                pclProfOk = sdProfileLoadOK ? 1 : 2;   //PC_Link: báo kết quả cho app
                calSdMillis = millis() - sdMillis;
            break;

            case SD_4:
                //Chờ
                sdReadStt = false; // Tắt flag đọc file để hiển thị tiến độ trong modbusMaster
                sdMillis = 0;
                pclSdReadReq = false;   //PC_Link: nạp xong, nhả cờ bypass SCRNUM
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

// Kẹp bậc bù về trần của pha. Giữ đúng phép so sánh ">=" của bản gốc.
static inline int16_t calibClampStep(int16_t step, int16_t limit){
    return (step >= limit) ? limit : step;
}

// ─────────────────────────────────────────────────────────────────────────────
// Bộ bù gas theo sai lệch BT so với hồ sơ mẫu. Tách khỏi calibProgram() cho dễ đọc,
// HÀNH VI GIỮ NGUYÊN 100%.
//
// Hai điểm dưới đây trông như lỗi nhưng là CỐ Ý, đã xác nhận với chủ máy — ĐỪNG "sửa":
//   1. Bậc bù tính lại mỗi 10 giây, nhưng ÁP MỖI GIÂY khi BT còn lệch. Áp mỗi giây là
//      để duy trì lực bù liên tục; đẩy 2 dòng cộng/trừ vào trong khối 10 giây là hỏng.
//   2. Cửa sổ 10 giây khớp trễ nhiệt bếp→hạt (15–30 s), đóng vai trò lọc xác nhận xu
//      hướng, chống hunting. Đừng chỉnh con số này.
// Xem memory project_gas_calib_auto và docs/plan/2026-09-10-auto-stall-cuoi-me.md.
// ─────────────────────────────────────────────────────────────────────────────
static void calibGasByProfile(uint16_t btTarget){
    //Deadband siết dần theo 3 nấc — càng về cuối càng đòi bám mẫu chặt:
    //  trước FCs      ±1.0°C (clRangeBt) — đỡ nhạy nhiễu giai đoạn đầu
    //  FCs → DEV 2'   ±0.6°C            — giữ Dev time bám mẫu
    //  DEV từ 2' trở đi ±0.3°C          — đoạn quyết chất hạt, sai số tích lũy nhanh nhất
    //Nấc 3 gác thêm progStep == STP_DEV vì TIME_DEV_SAVE chỉ có nghĩa trong pha đó.
    uint16_t clRange = clRangeBt;
    if(Temperature_BT >= FCS_PRO_R) clRange = CALIB_DEADBAND_FCS;
    if(progStep == STP_DEV && TIME_DEV_SAVE >= CALIB_LATE_DEV_SEC) clRange = CALIB_DEADBAND_LATE;
    const bool btLow  = (Temperature_BT <  btTarget - clRange);  //lạnh hơn mẫu → thêm gas
    const bool btHigh = (Temperature_BT >  btTarget + clRange);  //nóng hơn mẫu → bớt gas

    //Bám mẫu trong deadband → nhả sạch trạng thái bù
    if(!btLow && !btHigh){
        timeCalibGas = 0;
        numIncGas    = 0;
        calibGas     = 0;
        return;
    }

    timeCalibGas++; //Đếm số giây liên tục nằm ngoài deadband
    if(timeCalibGas >= 10){
        //Bậc bù tỉ lệ độ lệch. Sàn 1 bậc = 5% vì trên bếp NP dưới 5% gas không có
        //tác dụng (bếp premix có thể thấp hơn).
        calibGas = abs((int)Temperature_BT - (int)btTarget) / 5;
        if(calibGas <= 0) calibGas = 1;
        numIncGas = calibGas * 5;

        //Trần bậc theo pha (DE / YEL / FCS).
        //CỐ Ý để 3 lệnh if RIÊNG, KHÔNG phải else-if: hồ sơ thiếu mốc FCs làm
        //FCS_PRO_R = 0, khi đó vùng "BT < DE" và vùng "BT >= FCS" CHỒNG nhau và bản
        //gốc kẹp hai lần liên tiếp. Gộp thành else-if là ĐỔI HÀNH VI.
        if(Temperature_BT <  DE_PRO_R)
            numIncGas = calibClampStep(numIncGas, TpCalib_R);
        if(Temperature_BT >= DE_PRO_R && Temperature_BT < FCS_PRO_R)
            numIncGas = calibClampStep(numIncGas, DeCalib_R);
        if(Temperature_BT >= FCS_PRO_R)
            numIncGas = calibClampStep(numIncGas, FcsCalib_R);

        timeCalibGas = 0;
    }

    //btLow và btHigh loại trừ nhau (clRange không âm) nên nhánh này tương đương
    //đúng 2 lệnh if của bản gốc.
    gasPercent = btLow ? (gasPercent + numIncGas) : (gasPercent - numIncGas);
    gasPercent = constrain(gasPercent, 0, 100);
}

// ─────────────────────────────────────────────────────────────────────────────
// NHIỆT XẢ ĐỘNG — bù sai lệch THỜI GIAN bằng NHIỆT ĐỘ.
// Mẻ đi chậm hơn mẫu đã ngậm nhiều nhiệt hơn ở cùng một nhiệt độ ⇒ xả sớm hơn.
// Mẻ đi nhanh hơn thì ngược lại. Chỉ chạy khi DEV đã dài (mẻ DEV ngắn thì vài giây
// lệch không đổi được chất hạt). MỌI chỗ quyết định xả đều phải gọi hàm này, không
// được dùng thẳng DROP_PRO_R nữa, nếu không auto-drop và bồn nguội sẽ lệch nhau.
// ─────────────────────────────────────────────────────────────────────────────
static uint16_t dropTempTarget(){
    uint16_t dropT = DROP_PRO_R;
    //Biên chỉnh lấy từ $M54, thợ cài 0.0–1.0 °C trên HMI. 0 = TẮT, xả đúng nhiệt hồ sơ.
    const int16_t step = dropTrim10();
    //Chỉ chỉnh khi: có bật · đang ở pha phát triển · hồ sơ có nhiệt xả và có giây xả ·
    //DEV đã đủ dài. Thiếu bất kỳ điều kiện nào → giữ nguyên nhiệt xả hồ sơ.
    if(step > 0 && progStep == STP_DEV && dropT > (uint16_t)step
       && sdProfileEndTi > 0 && TIME_DEV_SAVE > ADAPT_DROP_MIN_DEV){
        if(timeRoast > (uint16_t)(sdProfileEndTi + ADAPT_DROP_DEV_SEC)){
            dropT -= (uint16_t)step;           //lê hơn mẫu → xả sớm hơn
        }else if(sdProfileEndTi > ADAPT_DROP_DEV_SEC
              && timeRoast < (uint16_t)(sdProfileEndTi - ADAPT_DROP_DEV_SEC)){
            dropT += (uint16_t)step;           //nhanh hơn mẫu → xả trễ hơn
        }
    }
    return dropT;
}

// ─────────────────────────────────────────────────────────────────────────────
// CHỐT CỨU ĐOẠN CUỐI MẺ — chạy mỗi giây, ĐỘC LẬP với bộ bù gas thường.
//
// Vì sao cần: khi lastTimeSD đã đóng băng ở giây xả, mục tiêu sdBT[] CHÍNH LÀ
// DROP_PRO_R, nên sai lệch chỉ CO LẠI khi BT còn bò lên. Bộ bù thường đòi lệch
// > 0.6 °C liên tục 10 giây ⇒ trong 0.6 °C cuối nó MÙ HOÀN TOÀN. Mẻ RoR thấp
// (hồ sơ vuốt gas về 0%, hoặc trời lạnh hơn mẻ mẫu) đứng lại ở đó và KHÔNG BAO
// GIỜ chạm nhiệt xả — mà STP_DEV không có điều kiện thoát.
//
// Khối này dùng bộ đếm RIÊNG, đo bằng ĐƠN VỊ BT THÔ (không đụng rorBT/Kalman):
//   BT không nhích 0.1 °C suốt END_STALL_WATCH giây  → coi là ĐỨNG, bơm 5%
//   giữ ≥ END_PULSE_MIN giây, BT nhích 0.1 °C        → ĐẠT, giữ nguyên mức gas
//   quá END_ESCALATE giây vẫn không nhích            → cộng thêm 5%, tối đa 3 bước
//   hết trần vẫn đứng                                → chuông + báo mã, KHÔNG tự xả
// ─────────────────────────────────────────────────────────────────────────────
static int16_t  endRescueOffset = 0;   // tổng % gas đang bơm thêm
static uint16_t endRescueMark   = 0;   // BT lúc bơm bước gần nhất
static uint16_t endRescueTimer  = 0;   // giây kể từ bước bơm gần nhất
static uint16_t endStallMark    = 0;   // BT lần nhích gần nhất
static uint16_t endStallTimer   = 0;   // giây kể từ lần nhích gần nhất
static uint16_t endTickGap      = 0;   // nhịp đo được: giây giữa 2 lần BT nhích
static bool     endRescueWarned = false;

static void endRescueReset(){
    endRescueOffset = 0; endRescueTimer = 0;
    endStallTimer   = 0; endStallMark = Temperature_BT;
    endTickGap      = 0;
    endRescueWarned = false;
}

// Còn bao lâu nữa tới nhiệt xả, theo nhịp nhích hiện tại. 0xFFFF = đứng hẳn/không đo được.
// Nhịp lấy LỚN HƠN giữa nhịp đã đo và thời gian đang trôi từ lần nhích cuối — nên khi BT
// vừa khựng lại là ETA phình lên ngay, không phải chờ hết một nhịp mới biết.
static uint16_t endRescueEta(){
    const uint16_t dropT = dropTempTarget();
    if(Temperature_BT >= dropT) return 0;
    const uint16_t unitsLeft = (uint16_t)(dropT - Temperature_BT);
    uint16_t gap = (endTickGap > endStallTimer) ? endTickGap : endStallTimer;
    if(gap == 0) gap = 1;
    const uint32_t eta = (uint32_t)unitsLeft * gap;
    return (eta > 0xFFFEu) ? 0xFFFFu : (uint16_t)eta;
}

// Bước bơm theo mức gas NỀN của hồ sơ: gas nền thấp thì bếp đang ở gần mức đóng,
// vùng phi tuyến, phải bơm bước lớn mới nhúc nhích.
static inline int16_t endRescueStep(int16_t baseGas){
    return (baseGas < END_GAS_LOW_THR) ? END_GAS_BUMP_LOW : END_GAS_BUMP_HI;
}

static void endBatchRescue(uint16_t btTarget, int16_t baseGas){
#if END_RESCUE_EN
    //Cổng theo KHOẢNG CÁCH TỚI NHIỆT XẢ, không theo mốc FCs: STP_DEV phụ thuộc $M21
    //cài đúng, còn khoảng cách tới nhiệt xả thì không phụ thuộc việc bắt mốc.
    const uint16_t dropT = dropTempTarget();
    const bool inWindow = (progStep == STP_DEV)
                       && (dropT > END_GUARD_BAND)
                       && (Temperature_BT >= (uint16_t)(dropT - END_GUARD_BAND))
                       && (Temperature_BT <  dropT);
    if(!inWindow){ endRescueReset(); return; }

    //Bộ bù BT đang muốn GIẢM gas ⇒ mẻ KHÔNG thiếu nhiệt. Lê lúc đó là chuyện khác
    //(gió quá lớn, mẻ quá tải) và không được chữa bằng gas. Nhả offset, đứng im.
    if(Temperature_BT > btTarget + 6){ endRescueReset(); return; }

    //Cập nhật nhịp nhích của BT (dùng cho cả ETA lẫn dò đứng)
    endStallTimer++;
    if(Temperature_BT >= endStallMark + END_BT_TICK){
        endTickGap    = endStallTimer;   //chốt nhịp vừa đo được
        endStallMark  = Temperature_BT;
        endStallTimer = 0;
    }

    if(endRescueOffset == 0){
        //CHƯA bơm — bơm khi DỰ BÁO không kịp, không chờ BT đứng hẳn
        if(endStallTimer >= END_STALL_WATCH && endRescueEta() > END_MAX_ETA){
            endRescueOffset = endRescueStep(baseGas);
            endRescueMark   = Temperature_BT;
            endRescueTimer  = 0;
            setMachineStatus(STT_END_RESCUE_ON);
        }
    }else{
        //ĐANG bơm — theo dõi BT có nhích không
        endRescueTimer++;
        if(endRescueTimer >= END_PULSE_MIN && Temperature_BT >= endRescueMark + END_BT_TICK
           && endRescueEta() <= END_MAX_ETA){
            //Bù có tác dụng VÀ đủ nhanh để kịp giờ → GIỮ nguyên mức gas, dời mốc.
            //PHẢI xét cả ETA: chỉ hỏi "BT có nhích không" là chưa đủ — BT nhích 15 giây
            //một lần vẫn là lê, mà nhánh này lại reset đồng hồ nên nhánh leo thang bên
            //dưới không bao giờ đếm tới nơi. Đó là lý do bản trước giữ nguyên 10% kể cả
            //khi còn 75 giây nữa mới tới nhiệt xả.
            endRescueMark  = Temperature_BT;
            endRescueTimer = 0;
        }else if(endRescueTimer >= END_ESCALATE){
            if(endRescueOffset < END_RESCUE_MAX && endRescueEta() > END_MAX_ETA){
                endRescueOffset += endRescueStep(baseGas);
                if(endRescueOffset > END_RESCUE_MAX) endRescueOffset = END_RESCUE_MAX;
                endRescueMark  = Temperature_BT;
                endRescueTimer = 0;
                setMachineStatus(STT_END_RESCUE_ON);
            }else if(!endRescueWarned){
                //Hết trần mà vẫn đứng: hết gas / tắc béc / hạt đã chín.
                //Cộng thêm chỉ làm cháy vỏ → dừng, báo thợ, để thợ quyết.
                endRescueWarned = true;
                buzzerTimerEn   = 1;
                setMachineStatus(STT_WARN_END_RESCUE_TMO);
            }
        }
    }

    //NÂNG TỚI mức mong muốn, KHÔNG cộng mù lên trên bộ bù thường.
    //Hai bộ trả lời CÙNG một câu hỏi ("mẻ thiếu bao nhiêu nhiệt") nên phải lấy cái
    //LỚN HƠN. Cộng lại thì ở BT ≤ nhiệt xả −0.7 °C hai bộ chồng nhau: hồ sơ gas nền
    //30% + calib 10% + chốt cứu 10% = 50% gas ở 216 °C → cháy vỏ.
    const int16_t want = constrain(baseGas + endRescueOffset, 0, 100);
    if(gasPercent < want) gasPercent = want;
#else
    (void)btTarget; (void)baseGas;
#endif
}

void calibProgram(){
    //Phát lại hồ sơ mẫu theo từng giây: gas / gió / trống lấy thẳng từ SD.
    //Chỉ GAS được bù thêm theo sai lệch BT; gió và trống giữ nguyên số của mẫu.
    // Kẹp tại giây XẢ của mẫu, KHÔNG phải giây cuối file. Vượt qua đó thì đóng băng
    // ở điểm xả thay vì bò vào đuôi làm nguội (gas 0 + gió mở hết) của hồ sơ.
    if(timeRoast<=sdProfileEndTi){
        lastTimeSD = timeRoast;
    }
#if MACHINE_HAS_VACUUM_SENSOR
    // Hồ sơ có điểm đặt áp hút nhưng máy KHÔNG có vacuum ($M62 bit 2 = 0) ⇒ chạy gió theo % của hồ sơ.
    if (optVacuum() && sdVacuumSetFlag[lastTimeSD] == 1) {
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
    if (optVacuum()) {
        nodeHMI.writeSingleRegister(vacuumSetFlag_W+2000,  vacuumSetFlag_R);
        nodeHMI.writeSingleRegister(vacuumSetpoint_W+2000, vacuumSetpoint_R);
    }
#endif


    //Hiệu chỉnh gas theo phase — chỉ bắt đầu sau TP, khi BT nằm ngoài định mức
    // RoR control chỉ dùng cho preheat, không can thiệp gas khi rang auto
    if(progStep>STP_TP){
        calibGasByProfile(sdBT[lastTimeSD]);
    }
    //Chốt cứu đoạn cuối — CHẠY SAU bộ bù thường, không dính deadband của nó.
    //baseGas = gas NỀN của hồ sơ (trước mọi bù) → quyết định bước bơm to hay nhỏ.
    endBatchRescue(sdBT[lastTimeSD], (int16_t)sdGas[lastTimeSD]);
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
// 21/10/2026 (panel thật: bấm "Làm mới" Hồ sơ mất > 12 s mới điền 10 dòng, vòng quét đứng suốt lúc đó): trước đây ghi
// 210 lần writeSingleRegister (30 ô × 7). Nay gom 9 ô (63 thanh ghi, vừa bộ đệm 64 từ của ModbusMaster) một lệnh FC16.
#define PROFILE_DATE_SLOTS_PER_TX  9
static uint8_t  pdNo = 0;            // số ô đang gom
static uint16_t pdBase = 0;          // thanh ghi đầu của nhóm

static void profileDateFlush() {
    if (pdNo == 0) return;
    if (nodeHMI.writeMultipleRegisters(pdBase, pdNo * PROFILE_REGS_PER_SLOT) != nodeHMI.ku8MBSuccess && enDebug)
        SerialComputer.println("ERRO HMI PROFILE DATES");
    pdNo = 0;
    delay(2);
}

static void profileDatePush(uint16_t base, const uint16_t v[PROFILE_REGS_PER_SLOT]) {
    if (pdNo == 0) pdBase = base;
    for (uint8_t r = 0; r < PROFILE_REGS_PER_SLOT; r++)
        nodeHMI.setTransmitBuffer(pdNo * PROFILE_REGS_PER_SLOT + r, v[r]);
    if (++pdNo >= PROFILE_DATE_SLOTS_PER_TX) profileDateFlush();
}

void loadAllProfileDates() {
    pdNo = 0;
    for (int slot = 1; slot <= MAX_PROFILE_SLOTS; slot++) {
        uint16_t base = PROFILE_DATE_BASE_W + (slot - 1) * PROFILE_REGS_PER_SLOT;

        char fname[8];
        sprintf(fname, "%d.csv", slot);

        File f = SD.open(fname);
        if (!f) {
            const uint16_t khong[PROFILE_REGS_PER_SLOT] = {0, 0, 0, 0, 0, 0, 0};
            profileDatePush(base, khong);
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

        // --- 7 registers của ô này vào nhóm ghi
        const uint16_t v[PROFILE_REGS_PER_SLOT] = {dd, mm, yy, chHH, chMM, roastTimeMin, roastTimeSec};
        profileDatePush(base, v);
    }
    profileDateFlush();

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
    if(!sdOK) return;              // thẻ hỏng → bảng rỗng; với dif cố định thì bảng không dùng tới
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
    if(!sdEnsure()) return;        // thẻ hỏng → bỏ qua, KHÔNG ngồi chờ timeout giữa lúc hút
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

#if LOADER_SD_LOG_EN
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
    if(!sdEnsure()){ if(loaderDbgEn) SerialComputer.println("LDR >>> LOG SKIP: no SD card"); return; }
    File f = SD.open("loader.csv", FILE_WRITE);
    if(!f){
        sdOK = false;   // thẻ vừa rớt → ngừng đụng thẻ, sdEnsure sẽ thử lại sau SD_RETRY_MS
        if(loaderDbgEn) SerialComputer.println("LDR >>> LOG FAIL: SD.open loader.csv FAILED");
        return;
    }
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
#endif  // LOADER_SD_LOG_EN

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
        // FEEDER_DIF_MANUAL → dif do người đặt bằng công thức trong Config.h, KHÔNG học và
        // KHÔNG ghi SD (tránh làm hỏng bảng + tránh ghi thẻ khi thẻ đang dở chứng).
        // Vẫn chấm điểm & ghi log để theo dõi.
#if FEEDER_DIF_MANUAL
        // TỰ HIỆU CHUẨN base TRONG RAM (không đụng thẻ SD).
        // err100 > 0 = hút THIẾU → cắt quá sớm → base phải NHỎ lại.
        // err100 < 0 = hút DƯ    → cắt quá muộn → base phải LỚN lên.
        // Chỉ tới được đây khi mẻ đủ lớn VÀ đã trượt deadband "hút OK" (lệch > 0,09 kg),
        // nên máy đang chạy đúng thì base đứng yên tuyệt đối, không giật.
        {
            int16_t oldBase = coastBase100;
            int32_t nb = (int32_t)oldBase - err100 * FEEDER_LEARN_GAIN / 100;
            if(nb < FEEDER_COAST_MIN100) nb = FEEDER_COAST_MIN100;
            if(nb > FEEDER_COAST_MAX100) nb = FEEDER_COAST_MAX100;
            coastBase100 = (int16_t)nb;
            difNew100    = (int16_t)nb;              // cột difNew của log = base mới
            if(loaderDbgEn){
                SerialComputer.print("LDR learn: err="); SerialComputer.print(err100);
                SerialComputer.print(" base ");          SerialComputer.print(oldBase);
                SerialComputer.print(" -> ");            SerialComputer.println(coastBase100);
            }
        }
#else
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
#endif
    }

#if LOADER_SD_LOG_EN
    loaderLogEvent(final100, target100, err100, score_x10, result, difOld100, difNew100, secHut);
#else
    (void)difOld100; (void)difNew100; (void)secHut;   // loader không ghi thẻ (xem LOADER_SD_LOG_EN)
#endif
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

/* Tắt ghi đồ thị TRỄ sau Drop (07/10/2026, đo trên panel thật): tắt ngay lúc Drop thì mốc Drop (giữ MARK_HOLD_MS) không kịp vào
   mẫu History nào (chu kỳ 9 s) -> đồ thị thiếu vạch Drop. Drop chỉ hẹn tắt; roastMarkTask() tắt khi hết giữ mốc + 1,5 s.
   Lối huỷ / reset vẫn tắt ngay (trendStopCancel). */
#define TREND_STOP_DELAY_MS (MARK_HOLD_MS + 1500)
static bool     trendStopPending = false;
static uint32_t trendStopMs = 0;

void trendStopLater() { trendStopPending = true; trendStopMs = millis(); }
void trendStopCancel() { trendStopPending = false; }

/* Max RoR (TP → FCs) + đánh dấu mốc Charge/TP/DE/FCs/Drop cho đồ thị HMI và web PC (07/10/2026, chủ máy).
   CHỈ ĐỌC profileData (hồ sơ SD) — không ghi gì vào hồ sơ. Gọi trong loop(), không trong ISR; chỉ ghi bus khi đổi.
   Max RoR chỉ tính khi BT đã qua đáy hiện tại (timeRoast > TIME_TP_DIP): RoR còn sót của preheat ngay sau Charge
   không bị lấy nhầm; đáy dời sâu hơn thì tính lại. Dừng ở FCs. Giây = lúc đạt max − giây đáy TP thật. */
void roastMarkTask() {
    static uint16_t lastCh = 0, lastTp = 0, lastYe = 0, lastFc = 0, lastDr = 0;
    static int16_t  maxRor = 0;
    static uint16_t maxT = 0, dipAt = 0;
    static int32_t  sentMax = -1, sentSec = -1;
    static uint32_t markMs = 0;
    static bool     markOn = false;

    if (trendStopPending && millis() - trendStopMs >= TREND_STOP_DELAY_MS) {
        trendStopPending = false;
        setTrendSample(0);                           // Turn off trend graph sample (trễ sau Drop — xem trendStopLater)
    }
    if (BT_CHARGE_SAVE == 0) {                       // mẻ mới (STP_DATA xoá hồ sơ) → xoá số cũ
        maxRor = 0; maxT = 0; dipAt = 0;
    } else if (timeRoastEn && TIME_FCS_SAVE == 0) {
        if (TIME_TP_DIP != dipAt) { dipAt = TIME_TP_DIP; maxRor = 0; maxT = 0; }
        if (timeRoast > TIME_TP_DIP && rorBT > maxRor) { maxRor = rorBT; maxT = timeRoast; }
    }
    // Chỉ đưa ra sau khi firmware đã CHỐT TP: trước đó đáy còn dời, số tạm (vd RoR sót của preheat ngay sau Charge)
    // không được hiện lên HMI / web (đo 07/10: vừa Charge hiện 300 / 1 s).
    bool daTP = (TIME_TP_SAVE != 0);
    int16_t raMax = daTP ? maxRor : 0;
    int32_t sec = (daTP && maxRor > 0 && maxT >= TIME_TP_DIP) ? (int32_t)(maxT - TIME_TP_DIP) : 0;
    if (raMax != sentMax) { nodeHMI.writeSingleRegister(MAXROR_W - 1, raMax); sentMax = raMax; delay(1); }
    if (sec != sentSec)    { nodeHMI.writeSingleRegister(MAXROR_SEC_W - 1, (uint16_t)sec); sentSec = sec; delay(1); }

    uint8_t  code = 0;
    uint16_t bt = 0, tm = 0;
    if (lastCh == 0 && BT_CHARGE_SAVE != 0)   { code = 1; bt = BT_CHARGE_SAVE; tm = 0; }
    if (lastTp == 0 && TIME_TP_SAVE != 0)     { code = 2; bt = BT_TP_SAVE;     tm = TIME_TP_SAVE; }
    if (lastYe == 0 && TIME_YELLOW_SAVE != 0) { code = 3; bt = BT_YELLOW_SAVE; tm = TIME_YELLOW_SAVE; }
    if (lastFc == 0 && TIME_FCS_SAVE != 0)    { code = 4; bt = BT_FCS_SAVE;    tm = TIME_FCS_SAVE; }
    if (lastDr == 0 && TIME_DROP_SAVE != 0)   { code = 5; bt = BT_DROP_SAVE;   tm = TIME_DROP_SAVE; }
    lastCh = BT_CHARGE_SAVE; lastTp = TIME_TP_SAVE; lastYe = TIME_YELLOW_SAVE;
    lastFc = TIME_FCS_SAVE;  lastDr = TIME_DROP_SAVE;

    if (code) {
        nodeHMI.writeSingleRegister(MARK_BT_W - 1, bt);                       delay(1);
        nodeHMI.writeSingleRegister(MARK_ROR_W - 1, (uint16_t)max<int16_t>(rorBT, 0)); delay(1);
        nodeHMI.writeSingleRegister(MARK_T_W - 1, tm);                        delay(1);
        nodeHMI.writeSingleRegister(MARK_CODE_W - 1, code);                   delay(1);   // mã ghi SAU CÙNG: PC thấy mã là các ô kia đã đủ
        markMs = millis(); markOn = true;
        if (enDebug) { SerialComputer.print("MARK "); SerialComputer.print(code);
                       SerialComputer.print(" BT="); SerialComputer.println(bt / 10.0f, 1); }
    } else if (markOn && millis() - markMs >= MARK_HOLD_MS) {
        nodeHMI.writeSingleRegister(MARK_BT_W - 1, 0);   delay(1);
        nodeHMI.writeSingleRegister(MARK_ROR_W - 1, 0);  delay(1);
        nodeHMI.writeSingleRegister(MARK_CODE_W - 1, 0); delay(1);
        nodeHMI.writeSingleRegister(MARK_T_W - 1, 0);    delay(1);
        markOn = false;
    }
}

/* $M53 autoEscape — MỘT CHỖ DUY NHẤT định nghĩa nghĩa của thanh ghi này.
   1 = máy TỰ mở cửa escape (kèm tách đá) sau khi làm mát xong — nếp cũ từ trước tới nay.
   0 = CHỈ LÀM MÁT: hết giờ tắt bồn nguội, không tách đá, không tự mở cửa; thợ xả tay.
   MACHINE_HAS_AUTO_ESCAPE_SWITCH = 0 (HMI đời cũ chưa có ô gạt) thì BỎ QUA thanh ghi và
   luôn trả true — máy cũ nạp firmware mới vẫn tự xả y nguyên. */
static inline bool autoEscapeEnabled(){
#if MACHINE_HAS_AUTO_ESCAPE_SWITCH
    return (autoEscape_R != 0);
#else
    return true;
#endif
}

// 21/10/2026: mã 53 (chờ BT nguội) chỉ báo khi THẬT SỰ chờ nguội, một lần mỗi mẻ (setMachineStatus không gộp mã thường
// trùng trong hàng đợi — gọi mỗi vòng sẽ lấp đầy hàng đợi)
static bool roastCoolSttSent = false;

void programScan(){
    // PRIORITY 1: keep drum/fan on when BT or ET is hotter than 80C
    if (forceDrumFanOnFlag) {
        if (((int16_t)Temperature_BT > 800 || (int16_t)Temperature_ET > 800) &&
            DRUM_FAN_BTN_R == 0) {
            nodeHMI.writeSingleRegister(DRUM_FAN_BTN_W - 1, 1);
            DRUM_FAN_BTN_R = 1;
            DRUM_FAN_BTN_R_CP = 1;
            if (optRelayExt()) { nodeIORelay.writeSingleCoil(CH1_IO_RL_W, DRUM_FAN_BTN_R); delay(10); } // Relay ngoài 1: drum/fan — chờ 10ms nhả bus (07/10/2026)
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

    /* ⛔ R5 (2026-07-30): SẤY LỒNG và FACTORY TUNE GIÓ dùng CHUNG ô tiến trình
       tunePercent (PID_Airflow.h ghi 3 chỗ, Preheat*.h ghi 6 chỗ). Trước đây không có gì
       chặn hai cái cùng chạy → thanh tiến trình trên HMI nhảy qua nhảy lại giữa hai
       nguồn, thợ không biết đang xem cái nào. Trọng tài đặt ở đây vì chỉ programScan()
       thấy cả ftState (PID_Airflow.h) lẫn wuState (Preheat*.h) — hai file kia include
       lệch nhau nên không tự biết về nhau.
       Ai chạy trước thì thắng: đang sấy lồng thì factory tune bị huỷ. */
    if (ftState != FT_IDLE && wuState != WU_IDLE) {
        pidFactoryTuneStop();
        setMachineStatus(STT_WARN_TUNE_BUSY);
        nodeHMI.writeSingleRegister(AUTO_PID_AIR_TU_W - 1, 0);   // nhả nút tuning trên HMI
        if (enDebug) SerialComputer.println("Factory tune cancelled: preheat is running");
    }
    // R3: bảng feed-forward gió đầy giữa lúc quét → báo mã, đừng để tune báo xong 100%
    // như không có gì. Báo một lần rồi hạ cờ.
    if (ffTableFull) {
        ffTableFull = false;
        setMachineStatus(STT_WARN_FF_TABLE_FULL);
    }

    // preheat — chạy độc lập, không phụ thuộc AUTO mode
    if (START_BTN_R == 0 && ftState == FT_IDLE) {  // không sấy lồng khi đang tune gió
        preheat();
    } else if (START_BTN_R == 1 && wuState != WU_IDLE) {
        /* Vào mẻ rang khi còn đang sấy lồng: preheat() không được gọi nữa nên nó không
           tự dọn được — wuState treo giữa chừng, phVacTaken treo theo và khóa luôn cờ
           vacuum của HMI/app tới lần khởi động sau. Còn phRunLearn() thì sẽ học trên
           dữ liệu cả mẻ rang khi preheat chạy lại — bảng FF bị bẩn.
           Đóng sấy lồng tại đây, TRƯỚC khối STP_DATA bên dưới để roastVacFlagSaved
           chụp đúng cờ vacuum đã được trả về. */
        /* wuReset() cắt luôn nút gas trên HMI — đúng cho lúc thuộc preheat, nhưng ở
           đây sẽ cướp lửa của luồng rang. Đường charge tay (chargeTemp_R = 0) không
           có bước tự mồi nào, cắt là thợ mất lửa giữa mẻ. Giữ nguyên trạng nút gas,
           để STP_COOL_DOWN/STP_GAS tự quyết định đóng hay mở. */
        uint16_t gasBtnBefore = START_GAS_BTN_R;
        wuReset();
        if (gasBtnBefore == 1) nodeHMI.writeSingleRegister(START_GAS_BTN_W - 1, 1);
        nodeHMI.writeSingleRegister(WU_W - 1, 0);
        setMachineStatus(STT_PREHEAT_CANCELLED);
        if (enDebug) SerialComputer.println("Preheat closed: roast started");
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
                //Mẻ lưu: ghi vào tệp tạm; hồ sơ của ô đã chọn chỉ bị thay lúc nạp hạt (sdLogWrite)
                if(progStatus == STT_PROGRAM_SAVE){
                    sdRecStartEn = 1;
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
                TIME_DEV_SAVE = 0;      //bị bỏ sót: giữ dev time của MẺ TRƯỚC sang mẻ mới
                TIME_DEV_MIN_SAVE = 0;
                TIME_DEV_SEC_SAVE = 0;
                
                TIME_DROP_SAVE = 0;
                timeTPAbsolute   = 0;
                timeDRYeAbsolute = 0;
                timeFCsAbsolute  = 0;
                timeDROPAbsolute = 0;

                timeRoast = 0;
                tpDipSeen = false;      // Bằng chứng cú tụt TP — mẻ mới phải dò lại từ đầu
                TIME_TP_DIP = 0;
                // Reset các chốt an toàn của mẻ (2026-07-30) — mẻ mới phải bắt đầu sạch,
                // không mang cờ cảnh báo hay bộ đếm của mẻ trước sang
                gasWaitTiEn = false; gasWaitTi = 0;
                loop2TiEn   = false; loop2Ti   = 0;
                devWarned   = false;
                rorCtrl_reset(); // Reset RoR control state khi bắt đầu mẻ mới
                trendPreStarted = false; // Cho phép bật lại trend sớm ở mẻ mới

                nodeHMI.writeSingleRegister(CLEAR_HIS_CONTROL_W-1, 1);  //Clear trend graph
                nodeHMI.writeSingleCoil(LOCK_BUTTON_W-1, 1);    //Lock các button trên HMI khi rang
                //Debug
                STEP_STRING = "RESET DATA";

                // 21/10/2026 (panel thật, nhiệt nạp = 0 = nạp tay): trước đây báo 53 "chờ BT nguội" ở đây cho MỌI mẻ -> HMI hiện
                // "lồng nóng hơn nhiệt nạp" cả khi máy đang chờ thợ bấm nạp. Mã 53 nay đặt trong STP_COOL_DOWN khi thật sự chờ.
                roastCoolSttSent = false;
                progStep = STP_COOL_DOWN;   //Chuyển trạng thái
            break;

            //Kiểm tra auto charge
            //Nếu có auto charge thì tắt gas và đợi nhiệt giảm
            case STP_COOL_DOWN:
                if(chargeTemp_R_CV>0){
                    //Debug
                    STEP_STRING = "BT COOLS DOWN";
                    if(Temperature_BT<=(chargeTemp_R_CV-turnGasPoint_R_CV)){
                        // 09/10/2026 (chủ máy, bàn thử): trước đây chỉ bật gas khi CH1 KHÔNG có lửa (READ_CH1==HIGH).
                        // Cảm biến lửa báo "có lửa" sẵn (kẹt, hoặc bàn thử nối cứng) -> không bật relay mà vẫn sang
                        // STP_GAS/STP_CHECK -> BT nguội mãi, mẻ treo không báo gì. Nay bật theo trạng thái RELAY gas.
                        if(READ_CH1==LOW && START_GAS_BTN_R==0 && enDebug)
                            SerialComputer.println("WARN: flame signal ON while gas relay OFF (sensor stuck?)");
                        if(START_GAS_BTN_R==0){
                            naviSourceGAS = SOURCE_AI_AUTO; //Đổi source gas sang auto
                            gasPercent = 50;
                            nodeHMI.writeSingleRegister(START_GAS_BTN_W-1, 1);  //Turn on gas
                            delay(1);
                        }
                        setMachineStatus(STT_ROAST_WAITGAS); progStep = STP_GAS; //Chuyển trạng thái kiểm tra gas 
                        
                    }else{
                        if(!roastCoolSttSent){ setMachineStatus(STT_ROAST_COOLDOWN); roastCoolSttSent = true; }
                        // 21/10/2026: chỉ ghi khi relay đang bật — trước đây ghi W40002 = 0 MỌI vòng quét suốt lúc chờ nguội
                        if(START_GAS_BTN_R != 0) nodeHMI.writeSingleRegister(START_GAS_BTN_W-1, 0);  //Turn off gas
                    }
                }else{
                    setMachineStatus(STT_ROAST_WAIT_CHARGE); progStep = STP_CHARGE; //Chuyển trạng thái kiểm tra charge   
                }
            break;

            //Kiểm tra bếp
            case STP_GAS:
                /* ⛔ CHỐT THỜI GIAN CHỜ LỬA (R1, 2026-07-30)
                   Trước đây bếp thường chờ READ_CH1 xuống LOW VÔ THỜI HẠN, mà bước
                   trước đã mở gas 50% — mồi hụt là xả gas không cháy vào buồng đốt cho
                   tới khi có người để ý. preheat() đã có chốt PH_IGNITE_TMO từ lâu,
                   luồng rang thì chưa. Dùng LẠI cùng hằng số cho nhất quán.
                   Hết hạn thì CẮT GAS rồi về DATA — không tự mồi lại, vì mồi hụt lặp
                   lại là dấu hiệu hỏng bếp, cần người xem chứ không phải thử tiếp. */
                if(!gasWaitTiEn){ gasWaitTiEn = true; gasWaitTi = 0; }
                //Nếu là bếp NP thì chờ gas on
                if(burnerPremix_R == 0){
                    if(READ_CH1==LOW){
                        naviSourceGAS = SOURCE_AI_AUTO; //Đổi source gas
                        gasPercent = preGas_R; //Set gas charge
                        STEP_STRING = "WAITGAS";
                        gasWaitTiEn = false; gasWaitTi = 0;
                        setMachineStatus(STT_ROAST_CHECK); progStep = STP_CHECK; //Chuyển trạng thái
                    }else if(gasWaitTi >= PH_IGNITE_TMO){
                        nodeHMI.writeSingleRegister(START_GAS_BTN_W-1, 0);  //CẮT GAS
                        gasPercent = 0;
                        naviSourceGAS = SOURCE_AI_VR;                      //trả quyền cho thợ
                        gasWaitTiEn = false; gasWaitTi = 0;
                        buzzerTimerEn = 1;
                        setMachineStatus(STT_ERR_IGNITION_FAIL);
                        setMachineStatus(STT_ERR_GAS_WAIT_TMO);
                        STEP_STRING = "GASFAIL";
                        if(enDebug) SerialComputer.println("!!! WAITGAS timeout: GAS CUT, roast aborted !!!");
                        // PHẢI tắt START, không thì về STP_DATA là chạy lại vòng
                        // COOL_DOWN→GAS→chờ lửa, tức mồi lại vô hạn — đúng cái vừa nói
                        // là không làm. Mở khoá HMI để thợ vào xem bếp.
                        nodeHMI.writeSingleRegister(START_BTN_W-1, 0);
                        nodeHMI.writeSingleCoil(LOCK_BUTTON_W-1, 0);
                        progStep = STP_DATA;
                        delay(1);
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
                    tpDipSeen = false;          //Bám đáy tính từ giây nạp này
                    TIME_TP_DIP = 0;

                    //Enable record airflow, drum, flame, gas signal

                    trendStopCancel(); setTrendSample(1);  //Turn on trend graph sample
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

            case STP_TP: {
                //Condition to TP
                STEP_STRING = "WAIT TP";

                /* Bám đáy NGAY TỪ GIÂY CHARGE, không chờ cửa sổ dò mở (2026-09-10).
                   Trước đây BT_TP_Pre chỉ được cập nhật bên trong cửa sổ, nên khi cửa
                   sổ chưa mở lần nào thì nó vẫn giữ nguyên nhiệt lúc nạp — nhánh cứu
                   bên dưới lấy đúng số đó làm TP. Bám liên tục thì BT_TP_Pre luôn là
                   đáy THẬT và TIME_TP_DIP là giây của đáy đó. */
                if(Temperature_BT < BT_TP_Pre){
                    BT_TP_Pre = Temperature_BT;
                    TIME_TP_DIP = timeRoast;
                }
                if(Temperature_BT < ulimitTPTemp) tpDipSeen = true;

                /* Bằng chứng "đã tụt thật": đáy ghi được phải thấp hơn nhiệt nạp ít
                   nhất TP_MIN_DROP_CV. Đây là thứ phân biệt "chưa tụt tới" với "đã
                   tụt xong" — thiếu nó thì nhịp BT nhích lên ngay sau khi đổ hạt
                   (quán tính đầu dò) cũng bị chốt thành TP. */
                bool tpDipReal = (BT_CHARGE_SAVE >= TP_MIN_DROP_CV) &&
                                 (BT_TP_Pre + TP_MIN_DROP_CV <= BT_CHARGE_SAVE);

                if(timeRoast>ulimitTPTime && tpDipReal && Temperature_BT<ulimitTPTemp){
                    if(Temperature_BT<=BT_TP_Pre){
                        STEP_STRING = "CHECK TP";   //còn tụt — đáy đã cập nhật ở trên

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
                /* ⛔ CỨU TP KHI TRƯỢT CỬA SỔ (R2 lớp 1, 2026-07-30; siết lại 2026-09-10)
                   Cửa sổ dò là AND của hai điều kiện. Nếu BT vượt ulimitTPTemp TRƯỚC khi
                   timeRoast qua ulimitTPTime thì cửa sổ KHÔNG BAO GIỜ mở → kẹt suốt mẻ.
                   Nhưng bản 30/07 chốt TP chỉ dựa vào "hết giờ + BT đang cao", nên mẻ nạp
                   nóng chưa kịp tụt (hoặc BT còn đang ĐI LÊN lúc bấm charge) bị chốt TP
                   giả ngay giây 21 rồi kéo DE chốt theo. Giờ đòi thêm hai bằng chứng:
                   tpDipReal (đáy đã thấp hơn nhiệt nạp) và tpDipSeen (đã từng xuống dưới
                   ulimitTPTemp rồi mới bật ngược lên qua nó) — đúng nghĩa "đáy đã trôi
                   mất", chứ không phải "đáy chưa tới". */
                else if(timeRoast>ulimitTPTime && tpDipReal && tpDipSeen
                        && Temperature_BT>=ulimitTPTemp){
                    BT_TP_SAVE = BT_TP_Pre;
                    TIME_TP_SAVE = TIME_TP_DIP;     //giây của đáy thật, không phải giây phát hiện
                    TIME_TP_MIN_SAVE = TIME_TP_SAVE/60;
                    TIME_TP_SEC_SAVE = TIME_TP_SAVE%60;
                    strcpy(sdCsvPendingEvent, "TP");
                    setMachineStatus(STT_WARN_TP_ASSUMED);
                    setMachineStatus(STT_EVENT_TP_REACHED);
                    if(enDebug) SerialComputer.println("TP window missed -> assumed TP from BT_TP_Pre");
                    setMachineStatus(STT_ROAST_YELLOW); progStep = STP_YELLOW;
                }
                /* Hạn cứng chống kẹt: đáy nằm TRÊN ulimitTPTemp (nạp rất nóng) hoặc đầu
                   dò đứng số thì hai nhánh trên không bao giờ đủ điều kiện. Chốt theo đáy
                   đã ghi được rồi đi tiếp — nhánh này chỉ phụ thuộc thời gian nên luôn
                   thoát được, không tạo đường kẹt mới. */
                else if(timeRoast > TP_HARD_TMO){
                    BT_TP_SAVE = BT_TP_Pre;
                    TIME_TP_SAVE = TIME_TP_DIP;
                    TIME_TP_MIN_SAVE = TIME_TP_SAVE/60;
                    TIME_TP_SEC_SAVE = TIME_TP_SAVE%60;
                    strcpy(sdCsvPendingEvent, "TP");
                    setMachineStatus(STT_WARN_TP_ASSUMED);
                    setMachineStatus(STT_EVENT_TP_REACHED);
                    if(enDebug) SerialComputer.println("TP hard timeout -> assumed TP from lowest BT");
                    setMachineStatus(STT_ROAST_YELLOW); progStep = STP_YELLOW;
                }
            } break;

            case STP_YELLOW:
                STEP_STRING = "WAIT YELLOW";
                /* Check YL — DE phải cách TP tối thiểu DE_MIN_GAP giây (2026-09-10).
                   TP nằm ở đáy (~75 °C), DE ở mốc vàng (~150 °C): không mẻ nào đi hết
                   quãng đó dưới 5 giây. Hai mốc dính liền nhau luôn có nghĩa là TP vừa
                   bị chốt bậy lúc BT còn cao. Sàn này chỉ dựa vào thời gian nên không
                   tạo thêm đường kẹt. */
                if(Temperature_BT>=yellowPhase_R_CV && timeRoast>=TIME_TP_SAVE+DE_MIN_GAP){// đã đạt mốc yellow
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
                /* ⚠ TRẦN PHA PHÁT TRIỂN (R3, 2026-07-30) — chỉ BÁO, KHÔNG tự xả.
                   Bước này không có điều kiện thoát; DROP_PRO_R cài 0 hoặc quá cao là
                   rang mãi tới khi thợ để ý. Nhưng tự xả một mẻ chưa tới nhiệt là làm
                   hỏng mẻ, nên chốt ở mức kêu chuông + báo mã, để thợ quyết.
                   Ngưỡng theo TỈ LỆ (phần nghìn) cho khớp cách thợ nghĩ, không theo giây. */
                if(!devWarned && PER_DEV_SAVE >= developmentWarnPermil()){
                    devWarned = true;
                    buzzerTimerEn = 1;
                    setMachineStatus(STT_WARN_DEV_TOO_LONG);
                    if(enDebug){ SerialComputer.print("DEV too long: "); SerialComputer.print(PER_DEV_SAVE/10);
                                 SerialComputer.println("% — check drop temperature"); }
                }
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
                    //Mẻ mới: bỏ chốt cưỡng chế tắt AB của mẻ vừa xong
                    abStep = 0; abUserOff = false; abSeenOn = false;
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
                if(!loop2TiEn){ loop2TiEn = true; loop2Ti = 0; }   // R4: đếm tổng thời gian đứng đây
                if(DROP_BTN_R == 0){
                    //Khởi động trình đếm để chờ drop đóng lại hoàn toàn
                    waitDropcloseTiEn = 1;
                }
                /* ⛔ CỬA XẢ KẸT MỞ (R4, 2026-07-30)
                   waitDropcloseTi chỉ chạy khi THẤY cửa xả đã đóng. Cửa kẹt mở (hoặc mất
                   tín hiệu đọc nút) thì không bao giờ đếm → đứng ở WCANCEL mãi. Mẻ đã xả
                   xong nên không nguy hiểm, nhưng TUYỆT ĐỐI không nạp mẻ mới khi cửa xả
                   còn mở. Hết hạn thì dừng hẳn và báo mã cho thợ vào xem xi-lanh. */
                if(loop2Ti >= loopDoorStuckSec() && DROP_BTN_R == 1){
                    setMachineStatus(STT_ERR_DROP_STUCK_OPEN);
                    buzzerTimerEn = 1;
                    nodeHMI.writeSingleRegister(START_BTN_W-1, 0);
                    nodeHMI.writeSingleCoil(LOCK_BUTTON_W-1, 0);
                    loop2TiEn = false; loop2Ti = 0;
                    waitDropcloseTiEn = false; waitDropcloseTi = 0;
                    if(enDebug) SerialComputer.println("!!! DROP cylinder stuck open — next batch cancelled !!!");
                    progStep = STP_DATA;
                    STEP_STRING = "NONE";
                    delay(1);
                    break;
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
        //khi còn cách charge TREND_PRECHARGE_BAND (Config.h, nay 30°C) thì bật sample để ghi cả đoạn tiến tới charge.
        //Chỉ khi có cài charge temp; mỗi mẻ 1 lần (trendPreStarted). Charge-press vẫn bật lại phòng hờ.
        if(chargeTemp_R_CV>0 && progStep>=STP_GAS && progStep<STP_TP && !trendPreStarted
           && Temperature_BT>=(chargeTemp_R_CV-TREND_PRECHARGE_BAND)
           && rorBT>=TREND_PRECHARGE_MIN_ROR){            // BT đang tăng về charge (không ghi đoạn mồi / tụt nhiệt)
            trendStopCancel(); setTrendSample(1);  //Turn on trend graph sample sớm
            trendPreStarted = true;
            delay(1);
        }

        //Check auto cân
        //Chỉ cân tự động sau khi DE hoàn thành
        if(progStep==STP_FCS){
            //Xử lí các tình huống trong khi rang auto
            if(progStatus == STT_PROGRAM_AUTO){
                // Máy KHÔNG có loader ($M62 bit 3 = 0): bỏ qua $M33 — HMI đời cũ đọc ra 1 cũng không vào nhánh
                // loader, không bắn STT_LOADER_FAIL rồi huỷ mẻ trên một máy không có bộ hút liệu nào.
                if(optLoader() && autoLoader_R == 1 && aLoaderStep == 0 && loop_R>1){
                    if(!optScale()){
                        // Loader KHÔNG cân: hút đúng feederSet_R giây (đồng hồ "Auto close feeder" bên dưới
                        // tắt và báo xong). Chưa cài số giây thì không biết hút bao lâu ⇒ báo lỗi, không hút mù.
                        if(feederSet_R > 0){
                            setMachineStatus(STT_LOADER_RUNNING); aLoaderStep = STP_ON_LOADER;
                        }else{
                            setMachineStatus(STT_LOADER_FAIL); aLoaderStep = STP_FAIL_LOADER;
                        }
                    }else
                    //Loader CÓ cân: chỉ cho auto cân khi phễu nguồn còn ≥ LOADER_MIN_BATCH_PCT% của 1 mẻ (LOADER_MIN_NETW ×10 kg)
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

        /* Check drop
           ⛔ R2 LỚP 2 (2026-07-30): hạ cổng từ STP_YELLOW xuống STP_CHARGE. Auto-drop
           theo nhiệt là CHỐT AN TOÀN CUỐI — nó phải đúng bất kể máy có bắt được mốc hay
           không. Gác ở STP_YELLOW nghĩa là một lỗi bắt mốc (xem lớp 1) làm mất luôn khả
           năng tự xả → cháy mẻ. Về lý thuyết BT không thể tới DROP_PRO_R trước khi qua
           DE/FCs nên nới cổng này không đổi hành vi mẻ bình thường. */
        if(progStep>=STP_CHARGE){
            /* ⛔ R7 (2026-07-30): CỔNG "ĐÃ CÓ HẠT TRONG LỒNG"
               Lớp 2 của R2 hạ cổng khối này xuống STP_CHARGE — nhưng STP_CHARGE là bước
               CHỜ THỢ NẠP, lồng đang ở nhiệt nạp mà hạt CHƯA vào. Auto-drop chỉ xét nhiệt
               nên nó mở cửa xả khi lồng còn trống. Bung ở 3 ca thật:
                 · hồ sơ ca cao xả THẤP HƠN nhiệt nạp (nạp 180 / xả 150)
                 · charge tay giữ nóng tới 220 °C
                 · ngay sau khi nạp, BT chưa kịp tụt (nạp 200 / xả 195) → mất trắng mẻ
               Lý lẽ cũ "BT không thể tới DROP_PRO_R trước khi qua DE/FCs" chỉ đúng khi
               nhiệt xả cao hơn nhiệt nạp — SAI với rang nhẹ.
               timeRoastEn bật đúng lúc bấm nạp và tắt lúc xả/huỷ nên nó là cờ "đang có hạt"
               chính xác hơn progStep. Chặn thêm DROP_MIN_SEC phòng hồ sơ xả thấp hơn nạp.
               KHÔNG gác nhánh xả TAY bên dưới — thợ phải bấm xả được mọi lúc. */
            bool batchRunning = (timeRoastEn == 1 && timeRoast > autoDropMinSec());

            //Xử lí các tình huống trong khi rang auto
            if(progStatus == STT_PROGRAM_AUTO && batchRunning){
                //Phát hiện auto drop khi rang auto
                if(Temperature_BT>=dropTempTarget() && progStep<STP_LOOP_1){
                    setMachineStatus(STT_ROAST_DROP); nodeHMI.writeSingleRegister(DROP_BTN_W-1, 1); //Turn on drop
                }
                //Tự bật cooling trước khi drop
                if(Temperature_BT>=(dropTempTarget()-preCool_R_CV)&&preCool_R_CV>0){
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

                trendStopLater();   //Turn off trend graph sample sau khi mốc Drop vào đồ thị (roastMarkTask)
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

            /* ⚠ R5 (2026-07-30): huỷ giữa mẻ mà vẫn để lửa cháy là có hạt trong lồng
               tiếp tục ăn nhiệt. Áp ĐÚNG luật đã có ở lúc DROP: chỉ tắt gas khi chủ máy
               bật autoOff_R. Ai để autoOff_R = 0 là cố ý muốn giữ nhiệt lồng để can
               thiệp tay — không giành quyền đó của thợ. */
            if(autoOff_R == 1){
                nodeHMI.writeSingleRegister(START_GAS_BTN_W-1, 0);
                gasPercent = 0;
                if(enDebug) SerialComputer.println("Roast cancelled: gas off (autoOff)");
            }
            //Các bước rang về 0
            progStep = 0;       //Program step off
            sdRecCancelEn = 1;  //Huỷ trước khi nạp hạt: bỏ tệp tạm, hồ sơ cũ còn nguyên
            setMachineStatus(STT_ROAST_IDLE);   //21/10/2026: không để mã bước cũ (52/53…) đứng trên HMI sau khi dừng

            //Reset chốt an toàn của mẻ
            gasWaitTiEn = false; gasWaitTi = 0;
            loop2TiEn   = false; loop2Ti   = 0;
            devWarned   = false;

            //Trạng thái auto loader về 0
            aLoaderStep = STP_NONE_LOADER;

            //Trình tự AB về 0 — huỷ mẻ mà để abStep treo là mẻ sau mất buồng đốt khói
            abStep = 0; abUserOff = false; abSeenOn = false;
            abTimerEn = 0; abTimer = 0;

            //Trả gió gas trống về biến trở
            naviSourceGAS = SOURCE_AI_VR; //Đổi source sang VR
            naviSourceDRUM = SOURCE_AI_VR;
            naviSourceAIR = SOURCE_AI_VR;
#if MACHINE_HAS_VACUUM_SENSOR
            vacuumSetFlag_R = roastVacFlagSaved;  // khôi phục vacuum PID về trạng thái trước rang
            nodeHMI.writeSingleRegister(vacuumSetFlag_W + 2000, vacuumSetFlag_R);
#endif

            trendStopCancel();
            setTrendSample(0);  //Turn off trend graph sample
            nodeHMI.writeSingleCoil(LOCK_BUTTON_W-1, 0);  //Mở khoá select
            STEP_STRING = "NONE";
        }
        // 14/10/2026: mẻ ĐANG LƯU hồ sơ vượt PROFILE_MAX_SECONDS mà chưa xả -> báo 1 lần / mẻ. File SD vẫn ghi đủ, nhưng lúc
        // nạp lại để rang AUTO phần sau giới hạn bị bỏ, điểm Xả mất -> AUTO không tự xả theo hồ sơ này (thợ xả tay).
        {
            static bool daBaoQuaDai = false;
            if(progStep < STP_CHARGE) daBaoQuaDai = false;
            else if(!daBaoQuaDai && progStatus == STT_PROGRAM_SAVE && progStep < STP_DROP && timeRoast >= PROFILE_MAX_SECONDS){
                daBaoQuaDai = true;
                setMachineStatus(STT_ROAST_PROFILE_TOO_LONG);
            }
        }
        //Tự động bật afterburner — chỉ máy CÓ buồng đốt khói ($M62 bit 9)
        if(optAfterburner() && afterburnerSet_R_CV>0 && timeRoast>60 && progStep>=STP_TP && progStep<STP_LOOP_1){
            STEP_AB_STRING = "WABHU"; //Wait AB heatup
            //Người dùng tự bật AB lên lại bằng tay → bỏ chốt, nhận lại quyền tự đóng lúc drop
            if(abUserOff && AB_BTN_R == 1){
                abUserOff = false; abSeenOn = true; abStep = STP_WAIT_AB;
            }
            //Kiểm tra nhiệt và trạng thái trình tự AB
            if(Temperature_BT>=afterburnerSet_R_CV && abStep==0 && !abUserOff){
                abStep = STP_ON_AB;
                abSeenOn = false;   //chờ HMI xác nhận bật thật rồi mới nhận lệnh tắt tay
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
    if (optScale()) loaderAdapt();   // Vòng tự học dif: chờ cân ổn định sau cắt → chỉnh feederTkg
#endif

    // Tự động cập nhật cân sau 10 giây nếu không có dữ liệu từ Bluetooth (chỉ máy CÓ cân — máy không cân
    // thì không bao giờ có dữ liệu, nhánh này sẽ đánh hỏng mọi lần hút theo giây)
    if (optScale() && updateNetWTi >= 5 && SerialBluetooth.available() == 0) {
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
#if FEEDER_DIF_MANUAL
    // dif THỦ CÔNG: bỏ qua giá trị vừa tra ở trên (qw/qr10/ci vẫn tính để in log đối chiếu).
    // Đường thẳng theo cỡ mẻ ĐẶT TRÊN HMI (netWTG_R, ×10 kg) — hằng số suốt mẻ, không dao
    // động theo ror, nên ngưỡng cắt vẫn đứng yên như bản dif số cứng.
    // coastBase100 là biến RAM TỰ HỌC sau mỗi mẻ (xem loaderAdapt) → một firmware chạy
    // được cả máy xi lanh khí lẫn xi lanh điện, không cần hiệu chuẩn tay.
    dif100 = (int32_t)coastBase100
           + (int32_t)netWTG_R * FEEDER_COAST_PER_KG / 100;   // set(kg)×PER_KG/1000, netWTG_R đã ×10
#endif
    if (dif100 > (int32_t)FEEDER_DIF_MAX * 10) dif100 = (int32_t)FEEDER_DIF_MAX * 10;
    if (dif100 < 0) dif100 = 0;
#endif
    dif = (int16_t)(dif100 / 10); // bản ×10 để tham chiếu/hiển thị

    // Tự động tắt feeder dựa trên trọng lượng và trạng thái nút FEEDER
    if (optScale() && FEEDER_BTN_R == 1 && netWTG_R > 0 && scaleDataValid) { // Nếu nút FEEDER đang bật và có trọng lượng mục tiêu
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
    if(FEEDER_BTN_R == 1 && (enDebug || LOADER_DEBUG_EN)){   // enDebug toàn cục HOẶC cờ log loader riêng
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
        SerialComputer.print(" base=");    SerialComputer.print(coastBase100);  // base coast dang tu hoc (x100 kg)
        SerialComputer.print(" thr=");     SerialComputer.print(thr);
        SerialComputer.print(" wS=");      SerialComputer.print(adaptStartW100);
        SerialComputer.print(" ph=");      SerialComputer.print(loaderAdaptPhase);
        SerialComputer.print(" arm=");     SerialComputer.print(adaptArmed);
        SerialComputer.print(" stp=");     SerialComputer.print(aLoaderStep);
        SerialComputer.print(" cfg=");     SerialComputer.print(cfgCount);
        // Ô lưới đang dùng: qw=cân snap (kg), qr10=ror snap (×10 kg/phút), ci=chỉ số ô (-1 = dùng công thức)
        SerialComputer.print(" qw=");      SerialComputer.print(qw);
        SerialComputer.print(" qr=");      SerialComputer.print(qr10);
        SerialComputer.print(" ci=");      SerialComputer.println(ci);
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
        // Trong chương trình auto: máy CÓ cân mà hết giờ chưa đạt khối lượng = LỖI;
        // máy KHÔNG cân thì hết giờ chính là NẠP XONG (nạp theo thời gian).
        if(aLoaderStep==STP_WAIT_LOADER){
            if(optScale()){
                setMachineStatus(STT_LOADER_FAIL);
                aLoaderStep = STP_FAIL_LOADER;
            }else{
                setMachineStatus(STT_LOADER_OK);
                aLoaderStep = STP_OK_LOADER;
            }
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
        // Máy khuấy chạy relay riêng ($M62 bit 11): hủy cooling thì tắt mixer theo.
        if (optCoolSplit()) nodeHMI.writeSingleRegister(MIXER_BTN_W-1, 0);
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

    /* Escape mở BẰNG TAY ở chế độ "chỉ làm mát" ($M53 autoEscape == 0).
       Chuỗi cooling không mở escape nữa nên không ai bật escapeTimerEn ⇒ cửa xy-lanh
       nằm mở tới khi thợ nhớ ra. Mọi xy-lanh khác đều có timer tự đóng, cửa escape
       không được là ngoại lệ. Xả tay chậm hơn xả tự động nên cộng ESCAPE_MANUAL_EXTRA_SEC.

       Hai cái gác, đừng bỏ:
       • PC_CONTROL_BTN_R == 0 — lúc app lái máy thì khối PC bên dưới lo escape.
       • coolStep != COOL_STEP_ESCAPE_OFF — phòng thợ gạt $M53 giữa chuỗi xả tự động;
         hai nơi cùng đụng escapeTimer là chuỗi cooling không thoát (bài học R6).

       escManualDone: sau khi tự đóng phải CHỜ nút nhả (ESCAPE_BTN_R về 0) mới cho đếm
       lại. Không có nó thì HMI chưa kịp hạ cờ là firmware thấy R==1 → bật timer lại →
       cứ mỗi manualEscapeSec giây lại bắn một lệnh đóng. */
    {
        static bool escManualArmed = false;  //escapeTimer hiện do KHỐI NÀY giữ
        static bool escManualDone  = false;  //đã tự đóng, chờ nút nhả mới đếm lại

        const bool escManualMode = (!autoEscapeEnabled() && PC_CONTROL_BTN_R==0 &&
                                    coolStep!=COOL_STEP_ESCAPE_OFF);

        if(!escManualMode){
            /* Rời chế độ GIỮA CHỪNG: thợ gạt $M53 về 0, bật PC control, hoặc chuỗi xả
               tự động vừa giành lấy escape. Timer nào khối này đang giữ phải NHẢ VỀ 0.
               Để treo là hỏng mẻ SAU: escapeTimerEn còn bật với escapeTimer lớn thì lần
               mở escape kế tiếp vừa mở đã thấy "quá giờ" và đóng ngay, cà phê không kịp
               thoát khỏi khay nguội. */
            if(escManualArmed){
                escapeTimerEn = 0;
                escapeTimer = 0;
                escManualArmed = false;
                if(enDebug) SerialComputer.println("Manual escape: auto-close released");
                //Rời chế độ: thợ gạt $M53 về 1, bật PC control, hoặc chuỗi tự động giành escape
            }
            escManualDone = false;
        }else{
            const int16_t manualEscapeSec = escapeDuration_R + manualEscapeExtraSec();

            if(ESCAPE_BTN_R==0) escManualDone = false;   //Nút đã nhả, cho phép đếm mẻ xả sau

            //Thợ vừa mở cửa bằng tay → bắt đầu đếm giờ tự đóng
            if(ESCAPE_BTN_R==1 && escapeTimerEn==0 && !escManualDone){
                escapeTimer = 0;
                escapeTimerEn = 1;
                escManualArmed = true;
                if(enDebug) SerialComputer.println("Manual escape: auto-close armed");
            }
            //Còi báo trước 5 giây — tay thợ có thể còn trong cửa
            if(escManualArmed && escapeTimer>=(manualEscapeSec-5)){
                buzzerTimerEn = 1;
            }
            //Huỷ khi thợ tự đóng cửa trước (xét TRƯỚC nhánh hết giờ, thợ luôn thắng máy)
            if(escManualArmed && ESCAPE_BTN_R==0 && escapeTimer>=1){
                escapeTimerEn = 0;
                escapeTimer = 0;
                escManualArmed = false;
            }
            //Hết giờ → đóng cửa
            else if(escManualArmed && escapeTimer>=manualEscapeSec){
                nodeHMI.writeSingleRegister(ESCAPE_BTN_W-1, 0);  //Turn off escape
                setMachineStatus(STT_EVENT_ESCAPE_CLOSED);
                escapeTimerEn = 0;
                escapeTimer = 0;
                escManualArmed = false;
                escManualDone = true;   //Chờ nút nhả rồi mới đếm lại
                buzzerTimerEn = 1;
                delay(1);
            }
        }
    }

    /* ⛔ R6 (2026-07-30): khối escape này chỉ dành cho lúc APP/PC mở escape ngoài chuỗi
       làm mát. Thêm điều kiện coolStep==0 vì khi chuỗi COOL_STEP_ESCAPE_OFF đang chạy thì
       CHÍNH NÓ lo đóng escape; hai khối cùng reset escapeTimer là chuỗi cooling có thể
       không bao giờ thoát. Một việc, một chỗ chịu trách nhiệm. */
    if(PC_CONTROL_BTN_R==1 && coolStep==0){
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
            if(AB_BTN_R == 1) abSeenOn = true;   //đọc ngược từ HMI: AB đã bật thật

            /* NGƯỜI DÙNG CƯỠNG CHẾ TẮT AB (sửa 2026-08-26)
               Trước đây nhánh này còn đòi dropTimerEn==1, tức CHỈ dọn được khi đang ở
               đúng lúc drop. Mà AB tự bật từ sau TP — tắt lúc đó thì điều kiện không bao
               giờ đúng, abStep kẹt ở STP_WAIT_AB. Kẹt rồi thì mẻ SAU không tự bật AB nữa
               (nhánh tự bật đòi abStep==0), im lặng, không mã lỗi nào.
               Nay tắt lúc nào dọn lúc đó. Phải chốt abUserOff kèm theo: BT vẫn đang trên
               ngưỡng nên chỉ dọn abStep về 0 là vòng quét sau máy bật AB lại ngay, giành
               nút với người đang đứng máy. */
            if(AB_BTN_R == 0 && abSeenOn){
                abTimerEn = 0; //Tắt timer
                abTimer = 0;   //Reset counter 
                abStep = 0; //Reset bước
                abUserOff = true;   //chốt: không tự bật lại trong mẻ này
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
            // Khuấy relay riêng ($M62 bit 11) thì bật mixer riêng; đấu chung thì cooling bật là mixer bật theo.
            if (optCoolSplit()) nodeHMI.writeSingleRegister(MIXER_BTN_W-1, 1);
            coolTimer = 0;
            coolTimerEn = 1; //Enable drop timer auto close count;
            coolStep = COOL_STEP_ESCAPE_ON; //Next to check escape on
        
        break;  

        case COOL_STEP_ESCAPE_ON: {
            /* $M53 autoEscape_R (xem autoEscapeEnabled): 1 = chuỗi đầy đủ (destoner +
               escape) như từ trước tới nay, 0 = CHỈ LÀM MÁT — thổi đủ coolTimer_R giây
               rồi tắt bồn nguội, không tự bật tách đá, không tự mở cửa escape; thợ xả tay. */
            // Một biểu thức DUY NHẤT cho cả bước: HMI/app ghi rác (2, 255…) vào $M53 thì
            // vẫn rơi gọn về một trong hai hành vi, không sinh trạng thái lai
            // (bỏ destoner nhưng vẫn mở escape).
            const bool coolOnly = !autoEscapeEnabled();
            STEP_COOLING_STRING = coolOnly ? "ONLYCOOL" : "WAESCAPE";
            //Call buzzer before escape run
            if(coolTimer>=(coolTimer_R-5)){
                buzzerTimerEn = 1; //Call buzzer
            }
            //Bật trước destoner — bỏ qua khi thợ chọn chỉ làm mát, hoặc máy KHÔNG có tách đá ($M62 bit 10)
            if(!coolOnly && optDestoner() && destonerSet_R>0){
                STEP_COOLING_STRING = "WAESDES";
                if(coolTimer>=(coolTimer_R-destonerPre_R)){
                    destonerTimerEn = 1; //Turn on destoner timer
                    setMachineStatus(STT_DESTONER_ON); nodeHMI.writeSingleRegister(DESTONER_BTN_W-1, 1);  //Turn on destoner button
                    delay(1);
                }
            }
            //Wait to cooling complete
            if(coolTimer>=coolTimer_R){
                if(coolOnly){
                    //Chỉ làm mát: hết giờ thì tắt bồn nguội, KHÔNG mở escape
                    STEP_COOLING_STRING = "OFFCO";
                    nodeHMI.writeSingleRegister(COOLING_BTN_W-1, 0);  // Tắt cooling
                    if (optCoolSplit()) nodeHMI.writeSingleRegister(MIXER_BTN_W-1, 0);  // Tắt mixer riêng
                    setMachineStatus(STT_ACT_COOLING_OFF);
                    coolTimerEn = 0; //Turn off cool timer
                    coolTimer = 0;
                    buzzerTimerEn = 1; //Call buzzer báo thợ ra xả tay
                    coolStep = 0; //Turn off cooling program
                    delay(1);
                }else{
                    STEP_COOLING_STRING = "ONES";
                    setMachineStatus(STT_ROAST_ESCAPE);
                    nodeHMI.writeSingleRegister(ESCAPE_BTN_W-1, 1);  //Turn on escape
                    escapeTimer = 0;    //Bộ đếm PHẢI về 0 tại đây: đường nào đó bỏ timer
                                        //treo là mẻ này vừa mở escape đã bị đóng ngay
                    escapeTimerEn = 1;  //Enable escape timer auto close count;
                    setMachineStatus(STT_EVENT_ESCAPE_OPENED);
                    delay(1);
                    coolStep = COOL_STEP_ESCAPE_OFF; //Next to check escape off
                }
            }

        } break;
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
                if (optCoolSplit()) nodeHMI.writeSingleRegister(MIXER_BTN_W-1, 0);  // Tắt mixer riêng (đấu chung: tắt theo cooling)
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
























































