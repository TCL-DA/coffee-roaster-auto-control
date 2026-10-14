"""Test tren PC cho hang doi ma trang thai (include/MachineStatus.h) — goi FW-01.

    python tools/fw_sim/test_stt_queue.py            -> ma thoat 0 neu dat het

Cach lam: chep MachineStatus.h THAT vao thu muc tam canh mot Define.h gia (dong ho gia,
nodeHMI gia ghi lai moi lan ghi), bien dich bang `zig c++` roi chay. Bo loc cu (ban commit
HEAD) duoc nhung vao de so hoi quy: moi ma 0..1000 phai giu nguyen ket qua loc, TRU nhom
duoc mo co chu dich (48-50 va khoi 401-430).
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
TMP = os.path.join(HERE, "out", "test_stt")

FAKE_DEFINE = r'''#pragma once
#include <cstdint>
#include <utility>
#include <vector>
#define STT_W 41
struct FakeSerial { template <class T> void print(T) {} template <class T> void println(T) {} };
static FakeSerial SerialComputer;
static bool enDebug = false;
static uint32_t fakeMs = 100000;
static inline uint32_t millis() { return fakeMs; }
struct FakeNode {
    std::vector<std::pair<uint16_t, uint16_t> > w;
    uint8_t writeSingleRegister(uint16_t a, uint16_t v) { w.push_back(std::make_pair(a, v)); return 0; }
};
static FakeNode nodeHMI;
'''

TEST_MAIN = r'''#include <cstdio>
#include <cstdint>
#include <vector>
#include "Define.h"
#include "old_visible.h"
#include "MachineStatus.h"

static int fails = 0;
static void check(bool ok, const char* msg) {
    printf("%s  %s\n", ok ? "DAT " : "HONG", msg);
    if (!ok) fails++;
}

// xa het hang doi + xoa dau vet, de moi ca thu bat dau sach
static void lamSach() {
    for (int i = 0; i < 80; i++) { fakeMs += 1000; flushMachineStatus(); }
    sttLastSent = 0;
    nodeHMI.w.clear();
    fakeMs += 5000;
}
// flush n lan, moi lan cach 1000 ms; tra ve day ma da ghi len HMI
static std::vector<uint16_t> xa(int n) {
    std::vector<uint16_t> out;
    for (int i = 0; i < n; i++) {
        size_t truoc = nodeHMI.w.size();
        flushMachineStatus();
        if (nodeHMI.w.size() > truoc) out.push_back(nodeHMI.w.back().second);
        fakeMs += 1000;
    }
    return out;
}
static bool bang(const std::vector<uint16_t>& a, std::initializer_list<uint16_t> b) {
    return a == std::vector<uint16_t>(b);
}
static void in(const char* ten, const std::vector<uint16_t>& a) {
    printf("      %s:", ten);
    for (size_t i = 0; i < a.size(); i++) printf(" %u", a[i]);
    printf("\n");
}

int main() {
    // T1 — hoi quy bo loc: chi nhom duoc mo co chu dich moi doi
    {
        int lech = 0;
        for (uint16_t c = 0; c <= 1000; c++) {
            // 96 (14/10/2026): mẻ đang lưu quá giới hạn hồ sơ — mở có chủ đích
            bool mo = (c >= 48 && c <= 50) || (c >= 401 && c <= 430) || c == 96;
            bool mong = sttOldVisible(c) || mo;
            if (sttIsOperatorVisible(c) != mong) { if (lech < 20) printf("      lech ma %u\n", c); lech++; }
        }
        check(lech == 0, "T1 bo loc: 48-50 va 401-430 hien; moi ma khac giu nguyen nhu ban cu");
        check(!sttIsOperatorVisible(45) && !sttIsOperatorVisible(46) && !sttIsOperatorVisible(47),
              "T1b ma tien trinh 45/46/47 van an (chua doi)");
    }
    // T2 — FIFO, moi 1000 ms mot ma, ghi dung thanh ghi STT_W-1
    {
        lamSach();
        setMachineStatus(21); setMachineStatus(23); setMachineStatus(26);
        flushMachineStatus();
        bool ok1 = nodeHMI.w.size() == 1 && nodeHMI.w[0].first == STT_W - 1 && nodeHMI.w[0].second == 21;
        flushMachineStatus();                      // cung ms -> chua duoc ghi tiep
        fakeMs += 999; flushMachineStatus();
        bool ok2 = nodeHMI.w.size() == 1;
        fakeMs += 1; flushMachineStatus();
        bool ok3 = nodeHMI.w.size() == 2 && nodeHMI.w[1].second == 23;
        check(ok1 && ok2 && ok3, "T2 FIFO + 1 ma moi 1000 ms + ghi vao thanh ghi 40");
    }
    // T3 — khong xep lai ma vua gui
    {
        lamSach();
        setMachineStatus(21);
        std::vector<uint16_t> a = xa(1);
        setMachineStatus(21);
        std::vector<uint16_t> b = xa(2);
        check(bang(a, {21}) && b.empty(), "T3 ma trung ma vua gui thi bo qua");
    }
    // T4 — ma nghiem trong di truoc
    {
        lamSach();
        setMachineStatus(21); setMachineStatus(23); setMachineStatus(26); setMachineStatus(27); setMachineStatus(28);
        setMachineStatus(413);
        std::vector<uint16_t> a = xa(12);
        if (!bang(a, {413, 21, 23, 26, 27, 28})) in("T4", a);
        check(bang(a, {413, 21, 23, 26, 27, 28}), "T4 ma 413 (bao chay) len HMI truoc 5 ma thuong dang cho");
    }
    // T5 — nhieu ma nghiem trong giu dung thu tu
    {
        lamSach();
        setMachineStatus(21); setMachineStatus(413); setMachineStatus(417);
        std::vector<uint16_t> a = xa(10);
        if (!bang(a, {413, 417, 21})) in("T5", a);
        check(bang(a, {413, 417, 21}), "T5 hai ma nghiem trong: dung thu tu phat, roi moi toi ma thuong");
    }
    // T6 — hang doi day: bo ma THUONG cu nhat, khong bo ma nghiem trong
    {
        lamSach();
        setMachineStatus(417);
        uint16_t thuong[12] = {21, 23, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34};
        for (int i = 0; i < 12; i++) setMachineStatus(thuong[i]);
        std::vector<uint16_t> a = xa(20);
        int dem417 = 0;
        for (size_t i = 0; i < a.size(); i++) if (a[i] == 417) dem417++;
        if (!(a.size() == 10 && a[0] == 417 && dem417 == 1)) in("T6", a);
        check(a.size() == 10 && a[0] == 417 && dem417 == 1, "T6 tran hang doi: ma 417 khong bi roi, len dau tien");
        check(a.size() == 10 && a[1] == 26 && a[9] == 34, "T6b tran hang doi: roi 3 ma thuong CU nhat (21, 23, 25)");
    }
    // T7 — ma nghiem trong phat lap khi dang cho: chi giu mot
    {
        lamSach();
        setMachineStatus(413); setMachineStatus(413); setMachineStatus(413);
        std::vector<uint16_t> a = xa(8);
        if (!bang(a, {413})) in("T7", a);
        check(bang(a, {413}), "T7 ma nghiem trong phat lap 3 lan: chi gui 1 lan");
    }
    // T8 — ma thuong giu nguyen nep cu: khong gop khi dang cho (trang thai cuoi phai dung)
    {
        lamSach();
        setMachineStatus(161); setMachineStatus(162); setMachineStatus(161);
        std::vector<uint16_t> a = xa(4);
        if (!bang(a, {161, 162, 161})) in("T8", a);
        check(bang(a, {161, 162, 161}), "T8 ma thuong 161,162,161: gui du 3, trang thai cuoi dung (161)");
    }
    // T9 — hang doi toan ma nghiem trong
    {
        lamSach();
        for (uint16_t c = 401; c <= 410; c++) setMachineStatus(c);
        setMachineStatus(21);                      // ma thuong khong duoc day ma nghiem trong ra
        setMachineStatus(411);                     // ma nghiem trong moi: bo ma nghiem trong cu nhat
        std::vector<uint16_t> a = xa(40);
        if (!bang(a, {402, 403, 404, 405, 406, 407, 408, 409, 410, 411})) in("T9", a);
        check(bang(a, {402, 403, 404, 405, 406, 407, 408, 409, 410, 411}),
              "T9 day 10 ma nghiem trong: ma thuong moi bi bo; ma nghiem trong moi day ma nghiem trong cu nhat");
    }
    // T10 — ma bi loc khong vao hang doi
    {
        lamSach();
        setMachineStatus(45); setMachineStatus(141); setMachineStatus(999);
        std::vector<uint16_t> a = xa(3);
        check(a.empty(), "T10 ma bi loc (45, 141, 999) khong len HMI");
    }
    // T11 — cac ma moi mo deu len duoc HMI
    {
        lamSach();
        uint16_t moi[12] = {413, 414, 415, 416, 417, 418, 419, 420, 421, 48, 49, 50};
        int ok = 0;
        for (int i = 0; i < 12; i++) {
            lamSach();
            setMachineStatus(moi[i]);
            std::vector<uint16_t> a = xa(2);
            if (a.size() == 1 && a[0] == moi[i]) ok++;
        }
        check(ok == 12, "T11 ca 12 ma moi mo (413-421, 48, 49, 50) deu duoc ghi len HMI");
    }
    // T12 — ma nghiem trong dung yen 3000 ms truoc khi ma ke ghi de
    //        (do tren HMIApp 04/10/2026: ma dung 1,0 s khong duoc bang canh bao ghi nhan; 1,2 s thi duoc)
    {
        lamSach();
        setMachineStatus(413); setMachineStatus(21);
        flushMachineStatus();                              // t0: 413
        bool a = nodeHMI.w.size() == 1 && nodeHMI.w[0].second == 413;
        fakeMs += 1000; flushMachineStatus();
        fakeMs += 1000; flushMachineStatus();
        fakeMs += 999;  flushMachineStatus();              // t0 + 2999: chua duoc ghi de
        bool b = nodeHMI.w.size() == 1;
        fakeMs += 1;    flushMachineStatus();              // t0 + 3000
        bool c = nodeHMI.w.size() == 2 && nodeHMI.w[1].second == 21;
        check(a && b && c, "T12 sau ma nghiem trong: ma ke chi duoc ghi sau 3000 ms");
    }
    // T13 — nhip ghi: nghiem trong cach 3000 ms, ma thuong van 1000 ms
    {
        lamSach();
        setMachineStatus(410); setMachineStatus(414); setMachineStatus(21); setMachineStatus(23);
        std::vector<uint32_t> luc;
        uint32_t t0 = fakeMs;
        for (int i = 0; i < 100; i++) {
            size_t truoc = nodeHMI.w.size();
            flushMachineStatus();
            if (nodeHMI.w.size() > truoc) luc.push_back(fakeMs - t0);
            fakeMs += 100;
        }
        bool ok = nodeHMI.w.size() == 4 && nodeHMI.w[0].second == 410 && nodeHMI.w[1].second == 414 &&
                  nodeHMI.w[2].second == 21 && nodeHMI.w[3].second == 23 &&
                  luc.size() == 4 && luc[0] == 0 && luc[1] == 3000 && luc[2] == 6000 && luc[3] == 7000;
        if (!ok) { printf("      T13 luc:"); for (size_t i = 0; i < luc.size(); i++) printf(" %u", luc[i]); printf("\n"); }
        check(ok, "T13 nhip ghi: 410 (0 ms), 414 (3000), 21 (6000), 23 (7000)");
    }
    printf("ket qua: %s (%d hong)\n", fails ? "CO LOI" : "DAT HET", fails);
    return fails ? 1 : 0;
}
'''


def old_visible():
    """Lay ham sttIsOperatorVisible cua ban commit HEAD, doi ten thanh sttOldVisible."""
    r = subprocess.run(["git", "show", "HEAD:include/MachineStatus.h"], cwd=REPO, capture_output=True)
    if r.returncode:
        sys.exit("khong doc duoc ban HEAD cua MachineStatus.h")
    src = r.stdout.decode("utf-8", "replace")
    m = re.search(r"inline bool sttIsOperatorVisible\(uint16_t code\) \{.*?\n\}\n", src, re.S)
    if not m:
        sys.exit("khong tim thay ham bo loc trong ban HEAD")
    return "#pragma once\n#include <cstdint>\n" + m.group(0).replace("sttIsOperatorVisible", "sttOldVisible")


def main():
    os.makedirs(TMP, exist_ok=True)
    inc = os.path.join(os.environ.get("OTL_FW_SRC") or REPO, "include")
    with open(os.path.join(inc, "MachineStatus.h"), "rb") as f:
        open(os.path.join(TMP, "MachineStatus.h"), "wb").write(f.read())
    for ten, nd in (("Define.h", FAKE_DEFINE), ("test_main.cpp", TEST_MAIN), ("old_visible.h", old_visible())):
        open(os.path.join(TMP, ten), "w", encoding="utf-8", newline="\n").write(nd)
    exe = os.path.join(TMP, "test_stt.exe")
    cmd = [sys.executable, "-m", "ziglang", "c++", "-std=gnu++17", "-O1", "-Wno-everything",
           "-I", TMP, os.path.join(TMP, "test_main.cpp"), "-o", exe]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        print("\n".join([ln for ln in (r.stderr or "").splitlines() if "error" in ln][:30]) or r.stderr[-3000:])
        sys.exit("LOI BIEN DICH test")
    r = subprocess.run([exe], capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout.rstrip())
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
