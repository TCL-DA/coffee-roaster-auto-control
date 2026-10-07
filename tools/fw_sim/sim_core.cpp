// Board ảo OTL — chạy firmware THẬT (src/main.cpp + include/*.h) trên PC.
//
// Phần cứng giả lập ở đây:
//   * thời gian thực (millis/micros/delay), ngắt TIM1 gọi bù đúng chu kỳ
//   * cổng HMI (Serial1)  -> bộ mô phỏng Delta HMIApp (F:\Project\112_Quanly\mcp-dpa\emu):
//       thanh ghi < 2000 = W4xxxx của {Link2} qua pipe \\.\pipe\otl_hmi_link
//       thanh ghi >= 2000 = $M qua Modbus TCP 127.0.0.1:502 của HMIApp
//       coil c = B(c+1) qua pipe
//   * cổng RS485 thiết bị (Serial2, board V400) -> mô hình: đồng hồ BT (ID 1), ET (ID 2),
//     biến tần trống (4), biến tần gió + cảm biến áp (5), module relay (7)
//   * DAC MCP4725 gas (0x61) / gió (0x60) -> mô hình nhiệt
//   * relay + đầu vào số (board V400) -> mô hình máy
//   * thẻ SD = thư mục tools/fw_sim/sdcard (đổi bằng biến OTL_SD_DIR)
//   * slave mbs (Artisan / app Roast Lab) -> Modbus TCP 0.0.0.0:1502 (OTL_FW_SLAVE_PORT)
//   * kênh điều khiển board ảo: pipe \\.\pipe\otl_fw_sim (lệnh chữ: status, set ...)
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <mmsystem.h>

#include <atomic>
#include <cstdio>
#include <deque>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include "Arduino.h"
#include "ModbusMaster.h"
#include "ModbusRTU.h"
#include "SD.h"
#include "SPI.h"
#include "Wire.h"

// ------------------------------------------------------------------ ngoại vi + đối tượng core
static USART_TypeDef u1{1}, u2{2}, u3{3}, u4{4}, u5{5};
USART_TypeDef *USART1 = &u1, *USART2 = &u2, *USART3 = &u3, *UART4 = &u4, *UART5 = &u5;
static TIM_TypeDef t1{1}, t2{2}, t3{3}, t4{4};
TIM_TypeDef *TIM1 = &t1, *TIM2 = &t2, *TIM3 = &t3, *TIM4 = &t4;
HardwareSerial Serial((USART_TypeDef *)nullptr);
HardwareSerial Serial2(USART2);
SDClass SD;
TwoWire Wire;
SPIClass SPI;

// biến firmware (Define.h) mà mô hình cần đọc
extern int16_t iMemHMI[62];

// ------------------------------------------------------------------ cấu hình board V400
// (Define.h: V400) — số chân theo stub/Arduino.h: PA0=0, PB0=16, PC0=32, PD0=48
static const int P_GAS_RL = PA0, P_COOL_RL = PA1, P_CHARGE_RL = PD2, P_DROP_RL = PC12,
                 P_ESCAPE_RL = PC4, P_AB_RL = PB0, P_GAS_SIGNAL = PB12, P_SWITCH1 = PB4,
                 P_BUZZER = PA4, P_FEEDER_RL = PB2;   // CH8_RL (V400) = máy hút liệu (IOConfig.h: FEEDER_BTN_R)
static const int PORT_HMI = 1, PORT_DEV = 2, PORT_SCALE = 3, PORT_DEBUG = 4;

// ------------------------------------------------------------------ thời gian
static LARGE_INTEGER g_freq, g_t0;
// L47: OTL_SIM_TOC = hệ số chạy nhanh của board ảo (mặc định 1 = thời gian thực). HMIApp vẫn chạy thời gian thực.
static double g_toc = 1.0;
static uint64_t now_us()
{
    LARGE_INTEGER t;
    QueryPerformanceCounter(&t);
    return (uint64_t)((double)(t.QuadPart - g_t0.QuadPart) * 1e6 * g_toc / (double)g_freq.QuadPart);
}

static void (*g_isr)() = nullptr;
static uint64_t g_isr_period = 0, g_isr_next = 0;
static bool g_in_poll = false;
static std::mutex g_plant_mx;
void sim_poll();

void sim_attach_isr(uint32_t us, void (*cb)())
{
    g_isr = cb;
    g_isr_period = us;
    g_isr_next = now_us() + us;
}

uint32_t millis()
{
    sim_poll();
    return (uint32_t)(now_us() / 1000);
}
uint32_t micros() { return (uint32_t)now_us(); }
void delay(uint32_t ms)
{
    uint64_t end = now_us() + (uint64_t)ms * 1000;
    sim_poll();
    while (now_us() < end) {
        Sleep(1);
        sim_poll();
    }
}
void delayMicroseconds(uint32_t us)
{
    uint64_t end = now_us() + us;
    while (now_us() < end) {
    }
}
void yield() { sim_poll(); }

long random(long howbig) { return howbig > 0 ? rand() % howbig : 0; }
long random(long a, long b) { return b > a ? a + rand() % (b - a) : a; }
void randomSeed(unsigned long s) { srand((unsigned)s); }

char *dtostrf(double val, signed char width, unsigned char prec, char *s)
{
    sprintf(s, "%*.*f", (int)width, (int)prec, val);
    return s;
}

