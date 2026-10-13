# -*- coding: utf-8 -*-
"""Dung manual OTL bang MOT lenh: noi engine + chay Illustrator + GAN BOOKMARK + render PNG
+ ra loi trinh bay.

    python make.py content.jsx
    python make.py content.jsx content-vi.jsx     # nhieu ban — CHUNG mot phien PowerShell
    python make.py content.jsx --nhanh            # ban nhap: bo luu .ai, chi xuat .pdf
    python make.py content.jsx --khong-anh        # bo qua buoc render PNG
    python make.py content.jsx --dpi 110          # render net hon de soi ky

Yeu cau: Illustrator dang cai, PyMuPDF (pip install pymupdf).
File content phai tu goi doc.saveAs(...) o cuoi nhu cac ban mau.

── TOC DO: do that ngay 30/09/2026, tai lieu 15 trang ────────────────────────
    Illustrator khoi dong NGUOI      ~32 s   <- chi ton mot lan, dung de no chay
    dong tai lieu con sot lai          ~2 s   (~9 s neu de don nhieu ban)
    ve 15 trang                       ~4 s
    luu .ai                           ~1,2 s  <- --nhanh bo duoc
    luu .pdf                          ~1,0 s
    gan bookmark (bookmark.py)        ~0,3 s  <- BAT BUOC, Illustrator khong tu sinh
    render PNG + ra soat              ~0,5 s
Ba viec script nay lam de nhanh hon:
  1. dong tai lieu NGAY trong lan chay do, khong de don sang lan sau
  2. --nhanh bo buoc luu .ai khi chi can xem bo cuc
  3. nhieu file thi dung CHUNG mot phien PowerShell, khong bat COM lai tung lan
Va dung tat Illustrator giua chung — bat lai mat 32 s.
"""
import io, os, re, subprocess, sys, glob, time

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, "engine.jsx")

IT_CHU = 420          # duoi nguong nay, khong anh -> nghi trang thua
CAO_TOI_THIEU = 430   # khoi chu cuoi ket thuc cao hon -> nua duoi trang trong

# Dong het tai lieu ngay trong lan chay nay, roi tra lai dung chuoi ket qua cu.
# Khong lam viec nay thi lan dung sau phai dong ho, mat ~2 s va de don thanh ~9 s.
DUOI = ("\n;(function(){ try { while (app.documents.length > 0) "
        "app.documents[0].close(SaveOptions.DONOTSAVECHANGES); } catch (e) {} })();\n"
        "msg;\n")

# Hai dang khai bao luu .ai trong cac ban content hien co
BO_AI = [
    re.compile(r'^\s*var ai = new File\(base \+ "[^"]+\.ai"\);\s*$\n'
               r'^\s*doc\.saveAs\(ai, new IllustratorSaveOptions\(\)\);\s*$\n',
               re.MULTILINE),
    re.compile(r'^\s*doc\.saveAs\(new File\(base \+ "[^"]+\.ai"\), '
               r'new IllustratorSaveOptions\(\)\);\s*$\n', re.MULTILINE),
]


def loi(msg):
    print("LOI: " + msg)
    sys.exit(1)


def soat_dau_cach(noi_dung):
    """Thieu dau cach truoc \\u2013 -> dinh chu, tung lot ra tan bia."""
    return [x.strip() for x in
            re.findall(r'.{0,24}(?<=[^\s"])\\u2013.{0,20}', noi_dung)]


def noi_file(content, nhanh):
    if not os.path.exists(content):
        loi("khong thay %s" % content)
    thu_muc = os.path.dirname(os.path.abspath(content))
    ten = os.path.basename(content)
    ra = os.path.join(thu_muc, ten if ten.startswith("manual") else "manual-" + ten)
    e = io.open(ENGINE, encoding="utf-8").read()
    c = io.open(content, encoding="utf-8").read()

    dinh = soat_dau_cach(c)
    if dinh:
        print("  ! thieu dau cach truoc \\u2013 tai %d cho:" % len(dinh))
        for x in dinh[:5]:
            print("      ..." + x)
        print("    -> sua trong %s roi chay lai" % ten)

    bo_duoc = False
    if nhanh:
        for pat in BO_AI:
            c, n = pat.subn("", c)
            bo_duoc = bo_duoc or n > 0
        if not bo_duoc:
            print("  ! --nhanh: khong nhan ra cho luu .ai, van luu nhu thuong")

    io.open(ra, "w", encoding="utf-8", newline="").write(e + c + DUOI)
    return ra


def tim_pdf(jsx):
    s = io.open(jsx, encoding="utf-8").read()
    base = re.findall(r'var base = "([^"]+)"', s)
    ten = re.findall(r'new File\(base \+ "([^"]+\.pdf)"\)', s)
    return (base[-1] + ten[-1]) if (base and ten) else None


