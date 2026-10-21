"""Bộ kiểm đợt 14 (14/09/2026, chủ máy giao) — Cài đặt TỰ LƯU + XUẤT/NHẬP file cài đặt, trục khung
"Đường rang dự kiến" theo Cài đặt, bỏ blur gây lag con trỏ.

Đo hành vi thật trên trang, không đọc code:
  1) chân trang không còn Hủy/Áp dụng/Lưu — có Hoàn tác / Nhập file / Xuất file
  2) đổi ô → 0,6 giây sau lưu bền; bấm ± liền tay chỉ ghi MỘT dòng nhật ký
  3) rời trang giữa nhịp chờ vẫn lưu nốt
  4) trục nhiệt/RoR của khung dự kiến theo Cài đặt (Cố định khoá cứng, Tự động chỉ nới lên)
  5) đang rang: tự lưu KHÔNG đổi cổng/baud; không rang: đổi baud mới đẩy xuống cầu nối, đổi ô khác thì không
  6) Hoàn tác trả về đúng lúc mở trang Cài đặt
  7) Xuất: tên file, tiêu đề cột, đủ mọi khoá app + $M; xuất rồi đọc lại = không khác gì
  8) Nhập: dấu ; + số thập phân dấu phẩy, kẹp số ngoài dải, bỏ khoá lạ / lựa chọn sai, GIỮ cổng COM,
     tham số $M chỉ điền form — KHÔNG ghi xuống máy kể cả khi đang nối máy
  9) file rác → báo, không mở hộp xác nhận
 10) hộp đăng nhập + lớp phủ không còn backdrop-filter
"""
import sys, pathlib, re
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

HTML = pathlib.Path(__file__).resolve().parent.parent / "OTL Roast Lab.html"

STUB = r"""
window.__exp=[]; window.__mcw=[]; window.__imp=null; window.__links=[];
window.pywebview={api:{
  link_snapshot: () => new Promise(()=>{}),
  link_config: async () => ({port:'COM9',baud:38400,slave:1,enabled:true}),
  link_set_config: async c => { window.__links.push(c); return c; },
  settings_export: async (text,name) => { window.__exp.push([text,name]); return {ok:true,path:'D:\\xuat\\'+name}; },
  settings_import: async () => window.__imp,
  mc_write: async items => { window.__mcw.push(items); return {ok:true,count:items.length}; },
  mc_read: async () => ({ok:false,err:'giả lập'}),
  op_log: () => null,
}};
"""

fails = []


def chk(name, cond, got=""):
    print(("  OK   " if cond else "  FAIL ") + name + (f"  → {got}" if got != "" else ""))
    if not cond:
        fails.append(name)


