"""Kiểm màn Tổng quan, màn Lịch sử và hộp Giới thiệu sau khi áp bản thiết kế
"Rang - Sửa lại" (docs/ui/design-web).

Chốt lại những gì bản thiết kế yêu cầu, để lần sau ai sửa giao diện mà làm mất
thì bộ kiểm này báo ngay:

  * Tổng quan  — lời chào có ngày, khối "Chuẩn bị mẻ rang" ba bước CHỈ MỘT bước
                 sáng, ba lối đi nhanh ở cột phải, bảng ba mẻ gần nhất.
  * Lịch sử    — bảng nằm trong thẻ bo góc, hàng tiêu đề dính đỉnh, phân trang
                 nằm TRONG thẻ và ở đáy.
  * Giới thiệu — có logo, tên chủ sở hữu, đủ mục liên hệ / tác giả / công nghệ /
                 AI, và số điện thoại + email đúng bản chủ máy đã xác nhận.

Không nối máy thật, không gửi lệnh — chạy trên trình duyệt cô lập.
"""
from pathlib import Path
import sys

from playwright.sync_api import sync_playwright

from test_ui_audit import PROBE, dang_nhap

APP = Path(__file__).resolve().parent.parent / "OTL Roast Lab.html"
CO_MAT = [(1920, 1080), (1366, 768), (1280, 800)]

# Liên hệ chủ máy đã xác nhận 30/08/2026 — sai một chữ là tài liệu giao khách sai.
DIEN_THOAI = "0936 198 938"
EMAIL = "otlpro.com@gmail.com"
MA_SO_THUE = "0314844413"

ME_GIA = """()=>{UX.latestRows=[
  {id:1,code:'#127',prof_name:'Colombia Huila',drop_sec:664,drop_temp:206,dev_pct:16,
   started_at:'2026-09-07 09:10:00',live:1,status:'DONE'},
  {id:2,code:'#126',prof_name:'Brazil Cerrado',drop_sec:686,drop_temp:209,dev_pct:14,
   started_at:'2026-09-06 15:02:00',live:1,status:'DONE'},
  {id:3,code:'#125',prof_name:'Ethiopia Yirgacheffe',drop_sec:598,drop_temp:197,dev_pct:18,
   started_at:'2026-09-06 10:44:00',live:0,status:'DONE'}];
  UX.latest=UX.latestRows[0];uxLatestRender();}"""