// ------------------------------------------------------------------ log
static FILE *g_log = nullptr;
static std::string g_line[8];
static void log_line(const char *tag, const std::string &s)
{
    SYSTEMTIME st;
    GetLocalTime(&st);
    char ts[32];
    snprintf(ts, sizeof(ts), "%02d:%02d:%02d.%03d", st.wHour, st.wMinute, st.wSecond, st.wMilliseconds);
    printf("%s %s %s\n", ts, tag, s.c_str());
    fflush(stdout);
    if (g_log) {
        fprintf(g_log, "%s %s %s\n", ts, tag, s.c_str());
        fflush(g_log);
    }
}

void sim_serial_write(int port, uint8_t b)
{
    if (port != PORT_DEBUG && port != 0)
        return;  // cổng HMI/RS485/cân: không có dây thật
    std::string &L = g_line[port == 0 ? 0 : 1];
    if (b == '\n') {
        if (!L.empty() && L.back() == '\r')
            L.pop_back();
        log_line("[FW]", L);
        L.clear();
    } else if (L.size() < 4000) {
        L += (char)b;
    }
}

// bộ đệm nhận: cổng cân Bluetooth (dòng "GS,NN.N,kg")
static std::deque<uint8_t> g_rx[8];
int sim_serial_available(int port) { return (port >= 0 && port < 8) ? (int)g_rx[port].size() : 0; }
int sim_serial_read(int port)
{
    if (port < 0 || port >= 8 || g_rx[port].empty())
        return -1;
    int c = g_rx[port].front();
    g_rx[port].pop_front();
    return c;
}
int sim_serial_peek(int port) { return (port >= 0 && port < 8 && !g_rx[port].empty()) ? g_rx[port].front() : -1; }

// ------------------------------------------------------------------ chân IO
static uint8_t g_pin_mode[SIM_NUM_PINS], g_pin_out[SIM_NUM_PINS];
void pinMode(uint32_t p, uint32_t m)
{
    if (p < SIM_NUM_PINS)
        g_pin_mode[p] = (uint8_t)m;
}
static const char *pin_name(int p)
{
    switch (p) {
    case PA0: return "RL1 GAS";
    case PA1: return "RL2 LAM_MAT";
    case PD2: return "RL3 NAP_LIEU";
    case PC12: return "RL4 XA_LIEU";
    case PC4: return "RL5 ESCAPE";
    case PB0: return "RL6 AFTERBURNER";
    case PB1: return "RL7";
    case PB2: return "RL8";
    case PA4: return "BUZZER";
    case PC13: return "LED_LOI";
    default: return nullptr;
    }
}
void digitalWrite(uint32_t p, uint32_t v)
{
    if (p >= SIM_NUM_PINS)
        return;
    uint8_t nv = v ? 1 : 0;
    if (g_pin_out[p] != nv) {
        g_pin_out[p] = nv;
        const char *n = pin_name((int)p);
        if (n && p != (uint32_t)P_BUZZER)
            log_line("[IO]", std::string(n) + (nv ? " = BAT" : " = TAT"));
    }
}

// ------------------------------------------------------------------ mô hình máy rang (30 kg)
struct Plant {
    double amb = 30.0;
    double et = 30.0, bean = 30.0, drum_wall = 30.0;
    double probe = 30.0;                 // số đầu dò BT (có trễ) — bean là nhiệt THẬT của khối hạt
    double gas_dac = 0, air_dac = 0;     // 0..4095
    bool flame = false;
    double beans_kg = 0;                 // hạt trong lồng
    double hopper_kg = 30.0;             // hạt chờ trên phễu máy rang (trên cửa nạp)
    double source_kg = 300.0;            // L47: phễu NGUỒN đặt trên cân Bluetooth — máy hút liệu hút từ đây lên phễu máy rang
    bool feeder = false;
    double drum_hz_set = 0, drum_hz = 0; // biến tần trống (×100)
    double vac_pa = 0;
    bool relay_mod[8] = {false};         // module relay ngoài ID 7
    bool flame_fault = false;            // giả lập mất lửa
    int bt_fault = 0, et_fault = 0;      // 1 = đồng hồ không trả lời
    uint16_t bt_sv = 0;
    uint16_t air_pid0800 = 0;
    bool prev_charge = false, prev_drop = false;
    double charge_t = -1;
} P;

static double gas_pct() { return P.gas_dac * 100.0 / 4095.0; }
static double air_pct() { return P.air_dac * 100.0 / 4095.0; }

