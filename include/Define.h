#pragma once
//-------------------------------------------------------Define
#include "Config.h"

#if (defined(V300) + defined(V350) + defined(V400)) != 1
#error "Select exactly one hardware variant: V300, V350, or V400"
#endif

//-------------------------------------------------------MODBUS CONFIG-------------------------------------------------------//
HardwareSerial Serial1(USART1);
HardwareSerial Serial3(USART3);
HardwareSerial Serial4(UART4);


#if defined(V300)
#define SerialBluetooth Serial3 
#define SerialModbus    Serial4
#define SerialHmi       Serial1
#define SerialComputer  Serial2
#elif defined(V350)
#define SerialBluetooth Serial3 
#define SerialModbus    Serial4
#define SerialHmi       Serial1
#define SerialComputer  Serial2
#elif defined(V400)
#define SerialBluetooth Serial3 
#define SerialModbus    Serial2
#define SerialHmi       Serial1
#define SerialComputer  Serial4
#endif

ModbusMaster nodeBT; //BT
ModbusMaster nodeET; //ET
ModbusMaster nodeHMI; //HMI
ModbusMaster nodeAir; //Airflow
ModbusMaster nodeDrum; //Drum
ModbusMaster nodeIORelay; //Modbus relay

//Khai bÃ¡o cÃ¡c biáº¿n lÆ°u giÃ¡ trá»‹ Ä‘á»c tá»« Ä‘á»“ng há»“ nhiá»‡t vÃ  biáº¿n táº§n
uint16_t Temperature_BT, Temperature_ET;
uint16_t SV_BT, SV_ET, SV_Chamber;
uint16_t Airflow_Freq, Drum_Freq;
int16_t Diff_Air, raw_Diff_Air, smoothedDiff_Air;

//Khai bÃ¡o cÃ¡c biáº¿n lÆ°u táº¡m cÃ¡c giÃ¡ trá»‹ Ä‘á»c tá»« Ä‘á»“ng há»“ nhiá»‡t vÃ  biáº¿n táº§n
uint16_t Temperature_BT_CP, Temperature_ET_CP;
uint16_t Airflow_Freq_CP, Drum_Freq_CP;

//Biáº¿n Ä‘áº¿m lá»—i (check lá»—i nhiá»…u, delay, treo khi Ä‘á»c ghi modbus)
uint16_t errorCount = 0;
#define MODBUS_GAS_CUTOFF_FAIL_LIMIT 5  // Số lỗi Modbus liên tiếp trước khi khóa gas
bool modbusGasCutoffLatched = false;

//Array
int16_t iMemHMI[60], iMemHMI_CP[60]; //$M HMI
uint16_t dAddress[500], dAddress_CP[500]; //40xxx HMI
uint8_t cAddress[50], cAddress_CP[50]; //Coils
uint8_t progStatus = 1;
uint16_t profileData[30];
uint16_t profilePhaseHMI_R[10]; //phase cÃ i Ä‘áº·t tá»« HMI
uint16_t dataConvert[30];

//Time
long timeMillis, calTime; //TÃ­nh thá»i gian xá»­ lÃ­ chÆ°Æ¡ng trÃ¬nh
long timeLoaderMillis, loaderCalTime; //TÃ­nh thá»i gian xá»­ lÃ­ chÆ°Æ¡ng trÃ¬nh

uint8_t minRoast = 0, secRoast = 0;
uint16_t timeRoast = 0;
uint16_t chargeTimer = 0;
uint16_t dropTimer = 0;
uint16_t coolTimer = 0;
uint16_t escapeTimer = 0;
uint16_t feederTimer = 0;
uint16_t destonerTimer = 0;
uint16_t abTimer = 0;
uint16_t buzzerTimer = 0;
uint16_t timerLimit = 3000;
uint16_t waitDropcloseTi = 0;
uint8_t drumHzTimer = 0;            // Bá»™ Ä‘áº¿m thá»i gian cáº­p nháº­t Drum Hz
uint8_t airHzTimer = 0;             // Bá»™ Ä‘áº¿m thá»i gian cáº­p nháº­t Airflow Hz
uint8_t gasTimer = 0;             // Bá»™ Ä‘áº¿m thá»i gian cáº­p nháº­t Gas
uint8_t updateNetWTi = 0;
uint8_t cleanFeederTi = 0;
uint8_t delCyFeederTi = 0;
uint16_t fillerTi = 0;   //Thá»i gian Ä‘á»ƒ tá»± Ä‘á»™ng táº¯t fill cÃ  phÃª vÃ o bá»“n chá»©a

uint8_t buzzerTimeOFF = 15;
uint8_t percentLoadProfile = 0; //Pháº§n trÄƒm táº£i cá»§a profile rang cÃ  phÃª, dÃ¹ng Ä‘á»ƒ dá»± Ä‘oÃ¡n thá»i gian cÃ²n láº¡i cá»§a quÃ¡ trÃ¬nh rang
uint16_t timeYelTemp = 0;   //Biáº¿n táº¡m Ä‘á»ƒ dá»± Ä‘oÃ¡n yellow
uint16_t timeFcsTemp = 0;   //Biáº¿n táº¡m Ä‘á»ƒ dá»± Ä‘oÃ¡n fcs
uint16_t timeDevTemp = 0;   //Biáº¿n táº¡m Ä‘á»ƒ tÃ­nh Dev

boolean chargeTimerEn = false;      //Báº­t táº¯t timer charge
boolean dropTimerEn = false;        //Báº­t táº¯t timer drop
boolean coolTimerEn = false;        //Báº­t táº¯t timer cooling
boolean escapeTimerEn = false;      //Báº­t táº¯t timer escaple
boolean feederTimerEn = false;      //Báº­t táº¯t timer feeder
boolean destonerTimerEn = false;    //Báº­t táº¯t timer destoner
boolean abTimerEn = false;          //Timer AB
boolean timeRoastEn = false;        //Timer chÆ°Æ¡ng trÃ¬nh rang cÃ  phÃª
boolean buzzerTimerEn = false;      //Timer buzzer
boolean waitDropcloseTiEn = false;  //Timer chá» drop táº¯t
boolean updateNetWTiEn = true;          //Cáº­p nháº­t netW
boolean drumHzTiEn = 1;             //Cáº­p nháº­p Drum Hz
boolean airHzTiEn = 1;             //Cáº­p nháº­p Airflow Hz
boolean gasTiEn = 1;             //Cáº­p nháº­p Gas
boolean cleanFeederTiEn = false;    //Timer Ä‘á»ƒ hÃºt sáº¡ch cÃ  phÃª
boolean delCyFeederTiEn = false;
boolean fillerTiEn = false;    //Timer Ä‘á»ƒ tá»± Ä‘á»™ng táº¯t fill cÃ  phÃª vÃ o bá»“n chá»©a
boolean updateDateTimeEn = false;    //Cáº­p nháº­t thá»i gian thá»±c vÃ o Ä‘á»“ng há»“ HMI
boolean scanProfileDate = false; //QuÃ©t dá»¯ liá»‡u ngÃ y vÃ  giá» rang trÃªn cÃ¡c profile Ä‘Ã£ lÆ°u trÃªn SD
boolean sdReadStt = false; //Tráº¡ng thÃ¡i read
volatile uint8_t sdDeleteProfileEn = 0; //Báº­t táº¯t xÃ³a profile trÃªn SD card
volatile int sdDeleteProfileIndex = -1; //Biáº¿n lÆ°u index profile cáº§n xÃ³a trÃªn SD card

boolean buzzerHMIEn = false;
boolean memBuzzerEn = false;

boolean idBaudSetEn = false;        //Báº­t cáº­p nháº­p id vÃ  baudrate modbus

//Debug
boolean enDebug = 0; //Bật tắt debug qua Serial Computer
volatile bool fireCutFlag = false;  // ISR sets this when BT > 250C, loop() handles Modbus
volatile bool forceDrumFanOnFlag = false;  // ISR sets this when BT/ET > 80C, loop() handles Modbus

//Khai bÃ¡o liÃªn quan Ä‘áº¿n autoGas
boolean calibGasProgramEn = false;

int16_t calibGas = 0; //Há»‡ sá»‘ hiá»‡u chá»‰nh
int16_t deviTemp = 0; // Äá»™ lá»‡ch nhiá»‡t Ä‘á»™
int16_t numIncGas = 0; //GiÃ¡ trá»‹ sáº½ tÄƒng gas


uint16_t timeCalibGas = 15; //Hiá»‡u chá»‰nh ngay khi báº¯t Ä‘áº§u Ä‘áº¿m
uint16_t clRangeBt = 10; //Clearange Ä‘á»ƒ auto gas

uint16_t lastTimeSD = 0;
//----------------------End

//Khai bÃ¡o liÃªn quan Ä‘áº¿n cÃ¢n 
int16_t difNetW = 0; //Hiá»‡u sá»‘ cÃ¢n giá»¯a tá»•ng cÃ¢n vÃ  target
int16_t dif = 0;  //CÄƒn chá»‰nh Ä‘á»™ lá»‡ch khi cÃ¢n

//----------------------Define profile data

//Temp
#define BT_CHARGE_SAVE          profileData[0] 
#define BT_TP_SAVE              profileData[1] 
#define BT_YELLOW_SAVE          profileData[2] 
#define BT_FCS_SAVE             profileData[3]
#define BT_DROP_SAVE            profileData[4]

