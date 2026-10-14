#pragma once
/*
 * CẤU HÌNH MÁY LÚC CHẠY — một firmware cho mọi biến thể (kế hoạch docs/plan/plan-mot-ban-nhieu-may.md).
 *
 * Ô $M62 (machineOptions) do Master chọn trên màn Cấu hình máy của HMI. PC_Link chỉ ĐỌC được ô này
 * (min > max trong protocol/pc_link.json ⇒ mọi lệnh ghi bị từ chối).
 *
 * Hai tầng:
 *   · MACHINE_HAS_* trong Config.h = TRẦN phần cứng lúc dựng (code có được biên dịch vào không).
 *   · mcOpt                        = máy NÀY có lắp thiết bị đó không (chọn lúc chạy).
 * Tính năng chạy khi CẢ HAI cùng bật.
 *
 * mcOpt chỉ đổi khi máy ĐỨNG YÊN (không lửa, không làm nóng, không AUTO, không trong chuỗi mẻ).
 * HMI đổi $M62 giữa mẻ thì giữ cấu hình cũ tới khi máy dừng — không đổi thiết bị dưới chân mẻ đang rang.
 *
 * ⛔ An toàn gas (chốt mồi hụt, giám sát lửa, watchdog) KHÔNG đọc mcOpt — chạy y nguyên ở mọi cấu hình.
 */

#define mcOpt_W             62      // $M62
#define mcOpt_R             iMemHMI[mcOpt_W]      // số HMI đang ghi (CHƯA chắc đã chốt)
#define mcOpt_R_CP          iMemHMI_CP[mcOpt_W]
#define vrHmi_W             63      // $M63: 1 = máy có núm vặn nhưng thợ chuyển sang nút +/− trên HMI
#define vrHmi_R             iMemHMI[vrHmi_W]
#define vrHmi_R_CP          iMemHMI_CP[vrHmi_W]

#define OPT_VR_GAS_AIR      0x0001  // bit 0  núm vặn gas + gió
#define OPT_VR_DRUM         0x0002  // bit 1  núm vặn trống (chỉ hợp lệ khi có bit 0 ⇒ VR 3)
#define OPT_VACUUM          0x0004  // bit 2  cảm biến áp hút + PID gió (biến tần gió nối RS485 ID 5)
#define OPT_LOADER          0x0008  // bit 3  nạp liệu tự động
#define OPT_SCALE           0x0010  // bit 4  đầu cân (loader có cân ⇒ nạp theo khối lượng)
#define OPT_RELAY_EXT       0x0020  // bit 5  module relay ngoài Modbus ID 7
#define OPT_SIZE_SHIFT      6       // bit 6–8 cỡ máy
#define OPT_SIZE_MASK       0x01C0
#define OPT_AFTERBURNER     0x0200  // bit 9  đốt khói
#define OPT_DESTONER        0x0400  // bit 10 tách đá
#define OPT_COOL_SPLIT      0x0800  // bit 11 khuấy và quạt khay nguội chạy relay riêng
#define OPT_CONFIGURED      0x8000  // bit 15 đã cấu hình (0 ⇒ chặn rang)

#define OPT_SIZE_COUNT      4       // 0 = 6 kg · 1 = 12 kg · 2 = 15 kg · 3 = 30 kg
static const uint8_t OPT_SIZE_KG[OPT_SIZE_COUNT] = {6, 12, 15, 30};

uint16_t mcOpt = 0;                 // cấu hình ĐANG DÙNG (đã chốt khi máy đứng yên)
bool     mcOptChanged = false;      // vừa đổi cấu hình — vòng chính khởi động lại ngoại vi rồi xoá cờ

// ── Hỏi cấu hình ─────────────────────────────────────────────────────────────
static inline bool mcConfigured()   { return (mcOpt & OPT_CONFIGURED) != 0; }
static inline bool mcHas(uint16_t m){ return mcConfigured() && (mcOpt & m) != 0; }

static inline bool optVrGasAir()    { return mcHas(OPT_VR_GAS_AIR); }
static inline bool optVrDrum()      { return mcHas(OPT_VR_GAS_AIR) && mcHas(OPT_VR_DRUM); }
static inline bool optVacuum()      { return MACHINE_HAS_VACUUM_SENSOR && mcHas(OPT_VACUUM); }
static inline bool optAirInverter() { return MACHINE_HAS_AIR_INVERTER && optVacuum(); }   // chỉ nối RS485 khi có vacuum
static inline bool optLoader()      { return mcHas(OPT_LOADER); }
static inline bool optScale()       { return MACHINE_HAS_SCALE_FEEDER && mcHas(OPT_SCALE); }
static inline bool optRelayExt()    { return MACHINE_HAS_IO_RELAY_MODULE && mcHas(OPT_RELAY_EXT); }
static inline bool optAfterburner() { return mcHas(OPT_AFTERBURNER); }
static inline bool optDestoner()    { return mcHas(OPT_DESTONER); }
static inline bool optCoolSplit()   { return mcHas(OPT_COOL_SPLIT); }
// Thợ bấm "Điều khiển trên HMI" khi núm vặn hỏng ($M63 = 1): số lấy từ nút +/− dù máy có núm.
bool vrUseHmi = false;
static inline bool vrKnobGasAir()   { return optVrGasAir() && !vrUseHmi; }
static inline bool vrKnobDrum()     { return optVrDrum()   && !vrUseHmi; }
static inline uint8_t optSizeCode() { return (uint8_t)((mcOpt & OPT_SIZE_MASK) >> OPT_SIZE_SHIFT); }
static inline uint8_t optBatchKg() {
    const uint8_t c = optSizeCode();
    return c < OPT_SIZE_COUNT ? OPT_SIZE_KG[c] : MACHINE_BATCH_KG;
}

// Cấu hình có hợp lệ không. Máy CHƯA cấu hình (bit 15 = 0) là hợp lệ — chỉ là bị chặn rang.
static inline bool mcOptValid(uint16_t v) {
    if (!(v & OPT_CONFIGURED)) return true;
    if ((v & OPT_VR_DRUM) && !(v & OPT_VR_GAS_AIR)) return false;          // VR trống phải đi với VR gas + gió
    if (((v & OPT_SIZE_MASK) >> OPT_SIZE_SHIFT) >= OPT_SIZE_COUNT) return false;
    if (v & 0x7000) return false;                                           // bit 12–14 để dành, phải = 0
    // Board chỉ có 8 relay (gas, nguội, nạp, xả, thoát, đốt khói, tách đá, nạp liệu): khuấy chạy riêng
    // phải có kênh 2 của module relay ngoài.
    if ((v & OPT_COOL_SPLIT) && !(v & OPT_RELAY_EXT)) return false;
    return true;
}

// Máy có ĐỨNG YÊN không — chỉ lúc này mới được đổi cấu hình. Cùng điều kiện với khoá ghi $M của PC_Link.
static inline bool mcOptIdle() {
    return !(gasSignal == 1 || WU_R == 1 || START_BTN_R == 1 ||
             (progStep >= STP_GAS && progStep <= STP_LOOP_2));
}

// Chốt $M62 vào mcOpt. Trả: 0 = không đổi · 1 = đã đổi · 2 = từ chối (vô lý) · 3 = chờ máy đứng yên.
static uint8_t mcOptLatch(bool idle) {
    const uint16_t want = (uint16_t)mcOpt_R;
    if (want == mcOpt) return 0;
    if (!idle) return 3;
    if (!mcOptValid(want)) return 2;
    mcOpt = want;
    mcOptChanged = true;
    return 1;
}
