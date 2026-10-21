"""Tệp cài đặt Artisan (.aset) cho máy rang O Tesla — mẫu chuẩn + sinh tệp theo module wifi.

Mẫu `otl_artisan_template.aset` dựng từ tệp Artisan bản auto mới nhất của O Tesla (13/08/2026:
HMI không VR, đủ tính năng — nút ±5 vacuum / gió / gas / trống, Charge, Drop, Escape, Ignition) rồi:
  · tách Mixer khỏi Cooling: nút 17 "Cooling" (ô 13), nút 18 (đang trống) thành "Mixer" (ô 21 — firmware 19/10/2026)
  · hiện nút ±5 vacuum (mẫu 12 kg đang ẩn) — bản đủ tính năng
  · xoá đường dẫn trên máy O Tesla (profilepath / settingspath), cổng COM về COM1
  · [Modbus] type=3 (TCP — đếm 450 tệp .aset thật: tệp dùng IP đều type=3), port 8899
Dựng lại mẫu:   python otl_aset.py --build <tệp .aset nguồn>
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = "otl_artisan_template.aset"
MIXER_REG, COOL_REG = 21, 13
BTN_COOL, BTN_MIXER = 17, 18


def _split(v):
    """Tách danh sách kiểu Qt ('a, "b,c", d') — dấu phẩy trong ngoặc kép không tách."""
    out, cur, q = [], "", False
    for ch in v:
        if ch == '"':
            q = not q
        if ch == "," and not q:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    out.append(cur.strip())
    return out


def _section(lines, name):
    start = next(i for i, ln in enumerate(lines) if ln.strip() == f"[{name}]")
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"^\[.+\]\s*$", lines[i])), len(lines))
    return start, end


def _set_key(lines, sec, key, value):
    s, e = _section(lines, sec)
    for i in range(s + 1, e):
        if lines[i].startswith(key + "="):
            lines[i] = f"{key}={value}"
            return
    lines.insert(e, f"{key}={value}")


def _edit_array(lines, key, idx, value):
    s, e = _section(lines, "ExtraEventButtons")
    for i in range(s + 1, e):
        if lines[i].startswith(key + "="):
            arr = _split(lines[i][len(key) + 1:])
            arr[idx] = value
            lines[i] = f"{key}=" + ", ".join(arr)
            return
    raise KeyError(key)


def _get_array(lines, key):
    s, e = _section(lines, "ExtraEventButtons")
    for i in range(s + 1, e):
        if lines[i].startswith(key + "="):
            return _split(lines[i][len(key) + 1:])
    raise KeyError(key)


def build_template(src):
    text = io.open(src, encoding="utf-8", errors="strict").read()
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()
    # thông tin trên máy O Tesla
    _set_key(lines, "General", "profilepath", "")
    _set_key(lines, "General", "settingspath", "")
    _set_key(lines, "SerialPort", "comport", "COM1")
    _set_key(lines, "Modbus", "comport", "COM1")
    _set_key(lines, "Batch", "batchcounter", "0")             # số mẻ / thời điểm mẻ cuối của máy O Tesla — khách bắt đầu từ 0
    _set_key(lines, "Batch", "lastroastepoch", "0")
    # nút: Cooling riêng (13), Mixer riêng (21) — chép thuộc tính hiển thị từ nút Cooling
    labels = _get_array(lines, "extraeventslabels")
    assert labels[BTN_COOL] in ("Mix&Cool", "Cooling") and labels[BTN_MIXER] in ("", "Mixer"), labels
    for key in ("extraeventstypes", "extraeventsvalues", "extraeventsactions", "extraeventsvisibility",
                "extraeventbuttoncolor", "extraeventbuttontextcolor", "extraeventsdescriptions"):
        _edit_array(lines, key, BTN_MIXER, _get_array(lines, key)[BTN_COOL])
    _edit_array(lines, "extraeventsvisibility", 0, "1")     # ±5 vacuum: bản đủ tính năng — hiện (mẫu 12 kg đang ẩn)
    _edit_array(lines, "extraeventsvisibility", 1, "1")
    _edit_array(lines, "extraeventslabels", BTN_COOL, "Cooling")
    _edit_array(lines, "extraeventslabels", BTN_MIXER, "Mixer")
    _edit_array(lines, "extraeventsactionstrings", BTN_COOL,
                f'"read(1,{COOL_REG});write(1,{COOL_REG},not(_));read(1,{COOL_REG});button(_)"')
    _edit_array(lines, "extraeventsactionstrings", BTN_MIXER,
                f'"read(1,{MIXER_REG});write(1,{MIXER_REG},not(_));read(1,{MIXER_REG});button(_)"')
    out = nl.join(make_lines(lines, "10.10.100.254", 8899, 1)) + nl
    io.open(os.path.join(HERE, TEMPLATE), "w", encoding="utf-8", newline="").write(out)
    return len(lines)


def make_lines(lines, ip, port, dev_id):
    lines = list(lines)
    _set_key(lines, "Modbus", "type", "3")
    _set_key(lines, "Modbus", "host", ip)
    _set_key(lines, "Modbus", "port", str(int(port)))
    s, e = _section(lines, "Modbus")
    for i in range(s + 1, e):
        if re.match(r"^input\d+deviceId=", lines[i]):
            lines[i] = re.sub(r"=.*$", f"={int(dev_id)}", lines[i])
    return lines


# ── Cá nhân hoá (mặc định = đúng tệp mẫu) ────────────────────────────────────
BTN_VAC = (0, 1)                        # ±5 vacuum
LANGS = ("en", "vi", "fr")
# Nhãn tiếng Pháp theo đúng chữ Artisan bản tiếng Pháp (artisan_fr.qm: DROP → VIDAGE, COOLING → Refroidissement);
# Escape = mở cửa xả bồn nguội → "Évacuation", Mixer = cánh khuấy bồn nguội → "Agitateur".
BTN_NAMES = {14: ("Charge", "Nạp", "Charge"), 15: ("Drop", "Xả", "Vidage"), 16: ("Escape", "Thoát", "Évacuation"),
             17: ("Cooling", "Làm nguội", "Refroidissement"), 18: ("Mixer", "Khuấy", "Agitateur"),
             19: ("Ignition", "Đánh lửa", "Allumage")}
MIXCOOL = ("Mix & Cool", "Khuấy & nguội", "Refroid. & agit.")
DEFAULTS = {"mixcool": "split", "vac": "1", "lbl": "en", "unit": "C", "xmin": "20", "ymax": "250", "zmax": "30",
            "et": "0", "auto": "0", "save": "0", "prefix": "", "w": "g"}
CHOICES = {"mixcool": ("split", "combined"), "vac": ("1", "0"), "lbl": LANGS, "unit": ("C", "F"),
           "xmin": ("15", "20", "25", "30"), "ymax": ("250", "275", "300"), "zmax": ("20", "30", "40"),
           "et": ("1", "0"), "auto": ("1", "0"), "save": ("1", "0"), "w": ("g", "kg")}


def clean_opts(raw):
    """Chỉ nhận giá trị trong danh sách cho phép; còn lại về mặc định. Mã đầu số mẻ: ≤ 8 ký tự chữ/số/-."""
    o = dict(DEFAULTS)
    for k, allowed in CHOICES.items():
        v = str(raw.get(k, o[k]))
        o[k] = v if v in allowed else o[k]
    o["prefix"] = re.sub(r"[^A-Za-z0-9-]", "", str(raw.get("prefix", "")))[:8]
    return o


def qt_escape(s):
    """Chữ có dấu theo kiểu QSettings INI (\\xhhhh) — Artisan bản Qt5 đọc UTF-8 thô sẽ vỡ chữ. Như Qt: ngay sau một mã
    \\x mà là chữ số hex thì cũng phải thoát, không Qt đọc dính vào mã trước ('lửa' → 'l\\x1eed\\x61')."""
    out, prev_esc = [], False
    for ch in s:
        if ord(ch) > 0x7E or (prev_esc and ch in "0123456789abcdefABCDEF"):
            out.append("\\x%x" % ord(ch))
            prev_esc = True
        else:
            out.append(ch)
            prev_esc = False
    return "".join(out)


def _personalize(lines, o, save_dir=None):
    li = LANGS.index(o["lbl"])
    for idx, names in BTN_NAMES.items():
        _edit_array(lines, "extraeventslabels", idx, qt_escape(names[li]))
    if o["mixcool"] == "combined":
        # một nút cho cả hai: đổi ô Cooling → đọc lại → ghi đúng trạng thái đó sang ô Mixer (luôn cùng bật / cùng tắt)
        _edit_array(lines, "extraeventslabels", BTN_COOL, qt_escape(MIXCOOL[li]))
        _edit_array(lines, "extraeventsactionstrings", BTN_COOL,
                    f'"read(1,{COOL_REG});write(1,{COOL_REG},not(_));read(1,{COOL_REG});write(1,{MIXER_REG},_);button(_)"')
        _edit_array(lines, "extraeventsvisibility", BTN_MIXER, "0")
        _edit_array(lines, "extraeventslabels", BTN_MIXER, "")
    if o["vac"] == "0":
        for i in BTN_VAC:
            _edit_array(lines, "extraeventsvisibility", i, "0")
    f = o["unit"] == "F"
    ymax = int(o["ymax"])
    _set_key(lines, "General", "Mode", "F" if f else "C")
    _set_key(lines, "Axis", "ymax", str(round(ymax * 9 / 5 + 32) if f else ymax))
    _set_key(lines, "Axis", "zmax", str(round(int(o["zmax"]) * 9 / 5) if f else o["zmax"]))
    secs = int(o["xmin"]) * 60
    for key in ("xmax", "resetmaxtime", "locktimex_end"):
        _set_key(lines, "Axis", key, str(secs))
    _set_key(lines, "General", "ETcurve", "true" if o["et"] == "1" else "false")
    _set_key(lines, "events", "autoCharge", "true" if o["auto"] == "1" else "false")
    _set_key(lines, "events", "autoDrop", "true" if o["auto"] == "1" else "false")
    if o["save"] == "1" and save_dir:
        _set_key(lines, "General", "autosaveflag", "1")
        _set_key(lines, "General", "autosavepath", save_dir.replace("\\", "/"))
    _set_key(lines, "Batch", "batchprefix", o["prefix"])
    _set_key(lines, "Units", "weight", o["w"])
    return lines


def default_save_dir():
    """Thư mục tự lưu mẻ trên máy khách (tạo sẵn — Artisan cần thư mục có thật). macOS chặn Terminal ghi vào
    Documents khi người dùng bấm "Không cho phép" ⇒ lùi về thư mục nhà, không làm hỏng tệp .aset đang tải."""
    home = os.path.expanduser("~")
    for d in (os.path.join(home, "Documents", "OTL Roasts"), os.path.join(home, "OTL Roasts")):
        try:
            os.makedirs(d, exist_ok=True)
            return d
        except OSError:
            continue
    return os.path.join(home, "Documents", "OTL Roasts")


def make_aset(ip, port=8899, dev_id=1, base_dir=HERE, opts=None):
    """Tệp .aset hoàn chỉnh cho module đang chọn (Type TCP, Host, Port, Device) + tuỳ chọn cá nhân hoá."""
    text = io.open(os.path.join(base_dir, TEMPLATE), encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in text else "\n"
    o = clean_opts(opts or {})
    lines = make_lines(text.splitlines(), ip, port, dev_id)
    lines = _personalize(lines, o, default_save_dir() if o["save"] == "1" else None)
    return nl.join(lines) + nl


if __name__ == "__main__" and "--build" in sys.argv:
    n = build_template(sys.argv[sys.argv.index("--build") + 1])
    print("template:", TEMPLATE, n, "lines")