static void plant_step(double dt)
{
    std::lock_guard<std::mutex> lk(g_plant_mx);
    bool gas_rl = g_pin_out[P_GAS_RL];
    P.flame = gas_rl && gas_pct() > 2.0 && !P.flame_fault;
    // trống quay theo biến tần (ramp 20 Hz/s)
    double d = P.drum_hz_set - P.drum_hz;
    double stepv = 2000.0 * dt;
    P.drum_hz += (d > stepv) ? stepv : (d < -stepv ? -stepv : d);
    // nạp / xả hạt theo cạnh lên relay
    bool ch = g_pin_out[P_CHARGE_RL], dr = g_pin_out[P_DROP_RL];
    if (ch && !P.prev_charge && P.hopper_kg > 0.5) {
        P.beans_kg = P.hopper_kg;
        P.hopper_kg = 0;
        P.bean = P.amb;
        P.charge_t = 0;
        log_line("[MAY]", "NAP HAT vao long: " + std::to_string((int)P.beans_kg) + " kg");
    }
    if (dr && !P.prev_drop && P.beans_kg > 0) {
        log_line("[MAY]", "XA HAT ra mam lam mat, BT luc xa = " + std::to_string((int)P.probe) + " C");
        P.beans_kg = 0;
    }
    P.prev_charge = ch;
    P.prev_drop = dr;
    // L47: máy hút liệu (relay CH8) — 0,5 kg/s từ phễu nguồn (cân) sang phễu máy rang
    bool fd = g_pin_out[P_FEEDER_RL] != 0;
    if (fd != P.feeder) {
        P.feeder = fd;
        log_line("[MAY]", std::string("HUT LIEU ") + (fd ? "BAT" : "TAT") + ", phe u nguon = " + std::to_string((int)P.source_kg) + " kg");
    }
    if (fd && P.source_kg > 0) {
        double m = 0.5 * dt;
        if (m > P.source_kg) m = P.source_kg;
        P.source_kg -= m;
        P.hopper_kg += m;
    }
    if (P.charge_t >= 0)
        P.charge_t += dt;
    // Nhiệt — hệ số KHỚP THEO MẺ THẬT ngày 18/04/2026 (F:/Artisan/Profile/1904/1.CSV, máy 30 kg, 03/10/2026):
    // đưa gas/gió từng giây của mẻ đó vào thì đầu dò mô hình lệch BT thật tối đa 2 °C từ TP tới DROP
    // (RMS 2,3 °C cả mẻ). Bản trước nóng gấp ~10 lần máy thật: gas 50 % là ET vọt quá 1000 °C, firmware
    // cắt gas an toàn (ET > 350) trước khi kịp rang. Hồ sơ không có số ET nên ET ở đây là suy ra.
    //   A   công suất đầu đốt (°C/s mỗi % gas)        B   thất thoát theo gió khi CÓ hạt
    //   BE  thất thoát khi lồng RỖNG (khí nóng đi thẳng ra ống khói; chọn để gas 50 % cân bằng ~320 °C)
    //   C   khí -> hạt   D   khí -> vách   E   vách nóng lên   K1/K2  hạt nhận từ khí / từ vách
    //   TAU trễ đầu dò khi có hạt (s)   W, TAU_E  lồng rỗng: đầu dò = W·ET + (1−W)·vách
    const double A = 0.05371, B = 0.00479, BE = 0.0168, C = 0.02428, D = 0.00100, E = 0.00177;
    const double K1 = 0.00010, K2 = 0.00532, TAU = 33.0, W = 0.20, TAU_E = 20.3;
    double airf = 0.25 + 0.75 * air_pct() / 100.0;
    double q_burner = P.flame ? gas_pct() * A : 0.0;
    double beans = P.beans_kg / 30.0;                           // 1 = mẻ 30 kg
    bool loaded = P.beans_kg > 0;
    double q_loss = (P.et - P.amb) * (loaded ? B : BE) * airf;  // gió hút nhiệt ra ống khói
    double q_beans = (P.et - P.bean) * C * beans;               // nhiệt truyền vào hạt
    double q_wall = (P.et - P.drum_wall) * D;
    P.et += dt * (q_burner - q_loss - q_beans - q_wall);
    P.drum_wall += dt * (P.et - P.drum_wall) * E;
    if (loaded) {
        P.bean += dt * ((P.et - P.bean) * K1 + (P.drum_wall - P.bean) * K2);
        P.probe += dt * (P.bean - P.probe) / TAU;               // đầu dò chìm trong hạt, có trễ
    } else {
        P.bean = P.amb;
        P.probe += dt * ((W * P.et + (1.0 - W) * P.drum_wall) - P.probe) / TAU_E;  // đầu dò đo khí + vách
    }
    if (P.et < P.amb)
        P.et = P.amb;
    // áp chân không theo gió
    P.vac_pa = -(5.0 + 110.0 * air_pct() / 100.0);
}

void sim_dac_set(uint8_t addr, uint16_t v)
{
    std::lock_guard<std::mutex> lk(g_plant_mx);
    if (addr == 0x61)
        P.gas_dac = v;
    else if (addr == 0x60)
        P.air_dac = v;
}

int digitalRead(uint32_t p)
{
    std::lock_guard<std::mutex> lk(g_plant_mx);
    if (p == (uint32_t)P_GAS_SIGNAL)
        return P.flame ? 0 : 1;  // tích cực mức thấp: 0 = có tín hiệu gas/lửa
    if (p == (uint32_t)P_SWITCH1)
        return 1;                // công tắc cửa: không tác động
    if (p < SIM_NUM_PINS && g_pin_mode[p] == OUTPUT)
        return g_pin_out[p];
    return 1;                    // đầu vào kéo lên
}
int analogRead(uint32_t) { return 0; }
void analogWrite(uint32_t, int) {}
void analogReadResolution(int) {}
void analogWriteResolution(int) {}

// ------------------------------------------------------------------ HMI: pipe otl_hmi_link + TCP 502
static HANDLE g_hmi_pipe = INVALID_HANDLE_VALUE;
static SOCKET g_hmi_tcp = INVALID_SOCKET;
static uint64_t g_hmi_retry_us = 0;
static uint16_t g_tcp_tid = 0;
static int g_hmi_ok = -1;

static void hmi_close()
{
    if (g_hmi_pipe != INVALID_HANDLE_VALUE)
        CloseHandle(g_hmi_pipe);
    g_hmi_pipe = INVALID_HANDLE_VALUE;
    if (g_hmi_tcp != INVALID_SOCKET)
        closesocket(g_hmi_tcp);
    g_hmi_tcp = INVALID_SOCKET;
}

