# -*- coding: utf-8 -*-
"""OTL Hồng — ĐỌC 100 % + THAO TÁC HMI máy rang ĐIỆN VX4 qua panel Delta (Modbus TCP 169.254.116.153:502).

Giáo trình đầy đủ (địa chỉ, ý nghĩa, quy trình, luật CẤM): .claude/skills/rang-ca-phe/references/hmi-dien-thao-tac.md
Bản HMI phải là bản bàn thử có bảng TCP mở hết ($0..$1023 + $M0..$M1023): T-R0-1014-LO99-DIEN.dpa (15/10/2026).
Bản giao khách DIEN-110WS chỉ mở $300..$399, $500..$515, $819..$847, $M32 → hàm đọc ở đây sẽ báo "ngoại lệ 2".

Đọc (luôn được, không đổi gì trên máy):
    python tools/hmi_dien.py doc [--json] [--ho_so]   # doc_tat_ca(): mọi ô có ý nghĩa, đã đổi đơn vị
    python tools/hmi_dien.py man                      # màn đang hiện ($21)
    python tools/hmi_dien.py doc_man <id> [--json]    # chỉ các nhóm số thuộc màn <id>
    python tools/hmi_dien.py ho_so                    # 30 hồ sơ: tên, ngày, giờ charge, thời gian rang
    python tools/hmi_dien.py tho <ô> [số ô]           # đọc thô: tho 60 3 · tho M34 3

Ghi (Hồng tự thử SAU mẻ, máy rảnh, theo kế hoạch mục 8 của giáo trình) — cần HONG_DUOC_THAO_TAC=1;
lệnh làm cơ cấu chạy / bật nhiệt cần thêm HONG_DUOC_LAI=1:
    chuyen_man <id> · chon_ho_so <1..30> · bo_chon_ho_so · che_do <save|auto> · nhiet_charge <°C>
    dat_ten_ho_so <n> <tên> · lam_moi_ho_so · pc_control <0|1> · xac_nhan_canh_bao · dung_chuong_trinh
    [+HONG_DUOC_LAI] bat_dau · lam_nong <0|1> [--dich 210 --phut 15] · co_cau <nap|xa_trong|xa_khay|quat_nguoi> <0|1>
Không có lệnh xoá hồ sơ / dò PID / đổi cấu hình máy — đó là việc chủ máy bấm tay (giáo trình mục 7).
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hong_qua_panel import Panel  # noqa: E402  — chỉ dùng lớp Panel (đọc / ghi $ qua TCP), không sửa file đó

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TCP_M = 2000            # $Mn ↔ thanh ghi TCP 2000 + n (PDU, 0-based)
O_DOI_MAN = 49          # $49 = W40050 Control Block "Screen No." — ghi số màn ⇒ panel chuyển màn
O_MAN = 21              # $21 = W40022 Status Block "Screen No." — màn đang hiện
CHO_GHI_S = 1.5         # board quét nút ≥ 4 lần / vòng (~130 ms), HMI macro đồng hồ 100 ms → 1,5 s là dư

TEN_MAN = {
    1: "SELECT · Cài đặt nhanh (popup)", 2: "Vận hành (màn rang chính)", 5: "Thông số 1/3", 6: "Hồ sơ trang 1/3 (1–10)",
    8: "Hỏi xoá 1 hồ sơ (popup)", 9: "Hệ thống", 10: "Số liệu mẻ (bảng)", 11: "Hỏi xoá TẤT CẢ hồ sơ (popup)",
    12: "Hồ sơ trang 2/3 (11–20)", 13: "Hồ sơ trang 3/3 (21–30)", 14: "Làm nóng trống (popup)", 15: "Đăng nhập / khoá",
    16: "Hỏi ghi đè hồ sơ (popup)", 17: "Báo chế độ AUTO (popup)", 18: "Báo chế độ RANG LƯU (popup)",
    19: "So sánh mẻ ↔ hồ sơ", 20: "Đang dò PID gió (popup)", 21: "Đồ thị mẻ cũ", 22: "Nhật ký thao tác",
    23: "Cảnh báo", 24: "Thông số 2/3", 25: "Thông số 3/3", 26: "Nền Cài đặt (main)", 30: "Cân / hút liệu",
    31: "Tài khoản", 32: "Giải thích: cửa + nhiệt", 33: "Giải thích: charge + tách đá",
    34: "Giải thích: đồng hồ + đầu đốt", 35: "Giải thích: cân + hút liệu", 36: "Cấu hình máy",
}
MAN_CHINH = {2, 6, 12, 13, 15, 22, 23, 26}          # màn chính (không phải popup) — đổi màn bằng $49 chắc chắn được
NGUON = {0: "Tay/HMI (VR)", 1: "PC", 2: "AUTO (máy)"}
VAI = {0: "tắt", 1: "Tiêu chuẩn", 2: "Chuyên gia"}
GIAI_DOAN = {0: "Sẵn sàng", 1: "Làm nóng", 2: "Làm khô", 3: "Chuyển nâu", 4: "Phát triển", 5: "Làm nguội",
             6: "Xong mẻ", 7: "Chưa có hồ sơ"}
LAM_NONG = {0: "Đang dừng", 1: "Đang mồi / bật nhiệt", 2: "Đang làm nóng trống", 3: "Đạt nhiệt — sẵn sàng rang",
            4: "Mồi lửa lỗi (mã 25)"}
MOC = {0: "", 1: "Charge", 2: "TP", 3: "DE", 4: "FCs", 5: "Drop"}
LOI_DANG_NHAP = {0: "", 1: "sai PIN", 2: "đang khoá (5 lần sai)", 4: "vừa khôi phục bằng mã OTL"}
BIT_CAU_HINH = {0: "núm VR gas+gió", 1: "núm VR trống", 2: "vacuum", 3: "hút liệu (loader)", 4: "cân",
                5: "relay ngoài ID 7", 9: "đốt khói", 10: "tách đá", 11: "tay đảo relay riêng", 15: "ĐÃ CẤU HÌNH"}
CO_MAY = {0: "6 kg", 1: "12 kg", 2: "15 kg", 3: "30 kg"}


def s16(v):
    return v - 65536 if v >= 32768 else v


def bit(v, n):
    return (v >> n) & 1


def chu(words):
    """Chuỗi ASCII Delta: mỗi word 2 ký tự, BYTE THẤP TRƯỚC (đo $M220 = 'thu1' 15/10/2026)."""
    b = bytearray()
    for w in words:
        b += bytes((w & 0xFF, w >> 8))
    return b.split(b"\0", 1)[0].decode("latin-1").strip()


def _ma_trang_thai():
    """Bảng mã $40 lấy THẲNG từ firmware (include/MachineStatus.h) — luôn khớp bản đang dựng."""
    bang = {}
    try:
        with open(os.path.join(GOC, "include", "MachineStatus.h"), encoding="utf-8") as f:
            for dong in f:
                m = re.match(r"\s*#define\s+(STT_\w+)\s+(\d+)\s*//\s*(.*)", dong)
                if m and int(m.group(2)) < 1000:
                    bang[int(m.group(2))] = (m.group(1), m.group(3).strip())
    except OSError:
        pass
    return bang


MA = _ma_trang_thai()


def y_nghia_ma(ma):
    if ma == 0:
        return "—"
    ten, mo_ta = MA.get(ma, ("?", "mã lạ — tra bảng Cảnh báo màn 23"))
    muc = "LỖI NGHIÊM TRỌNG" if 401 <= ma <= 430 else ("cảnh báo" if 261 <= ma <= 300 else "")
    return "%d %s — %s%s" % (ma, ten, mo_ta, (" [%s]" % muc) if muc else "")


# ── đọc khối ────────────────────────────────────────────────────────────────────────────────────────
def _doc_dai(p, dau, so):
    """Đọc so ô liên tiếp từ thanh ghi TCP dau (≤ 120 ô / giao dịch)."""
    ra = []
    while so > 0:
        n = min(120, so)
        ra += p.doc(dau, n)
        dau += n
        so -= n
    return ra


def _anh(p, ho_so=False):
    """Ảnh bộ nhớ panel: {'$': {n: v}, 'M': {n: v}}. ~10 giao dịch, ~50 ms."""
    d, m = {}, {}
    for dau, so in ((0, 126), (149, 3), (200, 30), (450, 18), (500, 16), (811, 189), (1100, 6)):
        for i, v in enumerate(_doc_dai(p, dau, so)):
            d[dau + i] = v
    if ho_so:
        for i, v in enumerate(_doc_dai(p, 600, 211)):
            d[600 + i] = v
    for dau, so in ((0, 64), (1000, 15)) + (((100, 900),) if ho_so else ()):
        for i, v in enumerate(_doc_dai(p, TCP_M + dau, so)):
            m[dau + i] = v
    return {"$": d, "M": m}


def _gom(a):
    """Đổi ảnh bộ nhớ thành dict tên dễ hiểu, đã đổi đơn vị."""
    r, M = a["$"], a["M"]
    cfg = M[62]
    ten_ho_so = chu([M[1000 + i] for i in range(15)])
    out = {
        "man": {"so": r[O_MAN], "ten": TEN_MAN.get(r[O_MAN], "?"), "dang_chuyen_man": bit(r[20], 0),
                "bang_phu_tro_mo": r[811], "cai_dat_dang_mo": r[940]},
        "tai_khoan": {"dang_nhap": r[950], "nguoi": r[952], "vai": VAI.get(r[956], r[956]), "chuyen_gia": r[951],
                      "tho_tieu_chuan": r[926], "phai_doi_pin": r[929], "loi": LOI_DANG_NHAP.get(r[959], r[959]),
                      "so_lan_sai": r[957], "giay_con_khoa": r[859], "da_khoi_dong": r[954]},
        "nhiet": {"bt": s16(r[60]) / 10, "et": s16(r[61]) / 10, "buong_vx4": s16(r[96]) / 10,
                  "ror_bt": s16(r[62]) / 100, "ror_et": s16(r[63]) / 100,
                  "ror_max_tp_fcs": s16(r[43]) / 100, "giay_tp_toi_ror_max": r[44]},
        "dieu_khien": {"lenh_nhiet": r[1], "dang_nung": r[59], "nhiet_thuc_pct": r[66] / 10, "gio_thuc_pct": r[64] / 10,
                       "trong_thuc_pct": r[65] / 10, "trong_hz": r[84] / 100, "trong_rpm": round(r[84] * 0.0098, 1),
                       "ap_hut_pa": s16(r[85]), "dat_nhiet_pct": M[36], "dat_gio_pct": M[35], "dat_trong_pct": M[34],
                       "nguon_nhiet": NGUON.get(r[14], r[14]), "pc_control": r[13], "cho_lua_giay": r[998],
                       "khoa_nut_nhiet": r[464], "khoa_nut_gio": r[465], "khoa_nut_trong": r[466],
                       "hien_nut_cong_tru": r[467], "theo_num_van": r[460], "tran_nhiet_pct": M[28]},
        "co_cau": {"nap_lieu": r[6], "xa_trong": r[7], "xa_khay": r[8], "quat_nguoi": r[4], "tay_dao": r[3],
                   "trong_quat": r[2], "hut_lieu": r[5], "tach_da": r[9], "dot_khoi": r[11], "tu_do_silo": r[30]},
        "dem_nguoc_giay": {"nap": r[962], "xa_trong": r[967], "xa_khay": r[968], "lam_nguoi": r[969], "tay_dao": r[994],
                           "hut_lieu": r[995], "dot_khoi": r[996], "tach_da": r[997], "bit_dang_dem": r[963]},
        "chuong_trinh": {"start": r[0], "che_do": "AUTO" if r[22] == 1 else "RANG LƯU (SAVE)", "ma": r[40],
                         "ma_y_nghia": y_nghia_ma(r[40]), "dang_co_me": r[932], "lam_nong": r[39], "do_pid_gio": r[31],
                         "giai_doan": GIAI_DOAN.get(r[887], r[887]), "may_san_sang": r[91], "ghi_do_thi": r[57],
                         "so_me_lap": M[11], "khoa_start": r[923]},
        "me": {"phut": r[67], "giay": r[68], "da_nap": int(r[81] > 0), "bt_charge": r[81] / 10, "bt_drop": r[82] / 10,
               "da_qua_tp": r[938], "da_xa": r[939], "pha_say": r[93], "pha_maillard": r[94], "pha_phat_trien": r[95],
               "mat_ket_noi_board": r[970],
               "thanh_pha": {"say": (r[903], r[904], r[905]), "maillard": (r[906], r[907], r[908]),
                             "phat_trien": (r[909], r[910])}},
        "moc": {"tp": (r[69] / 10, r[70], r[71]), "de": (r[72] / 10, r[73], r[74]), "fcs": (r[75] / 10, r[76], r[77]),
                "dev_pct": r[78] / 10, "dev": (r[79], r[80]),
                "moc_vua_cham": {"ten": MOC.get(r[47], r[47]), "bt": s16(r[45]) / 10, "ror": s16(r[46]) / 100, "giay": r[48]}},
        "ho_so": {"chon": r[15], "ten": ten_ho_so, "hop_le": r[118], "nap_pct": r[120],
                  "nut_dang_bat": [i + 1 for i in range(30) if r[200 + i]],
                  "charge_bt": r[102] / 10, "tp": (r[103] / 10, r[104], r[105]), "de": (r[106] / 10, r[107], r[108]),
                  "fcs": (r[109] / 10, r[110], r[111]), "dev_pct": r[112] / 10, "dev": (r[113], r[114]),
                  "drop": (r[115] / 10, r[116], r[117]), "khoa_xoa": r[924]},
        "canh_bao": {"ma_nghiem_trong_cho_xac_nhan": r[990], "co_nghiem_trong": r[991],
                     "ma_cuoi": y_nghia_ma(r[943]), "moi_lua_hong": r[849], "hut_lieu_thieu_hat": r[123]},
        "lam_nong": {"bat": r[39], "dich_c": M[52], "phut": M[51], "tien_trinh_pct": r[898],
                     "trang_thai": LAM_NONG.get(r[895], r[895]), "o_tien_trinh_chung_pct": r[124]},
        "khoa": {"pc_control": r[920], "nhiet_goc": r[921], "dang_co_me": r[922], "start": r[923], "xoa": r[924],
                 "auto": r[925], "che_do": r[927], "nhiet_charge": r[928], "nguon_nhiet_auto": r[933],
                 "auto_da_nap_chua_xa": r[934], "auto_chua_ho_so": r[935], "cua_xa_mo": r[936], "auto_ho_so_loi": r[937]},
        "cai_dat": {"mo_cua_nap_s": M[1], "mo_cua_trong_s": M[2], "xa_khay_s": M[3], "tran_bu_truoc_de_pct": M[4],
                    "tran_bu_de_fcs_pct": M[5], "tran_bu_sau_fcs_pct": M[31], "thanh_ghi_bt_et": M[6],
                    "dot_khoi_bat_c": M[7], "nhiet_cho_nap_pct": M[8], "lui_bat_lai_c": M[9], "dung_sai_nap_c": M[10],
                    "so_me_lap": M[11], "pc_slave_id": M[12], "pc_baud": M[13], "thoi_cap_lieu_s": M[14],
                    "tach_da_s": M[19], "nguong_de_c": M[20], "nguong_fcs_c": M[21], "lam_nguoi_s": M[22],
                    "nhiet_charge_c": M[23] / 10, "sv_dong_ho_bt_c": M[24], "thanh_ghi_sv": M[25],
                    "tach_da_som_s": M[26], "dot_khoi_them_s": M[27], "tran_nhiet_pct": M[28], "premix": M[29],
                    "lam_nguoi_som_c": M[30] / 10, "hut_moi_me_kg": M[32] / 10, "hut_tu_dong": M[33],
                    "tu_tat_nhiet": M[37], "vac_pid": M[47], "vac_dat_pa": M[48], "ap_min_pa": s16(M[49]),
                    "ap_max_pa": s16(M[50]), "lam_nong_phut": M[51], "lam_nong_dich_c": M[52], "tu_xa_khay": M[53],
                    "bien_xa_c": M[54] / 10, "con_lai_hut_kg": M[44] / 10},
        "cau_hinh_may": {"ma": cfg, "co": [t for b, t in BIT_CAU_HINH.items() if bit(cfg, b)],
                         "co_may": CO_MAY.get((cfg >> 6) & 7, "?"), "dieu_khien_tren_hmi": M[63],
                         "guong_461": r[461], "ket_qua_luu_cau_hinh": r[462]},
        "dong_ho_hmi": "%02d/%02d/%04d %02d:%02d:%02d" % (r[35], r[36], r[37], r[32], r[33], r[34]),
        "web": {"dia_chi": "%d.%d.%d.%d:%d" % tuple(r[1100 + i] for i in range(5)) if r[1100] else "", "nhip": r[1105],
                "khoa_web": r[847], "lua_ok": r[509], "lua_song": r[510]},
        "danh_dau_ban_hmi": r[819],            # = 820 ⇔ bản v28 đã dời khối (ZOOM51 trở đi)
    }
    if 600 in r:                                # có đọc danh sách 30 hồ sơ
        ds = []
        for n in range(1, 31):
            b = 600 + 7 * (n - 1)
            ds.append({"so": n, "ten": chu([M[100 + 30 * (n - 1) + i] for i in range(15)]),
                       "ngay": "%02d/%02d/%02d" % (r[b], r[b + 1], r[b + 2]) if r[b] else "",
                       "gio_charge": "%02d:%02d" % (r[b + 3], r[b + 4]) if r[b] else "",
                       "thoi_gian_rang": "%02d:%02d" % (r[b + 5], r[b + 6]) if r[b] else ""})
        out["danh_sach_ho_so"] = ds
    return out


def doc_tat_ca(p=None, ho_so=False):
    """MỌI ô có nghĩa trên HMI, gom nhóm, đổi đơn vị. ho_so=True: kèm danh sách 30 hồ sơ (thêm ~10 giao dịch)."""
    p = p or Panel()
    return _gom(_anh(p, ho_so=ho_so))


def man_hien_tai(p=None):
    p = p or Panel()
    so = p.doc(O_MAN, 1)[0]
    return so, TEN_MAN.get(so, "?")


NHOM_MAN = {   # màn → các nhóm số người đứng máy nhìn thấy trên màn đó
    2: ("nhiet", "dieu_khien", "co_cau", "dem_nguoc_giay", "chuong_trinh", "me", "moc", "ho_so", "canh_bao", "khoa"),
    6: ("ho_so", "danh_sach_ho_so", "co_cau", "khoa"), 12: ("ho_so", "danh_sach_ho_so", "co_cau", "khoa"),
    13: ("ho_so", "danh_sach_ho_so", "co_cau", "khoa"), 1: ("cai_dat", "dieu_khien", "co_cau", "canh_bao"),
    14: ("lam_nong", "nhiet", "khoa"), 5: ("cai_dat",), 24: ("cai_dat",), 25: ("cai_dat",), 30: ("cai_dat",),
    9: ("cai_dat", "chuong_trinh", "khoa"), 36: ("cau_hinh_may",), 31: ("tai_khoan",), 15: ("tai_khoan",),
    19: ("ho_so", "me", "moc"), 20: ("chuong_trinh", "lam_nong"), 23: ("canh_bao", "chuong_trinh"),
    8: ("ho_so",), 11: ("ho_so",), 16: ("ho_so",),
}


def doc_man(man_id, p=None):
    """Các nhóm số thuộc màn man_id (đọc thẳng bộ nhớ — không cần màn đó đang hiện)."""
    nhom = NHOM_MAN.get(int(man_id), ("man",))
    d = doc_tat_ca(p, ho_so="danh_sach_ho_so" in nhom)
    ra = {"man": {"so": int(man_id), "ten": TEN_MAN.get(int(man_id), "?"), "dang_hien": d["man"]["so"] == int(man_id)}}
    for k in nhom:
        if k in d:
            ra[k] = d[k]
    return ra


def doc_ho_so(p=None):
    return doc_tat_ca(p, ho_so=True)["danh_sach_ho_so"]


# ── ghi theo quy trình (Hồng tự thử sau mẻ — giáo trình mục 8) ────────────────────────────────────────────
class TuChoi(Exception):
    """Điều kiện trước không đạt — KHÔNG ghi gì."""


def _quyen(lai=False):
    if os.environ.get("HONG_DUOC_THAO_TAC") != "1":
        raise TuChoi("Chưa có quyền thao tác HMI (HONG_DUOC_THAO_TAC=1).")
    if lai and os.environ.get("HONG_DUOC_LAI") != "1":
        raise TuChoi("Lệnh này làm cơ cấu chạy / bật nhiệt — cần thêm HONG_DUOC_LAI=1 (anh Thành cho quyền).")


def _o(dia_chi):
    """'$15' / 15 → 15 ; 'M23' / '$M23' → 2023."""
    s = str(dia_chi).lstrip("$")
    return TCP_M + int(s[1:]) if s[:1].upper() == "M" else int(s)


def _ghi_kiem(p, dia_chi, gia_tri, cho=CHO_GHI_S, mong=None):
    """Ghi rồi ĐỌC LẠI. Trả (giá trị đọc lại, đạt?). mong = giá trị chờ thấy (mặc định = giá trị ghi)."""
    o = _o(dia_chi)
    vals = gia_tri if isinstance(gia_tri, (list, tuple)) else [gia_tri]
    p.ghi(o, [int(v) & 0xFFFF for v in vals])
    mong = vals if mong is None else (mong if isinstance(mong, (list, tuple)) else [mong])
    het = time.time() + cho
    while True:
        lai = p.doc(o, len(mong))
        if lai == list(mong) or time.time() > het:
            return (lai if len(lai) > 1 else lai[0]), lai == list(mong)
        time.sleep(0.15)


def _can_may_ranh(d):
    if d["chuong_trinh"]["start"]:
        raise TuChoi("Đang chạy chương trình ($0 = 1) — không đổi được.")
    if d["chuong_trinh"]["lam_nong"]:
        raise TuChoi("Đang làm nóng ($39 = 1) — dừng làm nóng trước.")
    if not d["tai_khoan"]["dang_nhap"]:
        raise TuChoi("Panel chưa đăng nhập ($950 = 0) — Panel().dang_nhap() trước.")


def chuyen_man(man_id, p=None):
    """Ghi $49 = số màn (Control Block), chờ $21 đổi. Popup (màn phụ) qua $49: CHƯA XÁC MINH."""
    _quyen()
    p = p or Panel()
    man_id = int(man_id)
    if man_id not in TEN_MAN:
        raise TuChoi("Màn %d không có trong bản HMI." % man_id)
    if p.doc(950, 1)[0] != 1 and man_id != 15:
        raise TuChoi("Chưa đăng nhập: macro nền tự mở lại màn 15 — đăng nhập trước.")
    p.ghi(O_DOI_MAN, [man_id])
    het = time.time() + 3
    while time.time() < het:
        if p.doc(O_MAN, 1)[0] == man_id:
            return {"man": man_id, "dat": True}
        time.sleep(0.2)
    return {"man": p.doc(O_MAN, 1)[0], "dat": False, "ghi_chu": "ghi $49 = %d mà $21 không đổi" % man_id}


def chon_ho_so(n, p=None, cho=15):
    """Chọn + nạp hồ sơ n (1..30) như người bấm nút chọn: đứng màn Hồ sơ, bật đúng 1 nút $199+n, rồi $15 = n.
    Board chỉ nạp khi $21 ∈ {6,12,13}; macro đồng hồ trả $15 về 0 nếu nút $199+n = 0 (vì vậy phải ghi nút TRƯỚC)."""
    _quyen()
    p = p or Panel()
    n = int(n)
    if not 1 <= n <= 30:
        raise TuChoi("Hồ sơ phải 1..30 (tệp n.csv trên thẻ SD).")
    _can_may_ranh(doc_tat_ca(p))
    trang = 6 if n <= 10 else (12 if n <= 20 else 13)
    if p.doc(O_MAN, 1)[0] != trang and not chuyen_man(trang, p)["dat"]:
        raise TuChoi("Không đưa được panel về màn Hồ sơ %d." % trang)
    _ghi_kiem(p, 200, [1 if i == n - 1 else 0 for i in range(30)])
    _, ok = _ghi_kiem(p, 15, n)
    het = time.time() + cho
    while time.time() < het:
        d = doc_tat_ca(p)
        if d["ho_so"]["nap_pct"] == 100 or d["ho_so"]["hop_le"] == 1 or d["chuong_trinh"]["ma"] in (103, 120, 381, 382, 383, 384, 385):
            break
        time.sleep(0.5)
    d = doc_tat_ca(p)
    return {"ghi_15": ok, "ho_so": d["ho_so"], "nhiet_charge_c": d["cai_dat"]["nhiet_charge_c"],
            "ma": d["chuong_trinh"]["ma_y_nghia"]}


def bo_chon_ho_so(p=None):
    _quyen()
    p = p or Panel()
    _can_may_ranh(doc_tat_ca(p))
    _ghi_kiem(p, 200, [0] * 30)
    return {"15": _ghi_kiem(p, 15, 0)}


def che_do(auto, p=None):
    """$22: 0 = RANG LƯU (ghi hồ sơ đang chọn), 1 = AUTO (chạy theo hồ sơ). Chỉ khi máy rảnh."""
    _quyen()
    p = p or Panel()
    _can_may_ranh(doc_tat_ca(p))
    return {"22": _ghi_kiem(p, 22, 1 if auto else 0)}


def nhiet_charge(c, p=None):
    """$M23 = °C × 10 (0..250 °C). Bị ghi đè mỗi lần nạp hồ sơ; khoá trên HMI khi AUTO ($928)."""
    _quyen()
    p = p or Panel()
    if not 0 <= float(c) <= 250:
        raise TuChoi("Nhiệt charge 0..250 °C.")
    if doc_tat_ca(p)["chuong_trinh"]["start"]:
        raise TuChoi("Đang chạy chương trình — đổi nhiệt charge giữa mẻ làm lệch bước COOL DOWN / CHECK.")
    return {"M23": _ghi_kiem(p, "M23", int(round(float(c) * 10)))}


def lam_moi_ho_so(p=None):
    """Nút 'Làm mới' màn Hồ sơ = đảo $38; firmware nạp lại ngày giờ 30 hồ sơ vào $600..$809."""
    _quyen()
    p = p or Panel()
    cu = p.doc(38, 1)[0]
    return {"38": _ghi_kiem(p, 38, 0 if cu else 1)}


def dat_ten_ho_so(n, ten, p=None):
    """Đặt TÊN hồ sơ n (1..30) = ô chữ màn Hồ sơ `$M(100 + 30(n−1))`, 15 word = 30 ký tự ASCII, byte thấp trước.
    Tên chỉ nằm trong `$M` của HMI (giữ khi mất điện) — firmware KHÔNG ghi tên xuống SD. Luật anh Thành 15/10: mỗi mẻ RANG LƯU
    xong ⇒ đặt tên `<ddmm> M<số mẻ> <khối lượng>g [ghi chú]`. Chỉ khi máy không chạy chương trình."""
    _quyen()
    p = p or Panel()
    n = int(n)
    if not 1 <= n <= 30:
        raise TuChoi("Hồ sơ phải 1..30.")
    if not ten or len(ten) > 30 or any(not (32 <= ord(c) < 127) for c in ten):
        raise TuChoi("Tên 1..30 ký tự ASCII không dấu.")
    if doc_tat_ca(p)["chuong_trinh"]["start"]:
        raise TuChoi("Đang chạy chương trình ($0 = 1) — đặt tên sau mẻ.")
    b = ten.encode("ascii").ljust(30, b"\x00")
    words = [b[i] | (b[i + 1] << 8) for i in range(0, 30, 2)]
    lai, ok = _ghi_kiem(p, "M%d" % (100 + 30 * (n - 1)), words)
    return {"ho_so": n, "ten_doc_lai": chu(lai if isinstance(lai, list) else [lai]), "dat": ok}


def pc_control(bat, p=None):
    """$13: 1 = board nghe PC (Artisan / PC_Link) thay vì panel. Hồng lái qua panel ⇒ luôn để 0."""
    _quyen()
    p = p or Panel()
    if bat and doc_tat_ca(p)["chuong_trinh"]["dang_co_me"]:
        raise TuChoi("Đang có mẻ — HMI khoá công tắc này ($920).")
    return {"13": _ghi_kiem(p, 13, 1 if bat else 0)}


def xac_nhan_canh_bao(p=None):
    """Nút 'Xác nhận đã xem' màn 23: $990 = 0 (xoá mã nghiêm trọng đang chốt). KHÔNG sửa lỗi gốc."""
    _quyen()
    p = p or Panel()
    return {"990": _ghi_kiem(p, 990, 0)}


def dung_chuong_trinh(p=None):
    """$0 = 0 — dừng chương trình (luôn được, như nút Dừng). KHÔNG tự tắt nhiệt / không làm nguội: gọi an_toan sau."""
    _quyen()
    p = p or Panel()
    return {"0": _ghi_kiem(p, 0, 0)}


def bat_dau(p=None):
    """START chương trình ($0 = 1). Kiểm như macro nút Bắt đầu mẻ + chốt của firmware. Máy sẽ TỰ CHẠY chuỗi mẻ."""
    _quyen(lai=True)
    p = p or Panel()
    d = doc_tat_ca(p)
    _can_may_ranh(d)
    if d["co_cau"]["xa_trong"]:
        raise TuChoi("Cửa xả trống đang mở ($7 = 1) — HMI khoá Start ($936).")
    if d["chuong_trinh"]["che_do"] == "AUTO" and d["ho_so"]["hop_le"] != 1:
        raise TuChoi("AUTO mà hồ sơ chưa hợp lệ ($118 ≠ 1) — chon_ho_so trước.")
    if not bit(d["cau_hinh_may"]["ma"], 15):
        raise TuChoi("Máy chưa cấu hình ($M62 bit 15 = 0) — board chặn (mã 422).")
    if d["dieu_khien"]["pc_control"]:
        raise TuChoi("Cờ PC control đang bật — board không nghe panel.")
    lai, ok = _ghi_kiem(p, 0, 1)
    time.sleep(1.0)
    d = doc_tat_ca(p)
    return {"0": (lai, ok), "ma": d["chuong_trinh"]["ma_y_nghia"], "ho_so": d["ho_so"]["chon"],
            "che_do": d["chuong_trinh"]["che_do"]}


def lam_nong(bat, dich=None, phut=None, p=None):
    """Làm nóng trống (preheat của firmware, PID): $M52 đích 150..230 °C, $M51 2..60 phút, $39 = 1 / 0."""
    _quyen(lai=bool(bat))
    p = p or Panel()
    ra = {}
    if bat:
        d = doc_tat_ca(p)
        _can_may_ranh(d)
        if dich is not None:
            if not 150 <= int(dich) <= 230:
                raise TuChoi("Đích làm nóng 150..230 °C.")
            ra["M52"] = _ghi_kiem(p, "M52", int(dich))
        if phut is not None:
            if not 2 <= int(phut) <= 60:
                raise TuChoi("Thời gian làm nóng 2..60 phút.")
            ra["M51"] = _ghi_kiem(p, "M51", int(phut))
        if p.doc(31, 1)[0]:                     # macro nút: tắt dò PID gió trước ({Link2}W40032 = 0)
            ra["31"] = _ghi_kiem(p, 31, 0)
    ra["39"] = _ghi_kiem(p, 39, 1 if bat else 0)
    return ra


CO_CAU = {"nap": 6, "xa_trong": 7, "xa_khay": 8, "quat_nguoi": 4}


def co_cau(ten, bat, p=None):
    """Bật/tắt 1 cơ cấu như nút dock. Ngoài chương trình firmware KHÔNG tự đóng cửa nạp / xả — phải ghi 0 lại."""
    if ten not in CO_CAU:
        raise TuChoi("Chỉ hỗ trợ: %s" % ", ".join(CO_CAU))
    _quyen(lai=bool(bat))
    p = p or Panel()
    o = CO_CAU[ten]
    return {str(o): _ghi_kiem(p, o, 1 if bat else 0)}


# ── CLI ───────────────────────────────────────────────────────────────────────────────────────────────
def _in(d, thut=""):
    for k, v in d.items():
        if isinstance(v, dict):
            print("%s[%s]" % (thut, k))
            _in(v, thut + "  ")
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            print("%s[%s]" % (thut, k))
            for x in v:
                if x.get("ten") or x.get("ngay"):
                    print(thut + "  " + " · ".join("%s" % x[c] for c in x))
        else:
            print("%s%s = %s" % (thut, k, v))


def _main(argv):
    if not argv:
        print(__doc__)
        return
    lenh, pos, opt = argv[0], [], {}
    co_gia_tri = {"dich", "phut"}                # '--dich 210' hoặc '--dich=210'; cờ trơn: --json, --ho_so
    it = iter(argv[1:])
    for a in it:
        if not a.startswith("--"):
            pos.append(a)
            continue
        k, _, v = a[2:].partition("=")
        opt[k] = v or (next(it, "") if k in co_gia_tri else "1")
    xuat = (lambda d: print(json.dumps(d, ensure_ascii=False, indent=1))) if "json" in opt else _in
    try:
        if lenh == "doc":
            xuat(doc_tat_ca(ho_so="ho_so" in opt))
        elif lenh == "man":
            print("%d · %s" % man_hien_tai())
        elif lenh == "doc_man":
            xuat(doc_man(int(pos[0])))
        elif lenh == "ho_so":
            for x in doc_ho_so():
                print("%2d  %-30s %s %s  rang %s" % (x["so"], x["ten"] or "-", x["ngay"], x["gio_charge"], x["thoi_gian_rang"]))
        elif lenh == "tho":
            o, n = _o(pos[0]), int(pos[1]) if len(pos) > 1 else 1
            print(Panel().doc(o, n))
        elif lenh == "chuyen_man":
            xuat(chuyen_man(int(pos[0])))
        elif lenh == "chon_ho_so":
            xuat(chon_ho_so(int(pos[0])))
        elif lenh == "bo_chon_ho_so":
            xuat(bo_chon_ho_so())
        elif lenh == "che_do":
            xuat(che_do(pos[0].lower() == "auto"))
        elif lenh == "nhiet_charge":
            xuat(nhiet_charge(float(pos[0])))
        elif lenh == "dat_ten_ho_so":
            xuat(dat_ten_ho_so(int(pos[0]), " ".join(pos[1:])))
        elif lenh == "lam_moi_ho_so":
            xuat(lam_moi_ho_so())
        elif lenh == "pc_control":
            xuat(pc_control(pos[0] == "1"))
        elif lenh == "xac_nhan_canh_bao":
            xuat(xac_nhan_canh_bao())
        elif lenh == "dung_chuong_trinh":
            xuat(dung_chuong_trinh())
        elif lenh == "bat_dau":
            xuat(bat_dau())
        elif lenh == "lam_nong":
            xuat(lam_nong(pos[0] == "1", dich=opt.get("dich"), phut=opt.get("phut")))
        elif lenh == "co_cau":
            xuat(co_cau(pos[0], pos[1] == "1"))
        else:
            print(__doc__)
    except TuChoi as e:
        sys.exit("TỪ CHỐI (không ghi gì): %s" % e)


if __name__ == "__main__":
    _main(sys.argv[1:])
