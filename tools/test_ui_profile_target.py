"""Đường rang dự kiến trong "Sửa hồ sơ" — kế hoạch phải khớp với máy.

Ba lỗi nền được chốt bằng bộ kiểm này, vì cả ba đều IM LẶNG (không ném lỗi, không
hiện gì lạ) nên chỉ có kiểm tự động mới giữ được:

  1. Nạp hồ sơ phải đẩy CẢ BA ngưỡng DE/FCs/DROP sang R.mileSet. Thiếu DE/FCs thì
     bản xem trước nói một đằng, màn rang chấm mốc một nẻo theo hồ sơ cũ.
  2. Kết thúc mẻ KHÔNG được ghi đè p.temp/p.time — mục tiêu trôi dần qua từng mẻ.
  3. RoR của bản xem trước phải tính bằng ĐÚNG bộ máy RoR của màn rang (rorRaw +
     cửa sổ trong Cài đặt), không phải công thức ±15 giây riêng.

Cộng thêm phần nâng cấp: giờ mốc do thợ đặt, và bộ "soi kế hoạch".
"""
import sys, pathlib
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

HTML = pathlib.Path(__file__).resolve().parent.parent / "OTL Roast Lab.html"
STUB = "window.pywebview=undefined;"

fails = []


def mmss(v):
    """"09:36" → 576 giây (bộ kiểm cần so thời gian bằng số)."""
    try:
        m, s = str(v).split(":")
        return int(m) * 60 + int(s)
    except Exception:
        return -1


def chk(name, cond, got=""):
    print(("  OK   " if cond else "  FAIL ") + name + (f"  → {got}" if got else ""))
    if not cond:
        fails.append(name)


