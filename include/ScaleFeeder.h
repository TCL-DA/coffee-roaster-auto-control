char scaleFrame[24];
uint8_t scaleFramePos = 0;
bool scaleFrameActive = false;
bool scaleDataValid = false;
int netW_int, netW_dec, netW;

void ConfigScale(){

}

// Đọc phần số của frame cân và đổi sang đơn vị x10 kg.
static bool parseScaleWeight10(const char *start, const char *end, int *outValue){
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

    int dec = 0;
    if(start < end && *start == '.'){
        start++;
        if(start < end && *start >= '0' && *start <= '9'){
            dec = *start - '0';
            start++;
        }
    }

    while(start < end && *start == ' ') start++;
    if(!hasDigit || start != end) return false;

    *outValue = sign * ((whole * 10) + dec);
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
                if(parseScaleWeight10(scaleFrame + 3, kgPtr, &parsedNetW)){
                    netW = parsedNetW;
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