def chay_illustrator(danh_sach_jsx):
    """Dung TAT CA file trong MOT phien PowerShell. Tra ve list ket qua theo thu tu."""
    dong = ["$ErrorActionPreference = 'Stop'",
            "$ai = New-Object -ComObject Illustrator.Application",
            "while ($ai.Documents.Count -gt 0) { $ai.ActiveDocument.Close(2) }"]
    for f in danh_sach_jsx:
        dong.append('"<<<KQ>>>" + $ai.DoJavaScriptFile("%s")' % f.replace("/", "\\"))
    ps = "\n".join(dong)
    try:
        r = subprocess.run(["powershell", "-NonInteractive", "-Command", ps],
                           capture_output=True, text=True, timeout=1800)
    except subprocess.TimeoutExpired:
        loi("Illustrator khong tra loi sau 30 phut — mo Illustrator xem co hop "
            "thoai nao dang chan khong")
    out = (r.stdout or "")
    kq = [x.strip() for x in out.split("<<<KQ>>>")[1:]]
    if len(kq) != len(danh_sach_jsx):
        loi("Illustrator khong dung du:\n%s\n%s"
            % (out.strip()[:800], (r.stderr or "").strip()[:800]))
    return kq


def gan_bookmark(pdf):
    """BAT BUOC: tai lieu giao khach phai co bookmark. Illustrator khong tu sinh."""
    try:
        import bookmark
    except ImportError:
        sys.path.insert(0, HERE)
        try:
            import bookmark
        except ImportError:
            print("  ! KHONG gan duoc bookmark: thieu bookmark.py canh engine")
            return
    try:
        n = bookmark.dat_bookmark(pdf)
    except Exception as e:                      # loi la bao, khong nuot
        print("  ! KHONG gan duoc bookmark: %s" % e)
        return
    if n == 0:
        print("  ! KHONG tim thay tieu de nao de lam bookmark — xem lai tai lieu co "
              "dung H1()/H2() khong")
    else:
        print("  bookmark=%d (soat lai tren file: %d)" % (n, bookmark.kiem(pdf)))


def ra_soat(pdf, ve_anh, dpi):
    try:
        import fitz
    except ImportError:
        print("  (bo qua ra soat: chua co pymupdf)")
        return
    d = fitz.open(pdf)
    thu_muc = os.path.dirname(pdf)
    canh_bao = []
    for i in range(d.page_count):
        p = d[i]
        t = p.get_text().strip()
        anh = len(p.get_images())
        khoi = [b for b in p.get_text("blocks") if b[4].strip()]
        day = max((b[3] for b in khoi), default=0)
        if i > 0 and anh == 0 and len(t) < IT_CHU:
            canh_bao.append("tr%02d chi %d ky tu, khong anh" % (i + 1, len(t)))
        elif i > 0 and anh == 0 and day < CAO_TOI_THIEU:
            canh_bao.append("tr%02d trong nua duoi" % (i + 1))
        if ve_anh:
            p.get_pixmap(dpi=dpi).save(os.path.join(thu_muc, "p_%02d.png" % (i + 1)))
    if canh_bao:
        print("  ! xem lai: " + "; ".join(canh_bao))
        print("    (trang muc luc thua chu la binh thuong)")
    else:
        print("  khong co trang thua chu")
    if ve_anh:
        print("  da render %d anh vao %s" % (d.page_count, thu_muc))


def main():
    args = list(sys.argv[1:])
    nhanh = "--nhanh" in args
    ve_anh = "--khong-anh" not in args
    args = [a for a in args if a not in ("--nhanh", "--khong-anh")]
    dpi = 80
    if "--dpi" in args:
        k = args.index("--dpi")
        dpi = int(args[k + 1])
        del args[k:k + 2]
    if not args:
        loi("thieu ten file content. Vi du: python make.py content.jsx")

    files = []
    for a in args:
        files.extend(sorted(glob.glob(a)) or [a])

    t0 = time.time()
    jsxs = []
    for c in files:
        print("== %s" % os.path.basename(c))
        jsxs.append(noi_file(c, nhanh))

    ket = chay_illustrator(jsxs)

    for c, jsx, kq in zip(files, jsxs, ket):
        print("-- %s" % os.path.basename(c))
        print("  " + kq)
        pdf = tim_pdf(jsx)
        if pdf and os.path.exists(pdf):
            gan_bookmark(pdf)          # truoc khi ra soat: PDF cuoi cung phai co bookmark
            ra_soat(pdf, ve_anh, dpi)
        else:
            print("  (khong doc duoc duong dan PDF tu content, bo qua ra soat)")

    print("== xong %d tai lieu trong %.1f s%s"
          % (len(files), time.time() - t0, " (che do --nhanh)" if nhanh else ""))
    if ve_anh:
        print("   NHAC: may chi bat duoc trang THUA CHU. Chong chu, tran khung, "
              "logo cham tieu de thi phai soi anh bang mat.")


if __name__ == "__main__":
    main()
