"""Bộ kiểm cho 11 phát hiện review Codex 14/09/2026 (docs/ui/2026-09-14-otl-roast-lab-review.md).

Mỗi mục dựng ĐÚNG tình huống Codex tả rồi đo hành vi, không đọc code:
  RF-01 mất kết nối giữa mẻ   → app không tự đếm/tự chốt; đóng tay = GIÁN ĐOẠN
  RF-02 lệnh xả 'queued'       → chỉ chốt khi máy báo cờ drop; không mở mẻ ma; hết hạn = băng đỏ
  RF-03 đổi hồ sơ khi chờ nạp  → huỷ lời hẹn, hiện rõ trạng thái chờ
  RF-04 tự xả gửi hỏng         → thử lại có giãn cách, trần 3 lần, băng bền
  RF-06 mở nhanh A rồi B       → hộp chỉ vẽ B; "Rang lại" không nhầm hồ sơ trùng tên
  RF-07 gói thiếu BT           → BẮT ĐẦU không ném lỗi
  RF-08 nháp kg                → lưu ghi chú không xoá số kg đang gõ; ghi chú ≤ 400
  RF-09 hộp thoại              → role/aria-modal/tên, ô có tên, tiêu điểm vào–ra, Tab xoay vòng
  RF-10 số BT viên trạng thái  → dùng mực BT chứ không dùng màu chủ đạo

Nhịp poll nền bị treo (link_snapshot không bao giờ trả) để không xen vào; mọi gói máy
đi qua feed() → dsApply() y như đường thật.
"""
import sys, pathlib
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

HTML = pathlib.Path(__file__).resolve().parent.parent / "OTL Roast Lab.html"

STUB = r"""
window.__sent=[]; window.__finish=[]; window.__begin=0; window.__writeOk=true;
window.pywebview={api:{
  link_snapshot: () => new Promise(()=>{}),
  link_write: async (n,v) => { window.__sent.push([n,v]);
    return window.__writeOk ? {ok:true,status:'queued',name:n,value:v} : {ok:false,err:'cầu nối từ chối (giả lập)'}; },
  link_begin_batch: async () => { window.__begin++; return {ok:true}; },
  link_new_batch: async () => ({ok:true}),
  db_batch_finish: async s => { window.__finish.push(s); return {ok:true,id:7}; },
  db_batch_stats: id => new Promise(r=>setTimeout(()=>r({total_sec:id*100,drop_temp:200}), id===1?700:40)),
  db_batch_curve: async () => null,
  inv_cup_list: async () => [],
  inv_cup_add: async d => ({ok:true,id:1}),
  op_log: () => null,
}};
"""