static bool hmi_open()
{
    if (g_hmi_pipe != INVALID_HANDLE_VALUE && g_hmi_tcp != INVALID_SOCKET)
        return true;
    if (now_us() < g_hmi_retry_us)
        return false;
    g_hmi_retry_us = now_us() + 1000000;  // thử lại mỗi 1 s
    if (g_hmi_pipe == INVALID_HANDLE_VALUE) {
        HANDLE h = CreateFileA("\\\\.\\pipe\\otl_hmi_link", GENERIC_READ | GENERIC_WRITE, 0, nullptr,
                               OPEN_EXISTING, 0, nullptr);
        if (h == INVALID_HANDLE_VALUE)
            return false;
        DWORD mode = PIPE_READMODE_MESSAGE;
        SetNamedPipeHandleState(h, &mode, nullptr, nullptr);
        g_hmi_pipe = h;
    }
    if (g_hmi_tcp == INVALID_SOCKET) {
        SOCKET s = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        sockaddr_in a{};
        a.sin_family = AF_INET;
        a.sin_port = htons(502);
        a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        DWORD to = 1000;
        setsockopt(s, SOL_SOCKET, SO_RCVTIMEO, (const char *)&to, sizeof(to));
        setsockopt(s, SOL_SOCKET, SO_SNDTIMEO, (const char *)&to, sizeof(to));
        BOOL nd = TRUE;
        setsockopt(s, IPPROTO_TCP, TCP_NODELAY, (const char *)&nd, sizeof(nd));
        if (connect(s, (sockaddr *)&a, sizeof(a)) != 0) {
            closesocket(s);
            return false;
        }
        g_hmi_tcp = s;
    }
    log_line("[SIM]", "da noi bo mo phong HMI (pipe otl_hmi_link + TCP 502)");
    return true;
}

static bool pipe_call(const std::vector<uint8_t> &req, std::vector<uint8_t> &rep)
{
    DWORD n = 0;
    if (!WriteFile(g_hmi_pipe, req.data(), (DWORD)req.size(), &n, nullptr))
        return false;
    rep.resize(4200);
    if (!ReadFile(g_hmi_pipe, rep.data(), (DWORD)rep.size(), &n, nullptr))
        return false;
    rep.resize(n);
    return n >= 1 && rep[0] == 1;
}

static std::vector<uint8_t> link_frame(char op, uint8_t kind, int32_t addr, uint16_t n)
{
    std::vector<uint8_t> f(8);
    f[0] = (uint8_t)op;
    f[1] = kind;
    memcpy(&f[2], &addr, 4);
    memcpy(&f[6], &n, 2);
    return f;
}

static bool tcp_txrx(const std::vector<uint8_t> &pdu, std::vector<uint8_t> &out)
{
    uint8_t hdr[7];
    g_tcp_tid++;
    uint16_t len = (uint16_t)(pdu.size() + 1);
    hdr[0] = g_tcp_tid >> 8; hdr[1] = g_tcp_tid & 0xFF; hdr[2] = 0; hdr[3] = 0;
    hdr[4] = len >> 8; hdr[5] = len & 0xFF; hdr[6] = 1;
    std::vector<uint8_t> buf(hdr, hdr + 7);
    buf.insert(buf.end(), pdu.begin(), pdu.end());
    if (send(g_hmi_tcp, (const char *)buf.data(), (int)buf.size(), 0) != (int)buf.size())
        return false;
    uint8_t rh[7];
    int got = 0;
    while (got < 7) {
        int r = recv(g_hmi_tcp, (char *)rh + got, 7 - got, 0);
        if (r <= 0)
            return false;
        got += r;
    }
    int body = ((rh[4] << 8) | rh[5]) - 1;
    out.resize(body);
    got = 0;
    while (got < body) {
        int r = recv(g_hmi_tcp, (char *)out.data() + got, body - got, 0);
        if (r <= 0)
            return false;
        got += r;
    }
    return body > 0 && !(out[0] & 0x80);
}