//Time
#define TIME_TP_SAVE            profileData[5]
#define TIME_TP_MIN_SAVE        profileData[6]
#define TIME_TP_SEC_SAVE        profileData[7]

#define TIME_YELLOW_SAVE        profileData[8]
#define TIME_YELLOW_MIN_SAVE    profileData[9] 
#define TIME_YELLOW_SEC_SAVE    profileData[10] 

#define TIME_FCS_SAVE           profileData[11] 
#define TIME_FCS_MIN_SAVE       profileData[12] 
#define TIME_FCS_SEC_SAVE       profileData[13] 

#define TIME_DROP_SAVE          profileData[14]
#define TIME_DROP_MIN_SAVE      profileData[15]
#define TIME_DROP_SEC_SAVE      profileData[16]  // FIX: was duplicate TIME_DROP_MIN_SAVE

#define PER_DEV_SAVE            profileData[17]
#define TIME_DEV_MIN_SAVE       profileData[18]
#define TIME_DEV_SEC_SAVE       profileData[19]

#define TIME_YEL_SEC_GUE        profileData[20]
#define TIME_FCS_SEC_GUE        profileData[21]

#define TIME_DEV_SAVE           profileData[22]

//----------------------Define Status
#define STT_NONE            0
#define STT_PROGRAM_SAVE    1
#define STT_PROGRAM_AUTO    2

//Define program step
uint8_t progStep = 0;   //Manual save step
uint8_t coolStep = 0;   //Cooling step
uint8_t abStep = 0;   //Afterburner step
uint8_t aLoaderStep = 0; //Auto Loader
uint16_t BT_TP_Pre = 0;
uint8_t ulimitTPTime = 20; //Thá»i gian cho phÃ©p check TP
uint16_t ulimitTPTemp = 1500; //Nhiá»‡t Ä‘á»™ cho phÃ©p check TP
uint8_t countIgnition = 0;
const char* STEP_STRING = "NONE";
const char* STEP_COOLING_STRING = "NONE";
const char* STEP_AB_STRING = "NONE";
const char* STEP_DRUM_WRITE = "NONE";
const char* STEP_LOADER = "NONE";

boolean svEn = false;

//Auto Loader step
#define STP_NONE_LOADER 0
#define STP_ON_LOADER   1
#define STP_WAIT_LOADER 2
#define STP_FAIL_LOADER 3
#define STP_OK_LOADER   4

//Manual save step detail
#define STP_DATA      0
#define STP_COOL_DOWN 1
#define STP_GAS       3
#define STP_CHECK     4
#define STP_CHARGE    5
#define STP_TP        6
#define STP_YELLOW    7
#define STP_FCS       8  
#define STP_DEV       9 
#define STP_DROP      10
#define STP_COOLING   11
#define STP_ESCAPE    12
#define STP_LOOP_1    13
#define STP_LOOP_2    14

//AB STEP
#define STP_ON_AB     1
#define STP_WAIT_AB   2  
#define STP_DELAY_AB  3 

//Mix&Cool step
#define COOL_STEP_COOLING       1
#define COOL_STEP_ESCAPE_ON     2
#define COOL_STEP_ESCAPE_OFF    3

#define TP_LIMIT_TIME       20
//ror calculate
SimpleKalmanFilter rorBTKalmanFilter(1, 1, 0.01); //Kalman filter for ror BT
SimpleKalmanFilter rorETKalmanFilter(1, 1, 0.01); //Kalman filter for ror BT and ET
SimpleKalmanFilter diff_KalmanFilter(150, 150, 0.1); // target â‰¤Â±5Pa

int16_t rorBTArray[10];
int16_t rorETArray[10];
int16_t rorBT=0, raw_rorBT=0, rorET=0, raw_rorET=0, old_rorBT=0;
uint16_t rorCount = 0;


#define rorBTSamp_1 rorBTArray[1] 
#define rorBTSamp_2 rorBTArray[2]

#define rorETSamp_1 rorETArray[1] 
#define rorETSamp_2 rorETArray[2]

//----------------------Define HMI
//Write holding register
#define START_BTN_W         1   //40001 - Báº­t/táº¯t Auto
#define START_GAS_BTN_W     2   //40002 - Báº­t táº¯t Gas
#define DRUM_FAN_BTN_W      3   //40003 - Báº­t/táº¯t drum/fan
#define MIXER_BTN_W         4   //40004 - Báº­t/táº¯t mixer
#define COOLING_BTN_W       5   //40005 - Báº­t/táº¯t cooling
#define FEEDER_BTN_W        6   //40006 - Báº­t/táº¯t feeder
#define CHARGE_BTN_W        7   //40007 - xi lanh charge
#define DROP_BTN_W          8   //40008 - Xi lanh drop
#define ESCAPE_BTN_W        9   //40009- Xi lanh escape
#define DESTONER_BTN_W      10  //40010 - Báº­t/táº¯t tÃ¡ch Ä‘Ã¡
#define DISCHARGE_BTN_W     11  //40011 - Xi lanh tÃ¡ch Ä‘Ã¡
#define AB_BTN_W            12  //40012 - Afterburner
#define SAVE_BTN_W          13  //40013 - Save
#define PC_CONTROL_BTN_W    14  //40013 - PC control
#define CONTROL_NAVI_W      15  //40013 - ThÃ´ng bÃ¡o cháº¿ Ä‘á»™ Ä‘iá»u khiá»ƒn
#define SELECT_FILE_W       16  //40016 - Chá»n file auto
#define DATE_PROFILE_W      17  //40017 - Set date profile
#define DEL_PROFILE_W       18  //40018 - Del profile
#define DEL_ALLPROFILE_W    19  //40019 - Del all profile
#define SAVE_PROPERTIES_W   20  //40020 - LÆ°u roast properties - macro

#define GENENAL_W           21
#define SCRNUM_W            22
#define SW_M_AUTO_W         23  //40023 - Switch manual/auto mode

#define AUTO_FS_BTN_W       31      //40031 - Auto fill silo
#define AUTO_PID_AIR_TU_W   32      //40032 - Auto PID Air Tuning

#define MANUAL_AUTO_W       23 //Chá»n mode rang

#define HOUR_W              33      //40033 - Show giá»
#define MINUTE_W            34      //40034 - Show phÃºt
#define SECOND_W            35      //40035 - Show giÃ¢y
#define DAY_W               36      //40036 - Show ngÃ y
#define MONTH_W             37      //40037 - Show thÃ¡ng
#define YEAR_W              38      //40038 - Show nÄƒm
#define REFRESH_LOAD_PF_W     39      //40039 - Load profile tá»« SD
#define WU_W                 40      //40040 - Warm up
#define STT_W               41      //40041 - Show status 
#define DRUM_FAN_W          42      //40042 - on/off drum fan
#define MIXER_W             43      //40043 - on/off mixer

#define SCRNUM_CONTROL_W    50
#define GENERAL_CONTROL_W   51
#define CLEAR_HIS_CONTROL_W 54

#define GAS_SIGNAL_HMI_W    60      //40060 - BÃ¡o Gas
#define BT_HMI_W            61      //40061 - Show BT
#define ET_HMI_W            62      //40062 - Show ET
#define ROR_BT_HMI_W        63      //40063 - Show ror BT
#define ROR_ET_HMI_W        64      //40064 - Show ror ET
#define AIRFLOW_HMI_W       65      //40065 - Show % Airflow
#define DRUM_HMI_W          66      //40066 - Show % Drum
#define GAS_HMI_W           67      //40067 - Show % Gas
#define MIN_HMI_W           68      //40068
#define SEC_HMI_W           69      //40069
#define TP_HMI_W            70
#define TP_MIN_HMI_W        71
#define TP_SEC_HMI_W        72
#define YELLOW_HMI_W        73
#define YELLOW_MIN_HMI_W    74
#define YELLOW_SEC_HMI_W    75
#define FCS_HMI_W           76
#define FCS_MIN_HMI_W       77
#define FCS_SEC_HMI_W       78
#define DEV_HMI_W           79  //Pháº§n trÄƒm
#define DEV_MIN_HMI_W       80
#define DEV_SEC_HMI_W       81
#define CHARGE_DATA_HMI_W   82  //Charge
#define DROP_DATA_HMI_W     83  //Drop
#define NETW_W              84  //CÃ¢n Ä‘á»c tá»« loader
#define DRUM_SPD_W          85  //Tá»‘c Ä‘á»™ trá»‘ng Ä‘á»c tá»« biáº¿n táº§n (5000)
#define DIFF_AIR_W          86  //Underpressure (5000)
#define PID_0800_W          87  //Show inv pid 0800 setting
#define PID_AIR_KP_W        88  //Show inv pid KP factor
#define PID_AIR_KI_W        89  //Show inv pid KI factor
#define PID_AIR_KD_W        90  //Show inv pid KD factor

#define CAL_WEI_HMI_W       100  //TÃ­nh toÃ¡n hao há»¥t khá»‘i lÆ°á»£ng sau rang (macro HMI)
#define CAL_MOIS_HMI_W      101  //TÃ­nh toÃ¡n hao há»¥t Ä‘á»™ áº©m sau rang (macro HMI)
#define CAL_DENS_HMI_W      102  //TÃ­nh toÃ¡n hao há»¥t khá»‘i lÆ°á»£ng riÃªng sau rang (macro HMI)

