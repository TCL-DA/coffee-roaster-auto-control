"""Tự xả theo ngưỡng nhiệt — hai chốt an toàn dễ vỡ nhất của luồng mẻ.

1) autoDrop() phải GHI THẲNG drop=1. cmdDrop() là toggle cho ngón tay thợ: nếu cửa xả
   đã mở bởi tác nhân khác (firmware tự xả chế độ AUTO, hoặc thợ bấm HMI 1-2s trước)
   thì toggle tính ra 0 → ĐÓNG CỬA XẢ NON, hạt còn trong trống.
2) Ngưỡng xả KHÔNG được gác theo mốc TP. Ở pclink mốc TP suy từ progStep=7, nên khi
   firmware kẹt ở STP_TP (rủi ro R2) mà app cũng gác theo TP là mất cả hai lớp cùng lúc.
"""
import sys, pathlib
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

HTML = pathlib.Path(__file__).resolve().parent.parent / "OTL Roast Lab.html"

STUB = """
window.__sent = [];
window.pywebview = { api: {
  link_write: async (name, v) => { window.__sent.push([name, v]); return {ok:true}; },
  link_snapshot: async () => ({state:'connected', err:'', port:'COM9', mode:'pclink', age_ms:10,
    data:{bt:200.0, et:210.0, ror_bt:0, ror_et:0, gas:30, air:80, drum:55, sv:0, vac:0,
      step:6, t_roast:400, phase:{dry:true,mai:false,dev:false},
      flags:{auto:false, gas:true, charge:false, drop:window.__dropOpen||false,
             escape:false, cool:false, pc_control:true, flame:true, pc_lost:false,
             flame_fail:false, drumfan:true, mixer:false, afterburner:false,
             loader:false, destoner:false, autoloader:false}, hb:1}}),
}};
"""


def boot(pg, drop_open):
    pg.add_init_script(f"window.__dropOpen = {'true' if drop_open else 'false'};" + STUB)
    pg.goto(HTML.as_uri())
    pg.wait_for_function("typeof autoDrop === 'function' && typeof checkMileSets === 'function'")
    # dựng đúng tình huống: đang trong mẻ, ngưỡng xả 195°, mốc TP CHƯA chấm (firmware kẹt TP)
    pg.evaluate("""() => {
      R.phase = 'RUNNING'; R._machRun = true; R.elapsed = 400;
      R.mileT = {}; R.mileD = {}; R._dropFired = false;
      R.mileSet = {DROP: 195};
      DS.state = 'connected'; DS.mode = 'pclink';
      DS.snap = {bt:200.0, step:6, t_roast:400, flags:{drop: !!window.__dropOpen,
                 pc_control:true, flame:true, gas:true}};
      window.__sent = [];
    }""")


def sent_drop(pg):
    return pg.evaluate("() => window.__sent.filter(x => x[0] === 'drop').map(x => x[1])")


fails = []
with sync_playwright() as p:
    br = p.chromium.launch()

    print("1) Firmware kẹt ở TP (mốc TP chưa chấm) — ngưỡng xả VẪN phải nổ")
    pg = br.new_page()
    boot(pg, drop_open=False)
    pg.evaluate("() => checkMileSets(200.0)")
    pg.wait_for_timeout(300)
    got = sent_drop(pg)
    if got == [1]:
        print("   OK — app ghi drop=1 dù chưa có mốc TP")
    else:
        fails.append(f"kẹt TP: mong [1], nhận {got}")
        print(f"   FAIL — mong [1], nhận {got}")
    pg.close()

    print("2) Cửa xả ĐÃ mở sẵn — tuyệt đối KHÔNG được ghi drop=0")
    pg = br.new_page()
    boot(pg, drop_open=True)
    pg.evaluate("() => checkMileSets(200.0)")
    pg.wait_for_timeout(300)
    got = sent_drop(pg)
    if 0 in got:
        fails.append(f"đóng cửa xả non: nhận {got}")
        print(f"   FAIL — app ghi drop=0, xi lanh sập non! ({got})")
    else:
        print(f"   OK — không lệnh nào đóng cửa xả ({got or 'không gửi gì'})")
    # mẻ vẫn phải được chốt dù không gửi lệnh
    ph = pg.evaluate("() => R.phase")
    if ph == 'DONE':
        print("   OK — mẻ đã được chốt (phase DONE)")
    else:
        fails.append(f"mẻ không chốt: phase={ph}")
        print(f"   FAIL — mẻ chưa chốt, phase={ph}")
    pg.close()
    br.close()

print()
if fails:
    print("THẤT BẠI:"); [print(" -", f) for f in fails]; sys.exit(1)
print("TẤT CẢ PASS")
