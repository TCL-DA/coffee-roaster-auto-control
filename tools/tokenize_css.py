# -*- coding: utf-8 -*-
"""Chuẩn hóa design token cho OTL Roast Lab.html — ĐÃ CHẠY XONG 2026-07-23.
GIỮ LẠI LÀM TƯ LIỆU. Chạy lại sẽ fail assert (an toàn) vì :root đã đổi;
chỉ chạy lại sau khi restore _archive/temp-scratch/OTL Roast Lab.pre-token.bak.html.
Đường dẫn SRC hardcode theo máy này — máy khác phải sửa SRC trước.
Chỉ biến đổi CSS bên trong các khối <style>…</style>; không đụng JS/inline/canvas.
- font-size: 32 cỡ → thang 20 bậc (--fs-*)  [gập xuống, lệch tối đa 2px]
- border-radius: 16 giá trị → 6 token (--r-*)
- màu trạng thái rải rác → --ok / --warn / --danger / --amber-ink / --tip-bg
"""
import re, sys, io

SRC = r"f:\Project\100_OTL_06ALS - CMS - Cacao\OTL Roast Lab.html"

FS_MAP = {13:14,14:14, 15:16,16:16,17:16, 18:18,19:18, 20:20,21:20,
          22:22,23:22, 24:24,25:24, 26:26,27:26, 28:28, 30:30, 32:32,34:32,
          36:36,38:36, 40:40, 44:44,46:44, 48:48, 52:52, 56:56,
          72:72, 80:80, 100:100,104:100, 150:150}
R_MAP  = {3:'xs',8:'sm',9:'sm',10:'sm',11:'sm',12:'sm',
          14:'md',15:'md',16:'md', 18:'lg',20:'lg',22:'lg',
          24:'xl',26:'xl',28:'xl', 34:'2xl'}

# Thay màu ngữ nghĩa — chuỗi cũ → mới (đếm kỳ vọng để tự kiểm)
COLOR_SUBS = [
    # linkchip (kết nối máy)
    ('color:#0f9d6b;border-color:color-mix(in srgb,#0f9d6b 45%,transparent)',
     'color:var(--ok);border-color:color-mix(in srgb,var(--ok) 45%,transparent)', 1),
    ('background:#0f9d6b;box-shadow:0 0 10px #0f9d6b',
     'background:var(--ok);box-shadow:0 0 10px var(--ok)', 1),
    ('color:#e11d2f;border-color:color-mix(in srgb,#e11d2f 45%,transparent)',
     'color:var(--danger);border-color:color-mix(in srgb,var(--danger) 45%,transparent)', 1),
    ('background:#e11d2f;box-shadow:0 0 10px #e11d2f',
     'background:var(--danger);box-shadow:0 0 10px var(--danger)', 1),
    ('{color:#d98a1a}', '{color:var(--warn)}', 1),
    ('.d{background:#d98a1a;', '.d{background:var(--warn);', 1),
    # huy hiệu / trạng thái lẻ
    ('color:#16a34a}', 'color:var(--ok)}', 1),
    ('background:color-mix(in srgb,#0f9d6b 22%,transparent);color:#0f9d6b',
     'background:color-mix(in srgb,var(--ok) 22%,transparent);color:var(--ok)', 1),
    ('.ppstat.err{color:#e5484d} .ppstat.ok{color:#0f9d6b}',
     '.ppstat.err{color:var(--danger)} .ppstat.ok{color:var(--ok)}', 1),
    ('.editbtn.del{color:#e5484d}', '.editbtn.del{color:var(--danger)}', 1),
    # nút STOP preheat: gradient đỏ → màu đặc (luật màu đặc)
    ('background:linear-gradient(135deg,#e5484d,#b3252a)', 'background:var(--danger)', 1),
    # amber mực đọc (gas/preheat/history)
    ('color:#b8860b}', 'color:var(--amber-ink)}', 1),
    ('color:#c9871a}', 'color:var(--amber-ink)}', 1),
    ('color:#c9871a;min-width:78px', 'color:var(--amber-ink);min-width:78px', 1),
    ('color:#c9871a;font-size:26px', 'color:var(--amber-ink);font-size:26px', 1),
    ('color:#a9760f;', 'color:var(--amber-ink);', 1),
    # preheat running amber
    ('background:linear-gradient(90deg,#e8a43c,var(--accent))',
     'background:linear-gradient(90deg,var(--warn),var(--accent))', 1),
    ('#phStatus{color:#e8a43c}', '#phStatus{color:var(--warn)}', 1),
    ('background:#e8a43c;box-shadow:0 0 10px #e8a43c', 'background:var(--warn);box-shadow:0 0 10px var(--warn)', 1),
    # tooltip nền mực
    ('background:#0f1620;color:#fff', 'background:var(--tip-bg);color:#fff', 1),
    ('border-top-color:#0f1620}', 'border-top-color:var(--tip-bg)}', 1),
    ('border-bottom-color:#0f1620}', 'border-bottom-color:var(--tip-bg)}', 1),
]