def kiem_tong_quan(pg, loi):
    pg.evaluate("gotoTab('tongquan')")
    pg.wait_for_timeout(300)

    if pg.evaluate("!!document.querySelector('.ovcards')"):
        loi.append("Tổng quan: bốn thẻ điều hướng cũ vẫn còn, bản thiết kế đã bỏ")
    if not pg.evaluate("!!document.getElementById('ovPrep')"):
        loi.append("Tổng quan: thiếu khối 'Chuẩn bị mẻ rang'")

    if not (pg.evaluate("document.getElementById('ovDate').textContent") or "").strip():
        loi.append("Tổng quan: lời chào thiếu ngày")

    buoc = pg.evaluate(
        """()=>[...document.querySelectorAll('.ovstep')].map(s=>({
             k:s.dataset.k, t:s.querySelector('.ovstep-t').textContent.trim(),
             s:s.querySelector('.ovstep-s').textContent.trim(),
             on:s.classList.contains('on'), done:s.classList.contains('done')}))"""
    )
    if [b["k"] for b in buoc] != ["heat", "prof", "load"]:
        loi.append("Tổng quan: ba bước chuẩn bị sai thứ tự hoặc thiếu")
    for b in buoc:
        if not b["t"] or not b["s"]:
            loi.append("Tổng quan: bước %s thiếu tên hoặc trạng thái" % b["k"])
    sang = [b for b in buoc if b["on"]]
    if len(sang) > 1:
        loi.append("Tổng quan: %d bước cùng sáng, chỉ được một" % len(sang))
    for b in buoc:
        if b["on"] and b["done"]:
            loi.append("Tổng quan: bước %s vừa sáng vừa xong" % b["k"])

    nav = pg.evaluate(
        """()=>[...document.querySelectorAll('.ovnav-row')].map(b=>
             [b.querySelector('.ovnav-t').textContent.trim(),
              b.querySelector('.ovnav-s').textContent.trim()])"""
    )
    if len(nav) != 3 or any(not a or not c for a, c in nav):
        loi.append("Tổng quan: ba lối đi nhanh thiếu chữ")

    # Bảng ba mẻ gần nhất — nạp dữ liệu giả rồi soi
    pg.evaluate(ME_GIA)
    pg.wait_for_timeout(200)
    bang = pg.evaluate(
        """()=>{const t=document.querySelector('#uxLatest .uxl-tbl');
          if(!t)return null;
          return {cot:t.querySelectorAll('thead th').length,
                  dong:t.querySelectorAll('tbody tr').length,
                  ngay:t.querySelector('tbody tr td.d')?.textContent.trim()||'',
                  link:!!document.querySelector('#uxLatest .uxl-more')};}"""
    )
    if not bang:
        loi.append("Tổng quan: 'Mẻ gần nhất' không dựng thành bảng")
    else:
        if bang["dong"] != 3:
            loi.append("Tổng quan: bảng mẻ gần nhất có %d dòng, phải là 3" % bang["dong"])
        if bang["cot"] != 6:
            loi.append("Tổng quan: bảng mẻ gần nhất có %d cột, phải là 6" % bang["cot"])
        if not bang["link"]:
            loi.append("Tổng quan: thiếu lối 'Xem lịch sử →'")
        # ngày phải là dd/mm/yyyy chứ không để nguyên ISO của kho
        if not bang["ngay"].startswith("07/09/2026"):
            loi.append("Tổng quan: ngày trong bảng chưa đổi sang dd/mm/yyyy (%r)" % bang["ngay"])


def kiem_lich_su(pg, loi):
    pg.evaluate("gotoTab('lichsu')")
    pg.wait_for_timeout(500)
    r = pg.evaluate(
        """()=>{const c=document.getElementById('histCard');
          if(!c)return null;
          const p=c.querySelector('.ux-paging'), th=c.querySelector('thead');
          return {phanTrangTrongThe:!!p, phanTrangODay:c.lastElementChild===p,
                  dinhDinh:th?getComputedStyle(th).position:'',
                  boGoc:parseFloat(getComputedStyle(c).borderRadius)||0,
                  locNgoaiThe:!!document.querySelector('#pane-lichsu .pghead + .ux-filters')};}"""
    )
    if not r:
        loi.append("Lịch sử: thiếu thẻ bọc bảng (#histCard)")
        return
    if not r["phanTrangTrongThe"]:
        loi.append("Lịch sử: phân trang không nằm trong thẻ bảng")
    elif not r["phanTrangODay"]:
        loi.append("Lịch sử: phân trang không ở đáy thẻ")
    if r["dinhDinh"] != "sticky":
        loi.append("Lịch sử: hàng tiêu đề không dính đỉnh khi cuộn")
    if r["boGoc"] <= 0:
        loi.append("Lịch sử: thẻ bảng không bo góc")
    if not r["locNgoaiThe"]:
        loi.append("Lịch sử: hàng bộ lọc không còn ngay dưới tiêu đề trang")

    nhan = pg.evaluate(
        "document.getElementById('uxFromLabel').textContent"
        "+'|'+document.getElementById('uxToLabel').textContent"
    )
    # HỢP ĐỒNG NHÃN (chốt 14/09/2026, review Codex RF-11): ghi thứ tự ngày bằng CHỮ —
    # "ngày/tháng/năm" / "day/month/year". Ô date hiện dd/mm/yyyy hay dd-----yyyy tuỳ
    # cấu hình Windows từng máy khách, nên ghi mẫu ký hiệu là có máy sai; chữ thì đúng
    # ở mọi máy. Kiểm CẢ HAI nhãn chứ không chỉ chuỗi ghép.
    for mot in nhan.split("|"):
        if "ngày/tháng/năm" not in mot and "day/month/year" not in mot:
            loi.append("Lịch sử: nhãn ô ngày không ghi thứ tự ngày/tháng/năm (%r)" % mot)