//Properties Ä‘á»c tá»« sd
#define CHARGE_PRO_W        103  //Charge temp
#define TP_PRO_W            104  //TP temp
#define TP_PRO_M_W          105  //TP time
#define TP_PRO_S_W          106  //TP time
#define DE_PRO_W            107  //DE temp
#define DE_PRO_M_W          108  //DE time
#define DE_PRO_S_W          109  //DE time
#define FCS_PRO_W           110  //FCs temp
#define FCS_PRO_M_W         111  //FCs time
#define FCS_PRO_S_W         112  //FCs time
#define DEV_PRO_W           113  //DEV %
#define DEV_PRO_M_W         114  //DEV time
#define DEV_PRO_S_W         115  //DEV time
#define DROP_PRO_W          116  //Drop temp
#define DROP_PRO_M_W        117  //Drop time
#define DROP_PRO_S_W        118  //Drop time

//Biáº¿n phá»¥ 
#define FA_SUC_W            119 //Failed/Success 
#define LOADING_W           120  //SHOW Loading
#define LOADING_SHOW_W      121  //SHOW Loading
#define SETTING_W           122  //On off setting screen
#define MULTI_W             123  //On off multi screen
#define ALARM_LOADER_W      124  //Alarm Feeder
#define TUNE_PERCENT_W     125  //Show % tiáº¿n Ä‘á»™ cá»§a quÃ¡ trÃ¬nh tune

//BiÃªn phá»¥ start
#define warnDeleteProfile     151 //Cáº£nh bÃ¡o xÃ³a profile
#define turnON40001           152 //Báº­t coil 40001

//Read holding register
#define START_BTN_R             dAddress[START_BTN_W]       //40001 - Báº­t/táº¯t Auto
#define START_GAS_BTN_R         dAddress[START_GAS_BTN_W]   //40002 - Báº­t táº¯t Gas
#define DRUM_FAN_BTN_R          dAddress[DRUM_FAN_BTN_W]    //40003 - Báº­t/táº¯t drum/fan
#define MIXER_BTN_R             dAddress[MIXER_BTN_W]       //40004 - Báº­t/táº¯t mixer
#define COOLING_BTN_R           dAddress[COOLING_BTN_W]     //40005 - Báº­t/táº¯t cooling
#define FEEDER_BTN_R            dAddress[FEEDER_BTN_W]      //40006 - Báº­t/táº¯t feeder
#define CHARGE_BTN_R            dAddress[CHARGE_BTN_W]      //40007 - xi lanh charge
#define DROP_BTN_R              dAddress[DROP_BTN_W]        //40008 - Xi lanh drop
#define ESCAPE_BTN_R            dAddress[ESCAPE_BTN_W]      //40009- Xi lanh escape
#define DESTONER_BTN_R          dAddress[DESTONER_BTN_W]    //40010 - Báº­t/táº¯t tÃ¡ch Ä‘Ã¡
#define DISCHARGE_BTN_R         dAddress[DISCHARGE_BTN_W]   //40011 - Xi lanh tÃ¡ch Ä‘Ã¡
#define AB_BTN_R                dAddress[AB_BTN_W]          //40012 - Afterburner
#define SAVE_BTN_R              dAddress[SAVE_BTN_W]        //40013 - Save
#define PC_CONTROL_BTN_R        dAddress[PC_CONTROL_BTN_W]  //40014 - PC control
#define CONTROL_NAVI_R          dAddress[CONTROL_NAVI_W]    //40015 - ThÃ´ng bÃ¡o cháº¿ Ä‘á»™ Ä‘iá»u khiá»ƒn

#define SELECT_FILE_R           dAddress[SELECT_FILE_W]
#define DATE_PROFILE_R          dAddress[DATE_PROFILE_W]
#define DEL_PROFILE_R           dAddress[DEL_PROFILE_W]
#define DEL_ALLPROFILE_R        dAddress[DEL_ALLPROFILE_W]

#define GENENAL_R               dAddress[GENENAL_W]

#define SCRNUM_R                dAddress[SCRNUM_W]
#define AUTO_FS_BTN_R           dAddress[AUTO_FS_BTN_W]      //40031 - Auto fill silo
#define AUTO_PID_AIR_TU_R       dAddress[AUTO_PID_AIR_TU_W]  //40032 - Auto PID Air Tuning

#define MANUAL_AUTO_R           dAddress[MANUAL_AUTO_W]

#define HOUR_R                  dAddress[HOUR_W]             //40033 - Show giá»
#define MINUTE_R                dAddress[MINUTE_W]           //40034 - Show phÃºt
#define SECOND_R                dAddress[SECOND_W]           //40035 - Show giÃ¢y
#define DAY_R                   dAddress[DAY_W]              //40036 - Show ngÃ y
#define MONTH_R                 dAddress[MONTH_W]            //40037 - Show thÃ¡ng
#define YEAR_R                  dAddress[YEAR_W]             //40038 - Show nÄƒm
#define REFRESH_LOAD_PF_R       dAddress[REFRESH_LOAD_PF_W]  //40039 - Load profile tá»« SD
#define WU_R                    dAddress[WU_W]               //40040 - Warm up
#define STT_R                   dAddress[STT_W]              //40041 - Show status

#define GENERAL_CONTROL_R       dAddress[GENERAL_CONTROL_W]
#define CLEAR_HIS_CONTROL_R     dAddress[CLEAR_HIS_CONTROL_W]

#define GAS_SIGNAL_HMI_R        dAddress[GAS_SIGNAL_HMI_W]  //40060 
#define BT_HMI_R                dAddress[BT_HMI_W] 
#define ET_HMI_R                dAddress[ET_HMI_W] 
#define ROR_BT_HMI_R            dAddress[ROR_BT_HMI_W] 
#define ROR_ET_HMI_R            dAddress[ROR_ET_HMI_W] 
#define AIRFLOW_HMI_R           dAddress[AIRFLOW_HMI_W] 
#define DRUM_HMI_R              dAddress[DRUM_HMI_W] 
#define GAS_HMI_R               dAddress[GAS_HMI_W]
#define MIN_HMI_R               dAddress[MIN_HMI_W]
#define SEC_HMI_R               dAddress[SEC_HMI_W] 
#define TP_HMI_R                dAddress[TP_HMI_W] 
#define TP_MIN_HMI_R            dAddress[TP_MIN_HMI_W] 
#define TP_SEC_HMI_R            dAddress[TP_SEC_HMI_W] 
#define YELLOW_HMI_R            dAddress[YELLOW_HMI_W] 
#define YELLOW_MIN_HMI_R        dAddress[YELLOW_MIN_HMI_W] 
#define YELLOW_SEC_HMI_R        dAddress[YELLOW_SEC_HMI_W] 
#define FCS_HMI_R               dAddress[FCS_HMI_W] 
#define FCS_MIN_HMI_R           dAddress[FCS_MIN_HMI_W] 
#define FCS_SEC_HMI_R           dAddress[FCS_SEC_HMI_W] 
#define DEV_HMI_R               dAddress[DEV_HMI_W] 
#define DEV_MIN_HMI_R           dAddress[DEV_MIN_HMI_W] 
#define DEV_SEC_HMI_R           dAddress[DEV_SEC_HMI_W] 
#define CHARGE_DATA_HMI_R       dAddress[CHARGE_DATA_HMI_W] 
#define DROP_DATA_HMI_R         dAddress[DROP_DATA_HMI_W]   

#define CHARGE_PRO_R            dAddress[CHARGE_PRO_W]  //Charge temp
#define TP_PRO_R                dAddress[TP_PRO_W]      //TP temp
#define TP_PRO_M_R              dAddress[TP_PRO_M_W]    //TP time
#define TP_PRO_S_R              dAddress[TP_PRO_S_W]    //TP time
#define DE_PRO_R                dAddress[DE_PRO_W]      //DE temp
#define DE_PRO_M_R              dAddress[DE_PRO_M_W]    //DE time
#define DE_PRO_S_R              dAddress[DE_PRO_S_W]    //DE time
#define FCS_PRO_R               dAddress[FCS_PRO_W]     //FCs temp
#define FCS_PRO_M_R             dAddress[FCS_PRO_M_W]   //FCs time
#define FCS_PRO_S_R             dAddress[FCS_PRO_S_W]   //FCs time
#define DEV_PRO_R               dAddress[DEV_PRO_W]     //DEV %
#define DEV_PRO_M_R             dAddress[DEV_PRO_M_W]   //DEV time
#define DEV_PRO_S_R             dAddress[DEV_PRO_S_W]   //DEV time
#define DROP_PRO_R              dAddress[DROP_PRO_W]    //Drop temp
#define DROP_PRO_M_R            dAddress[DROP_PRO_M_W]  //Drop time
#define DROP_PRO_S_R            dAddress[DROP_PRO_S_W]  //Drop time
#define NETW_R                  dAddress[NETW_W]        //CÃ¢n Ä‘á»c tá»« loader
#define DRUM_SPD_R              dAddress[DRUM_SPD_W]    //Tá»‘c Ä‘á»™ trá»‘ng rang Hz
#define DIFF_AIR_R              dAddress[DIFF_AIR_W]    //Underpressure
#define PID_0800_R              dAddress[PID_0800_W]    //Show inv pid 0800 setting
#define PID_AIR_KP_R            dAddress[PID_AIR_KP_W]  //Show inv pid KP factor
#define PID_AIR_KI_R            dAddress[PID_AIR_KI_W]  //Show inv pid KI factor
#define PID_AIR_KD_R            dAddress[PID_AIR_KD_W]  //Show inv pid KD factor

