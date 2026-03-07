#define SLAVE_ID 1  //Slave id
#define MaxReg 27

//Register
#define BT_show_artisan             0
#define ET_show_artisan             1

#define AIRshow_artisan             2
#define GAS_show_artisan            3
#define DRUM_show_artisan           4

#define CHAMBER_show_artisan        5
#define CYCLONE_show_artisan        6
#define AIR_BURNER_show_artisan     7
#define COOLING_show_artisan        8
#define UNDER_show_artisan          9

#define AIR_artisan_W               10
#define GAS_artisan_W               11
#define DRUM_artisan_W              20
#define UNDER_artisan_W             21

//HMI Button control
#define IGNITION_artisan_W          12
#define CHARGE_artisan_W            14
#define DROP_artisan_W              15
#define ESCAPE_artisan_W            16
#define MI_COOL_artisan_W           13
#define START_artisan_W             17 

#define SV_artisan_W                18
#define SV_show_artisan             19

 


ModbusRTU mbs;   

void ModbusSlaveConfig(){
    SerialComputer.begin(modbusBaud_R); 
    mbs.begin(&SerialComputer);
    mbs.slave(modbusID_R);

    for(int i=0; i<MaxReg; i++){
        mbs.addHreg(i);
    }
    SerialComputer.println("=> Modbus Slave RTU OK");
}

// void handle_Modbus_Slave(){
//     if(idBaudSetEn){
//         SerialComputer.begin(modbusBaud_R); 
//         mbs.begin(&SerialComputer);
//         mbs.slave(modbusID_R);  
//         idBaudSetEn = 0;  
//     }
//     //Set value register
//     mbs.Hreg(BT_show_artisan, Temperature_BT);  //Gán giá trị BT vào modbus slave
//     mbs.Hreg(ET_show_artisan, Temperature_ET);  //Gán giá trị ET vào modbus slave

//     mbs.Hreg(AIRshow_artisan, airflowPercent);  //Gán giá trị airflow vào modbus slave
//     mbs.Hreg(GAS_show_artisan, gasPercent);     //Gán giá trị gas vào modbus slave
//     mbs.Hreg(DRUM_show_artisan, drumPercent);   //Gán giá trị drum vào modbus slave
//     mbs.Hreg(SV_show_artisan, SV_BT);           //Gán giá trị sv vào modbus slave
    
//     mbs.Hreg(START_artisan_W, START_BTN_R);     //Gán giá trị start vào modbus slave

//     //Auto cập nhật data modbus
//     if(naviSourceGAS!=SOURCE_AI_PC){
//         mbs.Hreg(AIR_artisan_W, airflowPercent); 
//         mbs.Hreg(GAS_artisan_W, gasPercent);
//         mbs.Hreg(DRUM_artisan_W, drumPercent);
//         mbs.Hreg(SV_artisan_W, SV_BT);    
//     }

//     airflowPC = mbs.Hreg(AIR_artisan_W);
//     gasPC = mbs.Hreg(GAS_artisan_W);
//     drumPC = mbs.Hreg(DRUM_artisan_W);
//     svPC_CP = mbs.Hreg(SV_artisan_W);
    

//     //Cập nhập SV
//     if(svPC!=svPC_CP){
//         svPC = svPC_CP;
//         if(svPC>300*10) svPC = 300*10;  //giới hạn SV ở 300 độ C
//     }

//     //Đồng bộ artisan và HMI
//     if(PC_CONTROL_BTN_R==1){
//         Ignition_btn_PC_CP = mbs.Hreg(IGNITION_artisan_W);
//         Charge_btn_PC_CP = mbs.Hreg(CHARGE_artisan_W);
//         Drop_btn_PC_CP = mbs.Hreg(DROP_artisan_W);
//         Escape_btn_PC_CP = mbs.Hreg(ESCAPE_artisan_W);
//         MiCool_btn_PC_CP = mbs.Hreg(MI_COOL_artisan_W);
//         Start_btn_PC_CP = mbs.Hreg(START_artisan_W);

//         if(svPC!=btSV_R){
//             nodeHMI.writeSingleRegister(btSV_W+2000, svPC/10); 
//         }   