# Token mới chèn vào :root + hợp nhất bộ trạng thái cũ (--c-ok/--c-warn/--c-try thành alias)
OLD_ROOT = "  --c-ror:#a16207; --c-gas:#ffb020; --c-ok:#36c77e; --c-warn:#ef3b2e; --c-try:#f0a020;"
NEW_ROOT = """  --c-ror:#a16207; --c-gas:#ffb020;
  /* ── TOKEN TRẠNG THÁI (hợp nhất 2026-07-23) — 1 nghĩa 1 màu ── */
  --ok:#0f9d6b; --warn:#d98a1a; --danger:#e11d2f;
  --amber-ink:#b8860b;   /* mực amber đọc được (gas/preheat/lệch) */
  --tip-bg:#0f1620;      /* nền tooltip */
  --c-ok:var(--ok); --c-warn:var(--danger); --c-try:var(--warn); /* alias cũ */
  /* ── THANG BO GÓC (6 bậc) ── */
  --r-xs:4px; --r-sm:10px; --r-md:15px; --r-lg:20px; --r-xl:26px; --r-2xl:32px;
  /* ── THANG CỠ CHỮ (20 bậc, nền 2560×1440) ── */
  --fs-14:14px; --fs-16:16px; --fs-18:18px; --fs-20:20px; --fs-22:22px;
  --fs-24:24px; --fs-26:26px; --fs-28:28px; --fs-30:30px; --fs-32:32px;
  --fs-36:36px; --fs-40:40px; --fs-44:44px; --fs-48:48px; --fs-52:52px;
  --fs-56:56px; --fs-72:72px; --fs-80:80px; --fs-100:100px; --fs-150:150px;"""

def main():
    with io.open(SRC, encoding='utf-8') as f:
        html = f.read()

    # 1) chèn token vào :root
    assert html.count(OLD_ROOT) == 1, "khong tim thay dong :root goc"
    html = html.replace(OLD_ROOT, NEW_ROOT)

    # 2) thay màu ngữ nghĩa (kiểm số lần thay đúng kỳ vọng)
    for old, new, n in COLOR_SUBS:
        c = html.count(old)
        if c != n:
            print(f"!! LECH: '{old[:50]}...' mong {n}, thay {c} — BO QUA")
            continue
        html = html.replace(old, new)

    # 3) fs + radius: chỉ trong các khối <style>
    def xform_style(m):
        css = m.group(1)
        def fs(mm):
            v = int(mm.group(1))
            return f"font-size:var(--fs-{FS_MAP[v]})" if v in FS_MAP else mm.group(0)
        def rd(mm):
            v = int(mm.group(1))
            return f"border-radius:var(--r-{R_MAP[v]})" if v in R_MAP else mm.group(0)
        css = re.sub(r'font-size:\s*(\d+)px', fs, css)
        css = re.sub(r'border-radius:\s*(\d+)px(?=[;}!\s])', rd, css)
        return "<style>" + css + "</style>"

    html = re.sub(r'<style>(.*?)</style>', xform_style, html, flags=re.S)

    with io.open(SRC, 'w', encoding='utf-8', newline='\n') as f:
        f.write(html)
    print("OK — da ghi file.")

    # 4) kiểm lại
    style = "".join(re.findall(r'<style>(.*?)</style>', html, re.S))
    left_fs = sorted(set(re.findall(r'font-size:\s*([\d.]+)px', style)))
    left_rd = sorted(set(re.findall(r'border-radius:\s*([\d.]+)px', style)))
    hexes = re.findall(r'#[0-9a-fA-F]{3,8}\b', style)
    print("fs px con lai:", left_fs)
    print("radius px con lai:", left_rd)
    print("tong hex con lai:", len(hexes))

if __name__ == '__main__':
    sys.exit(main())