#define TUNE_PERCENT_R           dAddress[TUNE_PERCENT_W] //Show % tiáº¿n Ä‘á»™ cá»§a quÃ¡ trÃ¬nh tune

//Biáº¿n lÆ°u táº¡m Ä‘á»ƒ kiá»ƒm tra sá»± thay Ä‘á»•i cá»§a máº£ng data
#define START_BTN_R_CP          dAddress_CP[START_BTN_W]
#define START_GAS_BTN_R_CP      dAddress_CP[START_GAS_BTN_W]
#define DRUM_FAN_BTN_R_CP       dAddress_CP[DRUM_FAN_BTN_W]
#define MIXER_BTN_R_CP          dAddress_CP[MIXER_BTN_W]
#define COOLING_BTN_R_CP        dAddress_CP[COOLING_BTN_W]
#define FEEDER_BTN_R_CP         dAddress_CP[FEEDER_BTN_W]
#define CHARGE_BTN_R_CP         dAddress_CP[CHARGE_BTN_W]
#define DROP_BTN_R_CP           dAddress_CP[DROP_BTN_W]
#define ESCAPE_BTN_R_CP         dAddress_CP[ESCAPE_BTN_W]
#define DESTONER_BTN_R_CP       dAddress_CP[DESTONER_BTN_W]
#define DISCHARGE_BTN_R_CP      dAddress_CP[DISCHARGE_BTN_W]
#define AB_BTN_R_CP             dAddress_CP[AB_BTN_W]
#define SAVE_BTN_R_CP           dAddress_CP[SAVE_BTN_W]
#define PC_CONTROL_BTN_R_CP     dAddress_CP[PC_CONTROL_BTN_W] 
#define CONTROL_NAVI_R_CP       dAddress_CP[CONTROL_NAVI_W]   

#define SELECT_FILE_R_CP        dAddress_CP[SELECT_FILE_W] 
#define DATE_PROFILE_R_CP       dAddress_CP[DATE_PROFILE_W]
#define DEL_PROFILE_R_CP        dAddress_CP[DEL_PROFILE_W]
#define DEL_ALLPROFILE_R_CP     dAddress_CP[DEL_ALLPROFILE_W]

#define GENENAL_R_CP            dAddress_CP[GENENAL_W]
#define SCRNUM_R_CP             dAddress_CP[SCRNUM_W]
#define AUTO_FS_BTN_R_CP        dAddress_CP[AUTO_FS_BTN_W]
#define AUTO_PID_AIR_TU_R_CP    dAddress_CP[AUTO_PID_AIR_TU_W]

#define MANUAL_AUTO_R_CP        dAddress_CP[MANUAL_AUTO_W]

#define HOUR_R_CP               dAddress_CP[HOUR_W]
#define MINUTE_R_CP             dAddress_CP[MINUTE_W]
#define SECOND_R_CP             dAddress_CP[SECOND_W]
#define DAY_R_CP                dAddress_CP[DAY_W]
#define MONTH_R_CP              dAddress_CP[MONTH_W]
#define YEAR_R_CP               dAddress_CP[YEAR_W]
#define REFRESH_LOAD_PF_R_CP    dAddress_CP[REFRESH_LOAD_PF_W]
#define WU_R_CP                 dAddress_CP[WU_W]
#define STT_R_CP                dAddress_CP[STT_W]

#define GENERAL_CONTROL_R_CP    dAddress_CP[GENERAL_CONTROL_W]
#define CLEAR_HIS_CONTROL_R_CP  dAddress_CP[CLEAR_HIS_CONTROL_W]

#define GAS_SIGNAL_HMI_R_CP     dAddress_CP[GAS_SIGNAL_HMI_W] 
#define BT_HMI_R_CP             dAddress_CP[BT_HMI_W] 
#define ET_HMI_R_CP             dAddress_CP[ET_HMI_W] 
#define ROR_BT_HMI_R_CP         dAddress_CP[ROR_BT_HMI_W] 
#define ROR_ET_HMI_R_CP         dAddress_CP[ROR_ET_HMI_W] 
#define AIRFLOW_HMI_R_CP        dAddress_CP[AIRFLOW_HMI_W] 
#define DRUM_HMI_R_CP           dAddress_CP[DRUM_HMI_W] 
#define GAS_HMI_R_CP            dAddress_CP[GAS_HMI_W]
#define MIN_HMI_R_CP            dAddress_CP[MIN_HMI_W]
#define SEC_HMI_R_CP            dAddress_CP[SEC_HMI_W] 
#define TP_HMI_R_CP             dAddress_CP[TP_HMI_W] 
#define TP_MIN_HMI_R_CP         dAddress_CP[TP_MIN_HMI_W] 
#define TP_SEC_HMI_R_CP         dAddress_CP[TP_SEC_HMI_W] 
#define YELLOW_HMI_R_CP         dAddress_CP[YELLOW_HMI_W] 
#define YELLOW_MIN_HMI_R_CP     dAddress_CP[YELLOW_MIN_HMI_W] 
#define YELLOW_SEC_HMI_R_CP     dAddress_CP[YELLOW_SEC_HMI_W] 
#define FCS_HMI_R_CP            dAddress_CP[FCS_HMI_W] 
#define FCS_MIN_HMI_R_CP        dAddress_CP[FCS_MIN_HMI_W] 
#define FCS_SEC_HMI_R_CP        dAddress_CP[FCS_SEC_HMI_W] 
#define DEV_HMI_R_CP            dAddress_CP[DEV_HMI_W] 
#define DEV_MIN_HMI_R_CP        dAddress_CP[DEV_MIN_HMI_W] 
#define DEV_SEC_HMI_R_CP        dAddress_CP[DEV_SEC_HMI_W] 
#define CHARGE_DATA_HMI_R_CP    dAddress_CP[CHARGE_DATA_HMI_W] 
#define DROP_DATA_HMI_R_CP      dAddress_CP[DROP_DATA_HMI_W]

#define CHARGE_PRO_R_CP         dAddress_CP[CHARGE_PRO_W] //Charge temp
#define TP_PRO_R_CP             dAddress_CP[TP_PRO_W]     //TP temp
#define TP_PRO_M_R_CP           dAddress_CP[TP_PRO_M_W]  //TP time
#define TP_PRO_S_R_CP           dAddress_CP[TP_PRO_S_W]  //TP time
#define DE_PRO_R_CP             dAddress_CP[DE_PRO_W]     //DE temp
#define DE_PRO_M_R_CP           dAddress_CP[DE_PRO_M_W]   //DE time
#define DE_PRO_S_R_CP           dAddress_CP[DE_PRO_S_W]   //DE time
#define FCS_PRO_R_CP            dAddress_CP[FCS_PRO_W]    //FCs temp
#define FCS_PRO_M_R_CP          dAddress_CP[FCS_PRO_M_W]  //FCs time
#define FCS_PRO_S_R_CP          dAddress_CP[FCS_PRO_S_W]  //FCs time
#define DEV_PRO_R_CP            dAddress_CP[DEV_PRO_W]    //DEV %
#define DEV_PRO_M_R_CP          dAddress_CP[DEV_PRO_M_W]  //DEV time
#define DEV_PRO_S_R_CP          dAddress_CP[DEV_PRO_S_W]  //DEV time
#define DROP_PRO_R_CP           dAddress_CP[DROP_PRO_W]   //Drop temp
#define DROP_PRO_M_R_CP         dAddress_CP[DROP_PRO_M_W]  //Drop time
#define DROP_PRO_S_R_CP         dAddress_CP[DROP_PRO_S_W]  //Drop time

#define NETW_R_CP               dAddress_CP[NETW_W]        //CÃ¢n Ä‘á»c tá»« loader
#define DRUM_SPD_R_CP           dAddress_CP[DRUM_SPD_W]    //Tá»‘c Ä‘á»™ trá»‘ng rang Hz
#define DIFF_AIR_R_CP           dAddress_CP[DIFF_AIR_W]    //Underpressure
#define PID_0800_R_CP           dAddress_CP[PID_0800_W]    //Show inv pid 0800 setting
#define PID_AIR_KP_R_CP         dAddress_CP[PID_AIR_KP_W]  //Show inv pid KP factor
#define PID_AIR_KI_R_CP         dAddress_CP[PID_AIR_KI_W]  //Show inv pid KI factor
#define PID_AIR_KD_R_CP         dAddress_CP[PID_AIR_KD_W]  //Show inv pid KD factor

#define TUNE_PERCENT_R_CP        dAddress_CP[TUNE_PERCENT_W] //Show % tiáº¿n Ä‘á»™ cá»§a quÃ¡ trÃ¬nh tune
//----------------------End