with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={"width": 1600, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.add_init_script(STUB)
    pg.goto(HTML.as_uri())
    pg.wait_for_function("typeof settingsSave==='function' && typeof settingsImport==='function'")
    pg.evaluate("session={name:'M',role:'master',perms:{}};document.getElementById('login').classList.remove('on');"
                "try{updateBadge()}catch(e){}")

    print("1) Chân trang Cài đặt")
    r = pg.evaluate("""() => { gotoTab('caidat'); gotoSub('model');
      const f = document.getElementById('setfoot');
      return {t: [...f.querySelectorAll('button')].map(b => b.textContent.trim()),
              undo: document.getElementById('setUndo').disabled,
              hien: getComputedStyle(f).display !== 'none'}; }""")
    chk("không còn nút Hủy / Áp dụng / Lưu", not any(x in ("Hủy", "Áp dụng", "Lưu") for x in r["t"]), r["t"])
    chk("có Hoàn tác · Nhập file · Xuất file", r["t"] == ["Hoàn tác", "Nhập file", "Xuất file"], r["t"])
    chk("Hoàn tác mờ khi chưa đổi gì", r["undo"] is True)
    chk("chân trang hiện ở trang Model nhiệt", r["hien"] is True)

    print("2) Tự lưu sau 0,6 giây, gộp nấc bấm liền tay")
    r = pg.evaluate("""() => { window.__a0 = loadAudit().length; window.__v0 = +CFG.ch_tmax;
      fstep('ch_tmax',1); fstep('ch_tmax',1); fstep('ch_tmax',1);
      return {save: document.getElementById('setfoot').dataset.save,
              ls: (JSON.parse(localStorage.getItem(LS_CFG)||'{}')).ch_tmax, v0: window.__v0}; }""")
    muon = str(r["v0"] + 30)
    chk("chấm cam 'đang lưu' ngay khi bấm", r["save"] == "dang", r["save"])
    chk("trong nhịp chờ chưa ghi đĩa", r["ls"] != muon, r["ls"])
    pg.wait_for_timeout(900)
    r = pg.evaluate("""() => ({save: document.getElementById('setfoot').dataset.save,
      ls: JSON.parse(localStorage.getItem(LS_CFG)).ch_tmax, cfg: CFG.ch_tmax,
      nk: loadAudit().length - window.__a0, note: document.getElementById('setNote').textContent,
      undo: document.getElementById('setUndo').disabled})""")
    chk("0,6 giây sau đã lưu bền", r["ls"] == muon and r["cfg"] == muon, (r["ls"], r["cfg"]))
    chk("3 nấc liền tay = 1 dòng nhật ký", r["nk"] == 1, r["nk"])
    chk("chấm xanh + 'Đã tự lưu 1 thay đổi · giờ'", r["save"] == "ok" and re.search(r"Đã tự lưu 1 thay đổi · \d", r["note"]), r["note"])
    chk("Hoàn tác sáng lên", r["undo"] is False)

    print("3) Rời trang giữa nhịp chờ")
    r = pg.evaluate("""() => { const v0 = +CFG.ch_rmax; fstep('ch_rmax',1); gotoTab('rang');
      return {ls: JSON.parse(localStorage.getItem(LS_CFG)).ch_rmax, muon: String(v0+5), t: window._setSaveT}; }""")
    chk("đổi tab trước 0,6 giây vẫn lưu ngay", r["ls"] == r["muon"] and not r["t"], r)

    print("4) Trục khung 'Đường rang dự kiến' theo Cài đặt")
    r = pg.evaluate("""() => {
      CFG_EDIT = Object.assign({}, CFG, {ch_auto:'Cố định', ch_tmin:'50', ch_tmax:'250', ch_rmin:'-10', ch_rmax:'30'});
      settingsSave(true, true);
      newProfile(); peDrawPreview();
      const a = {lo: PE_HIT.lo, hi: PE_HIT.hi};
      CFG.ch_auto = 'Tự động'; CFG.ch_tmax = '150'; peDrawPreview();
      const b = {lo: PE_HIT.lo, hi: PE_HIT.hi};
      CFG.ch_auto = 'Cố định'; CFG.ch_tmax = '250'; peDrawPreview();
      closeProfEdit();
      return {a, b}; }""")
    chk("Cố định: trục nhiệt = 50…250 đúng Cài đặt", r["a"] == {"lo": 50, "hi": 250}, r["a"])
    chk("Tự động: đường vượt 150 → trục tự nới lên bội số 50", r["b"]["hi"] > 150 and r["b"]["hi"] % 50 == 0, r["b"])

    print("5) Cổng/baud khi đang rang và khi không")
    r = pg.evaluate("""() => { window.__links.length = 0; const ph0 = R.phase, b0 = CFG.cn_baud;
      R.phase = 'RUNNING';
      CFG_EDIT.cn_baud = b0 === '57600' ? '115200' : '57600'; markDirty(); settingsFlush();
      const kq = {b0, cfg: CFG.cn_baud, ls: JSON.parse(localStorage.getItem(LS_CFG)).cn_baud,
                  edit: CFG_EDIT.cn_baud, toast: (document.getElementById('toast')||{}).textContent||''};
      R.phase = ph0; return kq; }""")
    chk("đang rang: tự lưu KHÔNG đổi baud", r["cfg"] == r["b0"] and r["ls"] == r["b0"] and r["edit"] == r["b0"], r)
    chk("đang rang: nói rõ vì sao", "Đang rang" in r["toast"], r["toast"])
    pg.wait_for_timeout(150)
    chk("đang rang: không đẩy gì xuống cầu nối", pg.evaluate("window.__links.length") == 0)
    pg.evaluate("() => { CFG_EDIT.cn_baud = '57600'; markDirty(); settingsFlush(); }")
    pg.wait_for_timeout(200)
    r = pg.evaluate("window.__links.slice()")
    chk("không rang: đổi baud → đẩy baud mới xuống cầu nối 1 lần", len(r) == 1 and r[0].get("baud") == 57600, r)
    pg.evaluate("() => { window.__links.length = 0; fstep('ch_time',1); settingsFlush(); }")
    pg.wait_for_timeout(200)
    chk("đổi ô KHÁC cổng/baud → không đụng cầu nối (trước đây mỗi lần Lưu đều so lại)",
        pg.evaluate("window.__links.length") == 0, pg.evaluate("window.__links.slice()"))

    print("6) Hoàn tác")
    pg.evaluate("() => { gotoTab('caidat'); gotoSub('model'); window.__t0 = CFG.ch_time;"
                " fstep('ch_time',1); fstep('ch_time',1); settingsFlush(); }")
    chk("có thay đổi → Hoàn tác bật", pg.evaluate("document.getElementById('setUndo').disabled") is False)
    pg.evaluate("() => { settingsUndo(); }")
    pg.wait_for_selector("#askbox.on")
    pg.click("#askYes")
    pg.wait_for_timeout(250)
    r = pg.evaluate("""() => ({t: CFG.ch_time, t0: window.__t0, ls: JSON.parse(localStorage.getItem(LS_CFG)).ch_time,
      o: document.querySelector('.field[data-num="ch_time"] .n').textContent,
      undo: document.getElementById('setUndo').disabled})""")
    chk("về đúng giá trị lúc mở trang, đã lưu bền, ô hiện đúng", r["t"] == r["t0"] and r["ls"] == r["t0"] and r["o"] == r["t0"], r)
    chk("Hoàn tác mờ lại", r["undo"] is True)

    print("7) Xuất file cài đặt")
    pg.evaluate("() => { settingsExport(); }")
    pg.wait_for_function("window.__exp.length > 0")
    r = pg.evaluate("""() => { const [t, n] = window.__exp[0]; const L = t.split('\\r\\n');
      return {n, head: L.find(l => l.startsWith('nhom')), tmax: L.find(l => l.startsWith('app,ch_tmax,')),
              appN: L.filter(l => l.startsWith('app,')).length, cfgN: Object.keys(CFG_DEFAULT).length,
              mayN: L.filter(l => l.startsWith('may,')).length, mcN: Object.keys(MC_ALL).length,
              ghichu: L[0], text: t, toast: (document.getElementById('toast')||{}).textContent||''}; }""")
    chk("tên file OTL-cai-dat-YYYYMMDD-HHMM.csv", re.fullmatch(r"OTL-cai-dat-\d{8}-\d{4}\.csv", r["n"]) is not None, r["n"])
    chk("dòng tiêu đề cột", r["head"] == "nhom,khoa,gia_tri,mo_ta", r["head"])
    chk("dòng trục nhiệt có nhãn + đơn vị", r["tmax"] == "app,ch_tmax,250,Nhiệt tối đa (°C)", r["tmax"])
    chk("đủ mọi khoá app", r["appN"] == r["cfgN"], (r["appN"], r["cfgN"]))
    chk("đủ mọi tham số $M", r["mayN"] == r["mcN"], (r["mayN"], r["mcN"]))
    chk("dòng đầu là ghi chú #", r["ghichu"].startswith("# OTL Roast Lab"))
    chk("báo đã xuất kèm tên file", "Đã xuất file cài đặt" in r["toast"], r["toast"])
    kq = pg.evaluate("t => { const k = settingsParseFile(t); return {a: k.app.n, ak: k.app.khac, m: k.may.n, mk: k.may.khac, bo: k.bo, giu: k.giu}; }", r["text"])
    chk("xuất rồi đọc lại: 0 ô khác, 0 dòng lạ", kq["ak"] == 0 and kq["mk"] == 0 and kq["bo"] == 0, kq)

    print("8) Nhập file cài đặt (Excel vùng VN: dấu ; + thập phân dấu phẩy)")
    txt = ("\ufeff# file sửa tay\r\nnhom;khoa;gia_tri;mo_ta\r\n"
           "app;ch_rmax;60;RoR tối đa\r\napp;ch_tmin;999;quá dải\r\napp;mn_sens;1,5;phẩy thập phân\r\n"
           "app;cn_artisan;COM99;cổng của máy tính khác\r\napp;khong_co;1;khoá lạ\r\n"
           "app;ro_algo;Hồi quy bậc 1;lựa chọn đúng\r\napp;ch_auto;Linh tinh;lựa chọn sai\r\n"
           "may;chargeDuration;7;xi-lanh nạp\r\nmay;coolTimer;9999;quá dải\r\n")
    pg.evaluate("""t => { window.__imp = {ok:true, text:t, name:'cai-dat-sua.csv'};
      window.__com0 = CFG.cn_artisan; window.__auto0 = CFG.ch_auto;
      dsLive = () => true; mcRoasting = () => false; settingsImport(); }""", txt)
    pg.wait_for_selector("#askbox.on")
    sub = pg.evaluate("document.getElementById('askSub').textContent")
    chk("hộp xác nhận nói $M KHÔNG ghi xuống máy", "KHÔNG ghi xuống máy" in sub, sub)
    chk("hộp xác nhận báo số bị kẹp", "2 số ngoài dải" in sub, sub)
    chk("hộp xác nhận báo giữ cổng COM", "giữ nguyên cổng COM" in sub, sub)
    chk("hộp xác nhận báo dòng lạ (khoá lạ + lựa chọn sai)", "2 dòng lạ" in sub, sub)
    pg.click("#askYes")
    pg.wait_for_timeout(1400)          # quá nhịp 1 giây của mcCellAutoWrite — nếu có ghi là bắt được
    r = pg.evaluate("""() => ({rmax: CFG.ch_rmax, tmin: CFG.ch_tmin, sens: CFG.mn_sens, com: CFG.cn_artisan, com0: window.__com0,
      algo: CFG.ro_algo, auto: CFG.ch_auto, auto0: window.__auto0, ls: JSON.parse(localStorage.getItem(LS_CFG)).ch_rmax,
      cd: MC.cur.chargeDuration, cool: MC.cur.coolTimer, lsmc: JSON.parse(localStorage.getItem(LS_MC)||'{}').chargeDuration,
      mcw: window.__mcw.length, nk: (loadAudit()[0]||{}).action, pick: document.querySelector('[data-cfg="ro_algo"] .pv').textContent})""")
    chk("RoR tối đa 60 đã áp + lưu bền", r["rmax"] == "60" and r["ls"] == "60", r)
    chk("999 °C kẹp về 200 (trần của ô)", r["tmin"] == "200", r["tmin"])
    chk("'1,5' đọc thành 1.5", r["sens"] == "1.5", r["sens"])
    chk("cổng COM giữ nguyên", r["com"] == r["com0"], (r["com"], r["com0"]))
    chk("lựa chọn đúng được nhận + hiện trên ô", r["algo"] == "Hồi quy bậc 1" and r["pick"] == "Hồi quy bậc 1", r)
    chk("lựa chọn sai bị bỏ", r["auto"] == r["auto0"], r["auto"])
    chk("$M điền form: xi-lanh nạp 7, làm nguội kẹp 600", r["cd"] == 7 and r["cool"] == 600 and r["lsmc"] == 7, r)
    chk("KHÔNG ghi $M xuống máy dù đang nối máy", r["mcw"] == 0, r["mcw"])
    chk("nhật ký ghi thao tác Nhập", r["nk"] == "Nhập", r["nk"])

    print("9) File rác")
    pg.evaluate("() => { window.__imp = {ok:true, text:'hello world', name:'rac.txt'}; settingsImport(); }")
    pg.wait_for_timeout(300)
    r = pg.evaluate("({ask: document.getElementById('askbox').classList.contains('on'), toast: (document.getElementById('toast')||{}).textContent||''})")
    chk("không mở hộp xác nhận", r["ask"] is False)
    chk("báo file không có dòng cài đặt hợp lệ", "không có dòng cài đặt hợp lệ" in r["toast"], r["toast"])
    r = pg.evaluate("() => { const k = settingsParseFile('app,ui_view,Đơn gia\\u0309n\\r\\n'); return {n: k.app.n, v: k.app.v.ui_view}; }")
    chk("CSV kiểu ANSI (dấu thanh rời) vẫn khớp lựa chọn 'Đơn giản'", r == {"n": 1, "v": "Đơn giản"}, r)

    print("10) Không còn blur ở lớp phủ / hộp đăng nhập")
    r = pg.evaluate("""() => [getComputedStyle(document.getElementById('login')).backdropFilter,
                              getComputedStyle(document.querySelector('.loginbox')).backdropFilter]""")
    chk("backdrop-filter = none", r == ["none", "none"], r)

    chk("không có lỗi JS", not errs, errs[:3])
    br.close()

print("\nKẾT QUẢ:", "ĐẠT hết" if not fails else f"{len(fails)} mục TRƯỢT: {fails}")
sys.exit(1 if fails else 0)
