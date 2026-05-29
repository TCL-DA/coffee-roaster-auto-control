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
#define vacuumC_show_artisan        21
#define vacuumC_artisan_W           22

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

uint32_t artisanModbusBaud(){
    return (modbusBaud_R > 0) ? (uint32_t)modbusBaud_R : ARTISAN_MODBUS_BAUD_DEFAULT;
}

uint8_t artisanModbusID(){
    return (modbusID_R > 0) ? (uint8_t)modbusID_R : ARTISAN_MODBUS_SLAVE_ID_DEFAULT;
}

void ModbusSlaveConfig(){
    uint32_t baud = artisanModbusBaud();
    if(swSignal==0){
        SerialBluetooth.begin(baud);
        mbs.begin(&SerialBluetooth);
    }else{
        SerialComputer.begin(baud);
        mbs.begin(&SerialComputer);
    }
    mbs.slave(artisanModbusID());

    for(int i=0; i<MaxReg; i++){
        mbs.addHreg(i);
    }
    SerialComputer.println("=> Modbus Slave RTU OK");
}


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
    bool autoSourceActive =
        (naviSourceGAS  == SOURCE_AI_AUTO) ||
        (naviSourceAIR  == SOURCE_AI_AUTO) ||
        (naviSourceDRUM == SOURCE_AI_AUTO);
#ifdef SOURCE_AI_VR_FROM_HMI
    bool manualSetpointTwoWay =
        !autoSourceActive;
#else
    bool manualSetpointTwoWay = false;