//----------------------Define Profile Date List (Ä‘á»‹a chá»‰ HMI 600 trá»Ÿ Ä‘i)
// Má»—i há»“ sÆ¡ i (0-based, slot 1â€“30 â†’ file 1.csvâ€“30.csv) chiáº¿m 7 registers:
//   +0 = DD  (ngÃ y)
//   +1 = MM  (thÃ¡ng)
//   +2 = YY  (nÄƒm, 2 chá»¯ sá»‘: 2024 â†’ 24)
//   +3 = HH  (giá» lÃºc charge)
//   +4 = MIN_CHARGE (phÃºt lÃºc charge)
//   +5 = MIN_ROAST (phÃºt tá»•ng rang)
//   +6 = SEC_ROAST (giÃ¢y tá»•ng rang)
// Tá»•ng: 30 Ã— 7 = 210 registers â†’ Ä‘á»‹a chá»‰ 600â€“809
#define PROFILE_DATE_BASE_W     600   // base 1-based (HMI 40601)
#define MAX_PROFILE_SLOTS       30    // slot 1â€“30
#define PROFILE_REGS_PER_SLOT   7     // DD, MM, YY, HH, MIN_CHARGE, MIN_ROAST, SEC_ROAST

// Trigger reload profile dates tá»« HMI
#define LOAD_DATE_PROFILE_W     810   // HMI ghi 1 vÃ o Ä‘Ã¢y Ä‘á»ƒ trigger reload
#define LOAD_DATE_PROFILE_R     dAddress[LOAD_DATE_PROFILE_W]  // Ä‘á»c trigger
boolean enLoadDateProfile = false;  // flag Ä‘á»ƒ loop() gá»i loadAllProfileDates()
//----------------------End

//----------------------Define $M HMI - Ä‘á»‹a chá»‰ nhá»› HMI
//Internal register write
#define chargeDuration_W    1   //$M1 - Háº¹n giá» xi lanh charge
#define dropDuration_W      2   //$M2 - Háº¹n giá» xi lanh drop
#define escapeDuration_W    3   //$M3 - Háº¹n giá» xi lanh escape
#define TpCalib_W           4   //$M4 - Giá»›i háº¡n giÃ¡ trá»‹ auto gas á»Ÿ trÆ°á»›c khi DE
#define DeCalib_W           5   //$M5 - Giá»›i háº¡n giÃ¡ trá»‹ auto gas á»Ÿ trÆ°á»›c khi FCs
#define tempRegister_W      6   //khai bÃ¡o Ä‘á»‹a chá»‰ Ä‘á»c Ä‘á»“ng há»“ delta
#define afterburnerSet_W    7   //CÃ i Ä‘áº·t nhiá»‡t Ä‘á»™ cháº¡y afterburner
#define preGas_W            8   //Äáº·t gas BBP
#define turnGasPoint_W      9   //Äáº·t nhiá»‡t Ä‘á»™ báº­t gas
#define chTolerange_W       10  //Äá»™ lá»‡ch charge
#define loop_W              11  //Sample
#define modbusID_W          12  //Modbus slave ID
#define modbusBaud_W        13  //Modbus baudrate ID
#define feederSet_W         14  //Timer thá»•i liá»‡u
#define idDrum_W            15  //ID Drum
#define regDrum_W           16  //Reg Drum
#define destonerSet_W       19  //Timer destoner
#define yellowPhase_W       20  //CÃ i yellow
#define fcsPhase_W          21  //CÃ i fcs
#define coolTimer_W         22  //Timer cooling&mixer
#define chargeTemp_W        23  //CÃ i charge temp
#define btSV_W              24  //CÃ i set value BT
#define btSVReg_W           25  //CÃ i set value register
#define destonerPre_W       26  //Äá»™ lá»‡ch thá»i gian báº­t destoner
#define afterburnerNext_W   27  //Delay afterburner
#define maxGasSet_W         28  //Giá»›i háº¡n max gas
#define burnerPremix_W      29  //Lá»±a báº¿p
#define preCool_W           30  //Báº­t cooling trÆ°á»›c
#define FcsCalib_W          31  //$M5 - Giá»›i háº¡n giÃ¡ trá»‹ auto gas á»Ÿ sau khi FCs
#define netWTG_W            32  //Sá»‘ lÆ°á»£ng cÃ  phÃª sáº½ thá»•i lÃªn
#define autoLoader_W        33  //Báº­t táº¯t auto báº¿p
#define drumSpeed_W         34 //Set tá»‘c Ä‘á»™ Drum inverter 
#define airSpeed_W          35 //Set tá»‘c Ä‘á»™ Airflow inverter 
#define burnerValue_W       36 //Set gas 
#define autoOff_W           37 //Tá»± Ä‘á»™ng ngáº¯t Ä‘áº§u Ä‘á»‘t 
#define wThresholdHigh_W    38 //NgÆ°á»¡ng cÃ¢n
#define wThresholdMedium_W  39 //NgÆ°á»¡ng cÃ¢n 
#define wThresholdLow_W     40 //NgÆ°á»¡ng cÃ¢n
#define difHigh_W           41 //Sai sá»‘ cÃ¢n
#define difMedium_W         42 //Sai sá»‘ cÃ¢n
#define difLow_W            43 //Sai sá»‘ cÃ¢n
#define vacuumTraction_W    44 //Lá»¥c kÃ©o cá»§a vacuum
#define autoFill_W          45 //Ttá»± Ä‘á»™ng báº­t fill cÃ  phÃª tá»« tÃ¡ch Ä‘Ã¡ sang silo
#define autoFill_Time_W     46 //Thá»i gian auto fill cÃ  phÃª tá»« tÃ¡ch Ä‘Ã¡ sang silo
#define vacuumSetFlag_W     47 //Báº­t táº¯t pid vacuum
#define vacuumSetpoint_W    48 //Setpoint cá»§a vacuum
#define minPT_W             49  //Giá»›i háº¡n min Pressure transmitter
#define maxPT_W             50  //Giá»›i háº¡n max Pressure transmitter
#define wuTime_W            51  //Thá»i gian warm up
#define wuTemp_W            52  //Nhiá»‡t Ä‘á»™ warm up

//Internal register read
#define chargeDuration_R    iMemHMI[chargeDuration_W]  //$M1 - Háº¹n giá» xi lanh charge
#define dropDuration_R      iMemHMI[dropDuration_W]  //$M2 - Háº¹n giá» xi lanh drop
#define escapeDuration_R    iMemHMI[escapeDuration_W]  //$M3 - Háº¹n giá» xi lanh escape
#define TpCalib_R           iMemHMI[TpCalib_W]  //$M4 - TÄƒng giÃ¡ trá»‹ auto gas
#define DeCalib_R           iMemHMI[DeCalib_W]  //$M5 - Giáº£m giÃ¡ trá»‹ auto gas
#define tempRegister_R      iMemHMI[tempRegister_W]  //khai bÃ¡o Ä‘á»‹a chá»‰ Ä‘á»c Ä‘á»“ng há»“ delta

#define afterburnerSet_R    iMemHMI[afterburnerSet_W]
#define preGas_R            iMemHMI[preGas_W]
#define turnGasPoint_R      iMemHMI[turnGasPoint_W]
#define chTolerange_R       iMemHMI[chTolerange_W]
#define loop_R              iMemHMI[loop_W]
#define modbusID_R          iMemHMI[modbusID_W]
#define modbusBaud_R        iMemHMI[modbusBaud_W]
#define feederSet_R         iMemHMI[feederSet_W]
#define destonerSet_R       iMemHMI[destonerSet_W]
#define idDrum_R            iMemHMI[idDrum_W]
#define regDrum_R           iMemHMI[regDrum_W]

#define yellowPhase_R       iMemHMI[yellowPhase_W]
#define fcsPhase_R          iMemHMI[fcsPhase_W]

#define coolTimer_R         iMemHMI[coolTimer_W]
#define chargeTemp_R        iMemHMI[chargeTemp_W]
#define btSV_R              iMemHMI[btSV_W]
#define btSVReg_R           iMemHMI[btSVReg_W]
#define destonerPre_R       iMemHMI[destonerPre_W]
#define afterburnerNext_R   iMemHMI[afterburnerNext_W]

