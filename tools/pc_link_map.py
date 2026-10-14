"""
pc_link_map.py — SINH TỰ ĐỘNG từ protocol/pc_link.json — ĐỪNG SỬA TAY.
Sửa JSON rồi chạy: python protocol/gen_pc_link.py

Bản đồ register + giải mã gói dữ liệu máy rang, dùng chung với firmware.
"""

VERSION = 3
BAUD_DEFAULT = 9600
SLAVE_DEFAULT = 1

R_BASE, R_COUNT = 100, 23
W_BASE, W_COUNT = 140, 23

# Khối ĐỌC theo ĐÚNG thứ tự offset. Máy chạy firmware cũ có ít ô hơn,
# app lùi số ô rồi lấy R_KEYS[số_ô_đọc_được:] làm danh sách trường
# 'máy chưa có' — khỏi phải nhớ sửa tay mỗi lần thêm ô mới (otl_link).
R_KEYS = ["bt", "et", "ror_bt", "ror_et", "ror_pro", "gas", "air", "drum", "sv", "vac", "step", "t_roast", "phase", "flags", "hb", "drum_hz", "prof_pct", "prof_ok", "prof_sel", "scale", "ror_kg", "scale_tg", "vac_en"]

# tên → chỉ số trong khối GHI (offset từ W_BASE)
W_INDEX = {
    "gas": 0,
    "air": 1,
    "drum": 2,
    "sv": 3,
    "vac": 4,
    "ignite": 5,
    "charge": 6,
    "drop": 7,
    "escape": 8,
    "cool": 9,
    "auto": 10,
    "hb": 11,
    "drumfan": 12,
    "mixer": 13,
    "afterburner": 14,
    "loader": 15,
    "destoner": 16,
    "profile": 17,
    "mode": 18,
    "scale_tg": 19,
    "autoloader": 20,
    "vacen": 21,
    "agent": 22,
}

# giới hạn kẹp phía PC (firmware kẹp lần nữa — clamp 2 tầng)
W_RANGE = {
    "gas": (0, 100),   # gas %
    "air": (0, 100),   # gió %
    "drum": (0, 100),   # trống %
    "sv": (0, 3000),   # SV nhiệt hạt
    "vac": (90, 250),   # áp hút đặt
    "ignite": (0, 1),   # bật/tắt gas (START_GAS)
    "charge": (0, 1),   # nạp hạt
    "drop": (0, 1),   # xả mẻ
    "escape": (0, 1),   # thoát
    "cool": (0, 1),   # làm nguội
    "auto": (0, 1),   # bật/tắt AUTO (START)
    "hb": (0, 32767),   # heartbeat app: app tăng mỗi giây; firmware không thấy đổi quá PCL_APP_TMO_S thì nhả quyền
    "drumfan": (0, 1),   # quạt trống (DRUM_FAN_BTN)
    "mixer": (0, 1),   # cánh khuấy (MIXER_BTN)
    "afterburner": (0, 1),   # buồng đốt khói (AB_BTN)
    "loader": (0, 1),   # nạp liệu phễu (FEEDER_BTN)
    "destoner": (0, 1),   # tách đá (DESTONER_BTN)
    "profile": (0, 30),   # chọn slot profile SD (1-30) → firmware nạp file, theo dõi prof_pct/prof_ok
    "mode": (0, 2),   # chế độ rang: 1=SAVE (rang lưu), 2=AUTO (phát lại profile) — đặt TRƯỚC khi bật auto
    "scale_tg": (0, 990),   # cân đích kg (Setup trên HMI) — app gửi kg, ×10 xuống máy (netWTG_R)
    "autoloader": (0, 1),   # bật/tắt Auto loader (tự cân mẻ kế khi rang AUTO loop)
    "vacen": (0, 1),   # bật/tắt PID gió theo áp hút (vacuumSetFlag). Thêm 2026-07-30: trước đây app phải đi đường $M reg 47 vì khối GHI thiếu ô này
    "agent": (0, 1),   # tác nhân đang lái: 0=NGƯỜI (thợ bấm app) · 1=TỰ ĐỘNG (AI/script). Khai 1 là firmware siết watchdog PCL_AGENT_TMO_S giây; cờ CÀI THEN, không hạ về 0 giữa phiên để né watchdog — chỉ tắt PC control mới xoá
}

