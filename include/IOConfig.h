#include "MachineStatus.h"

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
    gasSignal = !READ_CH1;
    swSignal  = !READ_SWITCH_1;

    // Edge detection for status push (static vars track previous state)
    static uint8_t prevGasSignal  = 0;
    static uint8_t prevCooling    = 0;
    static uint8_t prevDestoner   = 0;

    // Gas signal edge: push status on change
    if (gasSignal != prevGasSignal) {
        setMachineStatus(gasSignal ? STT_GAS_SIGNAL_OK : STT_GAS_SIGNAL_LOST);
        prevGasSignal = gasSignal;
    }

    //Gas relay
    if(MACHINE_HAS_GAS_CONTROL && START_GAS_BTN_R == 1){
        CH1_RL_ON;
    }else{
        CH1_RL_OFF;
    }

    //Cooling edge
    if(COOLING_BTN_R != prevCooling) {
        setMachineStatus(COOLING_BTN_R ? STT_ACT_COOLING_ON : STT_ACT_COOLING_OFF);
        prevCooling = COOLING_BTN_R;
    }
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