#define drumSpeed_R         iMemHMI[drumSpeed_W]        //Set tá»‘c Ä‘á»™ Drum inverter (gá»­i PLC)
#define airSpeed_R          iMemHMI[airSpeed_W]         //Set tá»‘c Ä‘á»™ Airflow inverter (gá»­i PLC)
#define burnerValue_R       iMemHMI[burnerValue_W]      //Set gas (gá»­i PLC)
// #define destonerValue_R     iMemHMI[destonerValue_W]  // destonerValue_W not defined
#define maxGasSet_R         iMemHMI[maxGasSet_W]
#define burnerPremix_R      iMemHMI[burnerPremix_W]
#define preCool_R           iMemHMI[preCool_W]
#define FcsCalib_R          iMemHMI[FcsCalib_W]
#define netWTG_R            iMemHMI[netWTG_W]
#define autoLoader_R        iMemHMI[autoLoader_W]
#define drumSpeed_R         iMemHMI[drumSpeed_W] //Set tá»‘c Ä‘á»™ Drum inverter 
#define airSpeed_R          iMemHMI[airSpeed_W] //Set tá»‘c Ä‘á»™ Airflow inverter 
#define burnerValue_R       iMemHMI[burnerValue_W] //Set gas 
#define autoOff_R           iMemHMI[autoOff_W] //Tá»± Ä‘á»™ng ngáº¯t gas
#define wThresholdHigh_R    iMemHMI[wThresholdHigh_W] //NgÆ°á»¡ng cÃ¢n
#define wThresholdMedium_R  iMemHMI[wThresholdMedium_W] //NgÆ°á»¡ng cÃ¢n
#define wThresholdLow_R     iMemHMI[wThresholdLow_W] //NgÆ°á»¡ng cÃ¢n
#define difHigh_R           iMemHMI[difHigh_W] //Sai sá»‘ cÃ¢n
#define difMedium_R         iMemHMI[difMedium_W] //Sai sá»‘ cÃ¢n
#define difLow_R            iMemHMI[difLow_W] //Sai sá»‘ cÃ¢n
#define vacuumTraction_R    iMemHMI[vacuumTraction_W] //Lá»¥c kÃ©o cá»§a vacuum
#define autoFill_R          iMemHMI[autoFill_W] //Tá»± Ä‘á»™ng báº­t fill cÃ  phÃª tá»« tÃ¡ch Ä‘Ã¡ sang silo
#define autoFill_Time_R     iMemHMI[autoFill_Time_W] //Thá»i gian auto fill cÃ  phÃª tá»« tÃ¡ch Ä‘Ã¡ sang silo
#define vacuumSetFlag_R     iMemHMI[vacuumSetFlag_W] //Báº­t táº¯t pid vacuum
#define vacuumSetpoint_R    iMemHMI[vacuumSetpoint_W] //Setpoint cá»§a vacuum
#define minPT_R             iMemHMI[minPT_W]  //Giá»›i háº¡n min Pressure transmitter
#define maxPT_R             iMemHMI[maxPT_W]  //Giá»›i háº¡n max Pressure transmitter
#define wuTime_R            iMemHMI[wuTime_W]  //Thá»i gian warm up
#define wuTemp_R            iMemHMI[wuTemp_W]  //Nhiá»‡t Ä‘á»™ warm up

//Internal memory register- biáº¿n lÆ°u táº¡m
#define chargeDuration_R_CP     iMemHMI_CP[chargeDuration_W]  //$M1 - Háº¹n giá» xi lanh charge
#define dropDuration_R_CP       iMemHMI_CP[dropDuration_W]    //$M2 - Háº¹n giá» xi lanh drop
#define escapeDuration_R_CP     iMemHMI_CP[escapeDuration_W]  //$M3 - Háº¹n giá» xi lanh escape
#define TpCalib_R_CP            iMemHMI_CP[TpCalib_W]         //$M4
#define DeCalib_R_CP            iMemHMI_CP[DeCalib_W]         //$M5
#define tempRegister_R_CP       iMemHMI_CP[tempRegister_W]    //khai bÃ¡o Ä‘á»‹a chá»‰ Ä‘á»c Ä‘á»“ng há»“ delta

#define afterburnerSet_R_CP     iMemHMI_CP[afterburnerSet_W]
#define preGas_R_CP             iMemHMI_CP[preGas_W]
#define turnGasPoint_R_CP       iMemHMI_CP[turnGasPoint_W]
#define chTolerange_R_CP        iMemHMI_CP[chTolerange_W]
#define loop_R_CP               iMemHMI_CP[loop_W]
#define modbusID_R_CP           iMemHMI_CP[modbusID_W]
#define modbusBaud_R_CP         iMemHMI_CP[modbusBaud_W]
#define feederSet_R_CP          iMemHMI_CP[feederSet_W]
#define destonerSet_R_CP        iMemHMI_CP[destonerSet_W]
#define idDrum_R_CP             iMemHMI_CP[idDrum_W]
#define regDrum_R_CP            iMemHMI_CP[regDrum_W]

#define yellowPhase_R_CP        iMemHMI_CP[yellowPhase_W]
#define fcsPhase_R_CP           iMemHMI_CP[fcsPhase_W]

#define coolTimer_R_CP          iMemHMI_CP[coolTimer_W]
#define chargeTemp_R_CP         iMemHMI_CP[chargeTemp_W]
#define btSV_R_CP               iMemHMI_CP[btSV_W]
#define btSVReg_R_CP            iMemHMI_CP[btSVReg_W]
#define destonerPre_R_CP        iMemHMI_CP[destonerPre_W]
#define afterburnerNext_R_CP    iMemHMI_CP[afterburnerNext_W]

#define drumSpeed_R_CP          iMemHMI_CP[drumSpeed_W]        //Set tá»‘c Ä‘á»™ Drum inverter (gá»­i PLC)
#define airSpeed_R_CP           iMemHMI_CP[airSpeed_W]         //Set tá»‘c Ä‘á»™ Airflow inverter (gá»­i PLC)
#define burnerValue_R_CP        iMemHMI_CP[burnerValue_W]      //Set gas (gá»­i PLC)
// #define destonerValue_R_CP      iMemHMI_CP[destonerValue_W]  // destonerValue_W not defined
#define maxGasSet_R_CP          iMemHMI_CP[maxGasSet_W]
#define burnerPremix_R_CP       iMemHMI_CP[burnerPremix_W]
#define preCool_R_CP            iMemHMI_CP[preCool_W]
#define FcsCalib_R_CP           iMemHMI_CP[FcsCalib_W] 
#define netWTG_R_CP             iMemHMI_CP[netWTG_W] 
#define autoLoader_R_CP         iMemHMI_CP[autoLoader_W]
#define drumSpeed_R_CP          iMemHMI_CP[drumSpeed_W] //Set tá»‘c Ä‘á»™ Drum inverter 
#define airSpeed_R_CP           iMemHMI_CP[airSpeed_W] //Set tá»‘c Ä‘á»™ Airflow inverter 
#define burnerValue_R_CP        iMemHMI_CP[burnerValue_W] //Set gas
#define autoOff_R_CP            iMemHMI_CP[autoOff_W] //Tá»± Ä‘á»™ng ngáº¯t gas  
#define wThresholdHigh_R_CP     iMemHMI_CP[wThresholdHigh_W] //NgÆ°á»¡ng cÃ¢n
#define wThresholdMedium_R_CP   iMemHMI_CP[wThresholdMedium_W] //NgÆ°á»¡ng cÃ¢n
#define wThresholdLow_R_CP      iMemHMI_CP[wThresholdLow_W] //NgÆ°á»¡ng cÃ¢n
#define difHigh_R_CP            iMemHMI_CP[difHigh_W] //Sai sá»‘ cÃ¢n
#define difMedium_R_CP          iMemHMI_CP[difMedium_W] //Sai sá»‘ cÃ¢n
#define difLow_R_CP             iMemHMI_CP[difLow_W] //Sai sá»‘ cÃ¢n
#define vacuumTraction_R_CP     iMemHMI_CP[vacuumTraction_W] //Lá»¥c kÃ©o cá»§a vacuum
#define autoFill_R_CP           iMemHMI_CP[autoFill_W] //Tá»± Ä‘á»™ng báº­t fill cÃ  phÃª tá»« tÃ¡ch Ä‘Ã¡ sang silo
#define autoFill_Time_R_CP      iMemHMI_CP[autoFill_Time_W] //Thá»i gian auto fill cÃ  phÃª tá»« tÃ¡ch Ä‘Ã¡ sang silo
#define vacuumSetFlag_R_CP      iMemHMI_CP[vacuumSetFlag_W] //Báº­t táº¯t pid vacuum
#define vacuumSetpoint_R_CP     iMemHMI_CP[vacuumSetpoint_W] //Setpoint cá»§a vacuum
#define minPT_R_CP              iMemHMI_CP[minPT_W]  //Giá»›i háº¡n min Pressure transmitter
#define maxPT_R_CP              iMemHMI_CP[maxPT_W]  //Giá»›i háº¡n max Pressure transmitter
#define wuTime_R_CP             iMemHMI_CP[wuTime_W]  //Thá»i gian warm up
#define wuTemp_R_CP             iMemHMI_CP[wuTemp_W]  //Nhiá»‡t Ä‘á»™ warm up

//----------------------End

//----------------------Data convert
#define afterburnerSet_R_CV dataConvert[0]  //*10
#define turnGasPoint_R_CV   dataConvert[1]  //*10
#define chTolerange_R_CV    dataConvert[2]  //*10
#define yellowPhase_R_CV    dataConvert[3]  //*10
#define fcsPhase_R_CV       dataConvert[4]  //*10
#define chargeTemp_R_CV     dataConvert[5]  //*10
#define btSV_R_CV           dataConvert[6]  //*10
#define preCool_R_CV        dataConvert[7]  //*10
//----------------------End

//----------------------Coil Register
//Write
#define SAMPLE_COIL_W   1 //Báº­t giáº£n Ä‘á»“
#define LOCK_BUTTON_W   2 //Lock save
#define LOCK_START_W    3 //Lock start
#define LOCK_DEL_W      4 //Macro trÃªn HMI
#define LOCK_CHARGE_W   5 //Macro trÃªn HMI
#define LOCK_FEEDER_W   6 //Macro trÃªn HMI
#define LOCK_SELECT     7 //

//Read
#define SAMPLE_COIL_R         cAddress[SAMPLE_COIL_W]
#define LOCK_BUTTON_R         cAddress[LOCK_BUTTON_W]
#define LOCK_START_R          cAddress[LOCK_START_W]
#define LOCK_FEEDER_R         cAddress[LOCK_FEEDER_W]