def kiem_gioi_thieu(pg, loi):
    pg.evaluate("aboutOpen()")
    pg.wait_for_timeout(300)
    r = pg.evaluate(
        """()=>({mo:document.getElementById('aboutbox').classList.contains('on'),
                 logo:!!document.querySelector('.ab-mark use'),
                 chuSoHuu:document.getElementById('abOwn').textContent,
                 muc:[...document.querySelectorAll('.ab-sec h3')].map(h=>h.textContent),
                 than:document.getElementById('abBody').textContent,
                 banQuyen:document.getElementById('abCopy').textContent})"""
    )
    if not r["mo"]:
        loi.append("Giới thiệu: hộp không mở")
    if not r["logo"]:
        loi.append("Giới thiệu: thiếu logo O Tesla")
    if "O TESLA" not in r["chuSoHuu"].upper():
        loi.append("Giới thiệu: không ghi chủ sở hữu phần mềm")
    if len(r["muc"]) != 4:
        loi.append("Giới thiệu: có %d mục, phải đủ 4" % len(r["muc"]))
    for phai_co, ten in [
        (DIEN_THOAI, "điện thoại"), (EMAIL, "email"), (MA_SO_THUE, "mã số thuế"),
        ("Claude", "AI Claude"), ("Anthropic", "hãng Anthropic"),
        ("Codex", "AI Codex"), ("OpenAI", "hãng OpenAI"),
        ("pywebview", "vỏ desktop"), ("SQLite", "kho dữ liệu"),
        ("Modbus", "cách nối máy"), ("STM32F103RC", "firmware máy rang"),
    ]:
        if phai_co not in r["than"]:
            loi.append("Giới thiệu: thiếu %s (%r)" % (ten, phai_co))
    if "938 198 938" in r["than"]:
        loi.append("Giới thiệu: số điện thoại sai — phải là 0936 chứ không phải 0938")
    if "otesla.vn@gmail.com" in r["than"]:
        loi.append("Giới thiệu: còn email CŨ otesla.vn@gmail.com")
    if "O TESLA" not in r["banQuyen"].upper():
        loi.append("Giới thiệu: dòng bản quyền không nêu công ty")

    pg.evaluate("aboutClose()")
    pg.wait_for_timeout(150)
    if pg.evaluate("document.getElementById('aboutbox').classList.contains('on')"):
        loi.append("Giới thiệu: bấm Đóng mà hộp không đóng")


