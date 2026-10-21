# -*- coding: utf-8 -*-
"""Bộ kiểm CHỒNG LẤN + tràn khung trên toàn bộ màn và hộp thoại của app.

Vì sao cần: 12/09/2026 trên MÁY THẬT, đang đăng nhập thì dải "CẢM BIẾN: ET ngoài
dải đo" nằm đúng hàng phím 1-2-3 của bàn phím PIN — thợ nhìn không ra phím để
bấm. Cùng ngày còn thấy bảng "Thao tác" ở màn Rang mở ra là lòi 43px ra ngoài
mép trái màn hình. Hai lỗi đó mắt thường soi ảnh chụp mới thấy, nên phải có máy
soi hộ.

    python tools/test_ui_overlap.py

Ba luật bộ kiểm này canh:
  1. Hai thứ ĐỌC ĐƯỢC cùng một tầng không được đè nhau quá 30%.
  2. Thông báo nổi (toast · dải báo động) không được đè lên THẺ HỘP THOẠI.
     Đè lên nền phía sau thì không tính — nền đang bị làm mờ và không bấm được.
  3. Không phần tử nào lòi ra ngoài mép màn hình.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

GOC = Path(__file__).resolve().parent.parent
HTML = GOC / "OTL Roast Lab.html"

MAN = ["tongquan", "rang", "hoso", "lichsu", "kho", "caidat"]
HOP = ["portpick", "numpad", "keyboard", "picker", "aboutbox", "profedit",
       "napedit", "scalebox", "roastmgr", "batchDetail", "khoForm", "batchCompare"]

DO_JS = r"""
() => {
  const R = el => el.getBoundingClientRect();
  const hien = el => {
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || +s.opacity === 0) return false;
    const r = R(el);
    if (r.width < 3 || r.height < 3) return false;
    return r.bottom > 0 && r.right > 0 && r.top < innerHeight && r.left < innerWidth;
  };
  // <details> đóng: Chrome giữ hộp bố cục nhưng KHÔNG vẽ (content-visibility) →
  // vẫn có toạ độ dù mắt không thấy. Không lọc là báo động giả tràn màn hình.
  const ma = el => { const d = el.closest && el.closest('details'); return !!(d && !d.open); };
  /* BỊ KHUNG CUỘN CẮT (thêm 13/09/2026). Phần tử trôi ra ngoài một khung cha có
     overflow ẩn thì MẮT KHÔNG THẤY, dù toạ độ vẫn nằm trong cửa sổ. Thiếu chốt này
     thì mọi hộp thoại có RUỘT CUỘN RIÊNG (tiêu đề + hàng nút đứng yên, chỉ giữa
     cuộn) đều bị báo chồng lấn giả: ô đang khuất bên dưới bị tính là đè lên nút Lưu.
     Chỉ loại khi nằm HOÀN TOÀN ngoài khung cha — khuất một nửa thì vẫn xét như cũ. */
  const catBoiCha = el => {
    const r = R(el);
    for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
      const s = getComputedStyle(p);
      if (s.overflowX === 'visible' && s.overflowY === 'visible') continue;
      const pr = R(p);
      if (pr.width < 3 || pr.height < 3) continue;
      if (r.bottom <= pr.top + 1 || r.top >= pr.bottom - 1 ||
          r.right <= pr.left + 1 || r.left >= pr.right - 1) return true;
    }
    return false;
  };
  const ten = el => {
    const t = (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 30);
    return (el.id ? '#' + el.id : el.tagName.toLowerCase()) + (t ? ' "' + t + '"' : '');
  };
  const tang = el => {
    for (let p = el; p; p = p.parentElement)
      if (p.classList && p.classList.contains('overlay') && p.classList.contains('on'))
        return p.id || 'overlay';
    return 'base';
  };
  const noi = el => {
    for (let p = el; p; p = p.parentElement) {
      const c = (typeof p.className === 'string') ? p.className : '';
      if (/toast|alarm|fault|banner/i.test(c) || /toast|alarm|fault/i.test(p.id || '')) return true;
    }
    return false;
  };
  const all = [...document.querySelectorAll('body *')].filter(el => hien(el) && !ma(el) && !catBoiCha(el));
  const la = all.filter(el => {
    if (['SCRIPT', 'STYLE'].includes(el.tagName)) return false;
    const t = (el.textContent || '').trim();
    if (!t) return ['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName);
    return ![...el.children].some(c => (c.textContent || '').trim().length > 0);
  });
  const dat = new Set(['BUTTON', 'INPUT', 'SELECT', 'TEXTAREA', 'A']);
  const quanTrong = el => dat.has(el.tagName) || parseFloat(getComputedStyle(el).fontSize) >= 12;
  const coHop = !!document.querySelector('.overlay.on');

  const chong = [];
  for (let i = 0; i < la.length; i++) for (let j = i + 1; j < la.length; j++) {
    const a = la[i], b = la[j];
    if (a.contains(b) || b.contains(a)) continue;
    if (!quanTrong(a) || !quanTrong(b)) continue;
    const cung = tang(a) === tang(b);
    if (!cung && noi(a) === noi(b)) continue;
    if (coHop && tang(a) === 'base' && tang(b) === 'base') continue;   // nền đã mờ
    const ra = R(a), rb = R(b);
    const w = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left);
    const h = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
    if (w <= 1 || h <= 1) continue;
    const dt = w * h, nho = Math.min(ra.width * ra.height, rb.width * rb.height);
    if (dt < nho * 0.30) continue;
    chong.push(ten(a) + ' ⟷ ' + ten(b) + ' (' + Math.round(dt / nho * 100) + '%)');
  }
  const tran = all.filter(el => { const r = R(el); return r.left < -2 || r.right > innerWidth + 2; })
                  .map(el => ten(el) + ' [' + Math.round(R(el).left) + '..' + Math.round(R(el).right) + ']');
  return {chong: chong.slice(0, 6), tran: [...new Set(tran)].slice(0, 6),
          cuon: document.documentElement.scrollWidth > innerWidth + 2};
}
"""
_loi = []


def kiem(ten, dk, gc=""):
    print(("  OK   " if dk else "  HỎNG ") + ten + (" → " + str(gc) if gc else ""))
    if not dk:
        _loi.append(ten)


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        js_err = []
        pg.on("pageerror", lambda e: js_err.append(str(e)[:120]))
        pg.goto(HTML.as_uri())
        pg.wait_for_timeout(900)

        def soat(nhan):
            # 900ms: tầng chuyển động giữ hộp vừa đóng còn hiện trong lúc tan
            pg.wait_for_timeout(900)
            r = pg.evaluate(DO_JS)
            kiem("%-18s không chồng lấn" % nhan, not r["chong"], "; ".join(r["chong"])[:150])
            kiem("%-18s không tràn mép" % nhan, not r["tran"], "; ".join(r["tran"])[:150])
            if r["cuon"]:
                kiem("%-18s không cuộn ngang" % nhan, False)

        print("— màn khoá —")
        soat("Đăng nhập")
        pg.evaluate("session={name:'M',role:'master',perms:{}};"
                    "document.getElementById('login').classList.remove('on');updateBadge();")

        print("— 6 màn chính —")
        for t in MAN:
            pg.evaluate("gotoTab('%s')" % t)
            soat(t)

        print("— hộp thoại —")
        pg.evaluate("gotoTab('rang')")
        for h in HOP:
            pg.evaluate("() => { document.getElementById('%s').classList.add('on') }" % h)
            soat("hộp " + h)
            pg.evaluate("() => { document.getElementById('%s').classList.remove('on') }" % h)

        print("— thông báo lúc đang mở hộp thoại (ca gặp trên máy thật) —")
        pg.evaluate("""() => {
            renderLogin(); document.getElementById('login').classList.add('on');
            const fb = document.getElementById('faultBanner');
            fb.classList.add('show');
            document.getElementById('faultMsg').textContent = 'CẢM BIẾN: ET ngoài dải đo';
            try { toast('Đã gửi: Gas = 100', true); } catch (e) {}
        }""")
        soat("khoá + báo động")
        # bàn phím PIN phải TRỐNG hoàn toàn: không một phím nào bị thông báo che
        che = pg.evaluate("""() => {
            const phim = [...document.querySelectorAll('#login .padkey')];
            const noi = ['#toast', '#faultBanner'].map(s => document.querySelector(s))
                          .filter(el => el && getComputedStyle(el).display !== 'none' &&
                                  +getComputedStyle(el).opacity > 0);
            const dung = [];
            for (const k of phim) { const a = k.getBoundingClientRect();
              for (const n of noi) { const b = n.getBoundingClientRect();
                if (a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom)
                  dung.push(k.textContent.trim() + '←' + (n.id)); } }
            return dung;
        }""")
        kiem("không thông báo nào che phím PIN", not che, "; ".join(che))

        print("— băng trạng thái lệnh phải ở THANH ĐẦU, không đè thân màn Rang —")
        # Băng này từng ghim bottom:154px (đè ô TỐC ĐỘ TRỐNG 251×21px) rồi 392px
        # (đè hàng pha Sấy · Maillard · Phát triển). Thân màn Rang kín chỗ.
        pg.evaluate("gotoTab('rang')")
        pg.evaluate("""() => { DS.state='connected'; R.burner=82;
            document.getElementById('ovBurner').textContent='82';
            UX.command={id:1,name:'gas',value:82,state:'timeout',at:Date.now(),snapshot:0};
            uxCommandRender(); }""")
        pg.wait_for_timeout(500)
        bg = pg.evaluate("""() => {
            const c = document.getElementById('uxCommand'); if (!c) return null;
            const rc = c.getBoundingClientRect(), che = [];
            for (const e of document.querySelectorAll('body *')) {
                if (e === c || c.contains(e) || e.contains(c)) continue;
                const t = (e.textContent || '').trim();
                if (!t || t.length > 40) continue;
                if ([...e.children].some(x => (x.textContent || '').trim())) continue;
                const s = getComputedStyle(e);
                if (s.display === 'none' || s.visibility === 'hidden' || +s.opacity === 0) continue;
                const q = e.getBoundingClientRect();
                if (q.width < 3 || q.height < 3) continue;
                if (Math.min(rc.right, q.right) - Math.max(rc.left, q.left) > 1 &&
                    Math.min(rc.bottom, q.bottom) - Math.max(rc.top, q.top) > 1)
                    che.push(t.slice(0, 22));
            }
            return {tren: !!c.closest('#topbar'), che: che.slice(0, 3),
                    rong: Math.round(rc.width)};
        }""")
        kiem("băng lệnh nằm trên thanh đầu", bg and bg["tren"])
        kiem("băng lệnh không che gì", bg and not bg["che"], "; ".join(bg["che"]) if bg else "")
        kiem("câu dài nhất vẫn không xô thanh đầu", bg and bg["rong"] <= 560, bg["rong"] if bg else "")
        pg.evaluate("UX.command=null;uxCommandRender()")

        print("— viên trợ lý không được đậu lên dải tiêu đề —")
        # dựng lại đúng chỗ chủ máy kéo tới (mép trái, ngang tiêu đề)
        pg.evaluate("""() => {
            localStorage.setItem('otl_buddy_pos', JSON.stringify({x: 14, y: 180}));
            const b = document.getElementById('otlBuddy');
            if (b) { b._on = 0; buddyInit(); }
        }""")
        pg.wait_for_timeout(400)
        for t in ("rang", "hoso", "lichsu"):
            pg.evaluate("gotoTab('%s')" % t)
            pg.wait_for_timeout(500)
            # Chỉ canh TIÊU ĐỀ và nhãn. Viên trợ lý là thứ nổi, nó sẽ luôn đè lên
            # một chỗ nào đó trong vùng nội dung — chuyện đó thợ kéo đi là xong.
            # Thứ không chấp nhận được là nó ngồi lên tiêu đề trang, vì tiêu đề
            # nằm một chỗ cố định nên đã che là che vĩnh viễn.
            de = pg.evaluate("""() => {
                const b = document.getElementById('otlBuddy'); if (!b) return [];
                const r = b.getBoundingClientRect(), ra = [];
                for (const e of document.querySelectorAll('#stage .pane.on *')) {
                    const t = (e.textContent || '').trim();
                    // ≤24 ký tự = TIÊU ĐỀ / NHÃN. Câu dài trong vùng rỗng (kiểu
                    // "Các mẻ đã lưu sẽ xuất hiện ở đây") là nội dung, không phải
                    // tiêu đề — viên trợ lý nổi thì luôn đè lên nội dung ở đâu đó,
                    // chuyện đó thợ kéo nó đi là xong.
                    if (!t || t.length > 24) continue;
                    if ([...e.children].some(c => (c.textContent || '').trim())) continue;
                    // chỉ tính DẢI TIÊU ĐỀ: 30% trên cùng của màn. Tiêu đề ở đây
                    // không có lớp CSS chung (màn Rang là <span> trơn, màn Hồ sơ
                    // là <button>), nên bắt theo VỊ TRÍ mới chắc.
                    if (e.getBoundingClientRect().top > innerHeight * 0.30) continue;
                    const q = e.getBoundingClientRect();
                    if (q.width < 3 || q.height < 3) continue;
                    if (r.left < q.right && q.left < r.right && r.top < q.bottom && q.top < r.bottom)
                        ra.push(t.slice(0, 24));
                }
                return ra.slice(0, 3);
            }""")
            kiem("%-18s trợ lý không đè chữ" % t, not de, "; ".join(de))

        print("— bảng 'Thao tác' mở ra phải nằm trọn trong màn —")
        pg.evaluate("document.getElementById('login').classList.remove('on');gotoTab('rang')")
        pg.wait_for_timeout(600)
        r = pg.evaluate("""() => {
            const d = document.querySelector('details.match-more');
            if (!d) return null;
            d.open = true;
            const q = d.querySelector('.match-more-panel').getBoundingClientRect();
            return [Math.round(q.left), Math.round(q.right), innerWidth];
        }""")
        kiem("bảng Thao tác không lòi mép trái", r and r[0] >= -2, r)
        kiem("bảng Thao tác không lòi mép phải", r and r[1] <= r[2] + 2, r)

        b.close()

    kiem("không có lỗi JS", not js_err, "; ".join(js_err)[:150])
    print()
    if _loi:
        print("HỎNG %d mục:\n  - %s" % (len(_loi), "\n  - ".join(_loi)))
        return 1
    print("TẤT CẢ ĐẠT — không chỗ nào chồng lấn, không gì lòi ra ngoài màn.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
