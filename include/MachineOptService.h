#pragma once
// Phần "thi hành" của cấu hình máy — nạp SAU Modbus_Master.h và MachineStatus.h vì cần nodeHMI,
// modbusFailCount và setMachineStatus. Dữ liệu + hàm hỏi cấu hình nằm ở MachineOpt.h.

#define MC_BLOCK_WRITE_MS   1000    // nhịp ghi trả nút về 0 khi máy chưa cấu hình (không dội bus HMI)

// Vừa đổi cấu hình: thiết bị nay KHÔNG lắp thì xoá đếm lỗi của nó. Không xoá thì một lần mất kết nối
// cũ của biến tần gió / relay ngoài vẫn giữ chốt cắt gas (modbusGasCutoffLatched) dù thiết bị đã bỏ.
static void mcOptApplyChange() {
    if (!optAirInverter()) { modbusFailCount[MB_DEV_AIR] = 0; modbusFailCount[MB_DEV_VACUUM] = 0; }
    if (!optRelayExt())    { modbusFailCount[MB_DEV_RELAY] = 0; }
    modbusNoteSuccess(MB_DEV_COUNT);   // tính lại chốt cắt gas theo bộ đếm mới (MB_DEV_COUNT = không đổi đếm nào)
    if (enDebug) { SerialComputer.print("MC_OPT = 0x"); SerialComputer.println(mcOpt, HEX); }
}

// Gọi mỗi vòng sau rwMemHMI().
static void mcOptService() {
    static uint16_t rejected = 0;          // số vô lý đã báo — không báo lại mỗi vòng
    const uint8_t r = mcOptLatch(mcOptIdle());
    if (r == 2 && (uint16_t)mcOpt_R != rejected) {
        rejected = (uint16_t)mcOpt_R;
        setMachineStatus(STT_ERR_CONFIG_INVALID);
    }
    if (r != 2) rejected = 0;
    if (mcOptChanged) {
        mcOptChanged = false;
        mcOptApplyChange();
        // Board chỉ ghi W40041 khi có sự kiện MỚI: không báo gì thì mã 422 'chưa cấu hình' đứng mãi trên HMI (dòng cảnh báo vẫn
        // sáng) dù máy đã nhận cấu hình — đo bàn thử thật 13/10/2026. Báo 'sẵn sàng' để thay mã cũ.
        if (mcConfigured()) setMachineStatus(STT_SYSTEM_READY);
    }

    // CHƯA CẤU HÌNH ⇒ chặn rang. Relay gas đã bị chặn cứng ở controlIO(); ở đây trả nút trên HMI về 0
    // để thợ thấy lệnh không ăn, kèm mã 422 nói lý do.
    if (mcConfigured()) return;
    if (START_GAS_BTN_R == 1 || START_BTN_R == 1 || WU_R == 1) {
        static uint32_t lastMs = 0;
        if (millis() - lastMs >= MC_BLOCK_WRITE_MS) {
            lastMs = millis();
            if (START_GAS_BTN_R == 1) nodeHMI.writeSingleRegister(START_GAS_BTN_W - 1, 0);
            if (START_BTN_R == 1)     nodeHMI.writeSingleRegister(START_BTN_W - 1, 0);
            if (WU_R == 1)            nodeHMI.writeSingleRegister(WU_W - 1, 0);
            setMachineStatus(STT_ERR_NOT_CONFIGURED);
        }
    }
}