# hệ số ghi: giá trị kỹ thuật × scale = số gửi xuống máy
W_SCALE = {"gas": 1, "air": 1, "drum": 1, "sv": 10, "vac": 1, "ignite": 1, "charge": 1, "drop": 1, "escape": 1, "cool": 1, "auto": 1, "hb": 1, "drumfan": 1, "mixer": 1, "afterburner": 1, "loader": 1, "destoner": 1, "profile": 1, "mode": 1, "scale_tg": 10, "autoloader": 1, "vacen": 1, "agent": 1}

PHASE_BITS = {
    "dry": 0x01,   # đã qua TP  (progStep >= STP_TP)
    "mai": 0x02,   # đã qua FCs (progStep >= STP_FCS)
    "dev": 0x04,   # đã qua DEV (progStep >= STP_DEV)
}

FLAGS_BITS = {
    "auto": 0x01,   # START_BTN_R — đang chạy AUTO
    "gas": 0x02,   # START_GAS_BTN_R — gas đang bật
    "charge": 0x04,   # CHARGE_BTN_R
    "drop": 0x08,   # DROP_BTN_R
    "escape": 0x10,   # ESCAPE_BTN_R
    "cool": 0x20,   # COOLING_BTN_R
    "pc_control": 0x40,   # PC_CONTROL_BTN_R — app được phép điều khiển
    "flame": 0x80,   # CÓ LỬA THẬT (gasSignal, chân CH1) — khác hẳn 'đã bấm bật gas'
    "pc_lost": 0x100,   # firmware đã tự nhả quyền vì mất app (watchdog)
    "flame_fail": 0x200,   # firmware đã tự đóng gas vì mồi hoài không có lửa
    "drumfan": 0x400,   # DRUM_FAN_BTN_R — quạt trống đang bật
    "mixer": 0x800,   # MIXER_BTN_R — cánh khuấy đang bật
    "afterburner": 0x1000,   # AB_BTN_R — buồng đốt khói đang bật
    "loader": 0x2000,   # FEEDER_BTN_R — nạp liệu đang bật
    "destoner": 0x4000,   # DESTONER_BTN_R — tách đá đang bật
    "autoloader": 0x8000,   # autoLoader_R — chế độ tự cân đang bật
}

# progStep của firmware (Define.h)
STP = {
    "CHARGE": 5,
    "TP": 6,
    "DE": 7,
    "FCs": 8,
    "DEV": 9,
    "DROP": 10,
    "COOLING": 11,
    "ESCAPE": 12,
}

# MỐC ĐÃ ĐẠT ⟺ progStep >= giá trị này. LỆCH MỘT BƯỚC so với STP:
# progStep = 'đang CHỜ mốc đó', không phải 'đã qua'. Chấm mốc dùng bảng NÀY.
MILE_STEP = {
    "TP": 7,
    "DE": 8,
    "FCs": 9,
    "DEV": 9,
    "DROP": 10,
}

# ── Khối tương thích (reg 0..19) — máy chưa nạp PC_Link vẫn đọc được ──
A_BASE, A_COUNT = 0, 20
A_FIELDS = {   # key → (offset, scale, signed)
    "bt": (0, 10, False),   # nhiệt hạt
    "et": (1, 10, False),   # nhiệt khí
    "air": (2, 1, False),   # mức gió %
    "gas": (3, 1, False),   # mức gas %
    "drum": (4, 1, False),   # tốc độ trống %
    "vac": (9, 1, True),   # áp hút Diff_Air, Pa
    "cool": (13, 1, False),   # nút làm nguội (chỉ khi PC control TẮT)
    "charge": (14, 1, False),   # nút nạp hạt (chỉ khi PC control TẮT)
    "drop": (15, 1, False),   # nút xả mẻ (chỉ khi PC control TẮT)
    "escape": (16, 1, False),   # nút thoát (chỉ khi PC control TẮT)
    "auto": (17, 1, False),   # đang chạy AUTO (START_BTN_R) — LUÔN phản chiếu
    "sv": (19, 10, False),   # SV nhiệt hạt
}


