char scaleFrame[24];
uint8_t scaleFramePos = 0;
bool scaleFrameActive = false;
bool scaleDataValid = false;
int netW_int, netW_dec, netW;
/* netW100 — CÙNG số cân nhưng thang ×100 (61,35 kg = 6135).
   PHỤC HỒI 2026-07-30: biến này được dùng ở Program.h (ngưỡng cắt feeder, RoR cân),
   Modbus_Master.h (đẩy HMI) và PC_Link (ô SCALE) nhưng KHÔNG còn khai báo lẫn chỗ gán ở
   đâu — firmware không biên dịch được. Phần "cân ×100" bị mất khỏi file này lúc nào không
   rõ. Auto-loader so ngưỡng cắt ở ×100 nên nếu chỉ khai báo cho qua build mà không gán thì
   netW100 = 0 ≤ ngưỡng → CẮT NGAY khi vừa bật hút, mẻ nào cũng hút thiếu. */
int16_t netW100 = 0;

void ConfigScale(){

}

/* Đọc phần số của frame cân → đơn vị x100 kg (61.35 → 6135).
   Trước đây chỉ lấy MỘT chữ số lẻ (x10); auto-loader cần x100 để ngưỡng cắt không giật
   bậc 0,1 kg (xem ref-loader-autolearn.md). Cân gửi 1 số lẻ thì tự đệm 0: "61.7" → 6170.
   Chữ số lẻ thứ 3 trở đi bị bỏ (làm tròn xuống) chứ không làm hỏng cả khung. */
static bool parseScaleWeight100(const char *start, const char *end, int *outValue){
    while(start < end && *start == ' ') start++;

    int sign = 1;
    if(start < end && *start == '-'){
        sign = -1;
        start++;
    }

    int whole = 0;
    bool hasDigit = false;
    while(start < end && *start >= '0' && *start <= '9'){
        hasDigit = true;
        whole = (whole * 10) + (*start - '0');
        start++;
    }

    int dec = 0, nDec = 0;
    if(start < end && *start == '.'){
        start++;
        while(nDec < 2 && start < end && *start >= '0' && *start <= '9'){
            dec = (dec * 10) + (*start - '0');
            nDec++;
            start++;
        }
        // Chữ số lẻ dư (cân báo 3 số lẻ) → bỏ, đừng để khung bị coi là lỗi
        while(start < end && *start >= '0' && *start <= '9') start++;
    }
    while(nDec < 2){ dec *= 10; nDec++; }   // "61.7" → dec = 70

    while(start < end && *start == ' ') start++;
    if(!hasDigit || start != end) return false;

    *outValue = sign * ((whole * 100) + dec);
    return true;
}

// Đọc dữ liệu cân Bluetooth dạng "GS,    61.7,kg" và lưu netW theo x10 kg.
void readScale(){
    while(SerialBluetooth.available()){
        char inChar = (char)SerialBluetooth.read();

        if(inChar == 'G'){
            scaleFrameActive = true;
            scaleFramePos = 0;
        }

        if(scaleFrameActive){
            if(scaleFramePos < (sizeof(scaleFrame) - 1)){
                scaleFrame[scaleFramePos++] = inChar;
            }else{
                scaleFrameActive = false;
                scaleFramePos = 0;
                scaleDataValid = false;
            }
        }

        if((inChar == '\r' || inChar == '\n') && scaleFrameActive){
            scaleFrameActive = false;
            scaleFrame[scaleFramePos] = '\0';

            char *kgPtr = strstr(scaleFrame, ",kg");
            if(scaleFramePos >= 9 &&
               scaleFrame[0] == 'G' &&
               scaleFrame[1] == 'S' &&
               scaleFrame[2] == ',' &&
               kgPtr != NULL &&
               kgPtr > (scaleFrame + 3))
            {
                int parsedNetW = 0;
                if(parseScaleWeight100(scaleFrame + 3, kgPtr, &parsedNetW)){
                    // netW100 là số gốc ×100; netW giữ ×10 cho feeder/HMI như cũ
                    netW100 = (int16_t)parsedNetW;
                    netW    = parsedNetW / 10;
                    updateNetWTi = 0;
                    scaleDataValid = true;
                }else{
                    scaleDataValid = false;
                }
            }else{
                scaleDataValid = false;
            }

            scaleFramePos = 0;
        }
    }
}