def kiem_ho_so(pg, loi):
    """Màn Hồ sơ: lưới BA cột và thẻ gọn có hàng thao tác ở đáy."""
    pg.set_viewport_size({"width": 1920, "height": 1080})
    pg.evaluate("gotoTab('hoso')")
    pg.wait_for_timeout(600)

    cot = pg.evaluate(
        "getComputedStyle(document.getElementById('profgrid'))"
        ".gridTemplateColumns.split(' ').length")
    if cot != 3:
        loi.append("Hồ sơ: lưới %d cột ở 1920, bản thiết kế là 3" % cot)

    r = pg.evaluate(
        """()=>{const c=document.querySelector('.profcard');
          if(!c)return null;
          const a=c.querySelector('.pacts');
          return {acts:!!a,
                  nut:a?[...a.children].map(b=>b.className.split(' ')[0]):[],
                  saoTrenDau:!!c.querySelector('.ph .favstar'),
                  badge:!!c.querySelector('.ph .roastbadge'),
                  soCot:c.querySelectorAll('.pmeta>div').length};}"""
    )
    if not r:
        loi.append("Hồ sơ: không có thẻ nào")
        return
    if not r["acts"]:
        loi.append("Hồ sơ: thẻ thiếu hàng thao tác ở đáy (.pacts)")
    elif r["nut"][:1] != ["loadbtn"]:
        loi.append("Hồ sơ: hàng thao tác không bắt đầu bằng nút Nạp & rang (%s)" % r["nut"])
    if r["saoTrenDau"]:
        loi.append("Hồ sơ: sao yêu thích vẫn ở đầu thẻ, thiết kế xếp xuống hàng thao tác")
    if not r["badge"]:
        loi.append("Hồ sơ: đầu thẻ thiếu huy hiệu mức rang")
    if r["soCot"] != 3:
        loi.append("Hồ sơ: khối số có %d ô, phải đủ nạp/xả/thời gian" % r["soCot"])

    tieu_de = pg.evaluate("document.querySelector('#pane-hoso .pgtitle').textContent")
    if "Hồ sơ rang" not in tieu_de:
        loi.append("Hồ sơ: tiêu đề %r, thiết kế ghi 'Hồ sơ rang'" % tieu_de)
    pg.evaluate("gotoHs('nap')")
    pg.wait_for_timeout(200)
    if pg.evaluate("document.querySelector('#pane-hoso .pgtitle').textContent") == tieu_de:
        loi.append("Hồ sơ: sang tab Công thức nạp mà tiêu đề không đổi")
    pg.evaluate("gotoHs('rang')")
    pg.wait_for_timeout(200)


def kiem_khoi_luong(pg, loi):
    """Cột Khối lượng ở Lịch sử và ô nhập kg ở panel sau mẻ."""
    pg.evaluate("gotoTab('lichsu')")
    pg.wait_for_timeout(400)
    cot = pg.evaluate(
        "[...document.querySelectorAll('.histtable thead th')].map(t=>t.textContent)")
    if "Khối lượng" not in cot:
        loi.append("Lịch sử: bảng thiếu cột Khối lượng (%s)" % cot)

    o = pg.evaluate(
        """()=>{const i=document.getElementById('uxDoneKg');
          if(!i)return null;
          return {min:i.min,max:i.max,nhan:document.getElementById('uxDoneKgLabel')?.textContent||'',
                  nut:!!document.getElementById('uxDoneKgSave')};}"""
    )
    if not o:
        loi.append("Sau mẻ: thiếu ô nhập khối lượng")
    else:
        if not o["nut"]:
            loi.append("Sau mẻ: ô khối lượng thiếu nút Lưu")
        if float(o["max"] or 0) != 1000:
            loi.append("Sau mẻ: ô khối lượng không chặn trần 1000 kg")
        if not o["nhan"].strip():
            loi.append("Sau mẻ: ô khối lượng chưa có nhãn")
    # số đếm phải là hàm có thật, và không bịa số khi kho chưa đọc được
    if not pg.evaluate("typeof uxBatchCount==='function'"):
        loi.append("Thiếu hàm đếm mẻ uxBatchCount()")
    nav = pg.evaluate(
        "[...document.querySelectorAll('.ovnav-row .ovnav-s')].map(e=>e.textContent)")
    if any(t.strip().startswith("127") for t in nav):
        loi.append("Lối đi nhanh ghi số 127 của bản thiết kế thay vì số thật")