def decode_artisan(regs):
    """Khối tương thích thô → dict. Thiếu RoR/thời gian/mốc — xem roast_derive.py."""
    if len(regs) < A_COUNT:
        raise ValueError(f"cần {A_COUNT} register, nhận {len(regs)}")
    out = {}
    for key, (off, scale, sgn) in A_FIELDS.items():
        v = regs[off]
        if sgn:
            v = to_signed(v)
        out[key] = v / float(scale) if scale != 1 else v
    return out


# ── Ô LỆNH khối tương thích — điều khiển máy chưa nạp PC_Link ──
# KHÔNG có xung: mọi ô đều là MỨC. latch = ghi 1 rồi thôi, firmware tự đóng.
AW_INDEX = {   # key → (địa chỉ register, 'level' | 'toggle' | 'latch')
    "gas": (11, "level"),   # gas %
    "air": (10, "level"),   # gió %
    "drum": (20, "level"),   # trống %
    "sv": (18, "level"),   # SV nhiệt hạt
    "vac": (22, "level"),   # áp hút đặt
    "ignite": (12, "toggle"),   # đánh lửa (bật/tắt gas)
    "cool": (13, "toggle"),   # làm nguội (bật/tắt)
    "charge": (14, "latch"),   # nạp hạt — firmware tự đóng
    "drop": (15, "latch"),   # xả mẻ — firmware tự đóng
    "escape": (16, "latch"),   # xả liệu — firmware tự đóng
    "auto": (17, "level"),   # bật/tắt AUTO
}

# Tham số để tái tạo đúng phép tính firmware (xem roast_derive.py)
DERIVE = {
    "ror_window_s": 3,
    "ror_gain": 20,
    "ror_bt_clamp": 95.0,
    "ror_et_clamp": 20.0,
    "kalman_bt": [1.0, 1.0, 0.005],
    "kalman_et": [1.0, 1.0, 0.01],
    "tp_min_time_s": 20,
    "tp_max_temp": 150.0,
    "de_temp_default": 150.0,
    "fcs_temp_default": 196.0,
    "charge_drop_bt": 8.0,
}