//Read CP
#define SAMPLE_COIL_R_CP      cAddress_CP[SAMPLE_COIL_W]
#define LOCK_BUTTON_R_CP      cAddress_CP[LOCK_BUTTON_W]
#define LOCK_START_R_CP       cAddress_CP[LOCK_START_W]
#define LOCK_FEEDER_R_CP      cAddress_CP[LOCK_FEEDER_W]

//----------------------End

//----------------------IO relay Coil Register
#define CH1_IO_RL_W   0 //KÃ­ch hoáº¡t relay 1, relay modbus module
#define CH2_IO_RL_W   1 //KÃ­ch hoáº¡t relay 2, relay modbus module
#define CH3_IO_RL_W   2 //KÃ­ch hoáº¡t relay 3, relay modbus module
#define CH4_IO_RL_W   3 //KÃ­ch hoáº¡t relay 4, relay modbus module
#define CH5_IO_RL_W   4 //KÃ­ch hoáº¡t relay 5, relay modbus module
#define CH6_IO_RL_W   5 //KÃ­ch hoáº¡t relay 6, relay modbus module
#define CH7_IO_RL_W   6 //KÃ­ch hoáº¡t relay 7, relay modbus module
#define CH8_IO_RL_W   7 //KÃ­ch hoáº¡t relay 8, relay modbus module
//END

//HMI ScreenNumber
#define SCR_SELECT  1
#define SCR_MANUAL  2
#define SCR_AUTO    3
#define SCR_CONNECT 4
#define SCR_CONFIG  5
#define SCR_MULTI   6
#define SCR_YESNO   9

//----------------------End

//----------------------Define Modbus slave
boolean Start_btn_PC;
boolean Ignition_btn_PC;
boolean Charge_btn_PC;
boolean Drop_btn_PC;
boolean Escape_btn_PC;
boolean MiCool_btn_PC;


//LÆ°u táº¡m Ä‘á»ƒ so sÃ¡nh
boolean Start_btn_PC_CP;
boolean Ignition_btn_PC_CP;
boolean Charge_btn_PC_CP;
boolean Drop_btn_PC_CP;
boolean Escape_btn_PC_CP;
boolean MiCool_btn_PC_CP;
//----------------------End

//----------------------Define analog
// #define BTN_HMI_COOLING_ON  nodeHMI.writeSingleRegister(AIRFLOW_HMI_W, airflowPercent);
//----------------------End

//----------------------Define analog

//Max analog input value
SimpleKalmanFilter airKalFil(0.5, 100, 0.5);
SimpleKalmanFilter gasBTKalFil(2, 2, 0.01);
SimpleKalmanFilter drumBTKalFil(2, 2, 0.01);

#if defined(V300)
uint16_t CH1AInMax = 630;
uint16_t CH2AInMax = 630;
uint16_t CH3AInMax = 630;
#elif defined(V350)
uint16_t CH1AInMax = 1015;
uint16_t CH2AInMax = 1015;
uint16_t CH3AInMax = 1015;
#elif defined(V400)
// Giá trị mặc định V400 thấp hơn để VR air/gas lên đủ 100% trước khi có file calib SD.
uint16_t CH1AInMax = 650;
uint16_t CH2AInMax = 650;
uint16_t CH3AInMax = 650;
#endif

const float alpha = 0.5f;                          // EMA smoothing factor cho analog input

int16_t airflowAI, drumAI, gasAI;                  //Source VR
int16_t airflowKal, drumKal, gasKal;               //Kalman filter
int16_t airflowPC, drumPC, gasPC, svPC, svPC_CP, underSV_PC, underSV_CP;   //Source PC
int16_t airflowAUTO, drumAUTO, gasAUTO;            //Source AUTO

// Biáº¿n ná»™i bá»™ cho cháº¿ Ä‘á»™ airflow khi rang AUTO â€” khÃ´ng dÃ¹ng vacuumSetFlag_R/vacuumSetpoint_R
// Ä‘á»ƒ trÃ¡nh xung Ä‘á»™t vá»›i rwMemHMI() ghi Ä‘Ã¨ iMemHMI[] má»—i loop
bool    autoVacPIDEn = false;   // true = dÃ¹ng PID Ã¡p suáº¥t (tá»« SD profile)
int16_t autoVacSP    = 0;       // setpoint Pa cho PID khi rang AUTO

// uint16_t f_airflowAI;
int16_t airflowPercent, drumPercent, gasPercent;    //Source VR

uint16_t drumHz;

//Äiá»u hÆ°á»›ng khiá»ƒn analog
uint8_t naviSourceGAS = 0;
uint8_t naviSourceAIR = 0;
uint8_t naviSourceDRUM = 0;

#define SOURCE_AI_VR   0
#define SOURCE_AI_PC   1
#define SOURCE_AI_AUTO 2

uint16_t minDAC_airflow, maxDAC_airflow;
uint16_t minDAC_gas, maxDAC_gas;

uint16_t mapDAC_airflow;
uint16_t mapDAC_gas;

//----------------------End

//----------------------Define SPI/SD card
File tempFile;
File sdLogFile;   // file handle giá»¯ má»Ÿ suá»‘t quÃ¡ trÃ¬nh log (trÃ¡nh open/close má»—i giÃ¢y)

char strProfileName[12] = "";
const char* strLog = "";
const char* SDLogSTEP = "";

boolean sdLogStartEn = false;
boolean sdLogDataEn = false;
boolean sdLogEndEn = false;
boolean sdRemoveAll = false;

uint16_t timeAbsolute = 0;         // GiÃ¢y Ä‘áº¿m tá»« khi báº¯t Ä‘áº§u log (Start button)
uint16_t timeChargeAbsolute = 0;   // timeAbsolute táº¡i thá»i Ä‘iá»ƒm CHARGE
uint16_t timeTPAbsolute     = 0;   // timeAbsolute táº¡i thá»i Ä‘iá»ƒm TP
uint16_t timeDRYeAbsolute   = 0;   // timeAbsolute táº¡i thá»i Ä‘iá»ƒm DRYe
uint16_t timeFCsAbsolute    = 0;   // timeAbsolute táº¡i thá»i Ä‘iá»ƒm FCs
uint16_t timeDROPAbsolute   = 0;   // timeAbsolute táº¡i thá»i Ä‘iá»ƒm DROP
boolean  timeAbsoluteEn = false;   // KÃ­ch hoáº¡t Ä‘áº¿m timeAbsolute
boolean  sdChargeHappened = false; // Flag: Ä‘Ã£ qua CHARGE (Ä‘á»ƒ ghi Time2)
uint8_t  sdChargeHH = 0;          // Giá» RTC táº¡i thá»i Ä‘iá»ƒm CHARGE (lÆ°u vÃ o CSV header Time:)
uint8_t  sdChargeMM = 0;          // PhÃºt RTC táº¡i thá»i Ä‘iá»ƒm CHARGE
uint8_t  sdStartDD = 0;           // NgÃ y RTC táº¡i thá»i Ä‘iá»ƒm báº¯t Ä‘áº§u log
uint8_t  sdStartMM = 0;           // ThÃ¡ng RTC táº¡i thá»i Ä‘iá»ƒm báº¯t Ä‘áº§u log
uint16_t sdStartYYYY = 0;         // NÄƒm RTC táº¡i thá»i Ä‘iá»ƒm báº¯t Ä‘áº§u log

//Táº£i data tá»« sd card vÃ o array
boolean reSDFlag = false;

long sdMillis = 0;
long calSdMillis = 0;

const char* dataR = "";
boolean sStr = false;

char inStr[1] = "";
char inDataStr[1] = "";
boolean sDataStr = false;

char sdCsvPendingEvent[8] = "";  // Event Ä‘ang chá» ghi vÃ o CSV (set bá»Ÿi programScan, tiÃªu thá»¥ bá»Ÿi sdLogWrite)

#define PROFILE_MAX_SECONDS 2100  // Lưu tối đa 35 phút profile, mỗi phần tử tương ứng 1 giây

uint16_t sdTempData[20];
uint16_t sdTiRoast[PROFILE_MAX_SECONDS];
uint16_t sdBT[PROFILE_MAX_SECONDS];
uint16_t sdET[PROFILE_MAX_SECONDS];
uint8_t  sdAirflow[PROFILE_MAX_SECONDS];
uint8_t  sdGas[PROFILE_MAX_SECONDS];
uint8_t  sdDrum[PROFILE_MAX_SECONDS];
int16_t  sdRorBT[PROFILE_MAX_SECONDS];
uint8_t  sdVacuumSetFlag[PROFILE_MAX_SECONDS];   // vacuumSetFlag táº¡i má»—i giÃ¢y (0=direct, 1=PID)
int16_t  sdVacuumSetpoint[PROFILE_MAX_SECONDS];  // vacuumSetpoint (Pa) táº¡i má»—i giÃ¢y

#define sdTempTi      sdTempData[0] //GÃ¡n táº¡m - Time - Sd
#define sdTempBT      sdTempData[1] //GÃ¡n táº¡m - BT - Sd
#define sdTempET      sdTempData[2] //GÃ¡n táº¡m - ET - Sd
#define sdTempAir     sdTempData[3] //GÃ¡n táº¡m - Air - Sd
#define sdTempGas     sdTempData[4] //GÃ¡n táº¡m - Gas - Sd
#define sdTempDrum    sdTempData[5] //GÃ¡n táº¡m - Drum - Sd
#define sdTempRorBT   sdTempData[6] //GÃ¡n táº¡m - rorBT - Sd
#define sdTempVacFlag sdTempData[7] //GÃ¡n táº¡m - vacuumSetFlag - Sd
#define sdTempVacSP   sdTempData[8] //GÃ¡n táº¡m - vacuumSetpoint - Sd