#endif

    // ── Khởi tạo lại Modbus Slave khi baudrate/ID thay đổi ──────
    if (idBaudSetEn) {
        uint32_t baud = artisanModbusBaud();
        if(swSignal==0){
            SerialBluetooth.begin(baud);
            mbs.begin(&SerialBluetooth);
            SerialComputer.println("Switched to Serial Bluetooth for Modbus");
        }else{
            SerialComputer.begin(baud);
            SerialBluetooth.begin(SCALE_SERIAL_BAUD);
            mbs.begin(&SerialComputer);
            SerialComputer.println("Switched to Serial Computer for Modbus");
        }
        mbs.slave(artisanModbusID());
        idBaudSetEn = 0;
    }

    if(swSignalFallingEdge()){
        SerialBluetooth.begin(artisanModbusBaud());
        mbs.begin(&SerialBluetooth);
        SerialComputer.println("Switched to Serial Bluetooth for Modbus");
    }

    if(swSignalRisingEdge()){
        SerialComputer.begin(artisanModbusBaud());
        SerialBluetooth.begin(SCALE_SERIAL_BAUD);
        mbs.begin(&SerialComputer);
        SerialComputer.println("Switched to Serial Computer for Modbus");
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
    
    // ── Đồng bộ setpoint từ máy rang lên Artisan ────────────────
    // Chỉ cập nhật khi KHÔNG dùng nguồn điều khiển từ PC (AI_PC)
    if (naviSourceGAS != SOURCE_AI_PC && !manualSetpointTwoWay) {
        mbs.Hreg(AIR_artisan_W,  airflowPercent);
        mbs.Hreg(GAS_artisan_W,  gasPercent);
        mbs.Hreg(DRUM_artisan_W, drumPercent);
        mbs.Hreg(SV_artisan_W,   SV_BT);
        mbs.Hreg(vacuumC_artisan_W,   vacuumSetpoint_R);
    }

    // ── Đọc setpoint từ Artisan ──────────────────────────────────
    airflowPC = mbs.Hreg(AIR_artisan_W);
    gasPC     = mbs.Hreg(GAS_artisan_W);
    drumPC    = mbs.Hreg(DRUM_artisan_W);
    svPC_CP   = mbs.Hreg(SV_artisan_W);
    underSV_CP = mbs.Hreg(vacuumC_artisan_W);

    // Cập nhật SV, giới hạn tối đa 300°C (đơn vị ×10 = 3000)
    if (svPC != svPC_CP) {
        svPC = svPC_CP;
        if (svPC > 300 * 10) svPC = 300 * 10;
    }

    // Cập nhật SV
    if (underSV_PC != underSV_CP) {
        underSV_PC = underSV_CP;
        if(underSV_PC > 250) underSV_PC = 250;   // Giới hạn áp suất âm tối đa -250 Pa
        if(underSV_PC < 90) underSV_PC = 90;   // Giới hạn áp suất âm tối thiểu -80 Pa
    }

#ifdef SOURCE_AI_VR_FROM_HMI
    // ── SOURCE_AI_VR_FROM_HMI, không AUTO: sync setpoint hai chiều HMI ↔ Artisan
    // Nếu hai bên cùng đổi trong một vòng lặp, PC_CONTROL quyết định bên ưu tiên.
    static bool setpointSyncInit = false;
    static int16_t lastHmiAir = 0, lastHmiGas = 0, lastHmiDrum = 0, lastHmiVac = 0;
    static int16_t lastPcAir  = 0, lastPcGas  = 0, lastPcDrum  = 0, lastPcVac  = 0;

    if (!setpointSyncInit) {
        lastHmiAir  = airSpeed_R;
        lastHmiGas  = burnerValue_R;
        lastHmiDrum = drumSpeed_R;
        lastHmiVac  = vacuumSetpoint_R;
        lastPcAir   = airflowPC;
        lastPcGas   = gasPC;
        lastPcDrum  = drumPC;
        lastPcVac   = underSV_PC;
        setpointSyncInit = true;
    }

    if (manualSetpointTwoWay) {
        bool hmiAirChanged  = (airSpeed_R != lastHmiAir);
        bool hmiGasChanged  = (burnerValue_R != lastHmiGas);
        bool hmiDrumChanged = (drumSpeed_R != lastHmiDrum);
        bool hmiVacChanged  = (vacuumSetpoint_R != lastHmiVac);

        bool pcAirChanged   = (airflowPC != lastPcAir);
        bool pcGasChanged   = (gasPC != lastPcGas);
        bool pcDrumChanged  = (drumPC != lastPcDrum);
        bool pcVacChanged   = (underSV_PC != lastPcVac);

        if (hmiAirChanged && (!pcAirChanged || PC_CONTROL_BTN_R == 0)) {
            airflowPC = constrain(airSpeed_R, 0, 100);
            mbs.Hreg(AIR_artisan_W, airflowPC);
        } else if (pcAirChanged) {
            airflowPC = constrain(airflowPC, 0, 100);
            airSpeed_R = airflowPC;
            airSpeed_R_CP = airflowPC;
            airflowPercent = airflowPC;
            nodeHMI.writeSingleRegister(airSpeed_W + 2000, airflowPC);
        }

        if (MACHINE_HAS_GAS_CONTROL) {
            if (hmiGasChanged && (!pcGasChanged || PC_CONTROL_BTN_R == 0)) {
                gasPC = constrain(burnerValue_R, 0, 100);
                mbs.Hreg(GAS_artisan_W, gasPC);
            } else if (pcGasChanged) {
                gasPC = constrain(gasPC, 0, 100);
                burnerValue_R = gasPC;
                burnerValue_R_CP = gasPC;
                gasPercent = gasPC;
                nodeHMI.writeSingleRegister(burnerValue_W + 2000, gasPC);
            }
        }

        if (MACHINE_HAS_DRUM_SPEED_CONTROL) {
            if (hmiDrumChanged && (!pcDrumChanged || PC_CONTROL_BTN_R == 0)) {
                drumPC = constrain(drumSpeed_R, 0, 100);
                mbs.Hreg(DRUM_artisan_W, drumPC);
            } else if (pcDrumChanged) {
                drumPC = constrain(drumPC, 0, 100);
                drumSpeed_R = drumPC;
                drumSpeed_R_CP = drumPC;
                drumPercent = drumPC;
                nodeHMI.writeSingleRegister(drumSpeed_W + 2000, drumPC);
            }
        }

        if (MACHINE_HAS_VACUUM_SENSOR) {
            if (hmiVacChanged && (!pcVacChanged || PC_CONTROL_BTN_R == 0)) {
                underSV_PC = vacuumSetpoint_R;
                if (underSV_PC > 250) underSV_PC = 250;
                if (underSV_PC < 90)  underSV_PC = 90;
                mbs.Hreg(vacuumC_artisan_W, underSV_PC);
            } else if (pcVacChanged) {
                vacuumSetpoint_R = underSV_PC;
                vacuumSetpoint_R_CP = underSV_PC;
                nodeHMI.writeSingleRegister(vacuumSetpoint_W + 2000, underSV_PC);
                pidAirflowReset();
            }
        }
    }

    lastHmiAir  = airSpeed_R;
    lastHmiGas  = burnerValue_R;
    lastHmiDrum = drumSpeed_R;
    lastHmiVac  = vacuumSetpoint_R;
    lastPcAir   = airflowPC;
    lastPcGas   = gasPC;
    lastPcDrum  = drumPC;
    lastPcVac   = underSV_PC;
#endif

    // ── Chế độ PC_CONTROL: Artisan điều khiển HMI ───────────────
    if (PC_CONTROL_BTN_R == 1) {

        // Đọc các nút nhấn ảo từ Artisan
        Ignition_btn_PC_CP = mbs.Hreg(IGNITION_artisan_W);
        Charge_btn_PC_CP   = mbs.Hreg(CHARGE_artisan_W);
        Drop_btn_PC_CP     = mbs.Hreg(DROP_artisan_W);
        Escape_btn_PC_CP   = mbs.Hreg(ESCAPE_artisan_W);
        MiCool_btn_PC_CP   = mbs.Hreg(MI_COOL_artisan_W);
        Start_btn_PC_CP    = mbs.Hreg(START_artisan_W);

        if (!manualSetpointTwoWay && !autoSourceActive) {
            // Sync Air/Gas/Drum setpoints from Artisan to HMI $M34-$M36
            if (MACHINE_HAS_DRUM_SPEED_CONTROL && drumPC != drumSpeed_R_CP) {
                drumPercent = drumPC;
                nodeHMI.writeSingleRegister(drumSpeed_W + 2000, drumPercent);
            }

            if (airflowPC != airSpeed_R_CP) {
                airflowPercent = airflowPC;
                nodeHMI.writeSingleRegister(airSpeed_W + 2000, airflowPercent);
            }

            if (MACHINE_HAS_GAS_CONTROL && gasPC != burnerValue_R_CP) {
                gasPercent = gasPC;
                nodeHMI.writeSingleRegister(burnerValue_W + 2000, gasPercent);
            }
        }

        // Đồng bộ SV từ Artisan sang HMI
        if (svPC != btSV_R)
            nodeHMI.writeSingleRegister(btSV_W + 2000, svPC / 10);



        // Đồng bộ underSV từ Artisan sang HMI
        if (!manualSetpointTwoWay && !autoSourceActive && MACHINE_HAS_VACUUM_SENSOR && underSV_PC != vacuumSetpoint_R)
            nodeHMI.writeSingleRegister(vacuumSetpoint_W + 2000, underSV_PC);

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