HELPERS = r"""() => {
  window.mkSnap = (o, f) => {
    const d = Object.assign({bt:200, et:210, ror_bt:5, ror_et:3, gas:30, air:60, drum:55, sv:0, vac:0,
      step:8, t_roast:400, phase:{dry:true,mai:true,dev:false}, hb:1}, o||{});
    d.flags = Object.assign({auto:false,gas:true,charge:false,drop:false,escape:false,cool:false,
      pc_control:true,flame:true,pc_lost:false,flame_fail:false,drumfan:true,mixer:false,
      afterburner:false,loader:false,destoner:false,autoloader:false}, f||{});
    return d;
  };
  window.feed = (o, f) => { dsApply({state:'connected',err:'',port:'COM9',mode:'pclink',age_ms:10,data:mkSnap(o,f)}); return R.phase; };
  window.toastTxt = () => (document.getElementById('toast')||{}).textContent||'';
  R.mileSet = {}; R.mode = 'MANUAL'; R.chargeT = 0;
}"""

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
    pg.wait_for_function("typeof dsApply==='function' && typeof finishRoast==='function'")
    pg.wait_for_timeout(300)
    pg.evaluate("session={name:'M',role:'master',perms:{}};"
                "document.getElementById('login').classList.remove('on');updateBadge();gotoTab('rang')")
    pg.evaluate(HELPERS)

    # ─────────────────────────────────────────────────────────────── RF-02
    print("RF-02) Lệnh xả 'queued' chưa phải máy đã xả — và không được mở mẻ ma")
    pg.evaluate("newRoast(); feed({step:0,t_roast:0})")
    chk("máy vào CHARGE → app mở mẻ", pg.evaluate("feed({step:6,t_roast:1})") == "RUNNING")
    pg.evaluate("feed({step:8,t_roast:300})")
    pg.evaluate("async()=>{window.__sent=[]; await cmdDrop();}")
    chk("đã gửi drop=1", pg.evaluate("window.__sent") == [["drop", 1]], pg.evaluate("window.__sent"))
    chk("vẫn RUNNING khi mới 'queued'", pg.evaluate("R.phase") == "RUNNING", pg.evaluate("R.phase"))
    chk("đang chờ máy xác nhận", pg.evaluate("!!R._dropPending"))
    pg.evaluate("async()=>{await cmdDrop();}")
    chk("bấm lần hai lúc đang chờ KHÔNG gửi gì (không lỡ ghi drop=0)",
        pg.evaluate("window.__sent.length") == 1, pg.evaluate("window.__sent"))
    chk("gói máy chưa có cờ drop → vẫn RUNNING", pg.evaluate("feed({step:8,t_roast:301},{drop:false})") == "RUNNING")
    chk("máy báo cờ drop → chốt DONE", pg.evaluate("feed({step:8,t_roast:302},{drop:true})") == "DONE")
    chk("chốt đúng 1 lần", pg.evaluate("window.__finish.length") == 1, pg.evaluate("window.__finish.length"))
    chk("mẻ chốt thường vẫn mang ✓ Mẻ hoàn tất", pg.evaluate(
        "(b=>!b.classList.contains('intr')&&getComputedStyle(b.querySelector('.rd-intr')).display==='none')"
        "(document.querySelector('.rd-badge'))"))
    begin0 = pg.evaluate("window.__begin")
    chk("progStep còn trong dải rang (cờ trễ) → KHÔNG mở mẻ ma",
        pg.evaluate("feed({step:8,t_roast:303},{drop:true})") == "DONE" and pg.evaluate("window.__begin") == begin0,
        f"phase={pg.evaluate('R.phase')} begin={pg.evaluate('window.__begin')}")
    pg.evaluate("feed({step:11,t_roast:303})")
    chk("máy rời dải rồi vào CHARGE lại → mở mẻ mới bình thường",
        pg.evaluate("feed({step:6,t_roast:1})") == "RUNNING" and pg.evaluate("window.__begin") == begin0 + 1)
    pg.evaluate("feed({step:8,t_roast:50})")
    pg.evaluate("async()=>{delete BTN_HOLD.drop; window.__sent=[]; await cmdDrop(); R._dropPending.t0 -= 11000;}")
    chk("quá hạn không thấy cờ drop → mẻ VẪN MỞ", pg.evaluate("feed({step:8,t_roast:51},{drop:false})") == "RUNNING")
    chk("hết chờ + có cảnh báo", pg.evaluate("!R._dropPending && !!R._dropAlert"))
    chk("băng đỏ hiện 'CHƯA ĂN'", pg.evaluate(
        "document.getElementById('faultBanner').classList.contains('show') && "
        "document.getElementById('faultMsg').textContent.includes('CHƯA ĂN')"),
        pg.evaluate("document.getElementById('faultMsg').textContent"))

    # ─────────────────────────────────────────────────────────────── RF-01
    print("RF-01) Mất kết nối giữa mẻ — không tự đếm, không tự chốt")
    pg.evaluate("feed({step:8,t_roast:630},{drop:false}); R._dropAlert=null; ROAST_SECS=640; window.__finish=[];")
    pg.evaluate("DS.state='error'; DS.snap=null; for(let i=0;i<40;i++) roastTick(); faultCheck(null);")
    chk("vẫn RUNNING sau 40 nhịp", pg.evaluate("R.phase") == "RUNNING", pg.evaluate("R.phase"))
    chk("đồng hồ đứng ở mốc cuối máy báo (630)", pg.evaluate("R.elapsed") == 630, pg.evaluate("R.elapsed"))
    chk("không chốt bản ghi nào", pg.evaluate("window.__finish.length") == 0)
    chk("băng mất kết nối nói rõ app KHÔNG tự chốt",
        "KHÔNG tự chốt" in pg.evaluate("document.getElementById('faultMsg').textContent"),
        pg.evaluate("document.getElementById('faultMsg').textContent"))
    # bắn rồi quên: cmdDrop đứng chờ hộp hỏi, evaluate mà đợi promise đó là treo bài kiểm
    pg.evaluate("() => { window.__sent=[]; cmdDrop(); }")
    pg.wait_for_function("document.getElementById('askbox').classList.contains('on')")
    pg.click("#askYes")
    pg.wait_for_function("R.phase==='DONE'")
    chk("mất kết nối → KHÔNG gửi lệnh xả nào", pg.evaluate("window.__sent.length") == 0, pg.evaluate("window.__sent"))
    chk("đóng tay → bản ghi GIÁN ĐOẠN", pg.evaluate("window.__finish.at(-1).interrupted") is True)
    chk("tiêu đề tổng kết là '⚡ Mẻ gián đoạn', không mang ✓ hoàn tất", pg.evaluate(
        "(b=>b.classList.contains('intr')&&getComputedStyle(b.querySelector('.rd-ok')).display==='none'"
        "&&getComputedStyle(b.querySelector('.rd-intr')).display!=='none'"
        "&&b.querySelector('.rd-intr').textContent.includes('gián đoạn'))(document.querySelector('.rd-badge'))"))
    chk("mẻ gián đoạn không cho làm hồ sơ chuẩn",
        pg.evaluate("document.getElementById('uxDoneBaseline').disabled") is True)
    # mô phỏng (không phải mẻ máy thật) vẫn tự chốt khi hết curve — không phá chế độ demo
    pg.evaluate("newRoast(); R.phase='RUNNING'; R._liveBatch=false; R.elapsed=638; ROAST_SECS=640; "
                "DS.state='nobridge'; roastTick(); roastTick(); roastTick();")
    chk("mẻ mô phỏng vẫn tự chốt khi hết curve", pg.evaluate("R.phase") == "DONE", pg.evaluate("R.phase"))
    # nối lại mà đồng hồ máy lùi = máy đã sang mẻ khác
    pg.evaluate("newRoast(); feed({step:0,t_roast:0}); feed({step:6,t_roast:1}); feed({step:8,t_roast:420}); "
                "window.__finish=[]; R._linkLostAt=Date.now()-8000;")
    pg.evaluate("feed({step:7,t_roast:30})")
    chk("đồng hồ máy lùi sau mất kết nối → mẻ cũ đóng GIÁN ĐOẠN",
        pg.evaluate("window.__finish.length===1 && window.__finish[0].interrupted===true"),
        pg.evaluate("window.__finish"))
    chk("…và bám mẻ mới của máy", pg.evaluate("R.phase") == "RUNNING")

    # ─────────────────────────────────────────────────────────────── RF-04
    print("RF-04) Tự xả gửi hỏng — thử lại có giãn cách, có trần, có băng")
    pg.evaluate("feed({step:8,t_roast:500,bt:150}); R.mileSet={DROP:195}; R._dropFired=false; R._dropRetryAt=0;"
                "R._dropFails=0; R._dropAlert=null; window.__writeOk=false; window.__sent=[];")
    pg.evaluate("checkMileSets(200)")
    pg.wait_for_timeout(150)
    chk("lần 1 hỏng → trả cờ cho lần sau", pg.evaluate("R._dropFired") is False)
    chk("có giãn cách trước lần thử lại", pg.evaluate("R._dropRetryAt>Date.now()"))
    chk("băng ghi lần 1/3", "1/3" in (pg.evaluate("R._dropAlert&&R._dropAlert.vi") or ""), pg.evaluate("R._dropAlert"))
    pg.evaluate("checkMileSets(200)")
    pg.wait_for_timeout(100)
    chk("trong lúc giãn cách KHÔNG bắn lại", pg.evaluate("window.__sent.length") == 1, pg.evaluate("window.__sent"))
    for _ in range(4):
        pg.evaluate("R._dropRetryAt=0; checkMileSets(200)")
        pg.wait_for_timeout(120)
    chk("trần 3 lần gửi", pg.evaluate("window.__sent.length") == 3, pg.evaluate("window.__sent"))
    chk("hết lượt → cờ giữ true, băng 'HỎNG 3 LẦN'",
        pg.evaluate("R._dropFired===true && R._dropAlert.vi.includes('HỎNG 3 LẦN')"), pg.evaluate("R._dropAlert"))
    chk("mẻ vẫn RUNNING", pg.evaluate("R.phase") == "RUNNING")
    pg.evaluate("window.__writeOk=true; R.mileSet={}; R._dropAlert=null;")

    # ─────────────────────────────────────────────────────────────── RF-03 + RF-07
    print("RF-03) Đổi hồ sơ phải huỷ chờ tự nạp của hồ sơ trước")
    pg.evaluate("""() => { saveProfiles([
        {name:'Hồ sơ A', chargeT:200, temp:210, time:'12:00'},
        {name:'Hồ sơ B', chargeT:190, temp:205, time:'11:00'},
        {name:'Hồ sơ A', chargeT:185, temp:200, time:'10:30'}]);
      newRoast(); window.__sent=[]; loadProfile(0); feed({step:0,t_roast:0,bt:100}); R._machRun=false;
      startRoast();   /* không return promise — nó đứng chờ hộp hỏi */ }""")
    pg.wait_for_function("document.getElementById('askbox').classList.contains('on')")
    pg.click("#askNo")
    chk("chọn Chờ → có lời hẹn gắn hồ sơ A tại 200°",
        pg.evaluate("R._autoCharge&&R._autoCharge.name==='Hồ sơ A'&&R._autoCharge.t===200"), pg.evaluate("R._autoCharge"))
    chk("dòng 'Đang chờ TỰ NẠP' hiện trên màn chờ",
        pg.evaluate("(e=>e&&!e.hidden&&e.textContent.includes('TỰ NẠP'))(document.getElementById('riAutoCharge'))"))
    pg.evaluate("loadProfile(1)")
    chk("đổi sang hồ sơ B → lời hẹn bị huỷ", pg.evaluate("R._autoCharge") is False)
    chk("dòng chờ ẩn đi", pg.evaluate("document.getElementById('riAutoCharge').hidden") is True)
    pg.evaluate("chkChargeReady(260)")
    chk("tới nhiệt hồ sơ B KHÔNG tự nạp", not any(s[0] == "charge" for s in pg.evaluate("window.__sent")),
        pg.evaluate("window.__sent"))
    pg.evaluate("R._chargeReady=false; R._autoCharge={no:1,name:'Hồ sơ A',t:190}; chkChargeReady(260)")
    chk("lưới thứ hai: lời hẹn lệch hồ sơ đang nạp → không nạp",
        not any(s[0] == "charge" for s in pg.evaluate("window.__sent")), pg.evaluate("window.__sent"))

    print("RF-07) Gói máy thiếu BT — BẮT ĐẦU không được ném lỗi")
    n_err = len(errs)
    pg.evaluate("R._machRun=false; R._autoCharge=false; DS.state='connected'; DS.mode='pclink';"
                "DS.snap={flags:{pc_control:true,flame:true,gas:true}}; startRoast();")
    pg.wait_for_timeout(150)
    chk("không lỗi JS", len(errs) == n_err, errs[n_err:])
    chk("không bật hộp hỏi", pg.evaluate("document.getElementById('askbox').classList.contains('on')") is False)
    chk("báo đang chờ số BT", "BT" in pg.evaluate("toastTxt()"), pg.evaluate("toastTxt()"))

    # ─────────────────────────────────────────────────────────────── RF-06
    print("RF-06) Mở nhanh A rồi B; Rang lại với hồ sơ trùng tên")
    pg.evaluate("openBatch(1); openBatch(2);")
    pg.wait_for_timeout(1000)
    chk("tiêu đề là mẻ B", pg.evaluate("document.getElementById('bdTitle').textContent") == "#2")
    st = pg.evaluate("document.getElementById('bdStats').textContent")
    chk("số liệu là của B (03:20), không bị A (01:40) đè", "03:20" in st and "01:40" not in st, st)
    pg.evaluate("closeBatch()")
    chk("cặp (số, tên) khớp → đúng hồ sơ số 3",
        pg.evaluate("uxProfileForBatch({prof_name:'Hồ sơ A',prof_no:3}).idx") == 2)
    chk("tên trùng mà số lệch → MƠ HỒ, bắt thợ chọn",
        pg.evaluate("uxProfileForBatch({prof_name:'Hồ sơ A',prof_no:2}).ambiguous") == 2)
    chk("tên duy nhất dù số lệch → vẫn tìm ra",
        pg.evaluate("uxProfileForBatch({prof_name:'Hồ sơ B',prof_no:9}).idx") == 1)
    pg.evaluate("newRoast(); loadProfile(1); uxRoastAgain(uxProfileForBatch({prof_name:'Hồ sơ A',prof_no:2}))")
    chk("Rang lại mơ hồ → KHÔNG tự nạp hồ sơ nào", pg.evaluate("R.profName") == "Hồ sơ B", pg.evaluate("R.profName"))

    # ─────────────────────────────────────────────────────────────── RF-08
    print("RF-08) Lưu ghi chú không được xoá số kg đang gõ dở")
    pg.evaluate("newRoast(); feed({step:0,t_roast:0}); feed({step:6,t_roast:1}); feed({step:8,t_roast:200}); "
                "async()=>{}")
    pg.evaluate("async()=>{ delete BTN_HOLD.drop; await cmdDrop(); feed({step:8,t_roast:201},{drop:true}); }")
    pg.wait_for_function("UX.completed && UX.completed.id===7")
    pg.evaluate("""async()=>{ const k=document.getElementById('uxDoneKg');
        k.value='3.5'; k.dispatchEvent(new Event('input'));
        document.getElementById('uxDoneNote').value='ngọt hậu';
        document.getElementById('uxDoneSaveNote').focus();
        await uxDoneNoteSave(); }""")
    chk("số kg nháp còn nguyên sau khi lưu ghi chú",
        pg.evaluate("document.getElementById('uxDoneKg').value") == "3.5", pg.evaluate("document.getElementById('uxDoneKg').value"))
    chk("ô ghi chú giới hạn 400 (khớp kho)", pg.evaluate("document.getElementById('uxDoneNote').maxLength") == 400)

    # ─────────────────────────────────────────────────────────────── RF-09
    print("RF-09) Hộp thoại có vai trò/tên, ô có tên, tiêu điểm vào–ra, Tab xoay vòng")
    r = pg.evaluate("""() => {
      const bo=new Set(['numpad','keyboard','picker']);
      const thieu=[...document.querySelectorAll('.overlay')].filter(o=>!bo.has(o.id)).filter(o=>{
        const h=o.querySelector('[role=dialog],[role=alertdialog]');
        return !(h && h.getAttribute('aria-modal')==='true');}).map(o=>o.id);
      const hop=document.querySelector('#profedit [role=dialog]');
      const ten=hop&&document.getElementById(hop.getAttribute('aria-labelledby')||'');
      const vo=[...document.querySelectorAll('#profedit input.peval,#napedit input.peval')].filter(i=>{
        const ids=(i.getAttribute('aria-labelledby')||'').split(' ').filter(Boolean);
        return !ids.length||!ids.every(x=>document.getElementById(x));}).map(i=>i.id);
      const de=document.getElementById(document.getElementById('pe_deT').getAttribute('aria-labelledby'));
      return {thieu, ten: ten&&ten.textContent, vo, de: de&&de.textContent};
    }""")
    chk("mọi hộp .overlay có role dialog + aria-modal", not r["thieu"], r["thieu"])
    chk("hộp Sửa hồ sơ có tên 'Sửa hồ sơ'", r["ten"] == "Sửa hồ sơ", r["ten"])
    chk("mọi ô nhập hồ sơ/công thức có tên", not r["vo"], r["vo"])
    chk("ô Nhiệt DE đọc ra đúng nhãn", "Nhiệt DE" in (r["de"] or ""), r["de"])
    pg.evaluate("""() => { const b=document.createElement('button'); b.id='t9ve'; b.textContent='x';
      document.body.appendChild(b); b.focus(); document.getElementById('profedit').classList.add('on'); }""")
    pg.wait_for_timeout(250)
    chk("mở hộp → tiêu điểm vào trong hộp",
        pg.evaluate("document.getElementById('profedit').contains(document.activeElement)"),
        pg.evaluate("document.activeElement&&document.activeElement.id"))
    pg.evaluate("""() => { const o=document.getElementById('profedit');
      const ds=[...o.querySelectorAll('button,[href],input,select,textarea,[tabindex]')]
        .filter(el=>!el.disabled&&el.getAttribute('tabindex')!=='-1'&&el.getClientRects().length);
      window.__dau=ds[0]; ds[ds.length-1].focus(); }""")
    pg.keyboard.press("Tab")
    chk("Tab ở ô cuối → quay về ô đầu, không lọt ra nền app",
        pg.evaluate("document.activeElement===window.__dau"),
        pg.evaluate("document.activeElement&&(document.activeElement.id||document.activeElement.className)"))
    pg.evaluate("closeProfEdit()")
    pg.wait_for_timeout(200)
    chk("đóng hộp → tiêu điểm trả về chỗ cũ", pg.evaluate("document.activeElement&&document.activeElement.id") == "t9ve",
        pg.evaluate("document.activeElement&&document.activeElement.id"))

    # ─────────────────────────────────────────────────────────────── RF-10
    print("RF-10) Số BT trên viên trạng thái đọc được trên nền tối cố định của viên")
    # Viên có nền #15171c ở CẢ HAI theme → số BT phải là cam sáng #f58a35 (~7,5:1), không đi
    # theo token theme (theme sáng là cam đậm #b65010 → chỉ 3,54:1 trên nền tối).
    r10 = pg.evaluate("""() => { const pill=document.getElementById('batchPill'); if(!pill) return null;
      let e=pill.querySelector('.bp-bt'); if(!e){e=document.createElement('span');e.className='bp-bt';pill.appendChild(e);}
      return [getComputedStyle(e).color, getComputedStyle(pill).backgroundColor]; }""")
    chk("số BT cam sáng trên nền tối của viên", bool(r10) and r10[0] == "rgb(245, 138, 53)"
        and r10[1] == "rgb(21, 23, 28)", r10)

    chk("0 lỗi JS toàn bài", not errs, errs[:3])
    br.close()

print("\n" + ("TẤT CẢ ĐẠT" if not fails else f"{len(fails)} MỤC HỎNG: {fails}"))
sys.exit(1 if fails else 0)