//Program
uint8_t sdReadStep=0;

#define SD_0 0
#define SD_1 1
#define SD_2 2
#define SD_3 3
#define SD_4 4

//----------------------End


//-----------------------IO CONFIG

uint8_t gasSignal=0;
uint8_t swSignal=0; // 0: Serial bluetooth, 1: Serial Computer.
uint16_t tunePercent = 0;  // shared progress bar -- only rwHMI_2() writes to HMI
#if defined(V300)
#define CH3_ANALOG  PC1
#define CH2_ANALOG  PC2
#define CH1_ANALOG  PC3

#define CH6_INPUT   PA15
#define CH5_INPUT   PA8
#define CH4_INPUT   PB15
#define CH3_INPUT   PB14
#define CH2_INPUT   PB13
#define CH1_INPUT   PB12                              

#define SWITCH_1    PB4
#define SWITCH_2    PB3    

#define CH1_RL      PC13
#define CH2_RL      PA4
#define CH3_RL      PD2
#define CH4_RL      PC12
#define CH5_RL      PC5  
#define CH6_RL      PB0 
#define CH7_RL      PB1
#define CH8_RL      PB2

#define ERRO        PA0
#define BUZZER      PA1
#define chipSelect  PC4
#elif defined(V350)
#define CH3_ANALOG  PC2
#define CH2_ANALOG  PC1
#define CH1_ANALOG  PC0

#define CH1_DAC     PB6 //Air
#define CH2_DAC     PB7

#define CH6_INPUT   PA15
#define CH5_INPUT   PA8
#define CH4_INPUT   PB15
#define CH3_INPUT   PB13
#define CH2_INPUT   PB14
#define CH1_INPUT   PB12                              

#define SWITCH_1    PB4
#define SWITCH_2    PB3    

#define CH1_RL      PA4
#define CH2_RL      PD2
#define CH3_RL      PC12
#define CH4_RL      PC5
#define CH5_RL      PB0  
#define CH6_RL      PB1 
#define CH7_RL      PB2
#define CH8_RL      PB3

#define ERRO        PA0
#define BUZZER      PA1
#define chipSelect  PC4
#elif defined(V400)
#define CH3_ANALOG  PC1
#define CH2_ANALOG  PC2
#define CH1_ANALOG  PC3

#define CH6_INPUT   PA15
#define CH5_INPUT   PA11
#define CH4_INPUT   PB15
#define CH3_INPUT   PB14
#define CH2_INPUT   PB13
#define CH1_INPUT   PB12                              

#define SWITCH_1    PB4
#define SWITCH_2    PB3    

#define CH1_RL      PA0
#define CH2_RL      PA1
#define CH3_RL      PD2
#define CH4_RL      PC12
#define CH5_RL      PC4  
#define CH6_RL      PB0 
#define CH7_RL      PB1
#define CH8_RL      PB2


#define ERRO        PC13
#define BUZZER      PA4
#define chipSelect  PC5
#endif

#define BUZZ_ON     digitalWrite(BUZZER, HIGH)
#define BUZZ_OFF    digitalWrite(BUZZER, LOW)

#define chBTFlag        MACHINE_HAS_BT_TEMP_CONTROLLER
#define chETFlag        MACHINE_HAS_ET_TEMP_CONTROLLER
#define chHMIFlag       true
#define chAirFlag       MACHINE_HAS_AIR_INVERTER
#define chChamberFlag   false
#define chDrumFlag      MACHINE_HAS_DRUM_SPEED_CONTROL
#define chIORelayFlag   MACHINE_HAS_IO_RELAY_MODULE
#define chSDFlag        1

#define READ_CH1    digitalRead(CH1_INPUT)
#define READ_CH2    digitalRead(CH2_INPUT)
#define READ_CH3    digitalRead(CH3_INPUT)
#define READ_CH4    digitalRead(CH4_INPUT)
#define READ_CH5    digitalRead(CH5_INPUT)
#define READ_CH6    digitalRead(CH6_INPUT)
#define READ_SWITCH_1   digitalRead(SWITCH_1)
#define READ_SWITCH_2   digitalRead(SWITCH_2)

#define CH1_RL_ON   digitalWrite(CH1_RL, HIGH)
#define CH1_RL_OFF  digitalWrite(CH1_RL, LOW) 

#define CH2_RL_ON   digitalWrite(CH2_RL, HIGH) 
#define CH2_RL_OFF  digitalWrite(CH2_RL, LOW) 

#define CH3_RL_ON   digitalWrite(CH3_RL, HIGH) 
#define CH3_RL_OFF  digitalWrite(CH3_RL, LOW) 

#define CH4_RL_ON   digitalWrite(CH4_RL, HIGH) 
#define CH4_RL_OFF  digitalWrite(CH4_RL, LOW) 

#define CH5_RL_ON   digitalWrite(CH5_RL, HIGH) 
#define CH5_RL_OFF  digitalWrite(CH5_RL, LOW)

#define CH6_RL_ON   digitalWrite(CH6_RL, HIGH) 
#define CH6_RL_OFF  digitalWrite(CH6_RL, LOW)

#define CH7_RL_ON   digitalWrite(CH7_RL, HIGH) 
#define CH7_RL_OFF  digitalWrite(CH7_RL, LOW)

#define CH8_RL_ON   digitalWrite(CH8_RL, HIGH) 
#define CH8_RL_OFF  digitalWrite(CH8_RL, LOW)

#define SWITCH_1_ON   digitalWrite(SWITCH_1, HIGH)
#define SWITCH_1_OFF  digitalWrite(SWITCH_1, LOW)

#define SWITCH_2_ON   digitalWrite(SWITCH_2, HIGH)
#define SWITCH_2_OFF  digitalWrite(SWITCH_2, LOW) 

void ConfigIO(){
    pinMode(CH1_INPUT, INPUT);
    pinMode(CH2_INPUT, INPUT);
    pinMode(CH3_INPUT, INPUT);
    pinMode(CH4_INPUT, INPUT);
    pinMode(CH5_INPUT, INPUT);
    pinMode(CH6_INPUT, INPUT); 

    pinMode(BUZZER, OUTPUT);          // Buzzer

    pinMode(CH1_RL, OUTPUT);          
    pinMode(CH2_RL, OUTPUT);          
    pinMode(CH3_RL, OUTPUT);          
    pinMode(CH4_RL, OUTPUT);          
    pinMode(CH5_RL, OUTPUT);          
    pinMode(CH6_RL, OUTPUT);          
    pinMode(CH7_RL, OUTPUT);          
    pinMode(CH8_RL, OUTPUT); 

#ifdef V350
    pinMode(CH1_DAC, OUTPUT);          
    pinMode(CH2_DAC, OUTPUT);   
    analogWriteResolution(12);
#endif

    SerialComputer.println("=> IO OK");         
}
//-------------------------------------------------------END-------------------------------------------------------//

//-------------------------------------------------------Timer
#define TIMER0_INTERVAL_MS  1000

uint16_t countTimer = 0;

// Init STM32 timer TIM1
STM32Timer ITimer0(TIM1);

void timerPoll_1000ms();

void configTimer(){
  // Interval in microsecs
  if (ITimer0.attachInterruptInterval(TIMER0_INTERVAL_MS * 1000, timerPoll_1000ms))
  {
    Serial.print(F("Starting  Timer0 OK, millis() = ")); Serial.println(millis());
  }
  else
    Serial.println(F("Can't set ITimer0. Select another freq. or timer"));
}

void ModbusRS485Config(){
    SerialHmi.begin(HMI_SERIAL_BAUD);
    SerialModbus.begin(MACHINE_RS485_BAUD);
    SerialComputer.begin(DEBUG_SERIAL_BAUD);
    SerialBluetooth.begin(SCALE_SERIAL_BAUD);

    nodeHMI.begin(HMI_MODBUS_ID, SerialHmi);        // HMI
#if MACHINE_HAS_ET_TEMP_CONTROLLER
    nodeET.begin(ET_TEMP_MODBUS_ID, SerialModbus);  // Read RS485 Temperature ET
#endif
#if MACHINE_HAS_BT_TEMP_CONTROLLER
    nodeBT.begin(BT_TEMP_MODBUS_ID, SerialModbus);  // Read RS485 Temperature BT
#endif
#if MACHINE_HAS_DRUM_SPEED_CONTROL
    nodeDrum.begin(DRUM_INV_MODBUS_ID, SerialModbus); // Read Drum Inverter
#endif
#if MACHINE_HAS_AIR_INVERTER
    nodeAir.begin(AIR_INV_MODBUS_ID, SerialModbus); // Read Airflow Inverter
#endif
#if MACHINE_HAS_IO_RELAY_MODULE
    nodeIORelay.begin(IO_RELAY_MODBUS_ID, SerialModbus); // I/O Relay
#endif

    SerialComputer.println("=> Modbus Master RTU OK");
}



