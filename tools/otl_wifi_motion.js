// OTL WiFi Link — bộ chuyển động (kiểu macOS: lò xo có nảy nhẹ). Chỉ transform / opacity ⇒ mượt 120 Hz trên Chrome
// Windows lẫn Safari / Chrome macOS. Không bóng, không mờ nền, không gradient (luật áo OTL V7).
// Người dùng bật "giảm chuyển động" ở hệ điều hành ⇒ mọi hiệu ứng tắt, trang vẫn đủ chức năng.
"use strict";

const M = (() => {
  const RM = matchMedia("(prefers-reduced-motion: reduce)");
  const on = () => !RM.matches;

  // Mô phỏng lò xo khối lượng 1 (độ cứng k, cản c) ở 60 điểm/giây ⇒ chuỗi CSS linear(); máy cũ lùi về cubic-bezier.
  function spring(k, c) {
    let x = 0, v = 0;
    const pts = [];
    for (let i = 0; i < 180; i++) {
      v += (-k * (x - 1) - c * v) / 60;
      x += v / 60;
      pts.push(+x.toFixed(4));
      if (i > 12 && Math.abs(x - 1) < 0.002 && Math.abs(v) < 0.01) break;
    }
    pts[pts.length - 1] = 1;
    const ok = window.CSS && CSS.supports("transition-timing-function", "linear(0, 0.5, 1)");
    return { ease: ok ? `linear(0, ${pts.join(", ")})` : "cubic-bezier(.2,.8,.2,1)", ms: Math.round(pts.length * 1000 / 60) };
  }
  const S = { snappy: spring(260, 24), soft: spring(140, 18), gentle: spring(110, 21) };
  const root = document.documentElement.style;
  root.setProperty("--spring", S.snappy.ease); root.setProperty("--spring-ms", S.snappy.ms + "ms");
  root.setProperty("--spring-soft", S.soft.ease); root.setProperty("--spring-soft-ms", S.soft.ms + "ms");

  function run(el, kf, opt = {}) {
    if (!el || !on() || !el.animate) return null;
    const s = S[opt.spring || "snappy"];
    return el.animate(kf, { duration: opt.duration || s.ms, easing: opt.easing || s.ease, delay: opt.delay || 0, fill: opt.fill || "none" });
  }
  const pop = (el, d = 0) => run(el, [{ transform: "scale(.6)", opacity: 0 }, { transform: "scale(1)", opacity: 1 }], { spring: "soft", delay: d, fill: "backwards" });
  const press = (el) => run(el, [{ transform: "scale(.95)" }, { transform: "scale(1)" }], { spring: "soft" });
  const shake = (el) => run(el, [{ transform: "translateX(0)" }, { transform: "translateX(-7px)" }, { transform: "translateX(6px)" },
    { transform: "translateX(-4px)" }, { transform: "translateX(2px)" }, { transform: "translateX(0)" }], { duration: 380, easing: "ease-out" });
  const nudge = (el, dx = 4) => run(el, [{ transform: "translateX(0)" }, { transform: `translateX(${dx}px)` }, { transform: "translateX(0)" }], { duration: 420, easing: "ease-in-out" });
  const wiggle = (el) => run(el, [{ transform: "rotate(0)" }, { transform: "rotate(-12deg)" }, { transform: "rotate(10deg)" }, { transform: "rotate(-6deg)" }, { transform: "rotate(0)" }], { duration: 520, easing: "ease-out" });
  const flash = (el) => run(el, [{ opacity: .35 }, { opacity: 1 }], { duration: 360, easing: "ease-out" });
  const bump = (el) => run(el, [{ transform: "scale(1)" }, { transform: "scale(1.22)" }, { transform: "scale(1)" }], { spring: "soft" });
  const slideIn = (el, d = 0, dy = 10) => run(el, [{ transform: `translateY(${dy}px)`, opacity: 0 }, { transform: "none", opacity: 1 }], { spring: "gentle", delay: d, fill: "backwards" });
  const rise = (els, step = 40, max = 14) => [...els].slice(0, max).forEach((el, i) => slideIn(el, i * step));
  const fadeSwap = (el) => run(el, [{ opacity: 0, transform: "translateY(4px)" }, { opacity: 1, transform: "none" }], { spring: "gentle" });

  // Cuộn chữ từng ký tự (IP, mã thử) — kiểu bảng số lật.
  function roll(el, text) {
    if (!el) return;
    text = String(text ?? "");
    if (!on() || el.dataset.roll === text) { el.textContent = text; el.dataset.roll = text; return; }
    el.dataset.roll = text;
    el.textContent = "";
    [...text].forEach((ch, i) => {
      const s = document.createElement("span");
      s.className = "rch"; s.textContent = ch;
      el.append(s);
      run(s, [{ transform: "translateY(55%)", opacity: 0 }, { transform: "none", opacity: 1 }], { spring: "soft", delay: i * 22, fill: "backwards" });
    });
  }

  // Đếm số tới giá trị mới (BT / ET) theo nhịp màn hình.
  function countTo(el, to, fmt) {
    if (!el) return;
    const prev = parseFloat(el.dataset.v), from = isNaN(prev) ? 0 : prev;   // lần đầu đếm từ 0
    el.dataset.v = to;
    if (!on() || from === to) { el.innerHTML = fmt(to); return; }
    const t0 = performance.now(), dur = 700;
    const step = (now) => {
      const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 3);
      el.innerHTML = fmt(from + (to - from) * e);
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  // FLIP: danh sách đổi thứ tự / thêm bớt mà các ô trượt êm tới chỗ mới.
  function flip(container, mutate) {
    const kids = () => [...container.children];
    const first = new Map(kids().map(el => [el.dataset.key || el, el.getBoundingClientRect()]));
    mutate();
    if (!on()) return;
    kids().forEach(el => {
      const r0 = first.get(el.dataset.key || el), r1 = el.getBoundingClientRect();
      if (r0) {
        const dx = r0.left - r1.left, dy = r0.top - r1.top;
        if (dx || dy) run(el, [{ transform: `translate(${dx}px,${dy}px)` }, { transform: "none" }], { spring: "gentle" });
      } else slideIn(el, 0, 8);
    });
  }

  // Làm nổi một khu trên màn hình (từ tab Hướng dẫn bấm "Xem trên màn hình").
  function highlight(el) {
    if (!el) return;
    el.scrollIntoView({ behavior: on() ? "smooth" : "auto", block: "center" });
    el.classList.remove("hl"); void el.offsetWidth; el.classList.add("hl");
    setTimeout(() => el.classList.remove("hl"), 2400);
  }

  // Chuyển cảnh (tab, ngôn ngữ): View Transitions nếu trình duyệt có, không thì mờ dần.
  function transition(update, kind = "fade") {
    document.documentElement.dataset.vt = kind;
    if (on() && document.startViewTransition) return document.startViewTransition(update).finished.catch(() => {});
    update();
    return Promise.resolve();
  }

  // Thanh trượt cho nhóm nút (ngôn ngữ, tab, DHCP / cố định, chế độ, tốc độ): ô trắng trượt tới nút đang chọn.
  function thumb(seg) {
    if (!seg) return;
    let t = seg.querySelector(":scope > .thumb");
    if (!t) { t = document.createElement("span"); t.className = "thumb"; t.setAttribute("aria-hidden", "true"); seg.prepend(t); }
    const act = seg.querySelector('[aria-pressed="true"], [aria-selected="true"]');
    if (!act) { t.style.opacity = 0; return; }
    const r = act.getBoundingClientRect(), p = seg.getBoundingClientRect();
    if (!r.width) return;
    const first = !t.dataset.ready;
    if (first) t.style.transition = "none";
    t.style.opacity = 1;
    t.style.width = r.width + "px"; t.style.height = r.height + "px";
    t.style.transform = `translate(${r.left - p.left - seg.clientLeft}px, ${r.top - p.top - seg.clientTop}px)`;
    if (first) { void t.offsetWidth; t.style.transition = ""; t.dataset.ready = 1; }
  }
  const thumbs = () => document.querySelectorAll(".seg").forEach(thumb);
  addEventListener("resize", () => requestAnimationFrame(thumbs));

  // Nhấn nút: co lò xo mọi nút / ô bấm (ủy quyền một chỗ cho cả trang).
  document.addEventListener("pointerdown", (e) => {
    const b = e.target.closest(".btn, .mod, .seg button, .wifi-item, .toc a, .chip-btn");
    if (b && !b.disabled && !b.classList.contains("hold")) press(b);
  });

  return { on, run, pop, press, shake, nudge, wiggle, flash, bump, slideIn, rise, fadeSwap, roll, countTo, flip, highlight, transition, thumb, thumbs, S };
})();