static uint8_t hmi_transact(uint8_t fc, uint16_t addr, uint16_t qty, const uint16_t *tx, uint16_t *rx,
                            uint16_t cap)
{
    if (!hmi_open()) {
        if (g_hmi_ok != 0)
            log_line("[SIM]", "CHUA noi duoc bo mo phong HMI — firmware se thay HMI loi Modbus");
        g_hmi_ok = 0;
        Sleep(20);
        return ModbusMaster::ku8MBResponseTimedOut;
    }
    g_hmi_ok = 1;
    std::vector<uint8_t> rep;
    bool ok = false;
    if ((fc == 3 || fc == 6 || fc == 16) && addr >= 2000) {
        // $M: Modbus TCP của HMIApp, cùng địa chỉ firmware dùng (2000+n = $Mn)
        std::vector<uint8_t> pdu = {fc, (uint8_t)(addr >> 8), (uint8_t)addr};
        if (fc == 3) {
            pdu.push_back(qty >> 8);
            pdu.push_back(qty & 0xFF);
            ok = tcp_txrx(pdu, rep);
            if (ok)
                for (uint16_t i = 0; i < qty && i < cap; i++)
                    rx[i] = (uint16_t)(rep[2 + 2 * i] << 8 | rep[3 + 2 * i]);
        } else if (fc == 6) {
            pdu.push_back(tx[0] >> 8);
            pdu.push_back(tx[0] & 0xFF);
            ok = tcp_txrx(pdu, rep);
        } else {
            pdu.push_back(qty >> 8);
            pdu.push_back(qty & 0xFF);
            pdu.push_back((uint8_t)(2 * qty));
            for (uint16_t i = 0; i < qty; i++) {
                pdu.push_back(tx[i] >> 8);
                pdu.push_back(tx[i] & 0xFF);
            }
            ok = tcp_txrx(pdu, rep);
        }
    } else if (fc == 3) {
        auto f = link_frame('R', 0, 40001 + addr, qty);
        ok = pipe_call(f, rep);
        if (ok)
            for (uint16_t i = 0; i < qty && i < cap; i++) {
                rx[i] = (uint16_t)(rep[1 + 2 * i] | rep[2 + 2 * i] << 8);
                // ghi lại thay đổi do HMI/người bấm tạo ra (vùng nút 40001..40060)
                static uint16_t last[1000];
                static bool seen[1000];
                uint32_t k = (uint32_t)addr + i;
                if (k < 60 && seen[k] && last[k] != rx[i])
                    log_line("[HMI]", "W" + std::to_string(40001 + k) + ": " + std::to_string(last[k]) +
                                          " -> " + std::to_string(rx[i]));
                if (k < 1000) {
                    last[k] = rx[i];
                    seen[k] = true;
                }
            }
    } else if (fc == 6 || fc == 16) {
        auto f = link_frame('W', 0, 40001 + addr, qty);
        for (uint16_t i = 0; i < qty; i++) {
            f.push_back(tx[i] & 0xFF);
            f.push_back(tx[i] >> 8);
        }
        ok = pipe_call(f, rep);
    } else if (fc == 1) {
        // coil c = B(c+1); bộ giả lập xử lý từng bit, đóng gói như ModbusMaster (LSB trước)
        uint8_t bytes[128] = {0};
        ok = true;
        for (uint16_t i = 0; i < qty && ok; i++) {
            auto f = link_frame('R', 1, addr + 1 + i, 1);
            ok = pipe_call(f, rep);
            if (ok && rep.size() >= 2 && (rep[1] & 1))
                bytes[i / 8] |= (uint8_t)(1 << (i % 8));
        }
        if (ok)
            for (uint16_t w = 0; w < (qty + 15) / 16 && w < cap; w++)
                rx[w] = (uint16_t)(bytes[2 * w] | bytes[2 * w + 1] << 8);
    } else if (fc == 5) {
        auto f = link_frame('W', 1, addr + 1, 1);
        f.push_back(tx[0] ? 1 : 0);
        ok = pipe_call(f, rep);
    }
    if (!ok) {
        hmi_close();
        return ModbusMaster::ku8MBResponseTimedOut;
    }
    Sleep(2);  // ~ 1 khung RTU @115200 cả đi lẫn về
    return ModbusMaster::ku8MBSuccess;
}

// ------------------------------------------------------------------ thiết bị RS485 (mô hình)
static uint8_t dev_transact(uint8_t slave, uint8_t fc, uint16_t addr, uint16_t qty, const uint16_t *tx,
                            uint16_t *rx, uint16_t cap)
{
    std::lock_guard<std::mutex> lk(g_plant_mx);
    Sleep(4);  // RS485 @38400
    switch (slave) {
    case 1:  // đồng hồ nhiệt BT (Delta DTx): đọc PV ×10
    case 2:  // ET
        if ((slave == 1 && P.bt_fault) || (slave == 2 && P.et_fault))
            return ModbusMaster::ku8MBResponseTimedOut;
        if (fc == 3) {
            double t = slave == 1 ? P.probe : P.et;
            double noise = ((rand() % 7) - 3) * 0.1;
            for (uint16_t i = 0; i < qty && i < cap; i++)
                rx[i] = (uint16_t)(int16_t)lround((t + noise) * 10.0);
            return 0;
        }
        if (fc == 6) {
            P.bt_sv = tx[0];
            return 0;
        }
        return ModbusMaster::ku8MBIllegalFunction;
    case 4:  // biến tần trống
        if (fc == 3) {
            for (uint16_t i = 0; i < qty && i < cap; i++)
                rx[i] = (uint16_t)lround(P.drum_hz);
            return 0;
        }
        if (fc == 6) {
            if (addr == 8193)
                P.drum_hz_set = tx[0];
            return 0;
        }
        return ModbusMaster::ku8MBIllegalFunction;
    case 5:  // biến tần gió + cảm biến áp nối ACI
        if (fc == 3) {
            uint16_t v = 0;
            if (addr == 8716) {
                // ACI 0..10000 tương ứng minPT..maxPT ($M49/$M50 firmware đọc từ HMI)
                double lo = iMemHMI[49], hi = iMemHMI[50];
                if (hi == lo) {
                    lo = -500;
                    hi = 500;
                }
                double raw = (P.vac_pa - lo) / (hi - lo) * 10000.0;
                v = (uint16_t)constrain((long)lround(raw), 0L, 10000L);
            } else if (addr == 2048) {
                v = P.air_pid0800;
            } else if (addr == 8451) {
                v = (uint16_t)lround(air_pct() * 50.0);  // 0..5000 = 0..50.00 Hz
            }
            for (uint16_t i = 0; i < qty && i < cap; i++)
                rx[i] = v;
            return 0;
        }
        if (fc == 6) {
            if (addr == 2048)
                P.air_pid0800 = tx[0];
            return 0;
        }
        return ModbusMaster::ku8MBIllegalFunction;
    case 7:  // module relay 8 kênh
        if (fc == 1) {
            uint16_t w = 0;
            for (uint16_t i = 0; i < qty && i < 16; i++)
                if (P.relay_mod[(addr + i) & 7])
                    w |= (uint16_t)(1 << i);
            if (cap)
                rx[0] = w;
            return 0;
        }
        if (fc == 5) {
            bool on = tx[0] != 0;
            if (P.relay_mod[addr & 7] != on) {
                P.relay_mod[addr & 7] = on;
                log_line("[IO]", "RELAY NGOAI CH" + std::to_string((addr & 7) + 1) + (on ? " = BAT" : " = TAT"));
                if ((addr & 7) == 0)
                    P.drum_hz_set = on ? (P.drum_hz_set > 0 ? P.drum_hz_set : 4000) : 0;
            }
            return 0;
        }
        return ModbusMaster::ku8MBIllegalFunction;
    default:
        return ModbusMaster::ku8MBResponseTimedOut;
    }
}

