// Trả về true đúng 1 lần khi swSignal chuyển 0→1
bool swSignalRisingEdge() {
    static uint8_t prev = 0;
    bool edge = (swSignal == 1 && prev == 0);
    prev = swSignal;
    return edge;
}

// Trả về true đúng 1 lần khi swSignal chuyển 1→0
bool swSignalFallingEdge() {
    static uint8_t prev = 0;
    bool edge = (swSignal == 0 && prev == 1);
    prev = swSignal;
    return edge;
}

void controlIO(){
    gasSignal = !READ_CH1;  // FIX: was 2 lines (read then overwrite with NOT), collapsed to 1
    swSignal = !READ_SWITCH_1;

    //Gas
    if(START_GAS_BTN_R == 1){
        CH1_RL_ON;    
    }else{
        CH1_RL_OFF;
    }

    //Cooling
    if(COOLING_BTN_R == 1){
        CH2_RL_ON;    
    }else{
        CH2_RL_OFF;
    }

    //Charge
    if(CHARGE_BTN_R == 1){
        CH3_RL_ON;    
    }else{
        CH3_RL_OFF;
    }

    //Drop
    if(DROP_BTN_R == 1){
        CH4_RL_ON;    
    }else{
        CH4_RL_OFF;
    }


    //Escape
    if(ESCAPE_BTN_R == 1){
        CH5_RL_ON;    
    }else{
        CH5_RL_OFF;
    }


    //Afterburner
    if(AB_BTN_R == 1){
        CH6_RL_ON;    
    }else{
        CH6_RL_OFF;
    }

    //Destoner
    if(DESTONER_BTN_R == 1){
        CH7_RL_ON;    
    }else{
        CH7_RL_OFF;
    }

    //Feeder
    if(FEEDER_BTN_R == 1){
        CH8_RL_ON;    
    }else{
        CH8_RL_OFF;
    }
}