//         //Đồng bộ các nút nhấn ảo
//         //Ignition
//         if(Ignition_btn_PC != Ignition_btn_PC_CP){
//             Ignition_btn_PC = Ignition_btn_PC_CP;
//             nodeHMI.writeSingleRegister(START_GAS_BTN_W-1, Ignition_btn_PC);  
//         } 
//         //Charge
//         if(Charge_btn_PC != Charge_btn_PC_CP){
//             Charge_btn_PC = Charge_btn_PC_CP;
//             nodeHMI.writeSingleRegister(CHARGE_BTN_W-1, Charge_btn_PC);
//             //Enable auto close charge
//             chargeTimerEn = 1; 
//             buzzerTimerEn = 1; //Call buzzer
//         }  
//         //Drop
//         if(Drop_btn_PC != Drop_btn_PC_CP){
//             Drop_btn_PC = Drop_btn_PC_CP;
//             nodeHMI.writeSingleRegister(DROP_BTN_W-1, Drop_btn_PC);  
//             dropTimerEn = 1; //Enable drop timer auto close
//             buzzerTimerEn = 1; //Call buzzer
//         }
//         //Escape
//         if(Escape_btn_PC != Escape_btn_PC_CP){
//             Escape_btn_PC = Escape_btn_PC_CP;
//             nodeHMI.writeSingleRegister(ESCAPE_BTN_W-1, Escape_btn_PC);  
//             escapeTimerEn = 1;  //Enable escape timer auto close
//             buzzerTimerEn = 1; //Call buzzer
//         }
//         //Mix&Cool
//         if(MiCool_btn_PC != MiCool_btn_PC_CP){
//             MiCool_btn_PC = MiCool_btn_PC_CP;
//             nodeHMI.writeSingleRegister(COOLING_BTN_W-1, MiCool_btn_PC);  
//         } 
//     }else{
//         mbs.Hreg(IGNITION_artisan_W, 0); 
//         mbs.Hreg(CHARGE_artisan_W, CHARGE_BTN_R);
//         mbs.Hreg(DROP_artisan_W, DROP_BTN_R);    
//         mbs.Hreg(ESCAPE_artisan_W, ESCAPE_BTN_R); 
//         mbs.Hreg(MI_COOL_artisan_W, COOLING_BTN_R); 
//     }
 
//     //test
//     // mbs.Hreg(BTvalue, random(200,250));
//     // mbs.Hreg(ETvalue, random(250,300));
//     // mbs.Hreg(Gasvalue, random(350,450));
//     // mbs.Hreg(Airvalue, random(450,550));
    
//     //Slave holding
//     mbs.task();
//     yield();
// }