uint8_t sim_modbus_transact(int port, uint8_t slave, uint8_t fc, uint16_t addr, uint16_t qty, const uint16_t *tx,
                            uint16_t *rx, uint16_t cap)
{
    sim_poll();
    uint8_t r;
    if (port == PORT_HMI)
        r = hmi_transact(fc, addr, qty, tx, rx, cap);
    else if (port == PORT_DEV)
        r = dev_transact(slave, fc, addr, qty, tx, rx, cap);
    else
        r = ModbusMaster::ku8MBResponseTimedOut;
    sim_poll();
    return r;
}

// ------------------------------------------------------------------ slave mbs -> Modbus TCP 1502
static ModbusRTU *g_mbs = nullptr;
void sim_mbs_bind(ModbusRTU *m) { g_mbs = m; }
static SOCKET g_srv = INVALID_SOCKET;
static std::vector<SOCKET> g_cli;

static void mbs_serve_one(SOCKET c)
{
    uint8_t h[7];
    int r = recv(c, (char *)h, 7, MSG_PEEK);
    if (r < 7)
        return;
    int len = (h[4] << 8) | h[5];
    std::vector<uint8_t> fr(6 + len);
    int got = 0;
    while (got < (int)fr.size()) {
        int k = recv(c, (char *)fr.data() + got, (int)fr.size() - got, 0);
        if (k <= 0)
            return;
        got += k;
    }
    uint8_t fc = fr[7];
    uint16_t a = (uint16_t)(fr[8] << 8 | fr[9]);
    std::vector<uint8_t> pdu;
    if (fc == 3 || fc == 4) {
        uint16_t q = (uint16_t)(fr[10] << 8 | fr[11]);
        pdu = {fc, (uint8_t)(2 * q)};
        for (uint16_t i = 0; i < q; i++) {
            uint16_t v = g_mbs ? g_mbs->Hreg((uint16_t)(a + i)) : 0;
            pdu.push_back(v >> 8);
            pdu.push_back(v & 0xFF);
        }
    } else if (fc == 6) {
        if (g_mbs)
            g_mbs->Hreg(a, (uint16_t)(fr[10] << 8 | fr[11]));
        pdu.assign(fr.begin() + 7, fr.begin() + 12);
    } else if (fc == 16) {
        uint16_t q = (uint16_t)(fr[10] << 8 | fr[11]);
        for (uint16_t i = 0; i < q && g_mbs; i++)
            g_mbs->Hreg((uint16_t)(a + i), (uint16_t)(fr[13 + 2 * i] << 8 | fr[14 + 2 * i]));
        pdu.assign(fr.begin() + 7, fr.begin() + 12);
    } else {
        pdu = {(uint8_t)(fc | 0x80), 1};
    }
    std::vector<uint8_t> out(fr.begin(), fr.begin() + 7);
    out[4] = (uint8_t)((pdu.size() + 1) >> 8);
    out[5] = (uint8_t)((pdu.size() + 1) & 0xFF);
    out.insert(out.end(), pdu.begin(), pdu.end());
    send(c, (const char *)out.data(), (int)out.size(), 0);
}

void ModbusRTU::task()
{
    sim_poll();
    if (g_srv == INVALID_SOCKET)
        return;
    SOCKET c = accept(g_srv, nullptr, nullptr);
    if (c != INVALID_SOCKET) {
        u_long nb = 1;
        ioctlsocket(c, FIONBIO, &nb);
        g_cli.push_back(c);
        log_line("[SIM]", "app/Artisan da noi vao slave mbs qua TCP");
    }
    for (size_t i = 0; i < g_cli.size();) {
        char b;
        int r = recv(g_cli[i], &b, 1, MSG_PEEK);
        if (r == 0 || (r < 0 && WSAGetLastError() != WSAEWOULDBLOCK)) {
            closesocket(g_cli[i]);
            g_cli.erase(g_cli.begin() + i);
            continue;
        }
        if (r > 0) {
            u_long nb = 0;
            ioctlsocket(g_cli[i], FIONBIO, &nb);
            mbs_serve_one(g_cli[i]);
            nb = 1;
            ioctlsocket(g_cli[i], FIONBIO, &nb);
        }
        i++;
    }
}

