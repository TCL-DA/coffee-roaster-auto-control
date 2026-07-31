"""Bộ tính RoR của app — đối chiếu với công thức Artisan.

Dựng chuỗi BT/ET tăng ĐÚNG 0.5 °C/giây = 30 °C/phút rồi kiểm cả 4 tầng:
làm mượt đường → tính trên cửa sổ → làm mượt RoR → trần. Đường thẳng thì mọi
thuật toán và mọi mức làm mượt đều phải trả về đúng 30 — lệch là sai công thức,
không phải sai dữ liệu.
"""
import sys, pathlib
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

HTML = pathlib.Path(__file__).resolve().parent.parent / "OTL Roast Lab.html"
STUB = "window.pywebview=undefined;"

# chuỗi mẫu: 121 mẫu, 1 mẫu/giây, BT tăng 0.5 °C/s, ET cao hơn 15 °C và tăng 0.4 °C/s
FEED = """(cfg) => {
  seriesReset();
  for (let i = 0; i <= 120; i++) {
    SERIES.t.push(i);
    SERIES.bt.push(100 + 0.5 * i);
    SERIES.et.push(115 + 0.4 * i);
    SERIES.ror.push(99);            // số 'của máy' — cố tình khác để phân biệt nguồn
    SERIES.rorET.push(88);
    SERIES.gas.push(40); SERIES.air.push(80); SERIES.drum.push(55); SERIES.vac.push(0);
  }
  Object.assign(CFG, cfg);
  rorRecalc();
  return {bt: rorNow('bt'), et: rorNow('et'),
          nBt: rorArr('bt').filter(v => v != null).length};
}"""

BASE = {"ro_src": "App (kiểu Artisan)", "ro_span": "20", "ro_algo": "Hai điểm mút",
        "ro_csmooth": "0", "ro_smooth": "0", "ro_lim": "Không giới hạn",
        "ro_lmin": "-10", "ro_lmax": "45"}


def case(pg, name, cfg, want_bt, want_et, tol=0.05):
    r = pg.evaluate(FEED, {**BASE, **cfg})
    ok = True
    for lbl, got, want in (("ΔBT", r["bt"], want_bt), ("ΔET", r["et"], want_et)):
        if want is None:
            good = got is None
        else:
            good = got is not None and abs(got - want) <= tol
        ok = ok and good
        shown = "null" if got is None else f"{got:+.3f}"
        print(f"   {'OK  ' if good else 'FAIL'} {lbl} = {shown}"
              f"  (mong {'null' if want is None else f'{want:+.2f}'})")
    return ok, r


fails = []
with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page()
    pg.add_init_script(STUB)
    pg.goto(HTML.as_uri())
    pg.wait_for_function("typeof rorRecalc === 'function' && typeof rorNow === 'function'")

    print("1) Hai điểm mút, không làm mượt — đường thẳng phải ra đúng 30 / 24")
    ok, _ = case(pg, "endpoints", {}, 30.0, 24.0)
    if not ok: fails.append("hai điểm mút sai trên đường thẳng")

    print("2) Hồi quy bậc 1 — cùng đường thẳng, cùng kết quả")
    ok, _ = case(pg, "poly", {"ro_algo": "Hồi quy bậc 1"}, 30.0, 24.0)
    if not ok: fails.append("hồi quy bậc 1 sai trên đường thẳng")

    print("3) Bật cả hai tầng làm mượt — vẫn phải đúng 30 (lọc tuyến tính không đổi độ dốc)")
    ok, _ = case(pg, "smooth", {"ro_csmooth": "3", "ro_smooth": "5"}, 30.0, 24.0, tol=0.6)
    if not ok: fails.append("làm mượt làm lệch độ dốc")

    print("4) Đổi cửa sổ 3 giây (kiểu firmware) — độ dốc không đổi thì RoR không đổi")
    ok, _ = case(pg, "span3", {"ro_span": "3"}, 30.0, 24.0)
    if not ok: fails.append("đổi cửa sổ làm lệch kết quả")

    print("5) Trần trên 10, chế độ Bỏ điểm — mọi điểm 30 °C/ph phải bị BỎ (null)")
    ok, r = case(pg, "drop", {"ro_lmax": "10", "ro_lim": "Bỏ điểm"}, None, None)
    if not ok or r["nBt"] != 0:
        fails.append(f"Bỏ điểm không bỏ (còn {r['nBt']} điểm)")
    else:
        print(f"   OK   không còn điểm nào trong mảng ΔBT")

    print("6) Cùng trần đó nhưng Kẹp về biên — phải kẹp đúng 10, không null")
    ok, _ = case(pg, "clamp", {"ro_lmax": "10", "ro_lim": "Kẹp về biên"}, 10.0, 10.0)
    if not ok: fails.append("Kẹp về biên không kẹp đúng")

    print("7) Nguồn Máy (firmware) — phải trả thẳng số máy 99 / 88, KHÔNG tự tính")
    ok, _ = case(pg, "may", {"ro_src": "Máy (firmware)"}, 99.0, 88.0)
    if not ok: fails.append("nguồn Máy không dùng số firmware")

    print("8) Vẽ đồ thị với mảng đầy null — không được ném lỗi")
    err = pg.evaluate("""() => {
      Object.assign(CFG, {ro_src:'App (kiểu Artisan)', ro_lmax:'10', ro_lim:'Bỏ điểm'});
      rorRecalc();
      R.phase='RUNNING'; R.elapsed=120;
      try { drawChart(); return null; } catch(e) { return String(e); }
    }""")
    if err:
        fails.append(f"drawChart ném lỗi: {err}")
        print(f"   FAIL {err}")
    else:
        print("   OK   drawChart chạy sạch")

    br.close()

print()
if fails:
    print("THẤT BẠI:"); [print(" -", f) for f in fails]; sys.exit(1)
print("TẤT CẢ PASS")
