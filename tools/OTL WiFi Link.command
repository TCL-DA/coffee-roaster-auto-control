#!/bin/bash
# OTL WiFi Link (macOS) - bam dup de chay. Lan dau: chuot phai -> Open (macOS 15: Privacy & Security -> Open Anyway).
# Giu nguyen thu muc "app" canh tep nay.
cd "$(dirname "$0")/app" || exit 1
# Mac chua cai Xcode CLT van co /usr/bin/python3 gia (chi bat hop thoai cai dat) => phai CHAY thu, khong chi kiem ten lenh.
if ! python3 -I -c 'import sys; sys.exit(sys.version_info < (3, 8))' >/dev/null 2>&1; then
  xcode-select --install >/dev/null 2>&1   # mo hop thoai cai Python 3 cua Apple
  osascript -e 'display alert "OTL WiFi Link" message "Python 3 required / requis / can Python 3.\n\nInstall the Apple command line tools (Install), then double-click OTL WiFi Link again.\nInstallez les outils de ligne de commande Apple (Installer), puis double-cliquez de nouveau sur OTL WiFi Link.\nCai bo cong cu dong lenh cua Apple (Install) roi bam dup lai OTL WiFi Link."'
  exit 1
fi
exec python3 -I otl_wifi_link.py
