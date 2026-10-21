"""Kiểm OTL WiFi Link phần không cần phần cứng: tệp .aset (nhãn 3 thứ tiếng, chữ có dấu kiểu QSettings) và đọc wifi
trên macOS (bản JSON không dịch theo ngôn ngữ máy, tên bị giấu "<redacted>", đoán wifi theo IP khi macOS giấu tên).

    python -m pytest tools/test_otl_wifi_link.py -q
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import otl_aset  # noqa: E402
import otl_wifi_vault as vault  # noqa: E402

HEX = "0123456789abcdefABCDEF"


def qt_unescape(s):
    """Đúng thuật toán iniUnescapedStringList của Qt: \\x + mọi chữ số hex liền sau (tham lam)."""
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s) and s[i + 1] == "x":
            j = i + 2
            while j < len(s) and s[j] in HEX:
                j += 1
            out.append(chr(int(s[i + 2:j], 16)))
            i = j
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def _labels(text):
    return otl_aset._get_array(text.splitlines(), "extraeventslabels")


# ── .aset ────────────────────────────────────────────────────────────────────
def test_aset_default_keeps_template_english_labels():
    labels = _labels(otl_aset.make_aset("192.168.1.50"))
    assert labels[14:20] == ["Charge", "Drop", "Escape", "Cooling", "Mixer", "Ignition"]


def test_aset_french_labels_read_back_as_artisan_french_words():
    labels = [qt_unescape(x) for x in _labels(otl_aset.make_aset("192.168.1.50", opts={"lbl": "fr"}))[14:20]]
    assert labels == ["Charge", "Vidage", "Évacuation", "Refroidissement", "Agitateur", "Allumage"]


def test_aset_french_labels_are_ascii_escaped_in_file():
    text = otl_aset.make_aset("192.168.1.50", opts={"lbl": "fr"})
    line = next(ln for ln in text.splitlines() if ln.startswith("extraeventslabels="))
    assert all(ord(c) < 128 for c in line)


def test_aset_combined_button_french_label_and_hidden_mixer():
    lines = otl_aset.make_aset("192.168.1.50", opts={"lbl": "fr", "mixcool": "combined"}).splitlines()
    labels = otl_aset._get_array(lines, "extraeventslabels")
    assert qt_unescape(labels[17]) == "Refroid. & agit."
    assert labels[18] == ""
    assert otl_aset._get_array(lines, "extraeventsvisibility")[18] == "0"
    assert "write(1,21,_)" in otl_aset._get_array(lines, "extraeventsactionstrings")[17]


@pytest.mark.parametrize("word", ["Évacuation", "Refroid. & agit.", "Đánh lửa", "Khuấy & nguội", "ửa", "Ébc"])
def test_qt_escape_round_trip(word):
    assert qt_unescape(otl_aset.qt_escape(word)) == word


def test_aset_unknown_label_language_falls_back_to_default():
    assert otl_aset.clean_opts({"lbl": "de"})["lbl"] == "en"


def test_aset_has_no_locale_key_so_artisan_keeps_its_own_language():
    # Artisan lấy ngôn ngữ theo máy (macOS tiếng Pháp ⇒ Artisan tiếng Pháp); tệp .aset không được ép ngôn ngữ.
    assert not any(ln.startswith("locale=") for ln in otl_aset.make_aset("10.10.100.254").splitlines())


def test_aset_tcp_link_fields():
    lines = otl_aset.make_aset("192.168.1.77", 8899, 2).splitlines()
    s, e = otl_aset._section(lines, "Modbus")
    sec = lines[s:e]
    assert "type=3" in sec and "host=192.168.1.77" in sec and "port=8899" in sec
    assert all(ln.endswith("=2") for ln in sec if ln.startswith("input") and "deviceId=" in ln)


def test_save_dir_falls_back_when_documents_blocked(monkeypatch, tmp_path):
    monkeypatch.setattr(os.path, "expanduser", lambda p: str(tmp_path))
    real = os.makedirs

    def fake(d, exist_ok=False):
        if "Documents" in d:
            raise PermissionError("macOS TCC")
        return real(d, exist_ok=exist_ok)

    monkeypatch.setattr(os, "makedirs", fake)
    assert otl_aset.default_save_dir() == os.path.join(str(tmp_path), "OTL Roasts")


# ── wifi macOS ───────────────────────────────────────────────────────────────
MAC_JSON = {"SPAirPortDataType": [{"spairport_airport_interfaces": [
    {"_name": "en0",
     "spairport_current_network_information": {"_name": "Atelier-Torref", "spairport_signal_noise": "-48 dBm / -92 dBm"},
     "spairport_airport_other_local_wireless_networks": [
         {"_name": "USR-DR404_72F0", "spairport_signal_noise": "-60 dBm / -90 dBm"},
         {"_name": "<redacted>", "spairport_signal_noise": "-70 dBm / -90 dBm"},
         {"_name": "OTL Roaster", "spairport_signal_noise": "-75 dBm / -90 dBm"}]},
    {"_name": "awdl0"}]}]}


def test_parse_mac_airport_json_and_signal():
    nets = vault.parse_mac_airport(json.dumps(MAC_JSON))
    assert nets == {"Atelier-Torref": 100, "USR-DR404_72F0": 80, "OTL Roaster": 50}


def test_parse_mac_airport_bad_text():
    assert vault.parse_mac_airport("") == {} and vault.parse_mac_airport("Wi-Fi:\n  Autres réseaux") == {}


@pytest.mark.parametrize("name", ["<redacted>", "<SSID Redacted>", "", "   "])
def test_hidden_ssid_is_unknown(name):
    assert vault._clean_ssid(name) is None


class _Mac:
    """Giả lập macOS: networksetup / ipconfig trả chữ cho trước."""

    def __init__(self, monkeypatch, ssid_line, ip):
        monkeypatch.setattr(vault.sys, "platform", "darwin")
        monkeypatch.setattr(vault.os, "name", "posix")
        out = {"-listallhardwareports": "Hardware Port: Wi-Fi\nDevice: en1\nEthernet Address: aa\n",
               "-getairportnetwork": ssid_line, "getsummary": "", "getifaddr": ip + "\n"}

        def run(args, timeout=10):
            self.calls.append(args)
            return next((v for k, v in out.items() if k in args), "")

        self.calls = []
        monkeypatch.setattr(vault, "_run", run)


def test_mac_current_name_when_visible(monkeypatch):
    m = _Mac(monkeypatch, "Current Wi-Fi Network: Atelier-Torref\n", "192.168.1.20")
    assert vault.pc_current() == "Atelier-Torref"
    assert ["networksetup", "-getairportnetwork", "en1"] in m.calls


def test_mac_hidden_name_is_none_not_redacted(monkeypatch):
    _Mac(monkeypatch, "You are not associated with an AirPort network.\n", "192.168.1.20")
    assert vault.pc_current() is None


@pytest.mark.parametrize("ip,ssid,want", [
    ("10.10.100.150", "USR-DR404_72F0", True),     # đã sang wifi module
    ("10.10.100.150", "OTL Roaster", True),
    ("10.10.100.150", "Atelier-Torref", False),    # còn ở wifi module, chưa về wifi quán
    ("192.168.1.20", "Atelier-Torref", True),      # đã về wifi quán
    ("192.168.1.20", "OTL Roaster", False),
    ("", "OTL Roaster", False),                    # chưa có IP
    ("169.254.3.4", "Atelier-Torref", False),      # IP tự gán = chưa nối được
])
def test_mac_pc_on_guesses_by_ip_when_name_hidden(monkeypatch, ip, ssid, want):
    _Mac(monkeypatch, "You are not associated with an AirPort network.\n", ip)
    assert vault.pc_on(ssid) is want


def test_mac_pc_on_compares_name_when_visible(monkeypatch):
    _Mac(monkeypatch, "Current Wi-Fi Network: Atelier-Torref\n", "10.10.100.150")
    assert vault.pc_on("Atelier-Torref") is True and vault.pc_on("OTL Roaster") is False