def kiem_mau_bt_et(pg, loi):
    """BT/ET phải CÙNG MỘT MÀU ở mọi khung, mọi màu chủ đạo, cả hai nền.

    Trước đây :root để BT xanh / ET đỏ còn khung Rang lại BT cam / ET xanh, và
    thanh trên cùng thì tô cứng bằng mực chung --blue-ink/--red-ink — nên cùng
    một đường dữ liệu mà ba chỗ ba màu, có chỗ BT và ET đảo hẳn ý nghĩa.
    """
    pg.evaluate("gotoTab('rang')")
    pg.wait_for_timeout(300)
    for accent in ("ember", "otl", "custom"):
        for theme in ("dark", "light"):
            pg.evaluate("(a)=>setAccent(a)", accent)
            pg.evaluate("(t)=>setTheme(t)", theme)
            # Ô đang hiện dấu "—" (chưa có dữ liệu) CỐ Ý tô xám, không tô màu
            # BT/ET — dấu gạch không phải một nhiệt độ. Nên phải đưa số thật vào
            # rồi mới so màu, nếu không là đi đo trạng thái rỗng và báo lỗi oan.
            pg.evaluate("()=>{txt('liveBT','198.4');txt('liveET','214.0');}")
            pg.wait_for_timeout(150)
            r = pg.evaluate(
                """()=>{const g=(el,p)=>el?getComputedStyle(el).getPropertyValue(p).trim():'';
                  const rt=document.documentElement,pn=document.getElementById('pane-rang');
                  const hex=h=>{h=h.replace('#','');return 'rgb('+[0,2,4].map(i=>parseInt(h.substr(i,2),16)).join(', ')+')';};
                  return {btRoot:hex(g(rt,'--c-bt')),btPane:hex(g(pn,'--c-bt')),
                          btThe:g(document.getElementById('liveBT'),'color'),
                          etRoot:hex(g(rt,'--c-et')),etPane:hex(g(pn,'--c-et')),
                          etThe:g(document.getElementById('liveET'),'color')};}"""
            )
            for ky in ("bt", "et"):
                bo = {r[ky + hau] for hau in ("Root", "Pane", "The")}
                if len(bo) != 1:
                    loi.append("%s/%s: màu %s không đồng nhất → %s"
                               % (accent, theme, ky.upper(), sorted(bo)))
            if r["btRoot"] == r["etRoot"]:
                loi.append("%s/%s: BT và ET cùng màu, không phân biệt được"
                           % (accent, theme))
    pg.evaluate("setAccent('ember')")
    pg.evaluate("setTheme('dark')")
    pg.wait_for_timeout(150)


def kiem_thiet_bi_phu(pg, loi):
    """Khối Thiết bị phụ ở màn thấp: phải có dấu hiệu còn nội dung để cuộn."""
    pg.set_viewport_size({"width": 1366, "height": 768})
    pg.evaluate("gotoTab('rang')")
    pg.wait_for_timeout(600)
    r = pg.evaluate(
        """()=>{const a=document.querySelector('.od-aux'),s=document.getElementById('devstrip');
          if(!a||!s)return null;
          s.scrollTop=0;uxAuxScrollHint();
          const dau=[...a.classList].filter(c=>c.startsWith('aux-'));
          s.scrollTop=s.scrollHeight;uxAuxScrollHint();
          const cuoi=[...a.classList].filter(c=>c.startsWith('aux-'));
          s.scrollTop=0;uxAuxScrollHint();
          return {dau,cuoi,conCuon:s.scrollHeight-s.clientHeight>2,
                  dem:document.getElementById('auxOnCount').textContent,
                  soNut:a.querySelectorAll('.devbtn').length};}"""
    )
    if not r:
        loi.append("Thiết bị phụ: không tìm thấy khối")
        return
    if r["conCuon"]:
        if "aux-down" not in r["dau"]:
            loi.append("Thiết bị phụ: ở đầu danh sách không báo còn nội dung bên dưới")
        if "aux-up" not in r["cuoi"]:
            loi.append("Thiết bị phụ: ở cuối danh sách không báo còn nội dung bên trên")
        if "aux-down" in r["cuoi"]:
            loi.append("Thiết bị phụ: cuộn hết rồi mà vẫn báo còn nội dung bên dưới")
    if r["soNut"] > 1 and "/" not in r["dem"]:
        loi.append("Thiết bị phụ: nhãn đếm %r không ghi tổng số thiết bị" % r["dem"])
    pg.set_viewport_size({"width": 1920, "height": 1080})
    pg.wait_for_timeout(200)


