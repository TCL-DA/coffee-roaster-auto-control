String cumuStr = "";
boolean sCumu = false;
int  netW_int, netW_dec, netW;

void ConfigScale(){

}

// ============================================================
// readScale()
// Đọc dữ liệu cân từ SerialBluetooth, parse chuỗi dạng:
//   GS,    61.7,kg<CR><LF>
//   GS,   -12.3,kg<CR><LF>
//   GS,     0.0,kg<CR><LF>
//
// FIX: Bỏ hard-code index (cumuChar[11]==',') — dễ sai khi
//      số chữ số thay đổi. Thay bằng:
//   1. Kiểm tra prefix "GS," và suffix ",kg" động (indexOf)
//   2. Dùng String.toFloat() để parse, tránh logic riêng
//      cho số âm/dương
//   3. Kết quả nhân x10 để giữ 1 chữ số thập phân dạng int
// ============================================================
void readScale(){
    while(SerialBluetooth.available()){
        char inChar = (char)SerialBluetooth.read();

        // Bắt đầu tích lũy khi gặp 'G'
        if(inChar == 'G'){
            sCumu = true;
            cumuStr = "";
        }

        if(sCumu){
            cumuStr += inChar;
        }

        // Kết thúc frame khi gặp CR hoặc LF
        if((inChar == '\r' || inChar == '\n') && sCumu){
            sCumu = false;

            // Kiểm tra prefix "GS," (tối thiểu 9 ký tự: "GS,0.0,kg")
            if(cumuStr.length() >= 9 &&
               cumuStr.charAt(0) == 'G' &&
               cumuStr.charAt(1) == 'S' &&
               cumuStr.charAt(2) == ',')
            {
                // Tìm ",kg" động — không hard-code index
                int kgIdx = cumuStr.indexOf(",kg");
                if(kgIdx > 3){
                    // Cắt phần số: từ sau "GS," đến trước ",kg"
                    String numStr = cumuStr.substring(3, kgIdx);
                    numStr.trim(); // Xóa khoảng trắng hai đầu

                    // Parse float rồi nhân x10 → int (giữ 1 chữ số thập phân)
                    float val = numStr.toFloat();
                    netW = (int)(val * 10.0f);
                }
            }

            cumuStr = "";
        }
    }
}