static void mbs_server_start()
{
    char e[16] = "1502";
    GetEnvironmentVariableA("OTL_FW_SLAVE_PORT", e, sizeof(e));
    g_srv = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    sockaddr_in a{};
    a.sin_family = AF_INET;
    a.sin_port = htons((u_short)atoi(e));
    a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    BOOL yes = TRUE;
    setsockopt(g_srv, SOL_SOCKET, SO_REUSEADDR, (const char *)&yes, sizeof(yes));
    if (bind(g_srv, (sockaddr *)&a, sizeof(a)) != 0 || listen(g_srv, 4) != 0) {
        closesocket(g_srv);
        g_srv = INVALID_SOCKET;
        log_line("[SIM]", std::string("khong mo duoc cong slave TCP ") + e);
        return;
    }
    u_long nb = 1;
    ioctlsocket(g_srv, FIONBIO, &nb);
    log_line("[SIM]", std::string("slave mbs (Artisan/app) mo o 127.0.0.1:") + e);
}

// ------------------------------------------------------------------ kênh điều khiển \\.\pipe\otl_fw_sim
static std::string sim_status()
{
    std::lock_guard<std::mutex> lk(g_plant_mx);
    char b[900];
    snprintf(b, sizeof(b),
             "{\"t_ms\":%u,\"bt\":%.1f,\"et\":%.1f,\"drum_wall\":%.1f,\"gas_pct\":%.1f,\"air_pct\":%.1f,"
             "\"flame\":%d,\"beans_kg\":%.1f,\"hopper_kg\":%.1f,\"drum_hz\":%.0f,\"drum_hz_set\":%.0f,"
             "\"vac_pa\":%.1f,\"rl\":{\"gas\":%d,\"cool\":%d,\"charge\":%d,\"drop\":%d,\"escape\":%d,\"ab\":%d},"
             "\"relay_ngoai\":[%d,%d,%d,%d],\"hmi_ok\":%d,\"bt_sv\":%u,\"source_kg\":%.1f,\"feeder\":%d,\"toc\":%.1f}",
             (unsigned)(now_us() / 1000), P.probe, P.et, P.drum_wall, gas_pct(), air_pct(), P.flame ? 1 : 0,
             P.beans_kg, P.hopper_kg, P.drum_hz, P.drum_hz_set, P.vac_pa, g_pin_out[P_GAS_RL],
             g_pin_out[P_COOL_RL], g_pin_out[P_CHARGE_RL], g_pin_out[P_DROP_RL], g_pin_out[P_ESCAPE_RL],
             g_pin_out[P_AB_RL], P.relay_mod[0], P.relay_mod[1], P.relay_mod[2], P.relay_mod[3], g_hmi_ok,
             P.bt_sv, P.source_kg, P.feeder ? 1 : 0, g_toc);
    return b;
}

static std::string sim_command(const std::string &cmd)
{
    char k[64] = {0};
    double v = 0;
    if (cmd == "status")
        return sim_status();
    if (sscanf(cmd.c_str(), "set %63s %lf", k, &v) == 2) {
        std::lock_guard<std::mutex> lk(g_plant_mx);
        std::string key = k;
        if (key == "amb") P.amb = v;
        else if (key == "et") P.et = v;
        else if (key == "bt") P.probe = v;
        else if (key == "drum_wall") P.drum_wall = v;
        else if (key == "hopper_kg") P.hopper_kg = v;
        else if (key == "source_kg") P.source_kg = v;
        else if (key == "beans_kg") P.beans_kg = v;
        else if (key == "flame_fault") P.flame_fault = v != 0;
        else if (key == "bt_fault") P.bt_fault = (int)v;
        else if (key == "et_fault") P.et_fault = (int)v;
        else return "{\"loi\":\"khoa la\"}";
        return "{\"ok\":1}";
    }
    return "{\"loi\":\"lenh: status | set amb|et|bt|drum_wall|hopper_kg|beans_kg|flame_fault|bt_fault|et_fault <so>\"}";
}

static void ctl_thread()
{
    for (;;) {
        HANDLE h = CreateNamedPipeA("\\\\.\\pipe\\otl_fw_sim", PIPE_ACCESS_DUPLEX,
                                    PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT, 4, 4096, 4096, 0,
                                    nullptr);
        if (h == INVALID_HANDLE_VALUE) {
            Sleep(500);
            continue;
        }
        if (!ConnectNamedPipe(h, nullptr) && GetLastError() != ERROR_PIPE_CONNECTED) {
            CloseHandle(h);
            continue;
        }
        for (;;) {
            char buf[1024];
            DWORD n = 0;
            if (!ReadFile(h, buf, sizeof(buf) - 1, &n, nullptr) || !n)
                break;
            buf[n] = 0;
            std::string rep = sim_command(buf);
            WriteFile(h, rep.data(), (DWORD)rep.size(), &n, nullptr);
        }
        DisconnectNamedPipe(h);
        CloseHandle(h);
    }
}

// ------------------------------------------------------------------ vòng nền: ngắt + mô hình + cân
static uint64_t g_plant_last = 0, g_scale_last = 0;
void sim_poll()
{
    if (g_in_poll)
        return;
    g_in_poll = true;
    uint64_t t = now_us();
    if (g_isr && g_isr_period) {
        int guard = 0;
        while (t >= g_isr_next && guard++ < 5) {
            g_isr_next += g_isr_period;
            g_isr();  // ngắt TIM1 (timerPoll_1000ms)
        }
        if (t >= g_isr_next)
            g_isr_next = t + g_isr_period;
    }
    if (t - g_plant_last >= 50000) {
        double dt = (t - g_plant_last) / 1e6;
        if (dt > 1.0)
            dt = 1.0;
        g_plant_last = t;
        plant_step(dt);
    }
    if (t - g_scale_last >= 500000) {
        g_scale_last = t;
        char line[40];
        double kg;
        {
            std::lock_guard<std::mutex> lk(g_plant_mx);
            kg = P.source_kg;                // cân đặt dưới phễu nguồn (máy thật: đầu cân Bluetooth của auto-loader)
        }
        snprintf(line, sizeof(line), "GS,%05.1f,kg\r\n", kg);
        if (g_rx[PORT_SCALE].size() < 2000)
            for (char *p = line; *p; p++)
                g_rx[PORT_SCALE].push_back((uint8_t)*p);
    }
    g_in_poll = false;
}