def kiem_goi_thieu_truong(pg, loi):
    """Một gói dữ liệu máy thiếu trường KHÔNG được làm chết cả vòng cập nhật."""
    pg.evaluate("gotoTab('rang')")
    pg.wait_for_timeout(300)
    r = pg.evaluate(
        """()=>{const doc=i=>document.getElementById(i).textContent;
          applyMachine({bt:198.4,et:214,gas:40,air:80,drum:55});
          const du=[doc('ovBurner'),doc('ovAir'),doc('ovDrum')];
          applyMachine({gas:45,air:70,drum:50});           // thiếu bt/et
          const thieu=[doc('ovBurner'),doc('ovAir'),doc('ovDrum')];
          applyMachine({});                                 // rỗng hẳn
          const rong=[doc('ovBurner')];
          return {du,thieu,rong,muc:[R.burner,R.air,R.drum]};}"""
    )
    # BT/ET không còn đi qua applyMachine (đợt PD: thanh đầu bỏ BT/ET, nhiệt chỉ
    # hiện ở cột phải màn Rang qua đường vẽ đồ thị). Điều PHẢI giữ ở đây là: một gói
    # THIẾU TRƯỜNG không được làm chết cả vòng — gas/gió/trống vẫn phải cập nhật.
    if r["du"] != ["40", "80", "55"]:
        loi.append("applyMachine: gói đủ trường mà mức máy sai (%s)" % r["du"])
    if r["thieu"] != ["45", "70", "50"]:
        loi.append("applyMachine: thiếu bt/et làm chết luôn gas/gió/trống (%s)" % r["thieu"])
    if r["rong"] != ["—"]:
        loi.append("applyMachine: gói rỗng không ghi '—' (%s)" % r["rong"])
    if r["muc"] != [45, 70, 50]:
        loi.append("applyMachine: gói rỗng ghi đè mức đang giữ thành %s" % r["muc"])


def main():
    loi, js = [], []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        pg.on("pageerror", lambda e: js.append(str(e)))
        pg.goto(APP.as_uri())
        dang_nhap(pg)

        kiem_tong_quan(pg, loi)
        kiem_lich_su(pg, loi)
        kiem_gioi_thieu(pg, loi)
        kiem_ho_so(pg, loi)
        kiem_khoi_luong(pg, loi)
        kiem_mau_bt_et(pg, loi)
        kiem_thiet_bi_phu(pg, loi)
        kiem_goi_thieu_truong(pg, loi)

        # Tràn / chồng ở ba kích thước, cả nền sáng lẫn tối, cả hai ngôn ngữ
        do = PROBE.replace("__TAP__", "44")
        for w, h in CO_MAT:
            pg.set_viewport_size({"width": w, "height": h})
            for theme in ("light", "dark"):
                pg.evaluate("(t)=>setTheme(t)", theme)
                for lang in ("vi", "en"):
                    pg.evaluate("(l)=>{LANG=l;applyLang();}", lang)
                    for tab in ("tongquan", "lichsu", "hoso"):
                        pg.evaluate("(t)=>gotoTab(t)", tab)
                        pg.wait_for_timeout(120)
                        kq = pg.evaluate(do)
                        for loai in ("overflow", "overlap"):
                            if kq[loai]:
                                loi.append("%dx%d %s %s %s: %s"
                                           % (w, h, theme, lang, tab, kq[loai][:2]))
                    pg.evaluate("aboutOpen()")
                    pg.wait_for_timeout(120)
                    kq = pg.evaluate(do)
                    for loai in ("overflow", "overlap"):
                        if kq[loai]:
                            loi.append("%dx%d %s %s giới thiệu: %s"
                                       % (w, h, theme, lang, kq[loai][:2]))
                    pg.evaluate("aboutClose()")
        pg.evaluate("(l)=>{LANG=l;applyLang();}", "vi")
        b.close()

    if js:
        loi.append("Lỗi JS: %s" % js)
    if loi:
        print("HỎNG %d mục:" % len(loi))
        for m in loi:
            print("  -", m)
        sys.exit(1)
    print("ĐẠT — Tổng quan, Lịch sử và Giới thiệu đúng bản thiết kế.")


if __name__ == "__main__":
    main()
