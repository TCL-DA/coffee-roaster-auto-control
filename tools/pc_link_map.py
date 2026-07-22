"""
pc_link_map.py — SINH TỰ ĐỘNG từ protocol/pc_link.json — ĐỪNG SỬA TAY.
Sửa JSON rồi chạy: python protocol/gen_pc_link.py

Bản đồ register + giải mã gói dữ liệu máy rang, dùng chung với firmware.
"""

VERSION = 1
BAUD_DEFAULT = 9600
SLAVE_DEFAULT = 1

R_BASE, R_COUNT = 100, 22
W_BASE, W_COUNT = 120, 21

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
}

# hệ số ghi: giá trị kỹ thuật × scale = số gửi xuống máy
W_SCALE = {"gas": 1, "air": 1, "drum": 1, "sv": 10, "vac": 1, "ignite": 1, "charge": 1, "drop": 1, "escape": 1, "cool": 1, "auto": 1, "hb": 1, "drumfan": 1, "mixer": 1, "afterburner": 1, "loader": 1, "destoner": 1, "profile": 1, "mode": 1, "scale_tg": 10, "autoloader": 1}

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

# Chốt an toàn khi app là bộ điều khiển
FAILSAFE = {
    "app_timeout_s": 3,
    "on_app_lost": 'release_to_hmi',
    "flame_timeout_s": 75,
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
    }