# Handshake cấu hình $M — đọc/ghi 1 tham số (idx = số $M 1..MAXIDX)
CFG_BASE = 170
CFG_REG = {
    "cmd": 170,   # 0=rảnh · 1=đọc 1 tham số · 2=ghi 1 tham số (firmware set về 0 khi xong)
    "idx": 171,   # số $M cần đọc/ghi (1..62)
    "val": 172,   # giá trị HMI thô (app ghi khi cmd=2 · firmware điền khi cmd=1)
    "status": 173,   # 0=đang xử/chưa · 1=OK · 2=lỗi (idx sai/cmd lạ) · 3=máy đang bận (rang·mồi lửa·làm nóng·còn lửa → khoá ghi) · 4=giá trị ngoài dải · 5=HMI từ chối hoặc không phản hồi lệnh ghi
}
CFG_MAXIDX = 62
CFG_CMD = {'idle': 0, 'read': 1, 'write': 2}
CFG_STATUS = {'busy': 0, 'ok': 1, 'err': 2, 'locked': 3, 'range': 4, 'hmi': 5}
CFG_RANGE = {
    1: (0, 60),
    2: (0, 60),
    3: (0, 60),
    4: (0, 100),
    5: (0, 100),
    6: (0, 65535),
    7: (0, 600),
    8: (0, 100),
    9: (0, 300),
    10: (0, 30),
    11: (1, 99),
    12: (1, 247),
    13: (0, 7),
    14: (0, 60),
    15: (1, 247),
    16: (0, 65535),
    17: (1, 0),
    18: (1, 0),
    19: (0, 120),
    20: (0, 300),
    21: (0, 300),
    22: (0, 600),
    23: (0, 3000),
    24: (0, 300),
    25: (0, 65535),
    26: (0, 60),
    27: (0, 120),
    28: (0, 100),
    29: (0, 1),
    30: (0, 100),
    31: (0, 100),
    32: (0, 1000),
    33: (0, 1),
    34: (0, 100),
    35: (0, 100),
    36: (0, 100),
    37: (0, 1),
    38: (0, 65535),
    39: (0, 65535),
    40: (0, 65535),
    41: (0, 10000),
    42: (0, 10000),
    43: (0, 10000),
    44: (0, 100),
    45: (0, 1),
    46: (0, 120),
    47: (0, 1),
    48: (0, 300),
    49: (0, 1000),
    50: (0, 1000),
    51: (0, 60),
    52: (0, 300),
    53: (0, 1),
    54: (0, 10),
    55: (60, 900),
    56: (10, 120),
    57: (10, 30),
    58: (100, 300),
    59: (120, 600),
    60: (0, 30),
    61: (5, 60),
    62: (1, 0),
}
CFG_META = {23: {'name': 'chargeTemp10', 'unit': '°C', 'scale': 10, 'default': 1800, 'desc': 'nhiệt độ nạp, số thô ×10 (1800 = 180,0°C)'}, 53: {'name': 'autoEscape', 'unit': 'bool', 'scale': 1, 'default': 1, 'desc': '1 = tự động mở cửa xả sau làm mát; 0 = chỉ làm mát'}, 54: {'name': 'dropTrim10', 'unit': '°C', 'scale': 10, 'default': 3, 'desc': 'Biên chỉnh nhiệt xả theo sai lệch thời gian, ×10 (0 = TẮT, xả đúng nhiệt hồ sơ; 10 = ±1.0 °C). Chỉ tác dụng khi DEV đã quá 3 phút.'}, 55: {'name': 'preheatDeadlineSec', 'unit': 's', 'scale': 1, 'default': 180, 'zero_uses_default': True, 'desc': 'thời hạn PID preheat đạt nhiệt mục tiêu'}, 56: {'name': 'preheatHoldSettleSec', 'unit': 's', 'scale': 1, 'default': 45, 'zero_uses_default': True, 'desc': 'thời gian bỏ qua chuyển tiếp trước khi đánh giá giữ nhiệt'}, 57: {'name': 'preheatTargetBand10', 'unit': '°C', 'scale': 10, 'default': 30, 'zero_uses_default': True, 'desc': 'dải vào trạng thái giữ nhiệt, số thô ×10 (30 = 3,0°C)'}, 58: {'name': 'developmentWarnPermil', 'unit': '‰', 'scale': 1, 'default': 300, 'zero_uses_default': True, 'desc': 'ngưỡng cảnh báo tỷ lệ phát triển, phần nghìn (300 = 30,0%)'}, 59: {'name': 'autoDropMinSec', 'unit': 's', 'scale': 1, 'default': 120, 'zero_uses_default': True, 'desc': 'thời gian tối thiểu sau charge mới cho phép auto-drop'}, 60: {'name': 'manualEscapeExtraSec', 'unit': 's', 'scale': 1, 'default': 15, 'zero_uses_default': False, 'desc': 'số giây cộng thêm khi tự đóng escape mở tay; 0 là giá trị hợp lệ. HMI mới phải khởi tạo 15 nếu muốn mặc định; firmware không thể phân biệt số 0 cố ý với HMI cũ chưa có ô này'}, 61: {'name': 'loopDoorStuckSec', 'unit': 's', 'scale': 1, 'default': 60, 'zero_uses_default': True, 'desc': 'thời gian chờ cửa drop đóng ở vòng lặp trước khi báo kẹt'}, 62: {'name': 'machineOptions', 'unit': 'bitmask', 'scale': 1, 'default': 0, 'zero_uses_default': False, 'desc': 'CẤU HÌNH MÁY, CHỈ ĐỌC qua PC_Link (min>max ⇒ mọi lệnh ghi bị từ chối) — chỉ Master đổi trên màn Cấu hình máy của HMI. Bit 0 VR gas+gió · 1 VR trống · 2 vacuum · 3 loader · 4 cân · 5 relay ngoài ID 7 · 6–8 cỡ máy (0=6, 1=12, 2=15, 3=30 kg) · 9 đốt khói · 10 tách đá · 11 khuấy/quạt khay nguội relay riêng · 15 đã cấu hình (0 = chưa cấu hình ⇒ firmware chặn rang)'}}

