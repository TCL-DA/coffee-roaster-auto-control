// OTL WiFi Link — logic trang (gọi máy chủ 127.0.0.1 của otl_wifi_link.py).
"use strict";
// ─────────────────────────────── Trạng thái ───────────────────────────────
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const store = {
  get(k){ try { return localStorage.getItem("otl_usr_" + k); } catch { return null; } },
  set(k, v){ try { localStorage.setItem("otl_usr_" + k, v); } catch { /* chế độ riêng tư — bỏ qua */ } }
};
// Ngôn ngữ: đã chọn thì giữ; lần đầu theo ngôn ngữ trình duyệt (khách Pháp mở lên là tiếng Pháp), tiếng lạ ⇒ tiếng Anh.
function pickLang(){
  const saved = store.get("lang");
  if (LANGS.includes(saved)) return saved;
  const sys = ((navigator.languages && navigator.languages[0]) || navigator.language || "").slice(0, 2).toLowerCase();
  return LANGS.includes(sys) ? sys : "en";
}
const S = { lang: pickLang(), mods: [], sel: null, info: null,
            scanning: false, testing: false, applying: false, wan: "dhcp", mode: null, test: null, infoErr: false };

function t(key, p = {}){
  const s = (I18N[S.lang][key] ?? I18N.en[key] ?? I18N.vi[key] ?? key);
  return s.replace(/\{(\w+)\}/g, (_, k) => (p[k] ?? ""));
}
class UiErr extends Error { constructor(code, params = {}){ super(code); this.code = code; this.params = params; } }
function errText(e){
  if (!(e instanceof UiErr)) return t("err.unknown");
  const p = { ...e.params };
  if (p.field) p.field = t("f." + p.field);
  return t("err." + e.code, p);
}

// ─────────────────────────────── Gọi máy chủ ───────────────────────────────
async function api(path, body){
  let r;
  try {
    r = await fetch(path, body === undefined ? { cache: "no-store" } :
      { method: "POST", cache: "no-store", headers: { "Content-Type": "application/json", "X-OTL": "1" }, body: JSON.stringify(body) });
  } catch {
    serverDown(); throw new UiErr("net", { msg: "127.0.0.1" });
  }
  const j = await r.json();
  if (!j.ok) throw new UiErr(j.code || "unknown", j.params || {});
  return j.data;
}
function serverDown(){ $("#down").classList.add("on"); }
setInterval(() => { fetch("/api/ping", { cache: "no-store" }).catch(serverDown); }, 20000);

// ─────────────────────────────── Thông báo nổi ───────────────────────────────
function toast(msg, kind = "ok"){
  const box = $("#toasts"), el = document.createElement("div");
  el.className = "toast " + kind;
  if (M.on()) el.style.animation = "none";
  el.innerHTML = `<svg class="i"><use href="#${kind === "err" ? "i-warn" : "i-check"}"/></svg><span></span>`;
  el.lastChild.textContent = msg;
  M.flip(box, () => box.append(el));
  M.pop(el.firstChild, 90);
  if (kind === "err") M.shake(el);
  let left = kind === "err" ? 6000 : 3200, t0 = 0, timer = 0;
  const close = () => {
    const a = M.run(el, [{ opacity: 1, transform: "none" }, { opacity: 0, transform: "translateY(8px) scale(.97)" }], { duration: 180, easing: "ease-in", fill: "forwards" });
    const rm = () => M.flip(box, () => el.remove());
    a ? a.finished.then(rm, rm) : rm();
  };
  const arm = () => { t0 = Date.now(); timer = setTimeout(close, Math.max(600, left)); };
  el.addEventListener("mouseenter", () => { clearTimeout(timer); left -= Date.now() - t0; });
  el.addEventListener("mouseleave", arm);
  arm();
}
async function copy(v, btn){
  try { await navigator.clipboard.writeText(v); }
  catch { const a = Object.assign(document.createElement("textarea"), { value: v }); document.body.append(a); a.select(); document.execCommand("copy"); a.remove(); }
  const u = btn && btn.querySelector("use");
  if (u) {                                   // biểu tượng chép → dấu tích rồi quay lại
    const old = u.getAttribute("href");
    u.setAttribute("href", "#i-check"); M.pop(btn.querySelector("svg"));
    setTimeout(() => { u.setAttribute("href", old); M.pop(btn.querySelector("svg")); }, 1300);
  }
  toast(t("copied", { v }));
}

