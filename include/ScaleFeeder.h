String cumuStr = "";
boolean sCumu = false;
uint8_t cumuLen = 0;
int  netW_int, netW_dec, netW;

void ConfigScale(){

}

//Hàm xoá khoảng trắng
void delBlank(char s[], int len){
    for(int i=0;i<len;i++){
        if(s[i]==' '){
            for(int j=i;j<len;j++){
                s[j] = s[j+1];
            }
            i--;
        }
    }
}


//Sample: ST,GS,    -5.3,kg
void readScale(){
    // timeLoaderMillis = millis();
    // SerialComputer.println("run scale");
    while(SerialBluetooth.available()){
        char inChar = (char)SerialBluetooth.read(); //Đọc từng Char
        // SerialComputer.print(inChar); //Debug
        // if(inChar=='\r')    SerialComputer.print(""); //Debug

        //Kiểm tra chữ cái đầu
        if(inChar=='G'){
            sCumu = true;
            // SerialComputer.println("4");
        }
        //Cộng String
        if(sCumu){
            cumuStr += inChar;
            // SerialComputer.println("5");
        }
        //Kiểm tra kí tự cuối, in chuỗi
        if((inChar=='\r')&&(sCumu==true)){
            // SerialComputer.println(cumuStr); 
            // SerialComputer.println("6");
            cumuLen = cumuStr.length(); //Đếm số lượng kí tự
            char cumuChar[cumuLen];     //Tạo array
            cumuStr.toCharArray(cumuChar, cumuLen); //Đổi từ Str sang Array
            //GS,    61.7,kg
            if(cumuLen<=16 && cumuChar[0]=='G' && cumuChar[1]=='S' && cumuChar[11]==',' && cumuChar[12]=='k' && cumuChar[13]=='g'){
                //Xoá khoảng trắng
                for(int i=0;i<cumuLen;i++){
                    if(cumuChar[i]==' '){
                        for(int j=i;j<cumuLen;j++){
                            cumuChar[j] = cumuChar[j+1];
                        }
                        i--;
                    }
                }
                // SerialComputer.println("7");
                // SerialComputer.printf("%s %d\n", cumuChar,strlen(cumuChar)); //Debug

                //GS,-123.9,kg
                //GS,     0.0,kg<CR><LF>
                //GS,    -2.0,kg
                //%[^\t\n]
                // //%[^\t\n]
                //GS,-3.8,kg

                //Tách số
                sscanf(cumuChar,"GS,%d.%d,kg", &netW_int, &netW_dec); //Debug
                if(netW_int>=0)  netW = netW_int*10+netW_dec;
                if(netW_int<0)  netW = netW_int*10-netW_dec;
                // SerialComputer.printf("%d\n", netW); //Debug
            }
            cumuLen = 0;
            sCumu = false;
            cumuStr = "";  
        }
    }
    // loaderCalTime = millis() - timeLoaderMillis;
}
