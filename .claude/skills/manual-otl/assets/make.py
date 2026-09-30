# -*- coding: utf-8 -*-
"""Dung manual OTL bang MOT lenh: noi engine + chay Illustrator + render PNG + ra loi trinh bay.

    python make.py content.jsx
    python make.py content.jsx content-vi.jsx        # nhieu ban lien tiep
    python make.py content.jsx --khong-anh           # bo qua buoc render PNG
    python make.py content.jsx --dpi 110             # render net hon de soi ky

Thay cho chuoi thao tac tay: cat engine+content > manual.jsx -> PowerShell COM ->
python render PNG -> tu dem chu tung trang. Tiet kiem ~4 lenh moi lan dung.

Yeu cau: Illustrator dang cai, PyMuPDF (pip install pymupdf).
File content phai tu goi doc.saveAs(...) o cuoi nhu cac ban mau.
"""
import io, os, re, subprocess, sys, glob

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, "engine.jsx")

# ── nguong canh bao trang thua chu ─────────────────────────────────────────
IT_CHU = 420        # duoi nguong nay, khong anh, khong phai muc luc -> nghi thua
CAO_TOI_THIEU = 430  # khoi chu cuoi cung ma ket thuc cao hon -> nua duoi trang trong


def loi(msg):
    print("LOI: " + msg)
    sys.exit(1)


def noi_file(content):
    """Noi engine + content thanh manual-<ten>.jsx canh file content."""
    if not os.path.exists(content):
        loi("khong thay %s" % content)
    thu_muc = os.path.dirname(os.path.abspath(content))
    ten = os.path.basename(content)
    ra = os.path.join(thu_muc, "manual-" + ten if not ten.startswith("manual") else ten)
    e = io.open(ENGINE, encoding="utf-8").read()
    c = io.open(content, encoding="utf-8").read()

    # bat som loi thieu dau cach truoc gach ngang (Edit hay cat khoang trang cuoi chuoi)
    xau = re.findall(r'.{0,24}(?<=[^\s"])\\u2013.{0,20}', c)
    if xau:
        print("  ! thieu dau cach truoc \\u2013 tai %d cho:" % len(xau))
        for x in xau[:5]:
            print("      ..." + x.strip())
        print("    -> sua trong %s roi chay lai" % ten)

    io.open(ra, "w", encoding="utf-8", newline="").write(e + c)
    return ra


def chay_illustrator(jsx):
    ps = (
        "$ai = New-Object -ComObject Illustrator.Application; "
        "while ($ai.Documents.Count -gt 0) { $ai.ActiveDocument.Close(2) }; "
        '$ai.DoJavaScriptFile("%s")' % jsx.replace("/", "\\")
    )
    r = subprocess.run(["powershell", "-NonInteractive", "-Command", ps],
                       capture_output=True, text=True)
    out = (r.stdout or "").strip()
    if "OK pages=" not in out:
        loi("Illustrator khong dung duoc:\n%s\n%s" % (out, (r.stderr or "").strip()))
    return out


def tim_pdf(jsx):
    """Doc duong dan PDF ma content tu khai trong doc.saveAs(...)."""
    s = io.open(jsx, encoding="utf-8").read()
    m = re.findall(r'var base = "([^"]+)"', s)
    n = re.findall(r'new File\(base \+ "([^"]+\.pdf)"\)', s)
    if m and n:
        return m[-1] + n[-1]
    return None


def ra_soat(pdf, dpi, ve_anh):
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
        print("  da render %d anh vao %s (soi bang mat roi xoa)" % (d.page_count, thu_muc))


def main():
    args = [a for a in sys.argv[1:]]
    ve_anh = "--khong-anh" not in args
    args = [a for a in args if a != "--khong-anh"]
    dpi = 80
    if "--dpi" in args:
        k = args.index("--dpi")
        dpi = int(args[k + 1])
        del args[k:k + 2]
    if not args:
        loi("thieu ten file content. Vi du: python make.py content.jsx")

    for content in args:
        for c in sorted(glob.glob(content)) or [content]:
            print("== %s" % os.path.basename(c))
            jsx = noi_file(c)
            print("  " + chay_illustrator(jsx))
            pdf = tim_pdf(jsx)
            if pdf and os.path.exists(pdf):
                ra_soat(pdf, dpi, ve_anh)
            else:
                print("  (khong doc duoc duong dan PDF tu content, bo qua ra soat)")


if __name__ == "__main__":
    main()
