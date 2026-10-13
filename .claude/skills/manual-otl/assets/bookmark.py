# -*- coding: utf-8 -*-
"""Gan BOOKMARK (outline) vao file PDF do Illustrator xuat ra.

Illustrator luu PDF tu artboard, KHONG bao gio tu sinh bookmark. Khong co bookmark
thi nguoi doc phai keo 17 trang de tim muc 3.3 — tai lieu giao khach ma nhu vay la loi
trinh bay, khong phai chuyen lam them.

Cach nhan tieu de: doc lai chinh file PDF va TU DO co chu, khong ghi cung 19/12,5 pt.
Ly do: cac ban manual dung tu nhung ban engine khac nhau khong cung co chu — ban
airlock dung H1 19 pt / H2 12,5 pt, ban Auto dung 18 / 13. Ghi cung mot cap so la
lang mat tieu de cua nua so tai lieu trong kho.

Luat tu do (chi xet chu DAM, bo trang bia):
    H1 = co chu DAM LON NHAT con xuat hien tu 3 lan tro len
         (ten cong ty o trang thong tin chi hien 1 lan nen khong bi nham)
    H2 = co chu dam lon nhat con lai, nho hon H1 va tu 12 pt tro len, cung >= 3 lan
         (so buoc STEP la 11 pt, dau bang 10,5 pt — deu nam duoi nguong)
Chu dam to hon H1 ma chi hien mot hai lan (vi du tieu de "Muc luc") van lay lam muc 1.

So thu tu muc con suy ra tu so chuong trong H1 ("3  Quy trinh sua" -> 3.1, 3.2 ...),
dung bang so trong huy hieu tron ma engine ve canh tieu de H2.

    python bookmark.py tai-lieu.pdf [tai-lieu-2.pdf ...]
"""
import os, re, sys

CO_H1_CHUAN = 19.0     # engine.jsx hien tai ve H1 19 pt
CO_H2_CHUAN = 12.5     #                       va H2 12,5 pt
CO_NHO_NHAT = 12.0     # duoi nguong nay la chu than bai, khong phai tieu de
IT_NHAT = 3            # mot co chu phai lap lai tu ngan nay lan moi coi la cap tieu de
DAI_NHAT = 120         # dai hon thi la doan van in dam, khong phai tieu de


def _dong_dam(trang):
    """[(co_chu, chu, y)] — cac dong chu DAM cua trang, da gom manh cung mot dong."""
    ra = []
    for khoi in trang.get_text("dict")["blocks"]:
        if khoi.get("type") != 0:
            continue
        for dong in khoi["lines"]:
            manh = [s for s in dong["spans"] if s["text"].strip()]
            if not manh or "Bold" not in manh[0]["font"]:
                continue
            co = round(manh[0]["size"], 1)
            if co < CO_NHO_NHAT:
                continue
            chu = re.sub(r"\s+", u" ", u"".join(s["text"] for s in manh)).strip()
            if 2 < len(chu) <= DAI_NHAT:
                ra.append((co, chu, dong["bbox"][1]))
    return ra


def _do_co_chu(dong_theo_trang):
    """Tra ve (co_H1, co_H2) tu do theo tai lieu, hoac (None, None) neu khong ro."""
    dem = {}
    for dong in dong_theo_trang:
        for co, _chu, _y in dong:
            dem[co] = dem.get(co, 0) + 1
    # Ban engine hien tai: H1 19 pt, H2 12,5 pt. Thay dung co chuan thi tin ngay,
    # khong doi du IT_NHAT lan — tai lieu mong chi co hai muc con van phai co bookmark.
    # Phai thay tu 2 lan tro len: ban Auto chi co MOT chu 19 pt la tieu de trang
    # muc luc, con tieu de chuong cua no la 18 pt — tin 19 pt la hong ca cay muc luc.
    if dem.get(CO_H1_CHUAN, 0) >= 2:
        return CO_H1_CHUAN, (CO_H2_CHUAN if CO_H2_CHUAN in dem else None)
    hay_dung = sorted([c for c, n in dem.items() if n >= IT_NHAT], reverse=True)
    if not hay_dung:
        return None, None
    h1 = hay_dung[0]
    h2 = next((c for c in hay_dung[1:] if c < h1 and c >= CO_NHO_NHAT), None)
    return h1, h2


def lay_muc_luc(doc):
    """Dung cay muc luc [[muc, ten, trang], ...] theo dinh dang PyMuPDF."""
    # trang 1 la bia: chu to nhung khong phai tieu de chuong
    dong_theo_trang = [_dong_dam(doc[i]) if i > 0 else [] for i in range(doc.page_count)]
    h1, h2 = _do_co_chu(dong_theo_trang)
    if h1 is None:
        return []

    toc, so_chuong, dem_con = [], None, 0
    for i, dong in enumerate(dong_theo_trang):
        truoc = None                           # (co, y) cua dong tieu de vua lay tren trang nay
        for co, chu, y in sorted(dong, key=lambda t: t[2]):
            # Tieu de dai bi xuong 2 dong (hay gap o ban tieng Anh): dong sau cung co chu,
            # nam ngay duoi dong truoc -> NOI vao muc vua lay, khong tao muc moi.
            # Khong noi thi "6.2 ... fan housing" + "6.3 and impeller" lam lech so ca chuong.
            if truoc and abs(co - truoc[0]) < 0.05 and 0 < y - truoc[1] < co * 1.9 and toc:
                toc[-1][1] = toc[-1][1] + u" " + chu
                truoc = (co, y)
                continue
            truoc = (co, y)
            if co >= h1:                       # >= de lay ca tieu de "Muc luc" to hon
                toc.append([1, chu, i + 1])
                m = re.match(r"^(\d+)\s", chu)
                so_chuong = m.group(1) if m else None
                dem_con = 0
            elif h2 is not None and abs(co - h2) < 0.05:
                dem_con += 1
                ten = chu if so_chuong is None else u"%s.%d  %s" % (so_chuong, dem_con, chu)
                toc.append([2 if toc else 1, ten, i + 1])
    return toc


def dat_bookmark(duong_dan):
    """Ghi bookmark vao PDF (luu de len chinh no). Tra ve so bookmark da dat."""
    import fitz
    doc = fitz.open(duong_dan)
    toc = lay_muc_luc(doc)
    if not toc:
        doc.close()
        return 0
    doc.set_toc(toc)
    tam = duong_dan + ".tam"
    doc.save(tam, garbage=3, deflate=True)
    doc.close()
    os.replace(tam, duong_dan)
    return len(toc)


def kiem(duong_dan):
    """Soat lai TREN CHINH FILE PDF: doc co bao nhieu bookmark."""
    import fitz
    doc = fitz.open(duong_dan)
    n = len(doc.get_toc())
    doc.close()
    return n


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("dung: python bookmark.py tai-lieu.pdf [...]")
    for f in sys.argv[1:]:
        n = dat_bookmark(f)
        print("%s  bookmark=%d (soat lai tren file: %d)" % (os.path.basename(f), n, kiem(f)))