// ─────────────────────────────── Ngôn ngữ ───────────────────────────────
function applyLang(animate){
  const run = () => {
    document.documentElement.lang = S.lang;
    $$("[data-i18n]").forEach(el => { el.textContent = t(el.dataset.i18n); });
    $$("[data-lang]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.lang === S.lang)));
    $("#h-pdf").href = S.lang === "fr" ? "/guide-fr.pdf" : "/guide.pdf";
    $("#quit").setAttribute("aria-label", t("quit")); $("#quit").title = t("quit");   // màn hẹp: nút chỉ còn biểu tượng
    renderScanBtn(); renderList(); renderSel(); renderSummary(); renderHelp(); renderWifi();
    M.thumbs();
  };
  return animate ? M.transition(run, "fade").then(() => requestAnimationFrame(M.thumbs)) : run();
}

// ─────────────────────────────── Dò module ───────────────────────────────
function renderScanBtn(){
  const b = $("#scan");
  b.disabled = S.scanning;
  b.innerHTML = S.scanning ? `<span class="radar on"><svg class="i"><use href="#i-wifi"/></svg><i></i><i></i></span><span>${t("scanning")}</span>`
                           : `<svg class="i"><use href="#i-search"/></svg><span>${t("scan")}</span>`;
  $("#prog").classList.toggle("on", S.scanning);
}
async function scan(){
  if (S.scanning) return;
  S.scanning = true; renderScanBtn(); renderList();
  const t0 = performance.now();
  try {
    S.mods = await api("/api/scan");
  } catch (e) { toast(errText(e), "err"); }
  await new Promise(r => setTimeout(r, Math.max(0, 500 - (performance.now() - t0))));   // tiến trình hiện đủ lâu để mắt thấy
  S.scanning = false; renderScanBtn();
  const keep = S.mods.find(m => m.mac === (S.sel && S.sel.mac)) || S.mods.find(m => m.mac === store.get("mac")) ||
               (S.mods.length === 1 ? S.mods[0] : null);
  renderList(true);
  if (keep) select(keep, true); else if (!S.mods.length) { S.sel = null; S.info = null; renderSel(); }
  if (!S.mods.length && !S.setupOn) lookNear(); else if (S.mods.length && !S.setupOn) { S.near = null; renderSetup(); }
  return S.mods;
}
function renderList(animate){
  const box = $("#mods");
  if ($("#count").textContent !== String(S.mods.length)) { $("#count").textContent = S.mods.length; M.bump($("#count")); }
  const emptyNow = !(S.mods.length > 0 || S.scanning);
  if (emptyNow && $("#empty").hidden) setTimeout(() => M.rise($("#empty").children, 60));
  $("#empty").hidden = !emptyNow;
  box.replaceChildren(...S.mods.map((m, k) => {
    const b = document.createElement("button");
    b.type = "button"; b.className = "mod"; b.dataset.key = m.mac;
    b.setAttribute("aria-current", String(!!S.sel && S.sel.mac === m.mac));
    b.innerHTML = `<svg class="i"><use href="#i-wifi"/></svg><span><span class="ip num"></span><br><span class="mac"></span></span>
                   <span class="tag"><svg class="i" style="width:16px;height:16px"><use href="#i-check"/></svg>${t("list.selected")}</span>`;
    b.querySelector(".ip").textContent = m.ip;
    b.querySelector(".mac").textContent = [m.mac, m.via === "tcp" ? t("tcp.tag") : ""].filter(Boolean).join(" · ");
    b.addEventListener("click", () => select(m));
    return b;
  }));
  if (animate) M.rise(box.children, 45);
}

// ─────────────────────────────── Module đang chọn ───────────────────────────────
async function select(m, quiet){
  const changed = !S.sel || S.sel.mac !== m.mac;
  S.sel = m; store.set("mac", m.mac);
  if (changed) { S.info = null; S.test = null; S.testFail = false; }
  S.infoErr = false;
  renderList(); renderSel();
  try {
    S.info = await api("/api/info?ip=" + encodeURIComponent(m.ip));   // module tìm qua TCP vẫn thử: phiên lệnh tự gỡ kẹt
    if (S.sel !== m) return;
    fillForm(); renderSel(); renderSummary();
    test(true);
  } catch (e) {
    if (m.via === "tcp") { S.info = null; S.infoErr = "tcp"; renderSel(); test(true); return; }
    S.infoErr = !S.info; if (!quiet || changed) toast(errText(e), "err"); renderSel();
  }
}
const netpPort = () => { const p = (S.info?.netp || "").split(","); return p[2] || "8899"; };

function chip(icon, text, cls = ""){ return `<span class="chip ${cls}"><svg class="i"><use href="#${icon}"/></svg><span>${esc(text)}</span></span>`; }
function esc(s){ return String(s ?? "").replace(/[&<>"']/g, c => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c])); }

function renderSel(){
  const has = !!S.sel;
  $("#nosel").hidden = has; $("#sel").hidden = !has;
  if (typeof renderSetup === "function") renderSetup();
  if (!has) return;
  $("#settings").hidden = !S.info && !!S.infoErr;
  const i = S.info;
  M.roll($("#h-ip"), S.sel.ip);
  $("#a-host").textContent = S.sel.ip;
  $("#a-port").textContent = i ? netpPort() : "8899";
  $("#a-dev").textContent = devId();
  renderAuto(); renderGuide(); renderTech();
  // dải nhãn trạng thái
  if (!i) {
    $("#h-chips").innerHTML = S.infoErr === "tcp" ? (S.test ? chip("i-check", t("chip.reply"), "ok") : "") + chip("i-search", t("tcp.chip"))
      : S.infoErr ? "" : `<span class="sk" style="width:220px"></span>`;
    $("#pin").hidden = true;
  } else {
    const dhcp = (i.wan_mode || "").toUpperCase() === "DHCP";
    const mode = (i.mode || "").toUpperCase();
    $("#h-chips").innerHTML =
      (S.test ? chip("i-check", t("chip.reply"), "ok") : "") +
      (I18N.vi["chip." + mode] ? chip("i-wifi", t("chip." + mode, { ssid: i.sta_ssid || "" })) : "") +
      (mode === "AP" ? "" : dhcp ? chip("i-warn", t("chip.dhcp"), "warn") : chip("i-lock", t("chip.static")));
    $("#pin").hidden = mode === "AP" || !dhcp;
  }
  const chips = $("#h-chips");
  if (chips.dataset.h !== chips.innerHTML) { chips.dataset.h = chips.innerHTML; M.rise(chips.children, 55); }
  // nhiệt độ thử: đếm số chạy tới giá trị mới
  const fmtT = (v) => `${S.lang === "en" ? v.toFixed(1) : v.toFixed(1).replace(".", ",")}<small>°C</small>`;   // VI / FR: dấu phẩy thập phân
  for (const [id, v] of [["#t-bt", S.test?.bt], ["#t-et", S.test?.et]]) {
    const el = $(id);
    if (v == null) { el.innerHTML = "—"; delete el.dataset.v; }
    else if (+el.dataset.v !== v) {
      const first = el.dataset.v === undefined;
      M.countTo(el, v, fmtT);
      const tile = el.closest(".temp"); tile.classList.remove("fresh"); void tile.offsetWidth; tile.classList.add("fresh");
      if (first) M.pop(tile.querySelector(".k"));
    }
  }
  $("#test").disabled = S.testing || !i;
  $("#test").innerHTML = S.testing ? `<span class="spin"></span><span>${t("test.reading")}</span>`
                                   : `<svg class="i"><use href="#i-play"/></svg><span>${t("test.btn")}</span>`;
  $("#t-stat").textContent = S.testing ? "" : S.test ? t("test.ok", { time: S.test.time }) : S.testFail ? t("test.fail") : t("test.none");
  $("#t-stat").style.color = !S.testing && !S.test && S.testFail ? "var(--red)" : "";
  if ($("#t-stat").dataset.h !== $("#t-stat").textContent) { $("#t-stat").dataset.h = $("#t-stat").textContent; M.fadeSwap($("#t-stat")); }
  // bảng thông tin
  if (!i) {
    $("#info").innerHTML = S.infoErr === "tcp"
      ? `<dt>MAC</dt><dd class="num">${esc(S.sel.mac || "—")}</dd><dt>—</dt><dd class="muted">${esc(t("tcp.body"))}</dd>`
      : S.infoErr ? `<dt>—</dt><dd class="muted">${esc(t("err.no_reply", { ip: S.sel.ip }))}</dd>`
      : Array.from({ length: 6 }, () => `<dt><span class="sk" style="width:70px"></span></dt><dd><span class="sk"></span></dd>`).join("");
    $("#ap-open").hidden = true;
    return;
  }
  const mode = (i.mode || "").toUpperCase();
  const apOn = mode === "AP" || mode === "APSTA";
  const sec = (a) => (a || "").toUpperCase() === "OPEN" ? t("det.open") : t("det.secured");
  const rows = [
    ["det.mode", esc(t("mode." + mode) || i.mode)],
    ["det.sta", mode === "AP" ? "—" : `${esc(i.sta_ssid)} <span class="sub">· ${esc(sec(i.sta_auth))} · ${esc(i.wan_mode)}</span>`],
    ["det.ap", apOn ? `${esc(i.ap_ssid)} <span class="sub">· ${esc(sec(i.ap_auth))}</span>` : `<span class="sub">${esc(t("det.ap_off"))}</span>`],
    ["det.lan", `<span class="num">${esc(i.lan_ip)}</span>`],
    ["det.netp", `<span class="num">${esc((i.netp || "").split(",").slice(0, 3).join(" · "))}</span>`],
    ["det.uart", `<span class="num">${esc((i.uart || "").split(",").slice(0, 4).join(" · "))}</span>`],
    ["det.std", (i.std && i.std.length) ? `<span style="color:var(--amber)">${esc(t("det.std_bad", { items: stdNames(i.std) }))}</span>` : esc(t("det.std_ok"))],
    ["det.fw", `<span class="num">${esc(i.ver)}</span> <span class="sub">· ${esc(S.sel.mac)}</span>`],
  ];
  const html = rows.map(([k, v]) => `<dt>${esc(t(k))}</dt><dd>${v}</dd>`).join(""), inf = $("#info");
  if (inf.dataset.h !== html) { inf.dataset.h = html; inf.innerHTML = html; M.fadeSwap(inf); }
  $("#ap-open").hidden = !(apOn && (i.ap_auth || "").toUpperCase() === "OPEN");
}

async function test(silent){
  if (!S.sel || S.testing) return;
  S.testing = true; renderSel();
  $("#t-bt").classList.add("fade"); $("#t-et").classList.add("fade");
  try {
    const d = await api(`/api/test?ip=${encodeURIComponent(S.sel.ip)}&port=${encodeURIComponent(netpPort())}`);
    S.test = { ...d, time: new Date().toLocaleTimeString(LOCALE[S.lang]) }; S.testFail = false;
  } catch (e) { S.test = null; S.testFail = true; if (!silent) toast(errText(e), "err"); }
  S.testing = false; renderSel();
  requestAnimationFrame(() => { $("#t-bt").classList.remove("fade"); $("#t-et").classList.remove("fade"); });
}

// ─────────────────────────────── Cài đặt ───────────────────────────────
const IPV4 = /^(25[0-5]|2[0-4]\d|1?\d?\d)(\.(25[0-5]|2[0-4]\d|1?\d?\d)){3}$/;
function fillForm(){
  const i = S.info; if (!i) return;
  S.wan = (i.wan_mode || "").toUpperCase() === "DHCP" ? "dhcp" : "static";
  S.mode = (i.mode || "").toUpperCase();
  $("#f-ip").value = i.wan_ip || ""; $("#f-mask").value = i.wan_mask || "255.255.255.0"; $("#f-gw").value = i.wan_gw || "";
  $("#f-ssid").value = i.sta_ssid || ""; $("#f-skey").value = ""; $("#f-akey").value = "";
  $$(".field").forEach(f => f.classList.remove("bad"));
  $("#result").textContent = "";
  S.wifi = null; $("#key-src").textContent = ""; renderWifi();
  renderSegs();
}
function renderSegs(){
  $$("[data-wan]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.wan === S.wan)));
  $$("[data-mode]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.mode === S.mode)));
  ["#f-ip", "#f-mask", "#f-gw"].forEach(s => { $(s).disabled = S.wan === "dhcp"; });
  const mh = $("#mode-help"), txt = S.mode ? t("mode.help." + S.mode) : "";
  if (mh.textContent !== txt) { mh.textContent = txt; M.fadeSwap(mh); }
  requestAnimationFrame(M.thumbs);
}
function fieldErr(id, msg){
  const f = $("#" + id).closest(".field"), was = f.classList.contains("bad");
  f.classList.toggle("bad", !!msg);
  f.querySelector(".err").textContent = msg || "";
  if (msg && !was) { M.shake(f); M.slideIn(f.querySelector(".err"), 0, -4); }
  return !msg;
}
function validate(show){
  let ok = true;
  const chk = (id, bad, msg) => { const good = !bad; if (show || $("#" + id).closest(".field").classList.contains("bad")) fieldErr(id, good ? "" : msg); ok = ok && good; };
  if (S.wan === "static") [["f-ip", "f.ip"], ["f-mask", "f.mask"], ["f-gw", "f.gw"]].forEach(([id, key]) =>
    chk(id, !IPV4.test($("#" + id).value.trim()), t("v.ip")));
  const pw = (v) => v !== "" && (v.length < 8 || v.length > 63 || /,/.test(v));
  const ssid = $("#f-ssid").value;
  chk("f-ssid", /,/.test(ssid) || (!ssid.trim() && $("#f-skey").value !== ""), t("v.len", { lo: 1, hi: 32 }));
  chk("f-skey", pw($("#f-skey").value), t("v.len", { lo: 8, hi: 63 }));
  chk("f-akey", pw($("#f-akey").value), t("v.len", { lo: 8, hi: 63 }));
  return ok;
}
function buildReq(){
  const i = S.info; if (!i) return null;
  const req = { ip: S.sel.ip }, lines = [], after = [];
  const curDhcp = (i.wan_mode || "").toUpperCase() === "DHCP";
  const ip = $("#f-ip").value.trim(), mask = $("#f-mask").value.trim(), gw = $("#f-gw").value.trim();
  if (S.wan === "dhcp" && !curDhcp) { req.wan = { dhcp: true }; lines.push(t("sum.ip_dhcp")); }
  if (S.wan === "static" && (curDhcp || ip !== i.wan_ip || mask !== i.wan_mask || gw !== i.wan_gw)) {
    req.wan = { dhcp: false, ip, mask, gw }; lines.push(t("sum.ip_static", { ip, mask, gw }));
    if (ip !== S.sel.ip) after.push(t("sum.after_ip", { ip }));
  }
  const ssid = $("#f-ssid").value.trim(), skey = $("#f-skey").value;
  if (ssid && (ssid !== i.sta_ssid || skey)) {
    req.sta = { ssid, key: skey }; lines.push(t(skey ? "sum.sta" : "sum.sta_open", { ssid }));
    if ((i.mode || "").toUpperCase() === "AP" && S.mode === "AP") { S.mode = "STA"; renderSegs(); }   // bắt wifi quán thì phải ở chế độ STA
  }
  const akey = $("#f-akey").value;
  if (akey) { req.ap = { key: akey }; lines.push(t("sum.ap")); }
  const cur = (i.mode || "").toUpperCase();
  if (S.mode && S.mode !== cur) {
    req.mode = S.mode; lines.push(t("sum.mode", { mode: t("mode." + S.mode) }));
    if (S.mode === "AP") after.push(t("sum.after_ap", { ssid: i.ap_ssid || "OTL Roaster" }));
    if (S.mode === "STA") after.push(t("sum.after_sta", { ssid: ssid || i.sta_ssid || "" }));
  }
  return { req, lines, after };
}
function renderSummary(){
  if (!S.info) { $("#sum").innerHTML = ""; $("#apply").disabled = true; return; }
  const b = buildReq(), valid = validate(false);
  const sum = $("#sum"), prevH = sum.dataset.h;
  sum.innerHTML = `<b>${esc(t("sum.title"))}</b>` +
    (b.lines.length ? `<ul>${b.lines.map(l => `<li>${esc(l)}</li>`).join("")}</ul>` : `<div class="muted" style="margin-top:4px">${esc(t("sum.none"))}</div>`) +
    b.after.map(a => `<p class="after">${esc(a)}</p>`).join("");
  if (prevH !== sum.innerHTML) { sum.dataset.h = sum.innerHTML; M.rise(sum.querySelectorAll("li, .after"), 40); }
  $("#apply").disabled = !b.lines.length || !valid || S.applying;
}

// Nút GIỮ 1 giây: bước nguy hiểm duy nhất (đổi wifi / IP có thể làm mất module) nên làm khó có chủ đích
function holdButton(btn, ms, onDone){
  let timer = null, done = false;
  const fill = btn.querySelector(".fill");
  const go = (to, dur, ease) => { fill.style.transition = `transform ${dur}ms ${ease}`; fill.style.transform = `scaleX(${to})`; };
  const begin = () => { if (btn.disabled || timer) return; done = false; go(1, ms, "linear");
    timer = setTimeout(() => { timer = null; done = true; go(0, 0, "linear"); onDone(); }, ms); };
  const cancel = () => { if (!timer) return; clearTimeout(timer); timer = null; go(0, 180, "var(--ease)"); M.shake(btn);
    const h = $("#hold-hint"); h.textContent = t("hold.again"); h.classList.add("flash");
    setTimeout(() => { h.textContent = t("hold.hint"); h.classList.remove("flash"); }, 1600); };
  btn.addEventListener("pointerdown", e => { if (e.button === 0) { btn.setPointerCapture?.(e.pointerId); begin(); } });
  btn.addEventListener("pointerup", cancel);
  btn.addEventListener("pointercancel", cancel);
  btn.addEventListener("keydown", e => { if ((e.key === " " || e.key === "Enter") && !e.repeat) { e.preventDefault(); begin(); } });
  btn.addEventListener("keyup", e => { if (e.key === " " || e.key === "Enter") cancel(); });
  btn.addEventListener("click", e => e.preventDefault());
}
async function applyNow(){
  if (!validate(true)) { $(".field.bad input")?.focus(); return; }
  const b = buildReq(); if (!b || !b.lines.length) return;
  S.applying = true; renderSummary();
  const res = $("#result"); res.innerHTML = `<span class="muted">${esc(t("apply.writing"))}</span>`;
  const mac = S.sel.mac;
  try {
    const d = await api("/api/apply", b.req);
    if (d.restarted && b.req.sta && $("#wifi-remember").checked)
      api("/api/wifi/remember", { ssid: b.req.sta.ssid, key: b.req.sta.key }).then(() => toast(t("w.remembered", { ssid: b.req.sta.ssid }))).catch(() => {});
    if (!d.restarted) {
      const bad = d.results.filter(([, r]) => !r.startsWith("+ok")).map(([c, r]) => `${c} → ${r}`);
      const names = d.results.filter(([, r]) => !r.startsWith("+ok")).map(([c]) => c).join(", ");
      res.innerHTML = `<span style="color:var(--red);font-weight:600">${esc(t("apply.fail", { cmds: names }))}</span><br>` + bad.map(x => `<code>${esc(x)}</code>`).join(" ");
    } else {
      for (let s = 12; s > 0; s--) { res.innerHTML = `<span class="muted">${esc(t("apply.restart", { s }))}</span>`; M.flash(res); await new Promise(r => setTimeout(r, 1000)); }
      const list = await scan() || [];
      const m = list.find(x => x.mac === mac);
      res.innerHTML = m ? `<span class="chip ok">${esc(t("apply.found", { ip: m.ip }))}</span>` : `<span class="muted">${esc(t("apply.lost"))}</span>`;
      if (m) toast(t("apply.found", { ip: m.ip }));
    }
  } catch (e) { res.textContent = errText(e); toast(errText(e), "err"); }
  S.applying = false; renderSummary();
}

// ─────────────────────────────── Tự động kiểm & sửa ───────────────────────────────
const devId = () => S.test?.id || 1;
const curBaud = () => { const b = parseInt((S.info?.uart || "").split(",")[0], 10); return isNaN(b) ? "—" : b; };
const AU_GOOD = ["found"], AU_BAD = ["no_reply", "lost", "error"];
const stdNames = (items) => (Array.isArray(items) ? items : String(items || "").split(",")).filter(Boolean).map(k => t("std." + k)).join(", ");
const RING = 56.5;
const ringSvg = () => `<svg class="au-ring" viewBox="0 0 24 24" aria-hidden="true"><circle class="bg" cx="12" cy="12" r="9"/><circle class="fg" cx="12" cy="12" r="9" stroke-dasharray="${RING}" stroke-dashoffset="${RING}"/></svg>`;
const tickSvg = '<svg class="tick" viewBox="0 0 20 20" aria-hidden="true"><path d="M4 10.5 8 14.5 16 5.5"/></svg>';
const AU_CUR = ["check", "try", "std", "restore", "ap_name", "pc_join", "find", "sta", "pc_back", "find_shop", "need_key"];
function logLi(e){
  const li = document.createElement("li");
  li.className = AU_GOOD.includes(e.code) ? "good" : AU_BAD.includes(e.code) ? "bad" : "";
  li.dataset.code = e.code;
  li.innerHTML = `<span class="dot"></span><span></span><span class="tm num">${e.t.toFixed(0)} s</span>`;
  const key = e.code === "pc_join" && e.params.factory ? "au.pc_join_f" : "au." + e.code;
  li.children[1].textContent = t(key, e.code === "std" ? { items: stdNames(e.params.items) } : e.params);
  return li;
}
const wifiHint = () => S.info && (S.info.mode || "").toUpperCase() === "AP"
  ? `<div class="au-row" style="margin-top:12px"><span class="grow helper" style="margin:0">${esc(t("au.wifi"))}</span>
     <button class="btn sm" type="button" data-au="wifi"><svg class="i"><use href="#i-wifi"/></svg><span>${esc(t("au.wifi_btn"))}</span></button></div>` : "";
function renderAuto(){
  const box = $("#auto"); if (!box || !S.sel) return;
  const a = S.auto, running = !!(a && a.running);
  if (running) {
    if (box.dataset.mode !== "run") {
      box.dataset.mode = "run"; box.dataset.key = "";
      box.innerHTML = `<div class="au-title">${ringSvg()}<span>${esc(t("au.running"))}</span></div><ol class="au-log"></ol><p class="helper">${esc(t("au.wait"))}</p>`;
      M.fadeSwap(box);
    }
    const ol = box.querySelector(".au-log");
    a.log.slice(ol.children.length).forEach(e => { const li = logLi(e); ol.append(li); M.slideIn(li, 0, 8); });
    [...ol.children].forEach((li, k) => li.classList.toggle("cur", k === ol.children.length - 1 && AU_CUR.includes(li.dataset.code)));
    const p = Math.min(0.95, (a.log.length + 1) / 12);
    requestAnimationFrame(() => { const fg = box.querySelector(".au-ring .fg"); if (fg) fg.style.strokeDashoffset = (RING * (1 - p)).toFixed(1); });
    return;
  }
  box.dataset.mode = "static";
  let h, key;
  if (a && a.result && S.autoShown) {
    const r = a.result;
    key = "res" + JSON.stringify(r) + a.log.length + S.lang + (S.info?.mode || "");
    h = `<div class="au-title">${esc(t("au.start"))}</div><ol class="au-log">${a.log.map(e => logLi(e).outerHTML).join("")}</ol>`;
    h += r.ok ? `<div class="au-res">${tickSvg}<span>${esc(t("au.done_ok", r))}</span></div>` + (r.renamed ? `<div class="au-res fail">${esc(t("au.renamed", r))}</div>` : "") + wifiHint()
              : `<div class="au-res fail">${esc(t(r.reason === "lost" ? "au.done_lost" : "au.done_fail"))}</div>
                 <div class="test-row"><button class="btn" type="button" data-au="start">${esc(t("au.start"))}</button>
                 <button class="btn ghost" type="button" data-au="diag">${esc(t("rs.copy"))}</button></div>`;
  } else if (S.testing || (!S.info && !S.infoErr)) {
    key = "sk"; h = `<span class="sk" style="width:60%"></span>`;
  } else if (S.test) {
    key = "ok" + curBaud() + devId() + S.lang + (S.info?.mode || "");
    h = `<div class="au-row"><div class="au-title ok grow">${tickSvg}<span>${esc(t("au.ok", { baud: curBaud(), id: devId() }))}</span></div>
         <button class="btn ghost sm" type="button" data-au="recheck">${esc(t("au.recheck"))}</button></div>` + wifiHint();
  } else {
    const tcp = S.infoErr === "tcp";
    key = "fail" + tcp + S.lang;
    h = `<div class="au-row"><div class="grow"><div class="au-title"><svg class="i"><use href="#i-warn"/></svg><span>${esc(t("au.fail_title"))}</span></div>
         <p class="helper" style="margin-top:6px">${esc(t(tcp ? "au.tcp" : "au.fail_body"))}</p></div>
         <button class="btn primary" type="button" data-au="start" ${tcp ? "disabled" : ""}><svg class="i"><use href="#i-search"/></svg><span>${esc(t("au.start"))}</span></button></div>`;
  }
  if (box.dataset.key === key) return;     // không đổi thì không vẽ lại — tránh giật
  box.dataset.key = key; box.innerHTML = h; M.fadeSwap(box);
  if (key.startsWith("fail")) M.wiggle(box.querySelector(".au-title svg"));
  box.querySelectorAll("[data-au]").forEach(b => b.addEventListener("click", () => {
    const k = b.dataset.au;
    if (k === "start") autoStart(); else if (k === "recheck") { S.autoShown = false; test(); } else if (k === "wifi") openWifiPicker(); else diag(false);
  }));
}
async function autoStart(){
  if (!S.sel || (S.auto && S.auto.running)) return;
  try { await api("/api/auto", { ip: S.sel.ip, mac: S.sel.mac }); } catch (e) { toast(errText(e), "err"); return; }
  S.autoShown = true; S.auto = { running: true, log: [], result: null }; renderAuto(); autoPoll();
}
async function autoPoll(){
  try { S.auto = await api("/api/auto"); } catch { return; }
  renderAuto();
  if (S.auto.running) { setTimeout(autoPoll, 1000); return; }
  const r = S.auto.result;
  if (r && r.ok) { toast(t("au.done_ok", r)); S.test = { id: r.id, bt: r.bt, et: r.et, time: new Date().toLocaleTimeString(LOCALE[S.lang]) }; }
  await scan();                     // IP có thể đổi sau khởi động lại — tìm lại theo MAC rồi đọc lại
}

// ─────────────────────────────── Hướng dẫn Artisan + sửa tệp .aset ───────────────────────────────
function renderGuide(){
  if (!S.sel) return;
  $("#g-s3").textContent = t("g.s3", { ip: S.sel.ip, port: netpPort(), id: devId() });
  const dl = $("#aset-dl");
  dl.href = `/api/aset?ip=${encodeURIComponent(S.sel.ip)}&port=${encodeURIComponent(netpPort())}&id=${devId()}&` + new URLSearchParams(asetVal());
  renderAsetOpts();
  dl.setAttribute("download", `OTL-Artisan-${S.sel.ip}.aset`);
}
// Artisan [Modbus]: type 3 = TCP (đếm 450 tệp .aset thật 19/10/2026: tệp dùng IP đều type=3), host, port, inputNdeviceId.
function patchAset(text, ip, port, id){
  const nl = text.includes("\r\n") ? "\r\n" : "\n";
  const lines = text.split(/\r?\n/);
  let start = lines.findIndex(l => l.trim() === "[Modbus]");
  if (start < 0) { lines.push("[Modbus]"); start = lines.length - 1; }
  let end = lines.findIndex((l, i) => i > start && /^\[.+\]\s*$/.test(l)); if (end < 0) end = lines.length;
  const want = { type: "3", host: ip, port: String(port) }, seen = {};
  for (let i = start + 1; i < end; i++) {
    const m = lines[i].match(/^([A-Za-z0-9_]+)=/); if (!m) continue;
    const k = m[1];
    if (k in want) { lines[i] = `${k}=${want[k]}`; seen[k] = true; }
    else if (/^input\d+deviceId$/.test(k)) lines[i] = `${k}=${id}`;
  }
  const add = Object.keys(want).filter(k => !seen[k]).map(k => `${k}=${want[k]}`);
  lines.splice(end, 0, ...add);
  return lines.join(nl);
}
function handleAset(file){
  if (!file || !S.sel) return;
  const res = $("#aset-res");
  if (!/\.aset$/i.test(file.name)) { res.style.color = "var(--red)"; res.textContent = t("g.bad"); M.shake($("#drop")); return; }
  const rd = new FileReader();
  rd.onload = () => {
    const text = String(rd.result || "");
    if (!/^\[General\]/m.test(text) && !/^\[Modbus\]/m.test(text)) { res.style.color = "var(--red)"; res.textContent = t("g.bad"); M.shake($("#drop")); return; }
    const name = file.name.replace(/\.aset$/i, "") + "_wifi.aset";
    const out = patchAset(text, S.sel.ip, netpPort(), devId());
    const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(new Blob([out], { type: "application/octet-stream" })), download: name });
    document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    res.style.color = ""; res.textContent = t("g.made", { name, ip: S.sel.ip, port: netpPort(), id: devId() });
    M.slideIn(res); M.pop($("#drop svg"));
  };
  rd.readAsText(file);
}

// Tuỳ chỉnh tệp Artisan (mặc định = máy O Tesla; nhớ theo máy tính). Nhãn nút mặc định theo ngôn ngữ trang:
// trang tiếng Pháp ⇒ nhãn tiếng Pháp (Artisan của khách Pháp hiện tiếng Pháp), còn lại tiếng Anh như máy O Tesla.
// Chỉ lưu những mục người dùng đổi khác mặc định (aset2) — đổi ngôn ngữ trang thì nhãn mặc định đổi theo.
const ASET_BASE = { mixcool: "split", vac: "1", unit: "C", xmin: "20", ymax: "250", zmax: "30", et: "0", auto: "0", save: "0", prefix: "", w: "g" };
const asetDef = () => ({ ...ASET_BASE, lbl: S.lang === "fr" ? "fr" : "en" });
const asetVal = () => ({ ...asetDef(), ...S.asetOver });
const ASET_OPTS = [
  ["mixcool", "ao.mixcool", [["split", "ao.split"], ["combined", "ao.combined"]]],
  ["vac", "ao.vac", [["1", "ao.show"], ["0", "ao.hide"]]],
  ["lbl", "ao.lbl", [["en", "English"], ["vi", "Tiếng Việt"], ["fr", "Français"]]],
  ["unit", "ao.unit", [["C", "°C"], ["F", "°F"]]],
  ["xmin", "ao.xmin", [["15", "15′"], ["20", "20′"], ["25", "25′"], ["30", "30′"]]],
  ["ymax", "ao.ymax", [["250", "250 °C"], ["275", "275 °C"], ["300", "300 °C"]]],
  ["zmax", "ao.zmax", [["20", "20"], ["30", "30"], ["40", "40"]]],
  ["et", "ao.et", [["1", "ao.show"], ["0", "ao.hide"]]],
  ["auto", "ao.auto", [["1", "ao.on"], ["0", "ao.off"]]],
  ["save", "ao.save", [["1", "ao.on"], ["0", "ao.off"]]],
  ["w", "ao.w", [["g", "g"], ["kg", "kg"]]],
];
S.asetOver = (() => {
  try {
    const v2 = store.get("aset2");
    if (v2) return JSON.parse(v2);
    const old = JSON.parse(store.get("aset") || "{}"), base = { ...ASET_BASE, lbl: "en" };   // bản 1.3 lưu cả bộ
    return Object.fromEntries(Object.entries(old).filter(([k, v]) => k in base && base[k] !== v));
  } catch { return {}; }
})();
const lab = (k) => k.startsWith("ao.") ? t(k) : k;
const ymaxLabel = (v) => asetVal().unit === "F" ? `${Math.round(v * 9 / 5 + 32)} °F` : `${v} °C`;   // trục nhiệt theo đơn vị đang chọn
function renderAsetOpts(){
  const g = $("#ao-grid"); if (!g) return;
  const A = asetVal(), D = asetDef();
  const sig = JSON.stringify(A) + S.lang;
  if (g.dataset.sig !== sig) {
    g.dataset.sig = sig;
    g.innerHTML = ASET_OPTS.map(([k, name, opts]) => `<div class="ao-row ${A[k] !== D[k] ? "changed" : ""}"><span>${esc(t(name))}</span>
      <div class="seg" role="group">${opts.map(([v, l]) => `<button type="button" data-ao="${k}" data-v="${v}" aria-pressed="${A[k] === v}">${esc(k === "ymax" ? ymaxLabel(v) : lab(l))}</button>`).join("")}</div></div>`).join("")
      + `<div class="ao-row ${A.prefix ? "changed" : ""}"><span>${esc(t("ao.prefix"))}</span><input id="ao-prefix" maxlength="8" spellcheck="false" placeholder="${esc(t("ao.prefix_ph"))}" value="${esc(A.prefix)}"></div>`;
    g.querySelectorAll("[data-ao]").forEach(b => b.addEventListener("click", () => setAset(b.dataset.ao, b.dataset.v)));
    $("#ao-prefix").addEventListener("change", e => setAset("prefix", e.target.value.replace(/[^A-Za-z0-9-]/g, "").slice(0, 8)));
    requestAnimationFrame(() => g.querySelectorAll(".seg").forEach(M.thumb));
  }
  const n = Object.keys(D).filter(k => A[k] !== D[k]).length;
  $("#ao-sum").textContent = n ? t("ao.n", { n }) : t("ao.none");
}
function saveAset(over){ S.asetOver = over; store.set("aset2", JSON.stringify(over)); }
function setAset(k, v){
  const { [k]: _old, ...rest } = S.asetOver;
  saveAset(v === asetDef()[k] ? rest : { ...rest, [k]: v });
  renderGuide();
  M.flash($("#aset-dl"));
}

// ─────────────────────────────── Hỗ trợ từ xa + kỹ thuật viên ───────────────────────────────
async function diag(save){
  let d;
  try { d = await api("/api/diag?ip=" + encodeURIComponent(S.sel?.ip || "")); } catch (e) { toast(errText(e), "err"); return; }
  if (save) {
    const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(new Blob([d.text], { type: "text/plain" })), download: "OTL-WiFi-Link-diagnostics.txt" });
    document.body.append(a); a.click(); a.remove(); M.run($("#diag-save svg"), [{ transform: "translateY(0)" }, { transform: "translateY(5px)" }, { transform: "translateY(0)" }], { spring: "soft" }); return;
  }
  try { await navigator.clipboard.writeText(d.text); } catch { const x = Object.assign(document.createElement("textarea"), { value: d.text }); document.body.append(x); x.select(); document.execCommand("copy"); x.remove(); }
  M.pop($("#diag-copy svg")); toast(t("rs.copied"));
}
async function techOpen(){
  let d; try { d = await api("/api/tech/challenge"); } catch (e) { toast(errText(e), "err"); return; }
  if (d.unlocked) { S.tech = true; renderTech(); $("#tech").scrollIntoView({ behavior: "smooth", block: "start" }); return; }
  $("#tm-ch").textContent = d.challenge; $("#tm-code").value = ""; fieldErr("tm-code", "");
  $("#tech-modal").hidden = false; setTimeout(() => $("#tm-code").focus(), 50);
  M.run($("#tech-modal .modal-box"), [{ transform: "scale(.94) translateY(10px)", opacity: 0 }, { transform: "none", opacity: 1 }], { spring: "soft" });
  M.roll($("#tm-ch"), d.challenge);
}
const techClose = () => {
  const a = M.run($("#tech-modal .modal-box"), [{ transform: "none", opacity: 1 }, { transform: "scale(.96)", opacity: 0 }], { duration: 160, easing: "ease-in", fill: "forwards" });
  const done = () => { $("#tech-modal").hidden = true; $("#tech-open").focus(); };
  a ? a.finished.then(done, done) : done();
};
async function techUnlock(){
  try { await api("/api/tech/unlock", { code: $("#tm-code").value }); }
  catch (e) { fieldErr("tm-code", errText(e)); return; }
  techClose(); S.tech = true; renderTech(); toast(t("tm.done"));
  setTimeout(() => { M.highlight($("#tech")); M.wiggle($("#tech h2 svg")); }, 250);
}
function renderTech(){
  const card = $("#tech"); if (!card) return;
  card.hidden = !S.tech || !S.sel;
  if (card.hidden) return;
  if (!S.techBaud) S.techBaud = curBaud();
  $("#baud-seg").innerHTML = [4800, 9600, 19200, 38400, 57600, 115200].map(b =>
    `<button type="button" data-baud="${b}" aria-pressed="${b === S.techBaud}">${b}</button>`).join("");
  $$("#baud-seg [data-baud]").forEach(b => b.addEventListener("click", () => { S.techBaud = +b.dataset.baud; renderTech(); }));
  requestAnimationFrame(() => M.thumb($("#baud-seg")));
}
async function techBaud(){
  const res = $("#tc-baud-res"); res.textContent = t("tc.baud_ing");
  try {
    const d = await api("/api/tech/uart", { ip: S.sel.ip, mac: S.sel.mac, port: netpPort(), baud: S.techBaud });
    res.textContent = t("tc.baud_ok", { baud: d.baud, ip: d.ip || "?" }); await scan();
  } catch (e) { res.textContent = errText(e); }
}
async function techRead(){
  const out = $("#tc-read-out");
  try {
    const addr = +$("#tc-addr").value;
    const d = await api("/api/tech/read", { ip: S.sel.ip, port: netpPort(), id: +$("#tc-id").value, addr, count: +$("#tc-count").value });
    out.textContent = d.values.map((v, i) => `${addr + i}: ${v}`).join("\n");
  } catch (e) { out.textContent = errText(e); }
}
async function techAt(){
  const cmd = $("#tc-cmd").value.trim().toUpperCase(), out = $("#tc-at-out"); if (!cmd) return;
  try { const d = await api("/api/tech/at", { ip: S.sel.ip, cmd }); out.textContent += `> ${d.cmd}\n${d.reply || "(no reply)"}\n`; }
  catch (e) { out.textContent += `> ${cmd}\n${errText(e)}\n`; }
  out.scrollTop = out.scrollHeight;
}

// ─────────────────────────────── Chọn wifi cho module ───────────────────────────────
function bars(sig){
  const n = sig >= 75 ? 4 : sig >= 50 ? 3 : sig >= 25 ? 2 : 1;
  return `<svg class="bars anim" viewBox="0 0 22 18" aria-hidden="true">${[0, 1, 2, 3].map(i =>
    `<rect x="${i * 6}" y="${14 - i * 4}" width="4" height="${4 + i * 4}" rx="1" class="${i < n ? "on" : ""}"/>`).join("")}</svg>`;
}
function renderWifiBtn(){
  const b = $("#wifi-scan"); if (!b) return;
  b.disabled = !!S.wifiBusy || !S.info;
  b.querySelector(".radar").classList.toggle("on", !!S.wifiBusy);
  b.lastElementChild.textContent = t(S.wifiBusy ? "w.scanning" : "w.scan");
  $("#wifi-stat").textContent = S.wifiBusy || !S.wifi ? "" : S.wifi.length ? t("w.found", { n: S.wifi.length }) : t("w.none");
}
function renderWifi(animate){
  renderWifiBtn();
  const list = $("#wifi-list"); if (!list) return;
  const cur = $("#f-ssid").value.trim();
  list.replaceChildren(...(S.wifi || []).map(n => {
    const b = document.createElement("button");
    b.type = "button"; b.className = "wifi-item"; b.dataset.key = n.ssid; b.setAttribute("role", "option");
    b.setAttribute("aria-selected", String(n.ssid === cur));
    const tags = [n.saved ? t("w.saved") : "", n.pc ? t("w.pc") : "", n.secure ? "" : t("w.open")].filter(Boolean);
    b.innerHTML = `${bars(n.signal)}<span style="min-width:0"><span class="nm"></span><span class="sub"><span class="num">${n.signal}%</span>${tags.map(x => `<span class="tg">${esc(x)}</span>`).join("")}</span></span>${n.secure ? '<svg class="i lk"><use href="#i-lock"/></svg>' : ""}`;
    b.querySelector(".nm").textContent = n.ssid;
    b.addEventListener("click", () => pickWifi(n));
    return b;
  }));
  if (animate) M.rise(list.children, 35);
}
async function wifiScan(){
  if (!S.sel || S.wifiBusy || !S.info) return;
  S.wifiBusy = true; renderWifiBtn();
  try { S.wifi = (await api("/api/wifi/scan?ip=" + encodeURIComponent(S.sel.ip))).networks; }
  catch (e) { S.wifi = []; toast(errText(e), "err"); M.shake($("#wifi-scan")); }
  S.wifiBusy = false; renderWifi(true);
  const cur = $("#f-ssid").value.trim();          // tự gợi ý: wifi đang nhập → đã nhớ → máy tính đã lưu
  const pick = S.wifi.find(n => n.ssid === cur && (n.saved || n.pc)) || S.wifi.find(n => n.saved) || S.wifi.find(n => n.pc);
  if (pick && !$("#f-skey").value) pickWifi(pick, true);
}
async function pickWifi(n, auto){
  $("#f-ssid").value = n.ssid;
  $$("#wifi-list .wifi-item").forEach(b => b.setAttribute("aria-selected", String(b.dataset.key === n.ssid)));
  M.bump($(`#wifi-list .wifi-item[aria-selected="true"]`));
  const src = $("#key-src"); src.textContent = "";
  if (!n.secure) $("#f-skey").value = "";
  if (n.secure && (n.saved || n.pc)) {
    try {
      const d = await api("/api/wifi/key?ssid=" + encodeURIComponent(n.ssid));
      if (d.key) {
        $("#f-skey").value = d.key;
        const f = $("#f-skey").closest(".field"); f.classList.add("filled"); M.flash(f); setTimeout(() => f.classList.remove("filled"), 1800);
        src.textContent = t(d.source === "tool" ? "w.filled_tool" : "w.filled_pc", { ssid: n.ssid }); M.slideIn(src, 0, -4);
      }
    } catch { /* không lấy được mật khẩu — người dùng tự gõ */ }
  }
  if (n.secure && !$("#f-skey").value) { src.textContent = t("w.need_pw", { ssid: n.ssid }); if (!auto) $("#f-skey").focus(); }
  validate(false); renderSummary();
}
function openWifiPicker(){
  if ($("#set-toggle").getAttribute("aria-expanded") !== "true") $("#set-toggle").click();
  setTimeout(() => { M.highlight($("#wifi-box")); wifiScan(); }, 160);
}

// ─────────────────────────────── Cài trọn gói module mới (tự động hoàn toàn) ───────────────────────────────
async function lookNear(){
  S.nearLooking = true; renderSetup();
  try { const d = await api("/api/pcwifi"); S.near = d.modules.length ? d.modules[0] : null; S.pcCur = d.current; }
  catch { S.near = null; }
  S.nearLooking = false; renderSetup();
  if (S.near && !S.sel && !S.setupCancelled) countdown();
}
function countdown(){
  clearInterval(S.cdTimer); S.cd = 5; renderSetup();
  const fg = $("#setup .su-count .fg");               // vòng đầy rồi rút dần hết trong 5 giây
  if (fg) { fg.style.transition = "none"; fg.style.strokeDashoffset = 0; void fg.getBoundingClientRect(); fg.style.transition = ""; requestAnimationFrame(() => { fg.style.strokeDashoffset = RING; }); }
  S.cdTimer = setInterval(() => {
    S.cd -= 1;
    const n = $("#su-cd"); if (n) M.roll(n, t("su.count", { s: S.cd }));
    if (S.cd <= 0) { clearInterval(S.cdTimer); S.cd = null; setupStart(); }
  }, 1000);
}
async function setupStart(){
  clearInterval(S.cdTimer); S.cd = null;
  if (!S.near) return;
  try { await api("/api/setup", { ssid: S.near.ssid }); } catch (e) { toast(errText(e), "err"); return; }
  S.setupOn = true; S.setupKey = ""; S.auto = { running: true, log: [], result: null }; $("#setup").dataset.mode = ""; renderSetup(); setupPoll();
}
async function setupPoll(){
  try { S.auto = await api("/api/auto"); } catch { setTimeout(setupPoll, 1500); return; }   // máy tính đang đổi wifi — thử lại
  renderSetup();
  if (S.auto.running) { setTimeout(setupPoll, 1000); return; }
  const r = S.auto.result || {};
  if (r.ok) { toast(t(r.mode === "STA" ? "su.done_sta" : "su.done_ap", r)); await scan(); }
}
function renderSetup(){
  const box = $("#setup"); if (!box) return;
  const a = S.auto, show = S.setupOn || ((S.near || S.nearLooking) && !S.sel);
  box.hidden = !show;
  if (show) $("#nosel").hidden = true; else if (!S.sel) $("#nosel").hidden = false;
  if (!show) return;
  if (S.setupOn && a && a.running) {
    if (box.dataset.mode !== "run") {
      box.dataset.mode = "run";
      box.innerHTML = `<div class="au-title">${ringSvg()}<span>${esc(t("su.running"))}</span></div><ol class="au-log"></ol><div id="su-need"></div><p class="helper">${esc(t("su.wait"))}</p>`;
      M.fadeSwap(box);
    }
    const ol = box.querySelector(".au-log");
    a.log.slice(ol.children.length).forEach(e => { const li = logLi(e); ol.append(li); M.slideIn(li, 0, 8); });
    [...ol.children].forEach((li, k) => li.classList.toggle("cur", k === ol.children.length - 1 && AU_CUR.includes(li.dataset.code)));
    requestAnimationFrame(() => { const fg = box.querySelector(".au-ring .fg"); if (fg) fg.style.strokeDashoffset = (RING * (1 - Math.min(0.95, (a.log.length + 1) / 16))).toFixed(1); });
    const need = $("#su-need");
    if (a.need && !need.dataset.on) {
      need.dataset.on = "1";
      need.innerHTML = `<p class="su-body">${esc(t("su.key_why"))}</p><div class="su-key"><div class="field"><label for="su-key">${esc(t("su.key_label", a.need))}</label>
        <div class="box"><input id="su-key" class="pw" type="password" maxlength="63" autocomplete="off"><button class="eye" type="button" data-eye="su-key"><svg class="i"><use href="#i-eye"/></svg></button></div><div class="err"></div></div>
        <button class="btn primary" type="button" id="su-key-ok">${esc(t("su.key_ok"))}</button><button class="btn ghost" type="button" id="su-key-skip">${esc(t("su.key_skip"))}</button></div>`;
      M.slideIn(need);
      const inp = $("#su-key");
      need.querySelector(".eye").addEventListener("click", () => { inp.type = inp.type === "password" ? "text" : "password"; });
      $("#su-key-ok").addEventListener("click", async () => {
        const v = inp.value;
        if (v.length < 8 || v.length > 63 || /,/.test(v)) { fieldErr("su-key", t("v.len", { lo: 8, hi: 63 })); return; }
        try { await api("/api/setup/key", { key: v }); need.innerHTML = ""; } catch (e) { fieldErr("su-key", errText(e)); }
      });
      $("#su-key-skip").addEventListener("click", async () => { try { await api("/api/setup/key", { key: "" }); need.innerHTML = ""; } catch { /* bỏ qua */ } });
      setTimeout(() => inp.focus(), 60);
    } else if (!a.need && need.dataset.on) { need.dataset.on = ""; need.innerHTML = ""; }
    return;
  }
  let h, key;
  if (S.setupOn && a && a.result) {
    const r = a.result;
    key = "res" + JSON.stringify(r) + S.lang;
    h = `<div class="au-title">${esc(t("su.title"))}</div><ol class="au-log">${a.log.map(e => logLi(e).outerHTML).join("")}</ol>`;
    h += r.ok ? `<div class="au-res">${tickSvg}<span>${esc(t(r.mode === "STA" ? "su.done_sta" : "su.done_ap", r))}</span></div>`
              : `<div class="au-res fail">${esc(t(r.reason === "sta_lost" ? "su.fail_sta" : r.reason === "pc_join" ? "err.pc_join" : "su.fail", { ssid: r.ssid || "" }))}</div>`;
    h += `<div class="su-row">${r.ok ? "" : `<button class="btn" type="button" data-su="again">${esc(t("su.again"))}</button><button class="btn ghost" type="button" data-su="diag">${esc(t("rs.copy"))}</button>`}
          <button class="btn ghost" type="button" data-su="close">${esc(t("su.close"))}</button></div>`;
  } else if (S.nearLooking && !S.near) {
    key = "look" + S.lang;
    h = `<div class="au-title"><span class="radar on"><svg class="i"><use href="#i-wifi"/></svg><i></i><i></i></span><span>${esc(t("su.looking"))}</span></div>`;
  } else if (S.near) {
    const n = S.near, orig = S.pcCur && !/^(USR-|OTL Roaster$)/i.test(S.pcCur) ? S.pcCur : null;
    key = "near" + n.ssid + S.lang + (S.cd == null ? "x" : "c") + !!S.setupCancelled;
    h = `<div class="au-title"><svg class="i"><use href="#i-wifi"/></svg><span>${esc(t("su.title"))}</span></div>
      <p class="su-body">${esc(t(orig ? "su.body" : "su.body_ap", { label: n.label, signal: n.signal, orig }))}</p>
      <div class="su-row">${S.cd != null ? `<span class="su-count">${ringSvg()}<span id="su-cd" class="num">${esc(t("su.count", { s: S.cd }))}</span></span>` : ""}
        <button class="btn primary" type="button" data-su="start"><svg class="i"><use href="#i-play"/></svg><span>${esc(t("su.start"))}</span></button>
        ${S.cd != null ? `<button class="btn ghost" type="button" data-su="cancel">${esc(t("su.cancel"))}</button>` : ""}</div>
      ${S.setupCancelled ? `<p class="helper">${esc(t("su.cancelled"))}</p>` : ""}`;
  } else { box.hidden = true; return; }
  if (box.dataset.key === key) return;
  box.dataset.key = key; box.dataset.mode = "static"; box.innerHTML = h; M.fadeSwap(box);
  box.querySelectorAll("[data-su]").forEach(b => b.addEventListener("click", () => {
    const k = b.dataset.su;
    if (k === "start") setupStart();
    else if (k === "cancel") { clearInterval(S.cdTimer); S.cd = null; S.setupCancelled = true; renderSetup(); }
    else if (k === "again") { S.setupOn = false; S.setupCancelled = false; lookNear(); }
    else if (k === "diag") diag(false);
    else { S.setupOn = false; S.near = null; renderSetup(); renderSel(); }
  }));
}

// ─────────────────────────────── Tab Kết nối / Hướng dẫn ───────────────────────────────
function showView(name){
  const cur = $("#view-help").hidden ? "main" : "help";
  if (name === cur) return Promise.resolve();
  store.set("view", name);
  return M.transition(() => {
    $("#view-main").hidden = name !== "main"; $("#view-help").hidden = name !== "help";
    $$("[data-view]").forEach(b => b.setAttribute("aria-selected", String(b.dataset.view === name)));
    M.thumbs(); window.scrollTo(0, 0);
  }, name === "help" ? "slide" : "slide-back").then(() => { if (name === "help") requestAnimationFrame(tocThumb); });
}

// ─────────────────────────────── Gắn sự kiện ───────────────────────────────
$$("[data-lang]").forEach(b => b.addEventListener("click", () => { if (S.lang === b.dataset.lang) return; S.lang = b.dataset.lang; store.set("lang", S.lang); applyLang(true); }));
$("#scan").addEventListener("click", scan);
$("#test").addEventListener("click", () => { S.autoShown = false; M.run($("#test svg"), [{ transform: "scale(1)" }, { transform: "scale(1.3)" }, { transform: "scale(1)" }], { spring: "soft" }); test(); });   // đọc thử bằng tay thay kết quả tự dò cũ
$$("[data-copy]").forEach(b => b.addEventListener("click", () => {
  const k = b.dataset.copy; if (k === "ip") M.flash($("#h-ip")); copy(k === "type" ? "TCP" : k === "port" ? netpPort() : k === "dev" ? String(devId()) : S.sel?.ip || "", b);
}));
$("#set-toggle").addEventListener("click", () => {
  const open = $("#set-toggle").getAttribute("aria-expanded") !== "true";
  $("#set-toggle").setAttribute("aria-expanded", String(open));
  $("#set-body").classList.toggle("open", open);
});
$("#pin").addEventListener("click", () => {
  S.wan = "static"; renderSegs(); renderSummary();
  if ($("#set-toggle").getAttribute("aria-expanded") !== "true") $("#set-toggle").click();
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  $("#settings").scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
  setTimeout(() => $("#apply").focus({ preventScroll: true }), reduce ? 0 : 350);
});
$$("[data-wan]").forEach(b => b.addEventListener("click", () => { S.wan = b.dataset.wan; renderSegs(); renderSummary(); }));
$$("[data-mode]").forEach(b => b.addEventListener("click", () => { S.mode = b.dataset.mode; renderSegs(); renderSummary(); }));
$$(".field input").forEach(inp => {
  inp.addEventListener("input", renderSummary);
  inp.addEventListener("blur", () => { validate(true); renderSummary(); });
});
$$("[data-eye]").forEach(b => {
  const inp = $("#" + b.dataset.eye);
  b.setAttribute("aria-label", "Show / hide");
  b.addEventListener("click", () => { inp.type = inp.type === "password" ? "text" : "password"; });
});
$("#quit").addEventListener("click", async () => { try { await api("/api/quit", {}); } catch { /* đã tắt */ } serverDown(); });
holdButton($("#apply"), 1000, applyNow);
$$("[data-view]").forEach(b => b.addEventListener("click", () => showView(b.dataset.view)));
$("#wifi-scan").addEventListener("click", wifiScan);
$("#ao-reset").addEventListener("click", () => { saveAset({}); renderGuide(); });
$("#aset-opts").addEventListener("toggle", () => requestAnimationFrame(() => $$("#ao-grid .seg").forEach(M.thumb)));
$("#aset-dl").addEventListener("click", () => M.run($("#aset-dl svg"), [{ transform: "translateY(0)" }, { transform: "translateY(5px)" }, { transform: "translateY(0)" }], { spring: "soft" }));
$("#f-ssid").addEventListener("input", () => $$("#wifi-list .wifi-item").forEach(b => b.setAttribute("aria-selected", String(b.dataset.key === $("#f-ssid").value.trim()))));
$("#diag-copy").addEventListener("click", () => diag(false));
$("#diag-save").addEventListener("click", () => diag(true));
$("#tech-open").addEventListener("click", techOpen);
$("#tm-cancel").addEventListener("click", techClose);
$("#tm-ok").addEventListener("click", techUnlock);
$("#tm-copy").addEventListener("click", () => copy($("#tm-ch").textContent, $("#tm-copy")));
$("#tech-modal").addEventListener("keydown", e => { if (e.key === "Escape") techClose(); });
$("#tech-modal").addEventListener("click", e => { if (e.target.id === "tech-modal") techClose(); });
$("#tc-baud").addEventListener("click", techBaud);
$("#tc-read").addEventListener("click", techRead);
$("#tc-send").addEventListener("click", techAt);
$("#tc-cmd").addEventListener("keydown", e => { if (e.key === "Enter") techAt(); });
const drop = $("#drop");
$("#aset").addEventListener("change", e => handleAset(e.target.files[0]));
["dragenter", "dragover"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave", "drop"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove("over"); }));
drop.addEventListener("drop", e => handleAset(e.dataTransfer.files[0]));
api("/api/tech/challenge").then(d => { if (d.unlocked) { S.tech = true; renderTech(); } }).catch(() => {});
api("/api/auto").then(d => {
  if (!d.running) return;
  S.auto = d;
  if (d.log.some(e => e.code === "pc_join")) { S.setupOn = true; renderSetup(); setupPoll(); } else { S.autoShown = true; autoPoll(); }
}).catch(() => {});

applyLang();
requestAnimationFrame(M.thumbs);
if (store.get("view") === "help") showView("help");
scan();
