void ConfigIOModbus(){

}

void controlIOModbus(){

}

void controlIO(){
    gasSignal = READ_CH1;   //Đọc báo gas
    gasSignal = !gasSignal;

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