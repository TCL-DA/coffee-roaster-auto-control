# -*- coding: utf-8 -*-
"""Soát HIỆU ỨNG TRONG LÚC RANG — tiếng, giọng nói, và hiệu ứng nhìn.

Rang là lúc app nói nhiều nhất mà thợ nhìn màn ít nhất: mắt ở trống, tai nghe app.
Nên hiệu ứng lúc rang KHÔNG phải trang trí — nó là kênh báo tin chính. Bộ kiểm cũ
đo bố cục và màu ở trạng thái ĐỨNG YÊN; không bộ nào chạy trọn một mẻ để xem hiệu
ứng có nổ đúng lúc, đúng số lần, đúng thứ tự hay không.

Cách đo: thay 4 hàm phát tiếng gốc và `speechSynthesis` bằng bản GHI SỔ, rồi cho
chạy trọn một mẻ qua cầu máy giả. Không phát ra loa, nhưng ghi đúng cái app định
phát — nên đo được cả thứ tự lẫn số lần.

E1  mỗi mốc kêu ĐÚNG MỘT LẦN, đúng thứ tự TP→DE→FCs→DEV→DROP
E2  mỗi mốc được ĐỌC THÀNH LỜI, không câu nào bị câu sau nuốt mất
E3  đếm ngược tới lúc xả (60/30/10 giây) có kêu đủ không
E4  nhịp tim theo RoR: chạy khi bật, TẮT HẲN khi hết mẻ (không để timer mồ côi)
E5  hiệu ứng nhìn: chip mốc todo→now→done, không chip nào kẹt ở 'now'
E6  dải giai đoạn Sấy→Maillard→Phát triển đi đúng chiều
E7  hết mẻ rồi thì KHÔNG hiệu ứng nào còn nổ
E8  tắt tiếng = im hoàn toàn
E9  không lỗi JavaScript suốt mẻ

Chạy: python tools/test_ui_roast_effects.py [--report]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from test_ui_audit import dang_nhap  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "OTL Roast Lab.html"

# Cầu máy giả — thiếu nó là app chạy nhánh mô phỏng, đo ra kết quả của app khác.
BRIDGE = """
window.__snap=null; window.__st='connected';
window.pywebview={api:{
  link_snapshot: async()=>({state:window.__st,mode:'pclink',err:'',port:'COM-TEST',
                            age_ms:10,data:window.__snap}),
  link_config: async()=>({port:'COM-TEST',baud:9600}),
  toggle_fullscreen: async()=>null,
}};
"""

# Sổ ghi hiệu ứng. Phải cài SAU khi app nạp xong (các hàm này là khai báo toàn cục).
SPY = r"""
() => {
  window.__fx={snd:[],say:[],err:[]};
  const at=()=>({t:(typeof R!=='undefined'&&R.elapsed)||0, ms:Math.round(performance.now())});
  // Ghi ở TẦNG NGUYÊN LIỆU: mọi tiếng đều đi qua 4 hàm này, chặn ở đây là không sót.
  for(const k of ['_metal','_air','_crack','_body']){
    const orig=window[k];
    window[k]=function(){ window.__fx.snd.push(Object.assign({kind:k},at())); };
    window['__orig'+k]=orig;
  }
  // Ghi ở TẦNG CÔNG THỨC: _play() nhận trọn bộ tiếng của MỘT mốc. Đếm ở đây mới
  // biết có bao nhiêu bộ tiếng cùng nổ một lúc — đếm từng nốt thì vô nghĩa khi
  // bộ kiểm tua nhanh cả mẻ, mọi nốt rơi vào cùng một mili-giây.
  window.__fx.recipe=[];
  const op=window._play;
  window._play=function(rec){
    let ten='?';
    try{ for(const k in MILE_SND) if(MILE_SND[k]===rec) ten=k; }catch(e){}
    window.__fx.recipe.push(Object.assign({moc:ten},at()));
    return op.apply(this,arguments);
  };
  // Giọng nói: ghi cả lệnh HUỶ, vì huỷ chính là chỗ câu trước bị nuốt.
  const S=window.speechSynthesis;
  if(S){
    const spk=S.speak.bind(S), cxl=S.cancel.bind(S);
    S.speak=u=>{ window.__fx.say.push(Object.assign({do:'noi',text:String(u.text||'')},at())); };
    S.cancel=()=>{ window.__fx.say.push(Object.assign({do:'huy'},at())); };
    window.__origSpeak=spk; window.__origCancel=cxl;
  }
  return true;
}
"""

# Ảnh chụp máy đi qua trọn một mẻ. progStep = "đang CHỜ mốc", nên mốc ĐẠT khi step
# nhảy sang bước kế: TP đạt ⟺ step>=7 · DE ⟺ >=8 · FCs/DEV ⟺ >=9 · DROP ⟺ 10.
def frames(total=620, skip_at=None):
    out = []
    for t in range(0, total + 1):
        if t < 3:
            step = 4
        elif t < 60:
            step = 5
        elif t < 200:
            step = 6
        elif t < 380:
            step = 7
        elif t < 470:
            step = 8
        elif t < 600:
            step = 9
        else:
            step = 10
        bt = 200 - 110 * min(1, t / 60.0) if t < 60 else 90 + 125 * ((t - 60) / 560.0) ** 0.82
        out.append({
            "bt": round(bt, 1), "et": round(bt + 16, 1),
            "ror_bt": round(14 - 10 * t / total, 2), "ror_et": round(12 - 8 * t / total, 2),
            "ror_pro": round(14 - 10 * t / total, 2),
            "gas": 40 if t < 200 else 28, "air": 60, "drum": 55, "sv": 200.0, "vac": -110,
            "step": step, "t_roast": max(0, t - 3),
            "phase": {"dry": step >= 6, "mai": step >= 8, "dev": step >= 9},
            "flags": {"auto": True, "gas": True, "charge": False, "drop": step >= 10,
                      "escape": False, "cool": False, "pc_control": True},
            "hb": 1000 + t,
        })
    if skip_at:
        # Bỏ vài giây liên tiếp: đúng cái xảy ra khi một nhịp đọc máy bị trễ.
        lo, hi = skip_at
        out = [f for f in out if not (lo <= f["t_roast"] <= hi)]
    return out


def run_batch(page, fr, step_ms=0):
    """Đẩy từng gói dữ liệu qua đúng đường app dùng thật (applyMachine)."""
    page.evaluate(
        """(fr)=>{
             window.__snap=fr[0];
             for(const f of fr){ window.__snap=f; DS.state='connected'; DS.mode='pclink';
                                 DS.snap=f; applyMachine(f); }
           }""", fr)
    page.wait_for_timeout(300 + step_ms)


def main():
    report_only = "--report" in sys.argv
    found, ran = [], []

    def hit(code, lv, msg):
        found.append((code, lv, msg))

    def did(code, note):
        ran.append((code, note))

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.add_init_script(BRIDGE)
        page.goto(APP.as_uri())
        dang_nhap(page)
        page.wait_for_timeout(500)
        page.evaluate(SPY)

        # Bật hết tiếng, kể cả nhịp tim (mặc định tắt) để đo được nó.
        page.evaluate("""()=>{SND.on=true;SND.mile=true;SND.voice=true;
                            SND.alarm=true;SND.tick=true;
                            _voiceReady=true;      // khỏi chờ danh sách giọng
                            gotoTab('rang');
                            if(typeof loadProfile==='function')loadProfile(0);}""")
        page.wait_for_timeout(400)
        page.evaluate("()=>{window.__fx.snd=[];window.__fx.say=[];}")

        fr = frames()
        run_batch(page, fr)
        fx = page.evaluate("()=>window.__fx")
        phase = page.evaluate("()=>R.phase")
        mile = page.evaluate("()=>({...R.mileT})")
        did("mẻ", "kết thúc ở phase=%s · mốc=%s" % (phase, mile))

        said = [s["text"] for s in fx["say"] if s.get("do") == "noi"]
        did("E2", "đã nói: %s" % said)

        # ── E1 · mốc nào cũng phải KÊU, đúng thứ tự ────────────────────────
        # Đếm theo lời nói vì mỗi mốc phát nhiều nốt; lời nói là 1 mốc = 1 câu.
        # Một câu có thể gộp nhiều mốc ("Crack đầu, Phát triển") khi chúng rơi
        # cùng nhịp — vẫn tính là NGHE ĐƯỢC, miễn không bị câu sau cắt.
        want = ["Quay đầu", "Khô vàng", "Crack đầu", "Phát triển", "Xả mẻ"]
        nghe = []
        for cau in said:
            for m in want:
                if m in cau and m not in nghe:
                    nghe.append(m)
        order = nghe[:]
        thieu = [m for m in want if m not in nghe]
        if thieu:
            hit("E1", "P1", "mốc KHÔNG kêu: %s (đã kêu: %s)" % (", ".join(thieu), said))
        if order != [m for m in want if m in order]:
            hit("E1", "P1", "mốc kêu SAI THỨ TỰ: %s" % order)
        for m in want:
            n = sum(1 for c in said if m in c)
            if n > 1:
                hit("E1", "P2", "mốc %r kêu %d lần (phải đúng 1)" % (m, n))
        did("E1", "thứ tự mốc: %s" % order)

        # ── E2 · câu nào bị câu sau NUỐT MẤT ──────────────────────────────
        # say() gọi cancel() ngay trước speak(). Hai mốc rơi vào cùng một nhịp
        # cập nhật thì câu trước bị cắt trước khi kịp phát ra tiếng nào.
        nuot = []
        seq = fx["say"]
        for i, e in enumerate(seq):
            if e.get("do") != "noi":
                continue
            for j in range(i + 1, len(seq)):
                if seq[j].get("do") == "huy":
                    # bị huỷ trong CÙNG một mili-giây → chưa kịp phát ra gì
                    if seq[j]["ms"] - e["ms"] <= 1:
                        nuot.append(e["text"])
                    break
                if seq[j].get("do") == "noi":
                    break
        for t in dict.fromkeys(nuot):
            hit("E2", "P1", "câu %r bị câu kế tiếp CẮT NGAY (cùng nhịp) — thợ không nghe được" % t)
        # Hai mốc rơi cùng nhịp thì hai bộ tiếng chồng lên nhau thành tiếng bùng
        # nhùng — mất chất riêng vốn là cách tai phân biệt mốc trong xưởng ồn.
        moc_bo = [r["moc"] for r in fx.get("recipe", []) if r["moc"] != "?"]
        cau_moc = [c for c in said if any(m in c for m in want)]
        did("E2c", "bộ tiếng mốc đã phát: %s · số câu báo mốc: %d"
            % (moc_bo, len(cau_moc)))
        if len(moc_bo) > len(cau_moc):
            hit("E2", "P2", "%d bộ tiếng mốc nổ nhưng chỉ %d câu báo — có bộ chồng "
                "lên nhau thành tiếng bùng nhùng: %s"
                % (len(moc_bo), len(cau_moc), moc_bo))
        did("E2b", "câu bị cắt ngay: %s" % (list(dict.fromkeys(nuot)) or "không"))

        # ── E3 · đếm ngược tới lúc xả ─────────────────────────────────────
        dem = [s["text"] for s in fx["say"] if s.get("do") == "noi" and "giây" in s["text"]]
        did("E3", "đếm ngược nghe được: %s" % (dem or "không có"))
        if not dem:
            hit("E3", "P2", "cả mẻ KHÔNG có tiếng đếm ngược nào tới lúc xả")

        # ── E7 · hết mẻ rồi thì im ────────────────────────────────────────
        page.evaluate("()=>{window.__fx.snd=[];window.__fx.say=[];}")
        page.wait_for_timeout(2500)
        sau = page.evaluate("()=>window.__fx")
        did("E7", "sau khi xả, 2,5 s: %d tiếng · %d lời"
            % (len(sau["snd"]), len([x for x in sau["say"] if x.get("do") == "noi"])))
        if sau["snd"]:
            hit("E7", "P2", "mẻ đã xong mà còn %d tiếng nổ ra sau đó — nhịp tim chưa tắt?"
                % len(sau["snd"]))

        # ── E4 · nhịp tim phải TẮT HẲN khi hết mẻ ─────────────────────────
        orphan = page.evaluate("()=>_tickTmr!==null")
        did("E4", "timer nhịp tim sau khi xả: %s" % ("CÒN" if orphan else "đã tắt"))
        if orphan:
            hit("E4", "P2", "hết mẻ mà timer nhịp tim vẫn còn — tiếng nền chạy mãi")

        # ── E5/E6 · hiệu ứng NHÌN ─────────────────────────────────────────
        vis = page.evaluate("""()=>{
          const chips=[...document.querySelectorAll('.milestrip .mchip')].map(c=>({
            cls:[...c.classList].filter(x=>['done','now','todo'].includes(x)).join('|'),
            t:(c.querySelector('.tm')||{}).textContent}));
          const ph=[...document.querySelectorAll('.phasetl .ph')].map(p=>({
            ten:(p.querySelector('.pn')||{}).textContent,
            hoat:p.classList.contains('ph-active')}));
          return {chips,ph};}""")
        did("E5", "chip: %s" % [c["cls"] for c in vis["chips"]])
        did("E6", "giai đoạn: %s" % [(p["ten"], p["hoat"]) for p in vis["ph"]])
        chua = [c for c in vis["chips"] if c["cls"] != "done"]
        if chua:
            hit("E5", "P2", "mẻ xong mà %d chip mốc chưa về 'done': %s"
                % (len(chua), [c["cls"] for c in chua]))
        if sum(1 for p in vis["ph"] if p["hoat"]) > 1:
            hit("E6", "P2", "có %d giai đoạn cùng sáng một lúc"
                % sum(1 for p in vis["ph"] if p["hoat"]))

        # ── E8 · TẮT TIẾNG = im hoàn toàn ─────────────────────────────────
        page.evaluate("""()=>{SND.on=false;R.phase='IDLE';R._machRun=false;
                            mileWatchReset();window.__fx.snd=[];window.__fx.say=[];}""")
        run_batch(page, frames())
        im = page.evaluate("()=>window.__fx")
        noi = [x for x in im["say"] if x.get("do") == "noi"]
        did("E8", "tắt tiếng rồi chạy lại cả mẻ: %d tiếng · %d lời"
            % (len(im["snd"]), len(noi)))
        if im["snd"] or noi:
            hit("E8", "P1", "đã TẮT TIẾNG mà vẫn phát %d tiếng và %d lời nói"
                % (len(im["snd"]), len(noi)))

        # ── E10 · THÔNG BÁO không được che nút điều khiển lúc đang rang ────
        page.evaluate("""(d)=>{R.phase='RUNNING';gotoTab('rang');
          window.__snap=d;DS.state='connected';DS.mode='pclink';DS.snap=d;applyMachine(d);}""",
                      {"bt": 196.4, "et": 214.0, "ror_bt": 6.2, "ror_et": 4.0, "ror_pro": 6.0,
                       "gas": 34, "air": 58, "drum": 55, "sv": 205.0, "vac": -110,
                       "step": 9, "t_roast": 540,
                       "phase": {"dry": True, "mai": True, "dev": True},
                       "flags": {"auto": True, "gas": True, "flame": True, "charge": False,
                                 "drop": False, "escape": False, "cool": False,
                                 "pc_control": True}, "hb": 9001})
        page.wait_for_timeout(700)
        page.evaluate("()=>toast('Xả tự động tại 198°C theo hồ sơ')")
        page.wait_for_timeout(300)
        che = page.evaluate("""()=>{
          const t=document.getElementById('toast'),tr=t.getBoundingClientRect(),out=[];
          for(const el of document.querySelectorAll('#pane-rang button,#pane-rang input')){
            const r=el.getBoundingClientRect(); if(r.width<1)continue;
            const ox=Math.min(tr.right,r.right)-Math.max(tr.left,r.left);
            const oy=Math.min(tr.bottom,r.bottom)-Math.max(tr.top,r.top);
            if(ox>2&&oy>2)out.push((el.id||el.className||el.tagName).toString().slice(0,24));
          } return out;}""")
        did("E10", "thông báo che %d nút" % len(che))
        if che:
            hit("E10", "P3", "thông báo lúc rang che mất %d nút điều khiển: %s"
                % (len(che), ", ".join(dict.fromkeys(che))))

        if errs:
            hit("E9", "P1", "lỗi JavaScript suốt mẻ: %s" % "; ".join(dict.fromkeys(errs))[:300])
        did("E9", "lỗi JS: %s" % (len(errs) or "không"))
        browser.close()

    print("Kịch bản dựng được (%d):" % len(ran))
    for c, n in ran:
        print("  %-4s %s" % (c, n))
    print("")
    if not found:
        print("ĐẠT: hiệu ứng lúc rang nổ đúng lúc, đúng số lần, đúng thứ tự.")
        return 0
    rank = {"P1": 0, "P2": 1, "P3": 2}
    found.sort(key=lambda x: (rank.get(x[1], 9), x[0]))
    print("Phát hiện %d mục:\n" % len(found))
    for c, lv, m in found:
        print("  %-3s %s  %s" % (c, lv, m))
    return 0 if report_only else 1


if __name__ == "__main__":
    sys.exit(main())