// ------------------------------------------------------------------ main
std::string sim_sd_path(const char *p)
{
    char dir[600] = {0};
    if (!GetEnvironmentVariableA("OTL_SD_DIR", dir, sizeof(dir)))
        strcpy(dir, "sdcard");
    std::string r = dir;
    while (p && (*p == '/' || *p == '\\'))
        p++;
    r += "\\";
    r += p ? p : "";
    return r;
}

// L47: bắt SẬP THẦM (access violation…) — in mã lỗi + ngăn xếp có tên hàm / dòng (PDB) ra log rồi thoát.
#include <dbghelp.h>
static LONG WINAPI sim_bat_sap(EXCEPTION_POINTERS *e)
{
    static bool da = false;
    if (da) return EXCEPTION_CONTINUE_SEARCH;
    da = true;
    HANDLE pr = GetCurrentProcess(), th = GetCurrentThread();
    SymSetOptions(SYMOPT_LOAD_LINES | SYMOPT_UNDNAME);
    SymInitialize(pr, nullptr, TRUE);
    char b[512];
    char *goc = (char *)GetModuleHandleA(nullptr);
    snprintf(b, sizeof(b), "SAP code=0x%08lX addr=%p RVA=0x%llx base=%p (doc/ghi o %p)", e->ExceptionRecord->ExceptionCode,
             e->ExceptionRecord->ExceptionAddress, (unsigned long long)((char *)e->ExceptionRecord->ExceptionAddress - goc), goc,
             e->ExceptionRecord->NumberParameters > 1 ? (void *)e->ExceptionRecord->ExceptionInformation[1] : nullptr);
    log_line("[SAP]", b);
    CONTEXT c = *e->ContextRecord;
    STACKFRAME64 f = {};
    f.AddrPC.Offset = c.Rip; f.AddrPC.Mode = AddrModeFlat;
    f.AddrFrame.Offset = c.Rbp; f.AddrFrame.Mode = AddrModeFlat;
    f.AddrStack.Offset = c.Rsp; f.AddrStack.Mode = AddrModeFlat;
    for (int i = 0; i < 24 && StackWalk64(IMAGE_FILE_MACHINE_AMD64, pr, th, &f, &c, nullptr, SymFunctionTableAccess64,
                                          SymGetModuleBase64, nullptr); i++) {
        char sb[sizeof(SYMBOL_INFO) + 256] = {};
        SYMBOL_INFO *sy = (SYMBOL_INFO *)sb;
        sy->SizeOfStruct = sizeof(SYMBOL_INFO);
        sy->MaxNameLen = 255;
        DWORD64 d64 = 0;
        DWORD d = 0;
        IMAGEHLP_LINE64 ln = {};
        ln.SizeOfStruct = sizeof(ln);
        const char *ten = SymFromAddr(pr, f.AddrPC.Offset, &d64, sy) ? sy->Name : "?";
        bool co = SymGetLineFromAddr64(pr, f.AddrPC.Offset, &d, &ln);
        snprintf(b, sizeof(b), "#%02d RVA=0x%llx %s  %s:%lu", i, (unsigned long long)(f.AddrPC.Offset - (DWORD64)goc), ten,
                 co ? ln.FileName : "?", co ? ln.LineNumber : 0);
        log_line("[SAP]", b);
    }
    if (g_log) fflush(g_log);
    fflush(stdout);
    return EXCEPTION_CONTINUE_SEARCH;
}

void setup();
void loop();

int main(int argc, char **argv)
{
    SetUnhandledExceptionFilter(sim_bat_sap);
    AddVectoredContinueHandler(1, sim_bat_sap);
    QueryPerformanceFrequency(&g_freq);
    if (const char *e = getenv("OTL_SIM_TOC")) {               // L47: chạy nhanh (vd 4 = 4 giây máy / 1 giây thật)
        double v = atof(e);
        if (v >= 1.0 && v <= 20.0) g_toc = v;
    }
    QueryPerformanceCounter(&g_t0);
    timeBeginPeriod(1);
    WSADATA w;
    WSAStartup(MAKEWORD(2, 2), &w);
    SetConsoleOutputCP(65001);
    CreateDirectoryA("sdcard", nullptr);
    CreateDirectoryA("log", nullptr);
    SYSTEMTIME st;
    GetLocalTime(&st);
    char lf[80];
    snprintf(lf, sizeof(lf), "log\\fw_%04d%02d%02d_%02d%02d%02d.log", st.wYear, st.wMonth, st.wDay, st.wHour,
             st.wMinute, st.wSecond);
    g_log = fopen(lf, "w");
    log_line("[SIM]", "BOARD AO OTL — firmware that chay tren PC (V400, cau hinh Config.h hien tai)");
    for (int i = 1; i < argc; i++)
        log_line("[SIM]", std::string("tham so: ") + argv[i]);
    mbs_server_start();
    std::thread(ctl_thread).detach();
    setup();
    log_line("[SIM]", "setup() xong — vao loop()");
    for (;;) {
        loop();
        sim_poll();
    }
}