# Chốt an toàn khi app là bộ điều khiển
FAILSAFE = {
    "app_timeout_s": 3,
    "on_app_lost": 'release_to_hmi',
    "flame_timeout_s": 75,
    "agent_timeout_s": 3,
}


def to_signed(v):
    """Register 16-bit về số có dấu."""
    return v - 0x10000 if v >= 0x8000 else v


def decode(regs):
    """Khối ĐỌC thô (15 register) → dict đơn vị kỹ thuật."""
    if len(regs) < R_COUNT:
        raise ValueError(f"cần {R_COUNT} register, nhận {len(regs)}")
    return {
        "bt": regs[0] / 10.0,   # nhiệt hạt
        "et": regs[1] / 10.0,   # nhiệt khí
        "ror_bt": to_signed(regs[2]) / 100.0,   # RoR hạt
        "ror_et": to_signed(regs[3]) / 100.0,   # RoR khí
        "ror_pro": to_signed(regs[4]) / 100.0,   # RoR hồ sơ mẫu tại giây hiện tại
        "gas": regs[5],   # mức gas
        "air": regs[6],   # mức gió
        "drum": regs[7],   # tốc độ trống
        "sv": regs[8] / 10.0,   # SV nhiệt hạt
        "vac": to_signed(regs[9]),   # áp hút (âm = hút)
        "step": regs[10],   # progStep — bước quy trình rang
        "t_roast": regs[11],   # thời gian rang
        "phase": {k: bool(regs[12] & m) for k, m in PHASE_BITS.items()},
        "flags": {k: bool(regs[13] & m) for k, m in FLAGS_BITS.items()},
        "hb": regs[14],   # heartbeat — tăng mỗi vòng loop, app dò treo
        "drum_hz": regs[15] / 100.0,   # tần số THẬT đọc từ biến tần trống (Drum_Freq_CP, 0.01Hz)
        "prof_pct": regs[16],   # tiến độ nạp profile SD (percentLoadProfile, 0-99 đang đọc, 100 xong)
        "prof_ok": regs[17],   # kết quả nạp profile: 0=chưa/đang nạp, 1=OK đủ điều kiện rang auto, 2=LỖI
        "prof_sel": regs[18],   # slot profile SD đang chọn (SELECT_FILE_R, 0=chưa chọn)
        "scale": to_signed(regs[19]) / 100.0,   # cân phễu netW100 (61.35kg = 6135; âm khi trôi zero)
        "ror_kg": to_signed(regs[20]) / 100.0,   # tốc độ cân rorKG (hút ra = âm, 1kg/phút = 100)
        "scale_tg": regs[21] / 10.0,   # cân đích netWTG_R — hút tới còn ngần này thì tự cắt (Setup kg trên HMI)
        "vac_en": regs[22],   # PID gió theo áp hút đang BẬT hay không (vacuumSetFlag_R). Thêm 2026-09-09: khối GHI có ô vacen từ 30/07 nhưng khối ĐỌC thì không, nên app ra lệnh xong không có đường đọc lại — gương chỉ có một chiều
    }