with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={"width": 1600, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.add_init_script(STUB)
    pg.goto(HTML.as_uri())
    pg.wait_for_function("typeof buildTarget === 'function' && typeof peAudit === 'function'")
    # Đóng màn đăng nhập: bàn phím PIN của nó phủ kín sân khấu, mọi cú chạm chuột sẽ
    # rơi vào phím số chứ không tới nút trong hộp thoại (đọc DOM thì vẫn đúng — đó là
    # cái bẫy). Mục 13 chạm nút thật nên bắt buộc phải dọn.
    pg.evaluate("document.getElementById('login').classList.remove('on')")

    print("1) mmssToSec — dạng giờ")
    r = pg.evaluate("""() => ({
      a: mmssToSec('12:00'), b: mmssToSec('9:30'), c: mmssToSec('00:99'),
      d: mmssToSec('abc'), e: mmssToSec(''), f: mmssToSec('00:00')})""")
    chk("12:00 = 720 giây", r["a"] == 720, r["a"])
    chk("9:30 (thiếu số 0) đọc được", r["b"] == 570, r["b"])
    chk("00:99 vẫn dựng được = 99 giây", r["c"] == 99, r["c"])
    chk("chuỗi bậy / rỗng / 0 trả null", r["d"] is None and r["e"] is None and r["f"] is None)

    print("2) Thứ tự mốc LUÔN tăng dù thợ gõ số vô lý")
    r = pg.evaluate("""() => {
      const cases = [
        {time:'12:00', chargeT:160, temp:200},
        {time:'01:00', chargeT:160, temp:200},
        {time:'12:00', chargeT:200, temp:150},                       // xả thấp hơn charge
        {time:'12:00', chargeT:160, temp:200, deT:190, fcsT:150},    // DE > FCs
        {time:'12:00', chargeT:160, temp:200, fcsTime:'00:30'},      // nổ quá sớm
        {time:'12:00', chargeT:160, temp:200, deTime:'11:50'},       // hạt vàng quá muộn
        {time:'12:00', chargeT:160, temp:200, fcsTime:'20:00'},      // nổ ngoài mẻ
      ];
      return cases.map(c => { const T = buildTarget(c);
        if (!T) return 'null';
        const s = [0, T.tpS, T.deS, T.fcsS, T.totalS];
        const tang = s.every((v,i) => i===0 || v > s[i-1]);
        return tang ? 'ok' : s.join('<'); });
    }""")
    chk("7 hồ sơ méo đều ra mốc tăng dần", all(v == "ok" for v in r), ", ".join(r))
    r = pg.evaluate("() => buildTarget({time:'00:30', chargeT:160, temp:200})")
    chk("mẻ dưới 01:00 → không dựng đường bịa", r is None)

    print("3) Giờ mốc do thợ đặt THẮNG tỉ lệ tự suy")
    r = pg.evaluate("""() => {
      const auto = buildTarget({time:'12:00', chargeT:160, temp:200, devTarget:10});
      const tay  = buildTarget({time:'12:00', chargeT:160, temp:200, devTarget:10, fcsTime:'09:00'});
      const de   = buildTarget({time:'12:00', chargeT:160, temp:200, deTime:'05:00'});
      return {autoFcs:auto.fcsS, tayFcs:tay.fcsS, tayDtr:tay.dtrPct,
              deS:de.deS, deAuto:de.deAuto, fcsAuto:auto.fcsAuto};
    }""")
    chk("không đặt giờ → FCs theo % phát triển", r["autoFcs"] == 648, r["autoFcs"])
    chk("đặt 09:00 → FCs đúng 540 giây", r["tayFcs"] == 540, r["tayFcs"])
    chk("% phát triển tính NGƯỢC từ giờ nổ", r["tayDtr"] == 25, r["tayDtr"])
    chk("đặt hạt vàng 05:00 → DE đúng 300 giây", r["deS"] == 300, r["deS"])
    chk("cờ deAuto/fcsAuto báo đúng ai đặt", r["deAuto"] is False and r["fcsAuto"] is True)

    print("4) Ba pha luôn cộng đủ 100%")
    r = pg.evaluate("""() => [ {time:'12:00',chargeT:160,temp:200},
        {time:'09:13',chargeT:170,temp:205,devTarget:18},
        {time:'15:47',chargeT:150,temp:212,deTime:'06:41',fcsTime:'12:03'} ]
      .map(c => { const T=buildTarget(c); return T.dryPct+T.maiPct+T.dtrPct; })""")
    chk("dry+maillard+dev = 100 ở cả 3 hồ sơ", all(v == 100 for v in r), str(r))

    print("5) RoR dự kiến dùng CHUNG bộ máy với màn rang")
    r = pg.evaluate("""() => {
      Object.assign(CFG, {ro_span:'20', ro_algo:'Hai điểm mút', ro_csmooth:'0', ro_smooth:'0'});
      const T = buildTarget({time:'12:00', chargeT:160, temp:200});
      // tự tính lại bằng chính rorRaw() mà màn rang dùng
      const t=[],v=[]; for(let s=0;s<=T.totalS;s++){t.push(s);v.push(T.btAt(s));}
      const ref = rorRaw(t, v, 20, false);
      const got = T.rorSeries();
      let lech = 0;
      for (let s=0;s<=T.totalS;s++){
        if (ref[s]==null || got[s]==null) { if ((ref[s]==null)!==(got[s]==null)) lech = 999; continue; }
        lech = Math.max(lech, Math.abs(ref[s]-got[s]));
      }
      return {lech, dauMe:got[5], sauCuaSo:got[60]!=null, rFCs:T.rorAt(T.fcsS)};
    }""")
    chk("khớp rorRaw() từng giây", r["lech"] < 1e-9, r["lech"])
    chk("đầu mẻ chưa đủ cửa sổ → null, không bịa số 0", r["dauMe"] is None)
    chk("qua cửa sổ thì có số", r["sauCuaSo"] is True)
    chk("thẻ mốc có RoR tại FCs", r["rFCs"] is not None, r["rFCs"])
    r = pg.evaluate("""() => {
      Object.assign(CFG, {ro_span:'40'});
      const T = buildTarget({time:'12:00', chargeT:160, temp:200});
      const a = T.rorSeries();
      Object.assign(CFG, {ro_span:'20'});
      const B = buildTarget({time:'12:00', chargeT:160, temp:200});
      return {c40:a.filter(v=>v!=null).length, c20:B.rorSeries().filter(v=>v!=null).length};
    }""")
    chk("đổi cửa sổ trong Cài đặt là RoR dự kiến đổi theo", r["c40"] < r["c20"], f"{r['c40']} vs {r['c20']}")

    print("6) Nạp hồ sơ → CẢ BA ngưỡng đi theo hồ sơ")
    r = pg.evaluate("""() => {
      localStorage.setItem('otl_milset', JSON.stringify({DE:150, FCs:196, DROP:198}));
      R.mileSet = {DE:150, FCs:196, DROP:198};
      const ps = loadProfiles();
      ps[0] = {name:'Kiểm', roast:ps[0].roast, chargeT:160, temp:200, time:'12:00', deT:146, fcsT:192};
      saveProfiles(ps);
      loadProfile(0);
      const day = Object.assign({}, R.mileSet);
      ps[0] = {name:'Kiểm2', roast:ps[0].roast, chargeT:160, temp:204, time:'12:00'};   // hồ sơ mỏng
      saveProfiles(ps);
      loadProfile(0);
      return {day, mong: Object.assign({}, R.mileSet),
              luu: JSON.parse(localStorage.getItem('otl_milset'))};
    }""")
    chk("hồ sơ dày: DE 146 sang mileSet", r["day"].get("DE") == 146, r["day"])
    chk("hồ sơ dày: FCs 192 sang mileSet", r["day"].get("FCs") == 192, r["day"])
    chk("hồ sơ dày: DROP 200 sang mileSet", r["day"].get("DROP") == 200, r["day"])
    chk("hồ sơ mỏng: XOÁ ngưỡng DE/FCs cũ (chấm tay)",
        "DE" not in r["mong"] and "FCs" not in r["mong"], r["mong"])
    chk("hồ sơ mỏng: DROP vẫn theo hồ sơ mới", r["mong"].get("DROP") == 204, r["mong"])
    chk("ghi xuống localStorage", r["luu"].get("DROP") == 204, r["luu"])

    print("7) Kết thúc mẻ KHÔNG làm trôi kế hoạch")
    r = pg.evaluate("""() => {
      const ps = loadProfiles();
      ps[0] = {name:'Chuẩn', roast:ps[0].roast, chargeT:160, temp:200, time:'12:00'};
      saveProfiles(ps);
      loadProfile(0);
      seriesReset();
      for (let i=0;i<=600;i+=10){ SERIES.t.push(i); SERIES.bt.push(90+0.19*i);
        SERIES.et.push(120+0.2*i); SERIES.gas.push(40); SERIES.air.push(80);
        SERIES.drum.push(55); SERIES.vac.push(0); SERIES.ror.push(11); SERIES.rorET.push(9); }
      R.phase='RUNNING'; R.elapsed=754; R.mileT={FCs:620};
      finishRoast();
      const p = loadProfiles()[0];
      return {temp:p.temp, time:p.time, last:p.last||null};
    }""")
    chk("nhiệt xả kế hoạch giữ nguyên 200", r["temp"] == 200, r["temp"])
    chk("thời gian kế hoạch giữ nguyên 12:00", r["time"] == "12:00", r["time"])
    chk("kết quả thật ghi riêng vào p.last", bool(r["last"]), r["last"])
    chk("p.last giữ đúng giờ xả 12:34", (r["last"] or {}).get("time") == "12:34", r["last"])

    print("8) Soi kế hoạch — nói đúng chỗ sai")
    r = pg.evaluate("""() => {
      const soi = c => { const T = buildTarget(c); return T ? peAudit(T, c, null) : []; };
      const co = (list, tu) => list.some(x => x.t.indexOf(tu) >= 0);
      const nang = (list, tu) => list.some(x => x.lv==='bad' && x.t.indexOf(tu) >= 0);
      return {
        gio99:  nang(soi({time:'00:99', chargeT:160, temp:200}), 'giây phải dưới 60'),
        xaThap: nang(soi({time:'12:00', chargeT:200, temp:180}), 'không cao hơn'),
        deCao:  nang(soi({time:'12:00', chargeT:160, temp:200, deT:190, fcsT:150}), 'đã hạ DE'),
        dtrIt:  nang(soi({time:'12:00', chargeT:160, temp:200, fcsTime:'11:40'}), 'Phát triển chỉ'),
        dtrDai: co(soi({time:'12:00', chargeT:160, temp:200, fcsTime:'07:30'}), 'Phát triển 38%'),
        meNgan: co(soi({time:'04:00', chargeT:160, temp:200}), 'rất ngắn'),
        sach:   soi({time:'12:00', chargeT:160, temp:200, deT:150, fcsT:194, devTarget:20}).length,
      };
    }""")
    chk('"00:99" bị bắt là lỗi nặng', r["gio99"] is True)
    chk("nhiệt xả ≤ charge bị bắt", r["xaThap"] is True)
    chk("DE ≥ FCs bị bắt kèm số app đã hạ", r["deCao"] is True)
    chk("phát triển dưới 10% bị bắt", r["dtrIt"] is True)
    chk("phát triển 38% được nhắc", r["dtrDai"] is True)
    chk("mẻ 4 phút được nhắc", r["meNgan"] is True)
    chk("hồ sơ cân đối thì KHÔNG bịa lời nhắc", r["sach"] == 0, r["sach"])

    print("9) Hộp Sửa hồ sơ vẽ thật — mốc, RoR, dải soi")
    r = pg.evaluate("""() => {
      const ps = loadProfiles();
      ps[0] = {name:'Xem', roast:ps[0].roast, chargeT:160, temp:200, time:'12:00', deT:150, fcsT:194, devTarget:20};
      saveProfiles(ps);
      editProfile(0);
      peDrawPreview();
      const the = [...document.querySelectorAll('#peMiles .pe-mile')];
      const cv  = document.getElementById('peCurve');
      return {nThe:the.length, coRoR:the.filter(e=>e.querySelector('.m4')).length,
              rorFCs:(the[2].querySelector('.m4')||{}).textContent,
              nChk:document.querySelectorAll('#peCheck .pechk').length,
              chkOk:!!document.querySelector('#peCheck .pechk.ok'),
              veDuoc:cv.width>10 && cv.height>10,
              oGio:!!document.getElementById('pe_deTime') && !!document.getElementById('pe_fcsTime')};
    }""")
    chk("5 thẻ mốc", r["nThe"] == 5, r["nThe"])
    # Từ 14/09: thẻ thứ 4 là ô CHỈNH phát triển (thời lượng + %), không phải một mốc có RoR
    chk("4 thẻ mốc có dòng RoR + ô PHÁT TRIỂN", r["coRoR"] == 4, r["coRoR"])
    chk("RoR tại FCs là số, không phải gạch", r["rorFCs"] not in (None, "—"), r["rorFCs"])
    chk("dải soi kế hoạch có nội dung", r["nChk"] >= 1, r["nChk"])
    chk("hồ sơ cân đối → thẻ xanh 'ổn'", r["chkOk"] is True)
    chk("canvas có kích thước thật", r["veDuoc"] is True)
    chk("có hai ô giờ mốc trong form", r["oGio"] is True)

    print("10) Gõ vào ô là đường vẽ lại, không ném lỗi")
    pg.fill("#pe_time", "10:30")
    pg.fill("#pe_fcsTime", "08:15")
    pg.dispatch_event("#pe_fcsTime", "blur")
    r = pg.evaluate("""() => ({ time:peTmp.time, fcs:peTmp.fcsTime,
                                fcsS:buildTarget(peTmp).fcsS,
                                chuanHoa:(()=>{const el=document.getElementById('pe_time');
                                  el.value='00:99'; peTmp.time='00:99'; peTimeMain(el); return el.value;})() })""")
    chk("ô giờ nổ vào đúng peTmp", r["fcs"] == "08:15", r["fcs"])
    chk("đường dựng theo giờ nổ mới", r["fcsS"] == 495, r["fcsS"])
    chk('rời ô "Thời gian" thì 00:99 chuẩn hoá thành 01:39', r["chuanHoa"] == "01:39", r["chuanHoa"])

    print("11) Mẻ nền thật vẽ được trong bản xem trước + đem ra đối chiếu")
    pg.evaluate("""() => {
      // Mẻ nền giả: 13:20, xả 208° — cố tình lệch kế hoạch để bộ soi phải lên tiếng
      const t=[], bt=[];
      for (let s=0;s<=800;s+=5){ t.push(s); bt.push(s<90 ? 160-0.8*s : 88+0.155*(s-90)); }
      window.pywebview = { api: { db_batch_curve: async () => ({t, bt, et:bt.map(v=>v+15)}) } };
    }""")
    pg.evaluate("() => { peTmp.bgBatch = 7; PE_BG.id = 0; return peBgLoad(); }")
    pg.wait_for_timeout(300)
    r = pg.evaluate("""() => {
      peDrawPreview();
      const T = buildTarget(peTmp);
      const list = peAudit(T, peTmp, {end:800, drop:208, pts:[200,210]});
      return {coCv: !!(PE_BG.cv && PE_BG.cv.t.length),
              nhacDai: list.some(x => x.t.indexOf('Mẻ nền dài') >= 0),
              nhacXa:  list.some(x => x.t.indexOf('Mẻ nền xả') >= 0)};
    }""")
    chk("kéo được curve mẻ nền về", r["coCv"] is True)
    chk("bộ soi nhắc mẻ nền dài hơn kế hoạch", r["nhacDai"] is True)
    chk("bộ soi nhắc lệch nhiệt xả", r["nhacXa"] is True)

    print("12) Dải 3 pha + chú giải (khuôn bản thiết kế Claude Design)")
    r = pg.evaluate("""() => {
      const ps = loadProfiles();
      ps[0] = {name:'Pha', roast:ps[0].roast, chargeT:160, temp:200, time:'12:00',
               deT:150, fcsT:194, deTime:'06:00', fcsTime:'09:36', bgBatch:7};
      saveProfiles(ps); editProfile(0); peDrawPreview();
      const ph = [...document.querySelectorAll('#pePhases .pe-ph')];
      const lg = [...document.querySelectorAll('#peLegend span')];
      return {n:ph.length,
              ten:ph.map(e=>e.querySelector('.phn').textContent),
              gio:ph.map(e=>e.querySelector('.pht').textContent),
              pc:ph.map(e=>e.querySelector('.php').textContent),
              flex:ph.map(e=>e.style.flexGrow||e.style.flex),
              nLg:lg.length, lgTxt:lg.map(e=>e.textContent).join(' | '),
              donVi:!!document.querySelector('#peMiles .m4 i')};
    }""")
    chk("đủ 3 ô pha", r["n"] == 3, r["ten"])
    chk("ghi ĐỘ DÀI từng pha, không chỉ %", r["gio"] == ["06:00", "03:36", "02:24"], r["gio"])
    chk("phần trăm cộng đủ 100", sum(int(x.rstrip("%")) for x in r["pc"]) == 100, r["pc"])
    chk("bề rộng ô pha theo thời gian", r["flex"][0] != r["flex"][2], r["flex"])
    chk("chú giải kê đủ 3 đường đang vẽ", r["nLg"] == 3, r["lgTxt"])
    chk("chú giải gọi đúng tên mẻ nền", "M-0042" in r["lgTxt"] or "#7" in r["lgTxt"], r["lgTxt"])
    chk("thẻ mốc ghi đơn vị RoR", r["donVi"] is True)
    r = pg.evaluate("""() => {
      peTmp.time = 'xx'; peDrawPreview();
      return {ph:document.getElementById('pePhases').innerHTML.trim(),
              lg:document.getElementById('peLegend').innerHTML.trim()};
    }""")
    chk("thiếu số thì dọn sạch dải pha + chú giải", r["ph"] == "" and r["lg"] == "", r)

    print("13) Nút ± trên mọi ô số — chỉnh được bằng ngón tay, không cần bàn phím")
    pg.evaluate("""() => {
      const ps = loadProfiles();
      ps[0] = {name:'Chạm', roast:ps[0].roast, chargeT:160, temp:200, time:'12:00'};
      saveProfiles(ps); delete PE_BG.cv; PE_BG.id = 0; editProfile(0);
    }""")
    pg.wait_for_timeout(250)
    pg.evaluate("document.querySelectorAll('.roast-done.on').forEach(e=>e.classList.remove('on'))")
    r = pg.evaluate("""() => {
      const rows = [...document.querySelectorAll('#profedit .pestep')];
      return {n:rows.length, keys:rows.map(r=>r.dataset.pestep),
              nut:rows.every(r=>r.querySelectorAll('.fpm').length===2),
              o:rows.every(r=>r.querySelector('input.peval'))};
    }""")
    chk("12 ô số đều có hàng ± (10 ô form + 2 ô PHÁT TRIỂN dưới hình)", r["n"] == 12, r["keys"])
    chk("mỗi hàng đủ 2 nút", r["nut"] is True)
    chk("ô nhập vẫn còn (gõ tay được như cũ)", r["o"] is True)

    def tap(key, d, ms=90):
        """Chạm nút ± bằng CHUỘT THẬT (không gọi hàm) — phải qua đúng đường cử chỉ.

        Hộp thoại cao hơn cửa sổ nên các ô phía dưới nằm ngoài tầm chuột; không kéo
        vào trước thì cú chạm rơi ra ngoài cửa sổ và bài kiểm đỏ oan.
        """
        sel = f'#profedit .pestep[data-pestep="{key}"] .fpm[data-d="{d}"]'
        loc = pg.locator(sel)
        # Từ 14/09 ô nhập cuộn TRONG lưới .pe-fields (khung xem trước đóng băng): nút có thể
        # nằm trong cửa sổ mà vẫn bị vùng cuộn che — so với mép cửa sổ là không đủ. Luôn
        # cuộn tới nút trước (scroll_into_view_if_needed biết cuộn cả khung cuộn con).
        loc.scroll_into_view_if_needed(); pg.wait_for_timeout(140)
        box = loc.bounding_box()
        pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        pg.mouse.down(); pg.wait_for_timeout(ms); pg.mouse.up(); pg.wait_for_timeout(120)

    tap("temp", "1")
    chk("chạm + nhiệt xả = +1", pg.evaluate("()=>peTmp.temp") == 201,
        pg.evaluate("()=>peTmp.temp"))
    tap("temp", "-1"); tap("temp", "-1")
    chk("chạm − hai cái về 199", pg.evaluate("()=>peTmp.temp") == 199,
        pg.evaluate("()=>peTmp.temp"))
    chk("ô nhập hiện đúng số vừa bấm",
        pg.evaluate("()=>document.getElementById('pe_temp').value") == "199")

    tap("time", "1")
    chk("chạm + thời gian = +5 giây", pg.evaluate("()=>peTmp.time") == "12:05",
        pg.evaluate("()=>peTmp.time"))

    # ô TUỲ CHỌN đang trống: chạm ± lần đầu phải lấy số app đang ước làm điểm xuất phát
    r = pg.evaluate("""() => {
      delete peTmp.fcsT; document.getElementById('pe_fcsT').value=''; peDrawPreview();
      return buildTarget(peTmp).fcsT;
    }""")
    tap("fcsT", "1")
    got = pg.evaluate("()=>peTmp.fcsT")
    chk("ô trống: chạm + lấy đúng số app đang ước", got == r, f"ước {r} → {got}")

    r = pg.evaluate("""() => {
      delete peTmp.fcsTime; document.getElementById('pe_fcsTime').value=''; peDrawPreview();
      return fmtMMSS(buildTarget(peTmp).fcsS);
    }""")
    tap("fcsTime", "1")
    chk("ô giờ trống cũng lấy số ước", pg.evaluate("()=>peTmp.fcsTime") == r,
        f"ước {r} → {pg.evaluate('()=>peTmp.fcsTime')}")

    # GIỮ: tự lặp và bậc lớn dần — giữ 1,5s phải đi xa hơn hẳn 15 nấc đơn
    pg.evaluate("()=>{peTmp.temp=150;document.getElementById('pe_temp').value=150;}")
    tap("temp", "1", ms=1500)
    xa = pg.evaluate("()=>peTmp.temp") - 150
    # Giữ 1,5s: nấc đầu + tự lặp mỗi 0,2s từ mốc 0,45s, bậc nhảy lên ×5 sau 1,2s →
    # khoảng +15. Đặt ngưỡng 10 vì nhịp setTimeout trong trang lệch vài chục ms là
    # rụng một tick; không tăng tốc thì tối đa chỉ được +7, nên 10 vẫn chứng minh đủ.
    chk("giữ 1,5s chạy nhiều nấc và có tăng tốc", xa >= 10, f"+{xa}")
    chk("giữ xong nhả ra thì dừng hẳn",
        pg.evaluate("()=>peTmp.temp") == pg.evaluate("()=>{return new Promise(r=>setTimeout(()=>r(peTmp.temp),350))}"))

    # kẹp biên — giữ thật lâu không được vượt trần
    pg.evaluate("()=>{peTmp.devTarget=39;document.getElementById('pe_dev').value=39;}")
    tap("devTarget", "1", ms=1800)
    chk("không vượt trần 40%", pg.evaluate("()=>peTmp.devTarget") == 40,
        pg.evaluate("()=>peTmp.devTarget"))

    chk("đồ thị vẽ lại theo nút ±",
        pg.evaluate("()=>document.querySelectorAll('#peMiles .pe-mile').length") == 5)

    print("14) Ô 'Mẻ nạp (kg)' — gõ dở không bị xoá mất")
    r = pg.evaluate("""() => {
      const el=document.getElementById('pe_kg');
      el.value='0'; peKgIn(el); const a=peTmp.kg;
      el.value='0.5'; peKgIn(el); const b=peTmp.kg;
      el.value=''; peKgIn(el); const c=peTmp.kg;
      return {a:a===undefined?null:a, b:b===undefined?null:b, c:c===undefined?null:c};
    }""")
    chk("gõ '0' chưa tính là khối lượng", r["a"] is None, r)
    chk("gõ tiếp '.5' thì nhận 0.5", r["b"] == 0.5, r)
    chk("xoá trắng thì bỏ hẳn", r["c"] is None, r)

    print("15) Kéo mốc ngay trên hình")
    pg.evaluate("""() => {
      const ps = loadProfiles();
      ps[0] = {name:'Kéo', roast:ps[0].roast, chargeT:160, temp:200, time:'12:00',
               deT:150, fcsT:194, deTime:'06:00', fcsTime:'09:36'};
      saveProfiles(ps); delete peTmp.bgBatch; PE_BG.id = 0; PE_BG.cv = null;
      editProfile(0); peDrawPreview();
      // Cuộn ruột hộp về đầu: các mục trước đã cuộn xuống tận ô kg, mà đồ thị nằm
      // TRÊN cùng — không kéo về thì toạ độ chấm mốc rơi ra ngoài cửa sổ và cú kéo
      // đi lạc. (Hộp thoại nay chỉ cuộn phần ruột, xem .pe2col.)
      const c=document.querySelector('#profedit .pe2col'); if(c)c.scrollTop=0;
    }""")
    pg.wait_for_timeout(300)

    def mile_xy(mid):
        return pg.evaluate("""(mid) => {
          const q = PE_HIT.pts.find(p => p.id === mid); if (!q) return null;
          const r = document.getElementById('peCurve').getBoundingClientRect();
          return {x: r.left + q.x, y: r.top + q.y, doc: !!q.doc};
        }""", mid)

    def drag(mid, dx, dy):
        a = mile_xy(mid)
        if a is None:
            return False
        pg.mouse.move(a["x"], a["y"])
        pg.mouse.down()
        pg.mouse.move(a["x"] + dx / 2, a["y"] + dy / 2); pg.wait_for_timeout(40)
        pg.mouse.move(a["x"] + dx, a["y"] + dy); pg.wait_for_timeout(60)
        pg.mouse.up(); pg.wait_for_timeout(140)
        return True

    r = pg.evaluate("()=>PE_HIT.pts.map(p=>p.id)")
    chk("bắt được 3 mốc kéo: DE · FCs · DROP", sorted(r) == ["DE", "DROP", "FCs"], r)

    truoc = pg.evaluate("()=>({t:peTmp.fcsTime, d:peTmp.fcsT})")
    drag("FCs", -90, 0)
    sau = pg.evaluate("()=>({t:peTmp.fcsTime, d:peTmp.fcsT})")
    chk("kéo FCs sang TRÁI → vào nổ sớm hơn", mmss(sau["t"]) < mmss(truoc["t"]),
        f'{truoc["t"]} → {sau["t"]}')
    chk("kéo ngang KHÔNG đụng tới nhiệt", sau["d"] == truoc["d"], f'{truoc["d"]} → {sau["d"]}')
    chk("ô nhập chạy theo tay",
        pg.evaluate("()=>document.getElementById('pe_fcsTime').value") == sau["t"])

    truoc = pg.evaluate("()=>peTmp.fcsT")
    drag("FCs", 0, -40)
    chk("kéo FCs LÊN → nhiệt nổ cao hơn", pg.evaluate("()=>peTmp.fcsT") > truoc,
        f'{truoc} → {pg.evaluate("()=>peTmp.fcsT")}')

    truoc = pg.evaluate("()=>({t:peTmp.time, d:peTmp.temp})")
    drag("DROP", -120, -30)
    sau = pg.evaluate("()=>({t:peTmp.time, d:peTmp.temp})")
    chk("kéo DROP lên → nhiệt xả cao hơn", sau["d"] > truoc["d"], f'{truoc["d"]} → {sau["d"]}')
    chk("DROP KHÔNG đổi tổng thời gian khi kéo ngang", sau["t"] == truoc["t"],
        f'{truoc["t"]} → {sau["t"]}')

    # kéo thật xa: không được vượt mốc bên cạnh, không được lộn thứ tự
    drag("FCs", -600, 0)
    r = pg.evaluate("""() => { const T = buildTarget(peTmp);
      return {deS:T.deS, fcsS:T.fcsS, tpS:T.tpS, total:T.totalS}; }""")
    chk("kéo FCs quá đà vẫn giữ TP < DE < FCs < DROP",
        r["tpS"] < r["deS"] < r["fcsS"] < r["total"], r)
    drag("DE", 900, 900)
    r = pg.evaluate("""() => { const T = buildTarget(peTmp);
      return {deS:T.deS, fcsS:T.fcsS, deT:T.deT, fcsT:T.fcsT}; }""")
    chk("kéo DE quá đà vẫn không vượt FCs", r["deS"] < r["fcsS"] and r["deT"] < r["fcsT"], r)
    chk("kéo xong không còn giữ mốc nào", pg.evaluate("()=>PE_DRAG.id") is None)

    print("16) Lấy mốc theo mẻ nền — một chạm thành hồ sơ chuẩn")
    pg.evaluate("""() => {
      const t=[],bt=[],gas=[];
      for(let s=0;s<=700;s+=5){ t.push(s); bt.push(s<90?158-0.76*s:90+0.16*(s-90)); gas.push(45); }
      window.pywebview = { api: {
        db_batch_curve: async () => ({t, bt, et:bt.map(v=>v+14), gas}),
        db_batch_list: async () => [{id:9, code:'M-0099', live:1, drop_sec:700, drop_temp:203,
          charge_kg:11.5, mile:{DE:{t:330,bt:148},FCs:{t:560,bt:191},DROP:{t:700,bt:203}}}],
      }};
      HIST_ROWS = [];
      const ps = loadProfiles();
      ps[0] = {name:'Chép', roast:ps[0].roast, chargeT:160, temp:200, time:'12:00', bgBatch:9};
      saveProfiles(ps); PE_BG.id = 0; PE_BG.cv = null; editProfile(0);
    }""")
    pg.wait_for_timeout(400)
    chk("chưa ghim thì nút mờ — đã ghim thì sáng",
        pg.evaluate("()=>!document.getElementById('pe_bgApply').classList.contains('dis')"))
    pg.click("#pe_bgApply")
    pg.wait_for_timeout(200)
    chk("hỏi lại trước khi ghi đè", pg.evaluate("()=>document.getElementById('askbox').classList.contains('on')"))
    pg.click("#askYes")
    pg.wait_for_timeout(400)
    r = pg.evaluate("""()=>({time:peTmp.time, temp:peTmp.temp, deT:peTmp.deT, deTime:peTmp.deTime,
                             fcsT:peTmp.fcsT, fcsTime:peTmp.fcsTime, kg:peTmp.kg, gas:peTmp.preGas,
                             oTime:document.getElementById('pe_time').value})""")
    chk("giờ xả theo mẻ nền", r["time"] == "11:40", r["time"])
    chk("nhiệt xả theo mẻ nền", r["temp"] == 203, r["temp"])
    chk("mốc DE chép cả giờ lẫn nhiệt", r["deTime"] == "05:30" and r["deT"] == 148, r)
    chk("mốc FCs chép cả giờ lẫn nhiệt", r["fcsTime"] == "09:20" and r["fcsT"] == 191, r)
    chk("khối lượng mẻ chép theo", r["kg"] == 11.5, r["kg"])
    chk("gas mồi lấy từ đầu curve", r["gas"] == 45, r["gas"])
    chk("ô nhập cập nhật theo", r["oTime"] == "11:40", r["oTime"])

    print("17) Chạm thẻ cảnh báo → nhảy tới đúng ô")
    pg.evaluate("""() => {
      peTmp = {name:'Sai', roast:'Rang nhạt', chargeT:190, temp:200, time:'07:30',
               deT:185, fcsT:175, devTarget:6};
      refreshPE();
    }""")
    pg.wait_for_timeout(300)
    r = pg.evaluate("""() => {
      const c = [...document.querySelectorAll('#peCheck .pechk[data-go]')];
      return {n:c.length, dau:c.length?c[0].dataset.go:null};
    }""")
    chk("thẻ cảnh báo có chỉ đích ô", r["n"] >= 2, r)
    pg.click("#peCheck .pechk[data-go]")
    pg.wait_for_timeout(300)
    chk("chạm thẻ là con trỏ nhảy vào đúng ô",
        pg.evaluate("()=>document.activeElement&&document.activeElement.id") == r["dau"],
        pg.evaluate("()=>document.activeElement&&document.activeElement.id"))

    print("18) Đóng băng khung xem trước + chỉnh PHÁT TRIỂN theo thời lượng / % (14/09)")
    pg.evaluate("""() => {
      peTmp = {name:'Dev', roast:'Rang vừa', chargeT:190, temp:210, time:'12:00', deT:152, fcsT:196};
      refreshPE();
    }""")
    pg.wait_for_timeout(300)
    r = pg.evaluate("""() => {
      const f=document.querySelector('#profedit .pe2col>.pe-fields');
      const cv=document.getElementById('peCurve'), top0=cv.getBoundingClientRect().top;
      f.scrollTop=f.scrollHeight;
      const out={cuon:f.scrollTop>0, oy:getComputedStyle(f).overflowY,
                 ruot:getComputedStyle(document.querySelector('#profedit .pe2col')).overflowY,
                 lech:Math.abs(cv.getBoundingClientRect().top-top0)};
      f.scrollTop=0; return out;
    }""")
    chk("chỉ lưới ô nhập cuộn, ruột hộp không cuộn",
        r["cuon"] and r["oy"] in ("auto", "scroll") and r["ruot"] == "hidden", r)
    chk("cuộn ô nhập tới đáy thì đồ thị đứng yên", r["lech"] < 1, r)
    r = pg.evaluate("""() => { const T=buildTarget(peTmp);
      return {dev:T.totalS-T.fcsS, pct:T.dtrPct,
              oT:document.getElementById('pe_devTime').value, oP:document.getElementById('pe_devPct').value}; }""")
    chk("ô PHÁT TRIỂN hiện đúng thời lượng + % của đường",
        mmss(r["oT"]) == r["dev"] and r["oP"] == str(r["pct"]), r)
    tap("devTime", "1")
    r2 = pg.evaluate("""() => { const T=buildTarget(peTmp);
      return {dev:T.totalS-T.fcsS, fcsTime:peTmp.fcsTime||null, time:peTmp.time,
              from:document.getElementById('peDevFrom').textContent,
              oT:document.getElementById('pe_devTime').value}; }""")
    # Luật chung của mọi ô giờ trong hộp: nhích một bậc 5 giây rồi BO về bội của bậc (72 → 75)
    chk("chạm + thời lượng → phát triển dài thêm một bậc 5 giây",
        r2["dev"] == round((r["dev"] + 5) / 5) * 5 and r2["dev"] > r["dev"], (r["dev"], r2))
    chk("… tổng thời gian GIỮ NGUYÊN, giờ nổ dời theo",
        r2["time"] == "12:00" and r2["fcsTime"] and mmss(r2["fcsTime"]) == 720 - r2["dev"], r2)
    chk("… ô và nhãn neo theo giờ nổ", mmss(r2["oT"]) == r2["dev"] and "giờ nổ" in r2["from"], r2)
    tap("devPct", "1")
    r3 = pg.evaluate("""() => { const T=buildTarget(peTmp);
      return {dt:peTmp.devTarget, pct:T.dtrPct, fcsTime:peTmp.fcsTime||null, time:peTmp.time,
              from:document.getElementById('peDevFrom').textContent,
              oP:document.getElementById('pe_devPct').value, oDev:document.getElementById('pe_dev').value}; }""")
    chk("chạm + % → neo theo %, bỏ giờ nổ cứng", r3["fcsTime"] is None and "%" in r3["from"], r3)
    chk("… % của đường đúng bằng số vừa đặt, ô form khớp",
        r3["pct"] == r3["dt"] and r3["oP"] == str(r3["dt"]) and r3["oDev"] == str(r3["dt"]), r3)
    chk("… tổng thời gian vẫn 12:00", r3["time"] == "12:00", r3)
    r4 = pg.evaluate("""() => { const el=document.getElementById('pe_devTime');
      el.focus(); el.value='02:00'; el.blur(); const T=buildTarget(peTmp);
      return {dev:T.totalS-T.fcsS, fcsTime:peTmp.fcsTime, o:el.value}; }""")
    chk("gõ tay thời lượng 02:00 → vào nổ 10:00", r4["dev"] == 120 and r4["fcsTime"] == "10:00", r4)

    chk("không có lỗi JS nào trong cả phiên", not errs, "; ".join(errs[:3]))
    br.close()

print()
if fails:
    print("THẤT BẠI:"); [print(" -", f) for f in fails]; sys.exit(1)
print("TẤT CẢ PASS")