// ============================================================
// handle_Modbus_Slave()
// Quản lý giao tiếp Modbus Slave giữa Arduino và Artisan PC
//
// Sơ đồ giao tiếp:
//   Arduino (Slave) ↔ Artisan PC (Master)
//   Arduino         ↔ HMI Delta (đồng bộ nút nhấn, SV)
//
// Có 2 chế độ điều khiển:
//   PC_CONTROL  = 1: Artisan điều khiển máy rang (qua Arduino → HMI)
//   PC_CONTROL  = 0: HMI điều khiển, Artisan chỉ hiển thị dữ liệu
// ============================================================
void handle_Modbus_Slave() {

    // ── Khởi tạo lại Modbus Slave khi baudrate/ID thay đổi ──────
    if (idBaudSetEn) {
        SerialComputer.begin(modbusBaud_R);
        mbs.begin(&SerialComputer);
        mbs.slave(modbusID_R);
        idBaudSetEn = 0;
    }

    // ── Ghi dữ liệu máy rang lên Artisan (Artisan chỉ đọc) ──────
    mbs.Hreg(BT_show_artisan,  Temperature_BT);
    mbs.Hreg(ET_show_artisan,  Temperature_ET);
    mbs.Hreg(AIRshow_artisan,  airflowPercent);
    mbs.Hreg(GAS_show_artisan, gasPercent);
    mbs.Hreg(DRUM_show_artisan,drumPercent);
    mbs.Hreg(SV_show_artisan,  SV_BT);
    mbs.Hreg(START_artisan_W,  START_BTN_R);
    mbs.Hreg(UNDER_show_artisan, Diff_Air);   // Áp suất âm (underpressure)
    mbs.Hreg(UNDER_artisan_W, vacuumSetpoint_R);   // Áp suất âm (underpressure)

    // ── Đồng bộ setpoint từ máy rang lên Artisan ────────────────
    // Chỉ cập nhật khi KHÔNG dùng nguồn điều khiển từ PC (AI_PC)
    if (naviSourceGAS != SOURCE_AI_PC) {
        mbs.Hreg(AIR_artisan_W,  airflowPercent);
        mbs.Hreg(GAS_artisan_W,  gasPercent);
        mbs.Hreg(DRUM_artisan_W, drumPercent);
        mbs.Hreg(SV_artisan_W,   SV_BT);
    }

    // ── Đọc setpoint từ Artisan ──────────────────────────────────
    airflowPC = mbs.Hreg(AIR_artisan_W);
    gasPC     = mbs.Hreg(GAS_artisan_W);
    drumPC    = mbs.Hreg(DRUM_artisan_W);
    svPC_CP   = mbs.Hreg(SV_artisan_W);

    // Cập nhật SV, giới hạn tối đa 300°C (đơn vị ×10 = 3000)
    if (svPC != svPC_CP) {
        svPC = svPC_CP;
        if (svPC > 300 * 10) svPC = 300 * 10;
    }

    // ── Chế độ PC_CONTROL: Artisan điều khiển HMI ───────────────
    if (PC_CONTROL_BTN_R == 1) {

        // Đọc các nút nhấn ảo từ Artisan
        Ignition_btn_PC_CP = mbs.Hreg(IGNITION_artisan_W);
        Charge_btn_PC_CP   = mbs.Hreg(CHARGE_artisan_W);
        Drop_btn_PC_CP     = mbs.Hreg(DROP_artisan_W);
        Escape_btn_PC_CP   = mbs.Hreg(ESCAPE_artisan_W);
        MiCool_btn_PC_CP   = mbs.Hreg(MI_COOL_artisan_W);
        Start_btn_PC_CP    = mbs.Hreg(START_artisan_W);

        // Đồng bộ SV từ Artisan sang HMI
        if (svPC != btSV_R)
            nodeHMI.writeSingleRegister(btSV_W + 2000, svPC / 10);

        // Macro đồng bộ nút nhấn: chỉ ghi HMI khi trạng thái thay đổi
        #define SYNC_BTN(cur, cp, reg) \
            if ((cur) != (cp)) { (cur) = (cp); nodeHMI.writeSingleRegister((reg)-1, (cur)); }

        SYNC_BTN(Ignition_btn_PC, Ignition_btn_PC_CP, START_GAS_BTN_W);
        SYNC_BTN(MiCool_btn_PC,   MiCool_btn_PC_CP,   COOLING_BTN_W);

        // Charge: đồng bộ + bật timer tự đóng + buzzer
        if (Charge_btn_PC != Charge_btn_PC_CP) {
            Charge_btn_PC = Charge_btn_PC_CP;
            nodeHMI.writeSingleRegister(CHARGE_BTN_W - 1, Charge_btn_PC);
            chargeTimerEn = 1;
            buzzerTimerEn = 1;
        }

        // Drop: đồng bộ + bật timer tự đóng + buzzer
        if (Drop_btn_PC != Drop_btn_PC_CP) {
            Drop_btn_PC = Drop_btn_PC_CP;
            nodeHMI.writeSingleRegister(DROP_BTN_W - 1, Drop_btn_PC);
            dropTimerEn   = 1;
            buzzerTimerEn = 1;
        }

        // Escape: đồng bộ + bật timer tự đóng + buzzer
        if (Escape_btn_PC != Escape_btn_PC_CP) {
            Escape_btn_PC = Escape_btn_PC_CP;
            nodeHMI.writeSingleRegister(ESCAPE_BTN_W - 1, Escape_btn_PC);
            escapeTimerEn = 1;
            buzzerTimerEn = 1;
        }

    // ── Chế độ HMI_CONTROL: đồng bộ trạng thái HMI lên Artisan ─
    } else {
        mbs.Hreg(IGNITION_artisan_W, 0);
        mbs.Hreg(CHARGE_artisan_W,   CHARGE_BTN_R);
        mbs.Hreg(DROP_artisan_W,     DROP_BTN_R);
        mbs.Hreg(ESCAPE_artisan_W,   ESCAPE_BTN_R);
        mbs.Hreg(MI_COOL_artisan_W,  COOLING_BTN_R);
    }

    // ── Cập nhật Modbus Slave ────────────────────────────────────
    mbs.task();
    yield();
}