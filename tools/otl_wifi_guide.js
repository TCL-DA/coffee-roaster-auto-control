// OTL WiFi Link — tab Hướng dẫn (VI / EN / FR). Viết ở mức người vận hành: không tên hãng module, không thanh ghi.
// Mỗi mục có thể trỏ tới một khu trên tab Kết nối (target) — bấm "Xem trên màn hình" là chuyển tab và làm nổi khu đó.
// FR: tên menu Artisan theo đúng Artisan bản tiếng Pháp (Aide → Charger les réglages…, Config → Port…, onglet Modbus).
"use strict";

const GUIDE = [
  { id: "start", icon: "i-play", target: "#auto",
    t: { vi: "Bắt đầu nhanh", en: "Quick start", fr: "Démarrage rapide" },
    steps: {
      vi: ["Mở OTL WiFi Link — chương trình tự tìm module wifi của máy rang và tự đọc thử nhiệt độ.",
           "Thẻ ghi “Máy rang đang trả lời” là xong phần nối: sang mục Cài Artisan.",
           "Thẻ vàng “Máy rang chưa trả lời”: bấm Tự động dò & sửa và chờ tối đa 2–3 phút."],
      en: ["Open OTL WiFi Link — it finds the roaster's Wi-Fi module and test-reads the temperatures by itself.",
           "If the panel says “Roaster is answering”, the link is done: go to Set up Artisan.",
           "Yellow panel “Roaster not answering”: click Auto detect & fix and wait up to 2–3 minutes."],
      fr: ["Ouvrez OTL WiFi Link : il trouve tout seul le module Wi-Fi du torréfacteur et lit les températures pour test.",
           "Si le panneau indique « Le torréfacteur répond », la liaison est faite : passez à Configurer Artisan.",
           "Panneau jaune « Le torréfacteur ne répond pas » : cliquez sur Détecter et corriger et patientez 2 à 3 minutes au plus."] } },
  { id: "new", icon: "i-wifi", target: "#scan",
    t: { vi: "Module mới mua hoặc bị cài sai", en: "New or wrongly configured module", fr: "Module neuf ou mal configuré" },
    steps: {
      vi: ["Cấp điện cho module. Module mới hoặc vừa reset phát một wifi không mật khẩu (tên mặc định của nhà sản xuất).",
           "Mở OTL WiFi Link: chương trình tự thấy wifi của module, hiện thẻ “Tìm thấy module mới” và đếm ngược 5 giây rồi tự cài.",
           "Chương trình tự nối máy tính vào wifi module, cài chuẩn O Tesla, dò tốc độ, nối module vào wifi quán (dùng mật khẩu máy tính đã lưu) rồi đưa máy tính về lại. Máy tính tạm mất internet 2–4 phút.",
           "Xong: module hiện trong danh sách, máy rang trả lời — sang mục Cài Artisan."],
      en: ["Power the module. A new or freshly reset module broadcasts an open Wi-Fi (the manufacturer's default name).",
           "Open OTL WiFi Link: it spots the module's Wi-Fi, shows “New module found” and counts down 5 seconds, then sets it up by itself.",
           "The program joins the module's Wi-Fi, applies the O Tesla standard, finds the speed, joins the module to your shop Wi-Fi (using the password this computer saved) and brings the computer back. The computer has no internet for 2–4 minutes.",
           "Done: the module shows in the list and the roaster answers — go to Set up Artisan."],
      fr: ["Mettez le module sous tension. Un module neuf ou réinitialisé diffuse un Wi-Fi ouvert (nom par défaut du fabricant).",
           "Ouvrez OTL WiFi Link : il repère le Wi-Fi du module, affiche « Nouveau module détecté », compte 5 secondes puis le configure tout seul.",
           "Le programme rejoint le Wi-Fi du module, applique la configuration standard O Tesla, détecte la vitesse, connecte le module au Wi-Fi de votre atelier puis ramène l’ordinateur sur son Wi-Fi. L’ordinateur n’a pas Internet pendant 2 à 4 minutes.",
           "Sur Mac, si la carte « Nouveau module détecté » n’apparaît pas : dans le menu Wi-Fi de la barre des menus, rejoignez le Wi-Fi du module, puis cliquez sur Rechercher les modules et sur Détecter et corriger.",
           "Terminé : le module apparaît dans la liste et le torréfacteur répond — passez à Configurer Artisan."] },
    note: { vi: "Module không vào được mạng (cài sai wifi, sai mật khẩu): giữ nút Reload trên module 3–5 giây để về cài đặt gốc, rồi làm lại từ bước 2.",
            en: "Module cannot get online (wrong Wi-Fi or password): hold the Reload button on the module for 3–5 s to restore factory settings, then start again from step 2.",
            fr: "Le module n’accède pas au réseau (mauvais Wi-Fi ou mot de passe) : maintenez le bouton Reload du module 3 à 5 s pour revenir aux réglages d’usine, puis reprenez à l’étape 2." } },
  { id: "auto", icon: "i-search", target: "#auto",
    t: { vi: "Tự động dò & sửa", en: "Auto detect & fix", fr: "Détecter et corriger" },
    steps: {
      vi: ["Kiểm module có đúng chuẩn O Tesla không; lệch thì sửa (chế độ truyền, cổng kết nối, khung truyền).",
           "Thử lần lượt các tốc độ truyền; mỗi lần module khởi động lại khoảng 25 giây.",
           "Gặp tốc độ máy rang trả lời thì giữ lại; không khớp thì trả module về như cũ và gợi ý gửi chẩn đoán cho O Tesla."],
      en: ["Checks the module against the O Tesla standard and fixes any difference (transfer mode, network port, frame).",
           "Tries each link speed; the module restarts for about 25 seconds each time.",
           "Keeps the speed the roaster answers on; if none matches, puts the module back and suggests sending diagnostics to O Tesla."],
      fr: ["Vérifie que le module respecte le standard O Tesla et corrige les écarts (mode de transfert, port réseau, trame).",
           "Essaie chaque vitesse de liaison ; le module redémarre environ 25 secondes à chaque fois.",
           "Garde la vitesse à laquelle le torréfacteur répond ; si aucune ne convient, remet le module dans son état initial et propose d’envoyer le diagnostic à O Tesla."] },
    note: { vi: "Trong lúc dò: để trang mở và để máy rang bật.", en: "While detecting: keep this page open and the roaster on.",
            fr: "Pendant la détection : gardez cette page ouverte et le torréfacteur allumé." } },
  { id: "artisan", icon: "i-help", target: "#guide",
    t: { vi: "Cài Artisan", en: "Set up Artisan", fr: "Configurer Artisan" },
    steps: {
      vi: ["Bấm Mở trang tải Artisan, tải bản cho Windows hoặc macOS và cài như phần mềm bình thường.",
           "Bấm Tải tệp Artisan cho máy này (.aset) — tệp dựng sẵn cho máy O Tesla, đã điền kết nối wifi. Có tệp .aset riêng của máy thì kéo vào ô bên dưới nút để điền kết nối wifi.",
           "Lần đầu mở Artisan: chọn Config → Mode → Expert. Artisan mới cài ở chế độ Standard nên menu chưa có mục Load Settings… và Port… — chế độ Expert mới có.",
           "Trong Artisan: Help → Load Settings… → chọn tệp vừa tải. Trên Mac phải nạp qua menu này — bấm đúp tệp .aset không nạp được. Hoặc điền tay ở Config → Port… → tab Modbus.",
           "Bấm ON trên Artisan: đường BT / ET chạy là xong."],
      en: ["Click Open Artisan download page, download the Windows or macOS version and install it.",
           "Click Download Artisan file for this roaster (.aset) — a ready-made file for O Tesla roasters with the Wi-Fi link filled in. Have this machine's own .aset file? Drop it on the box below the button to fill in the Wi-Fi link.",
           "First time in Artisan: choose Config → Mode → Expert. A fresh Artisan starts in Standard mode, where the Load Settings… and Port… items are hidden.",
           "In Artisan: Help → Load Settings… → choose the downloaded file. On a Mac you must use this menu — double-clicking the .aset file does not load it. Or enter it by hand in Config → Port… → Modbus tab.",
           "Click ON in Artisan: when BT / ET curves run, you are done."],
      fr: ["Cliquez sur Ouvrir la page de téléchargement d’Artisan, téléchargez la version Windows ou macOS et installez-la.",
           "Cliquez sur Télécharger le fichier Artisan de ce torréfacteur (.aset) : un fichier prêt à l’emploi pour les torréfacteurs O Tesla, liaison Wi-Fi déjà renseignée. Vous avez le fichier .aset propre à la machine ? Déposez-le dans la zone sous le bouton pour y renseigner la liaison Wi-Fi.",
           "À la première ouverture d’Artisan : choisissez Config → Mode → Expert. Une installation neuve d’Artisan démarre en mode Standard : les menus Charger les réglages… et Port… n’y apparaissent pas.",
           "Dans Artisan : Aide → Charger les réglages… → sélectionnez le fichier téléchargé. Sur Mac, passez obligatoirement par ce menu : un double-clic sur le fichier .aset ne le charge pas. Ou saisie manuelle dans Config → Port… → onglet Modbus.",
           "Cliquez sur ON dans Artisan : quand les courbes BT / ET avancent, c’est terminé."] },
    note: { vi: "Artisan hiện tiếng gì là theo ngôn ngữ của máy tính; đổi ở Config → Language.",
            en: "Artisan's language follows the computer's language; change it in Config → Language.",
            fr: "Artisan s’affiche dans la langue de l’ordinateur (en français sur un Mac en français) ; pour la changer : Config → Langue." } },
  { id: "wifi", icon: "i-wifi", target: "#wifi-box",
    t: { vi: "Nối module vào wifi quán", en: "Join shop Wi-Fi", fr: "Connecter le module au Wi-Fi de l’atelier" },
    steps: {
      vi: ["Mở Cài đặt module, bấm Quét wifi quanh module.",
           "Chọn wifi của quán. Wifi đã nhớ hoặc máy tính đã lưu sẽ tự điền mật khẩu.",
           "Kiểm mật khẩu, để ô Nhớ mật khẩu trên máy này, rồi giữ nút ghi 1 giây.",
           "Module khởi động lại và bắt wifi quán. Cho máy tính bắt cùng wifi đó rồi bấm Tìm module."],
      en: ["Open Module settings and click Scan Wi-Fi around the module.",
           "Pick your shop Wi-Fi. A remembered network, or one this computer already knows, fills in the password.",
           "Check the password, keep Remember password on this computer, then hold the write button for 1 second.",
           "The module restarts and joins the shop Wi-Fi. Join the same Wi-Fi on the computer and click Find modules."],
      fr: ["Ouvrez Réglages du module et cliquez sur Scanner le Wi-Fi autour du module.",
           "Choisissez le Wi-Fi de votre atelier. Un réseau mémorisé, ou déjà connu de cet ordinateur, renseigne le mot de passe tout seul.",
           "Vérifiez le mot de passe, laissez cochée la case Mémoriser le mot de passe sur cet ordinateur, puis maintenez le bouton d’écriture 1 seconde.",
           "Le module redémarre et rejoint le Wi-Fi de l’atelier. Connectez l’ordinateur au même Wi-Fi et cliquez sur Rechercher les modules."] },
    note: { vi: "Module không có wifi dự phòng: sai mật khẩu là module mất mạng — khi đó giữ nút Reload rồi làm lại theo mục Module mới.",
            en: "The module has no backup Wi-Fi: a wrong password takes it offline — then hold Reload and follow New module.",
            fr: "Le module n’a pas de Wi-Fi de secours : un mot de passe erroné le met hors réseau — maintenez alors Reload et suivez Module neuf." } },
  { id: "pin", icon: "i-pin", target: "#pin",
    t: { vi: "Giữ IP cố định", en: "Pin the IP", fr: "Fixer l’IP" },
    steps: {
      vi: ["Nhãn vàng “IP tự cấp — có thể đổi”: bấm Giữ cố định IP này.",
           "Xem khung Sẽ ghi, rồi giữ nút đỏ 1 giây. Module khởi động lại khoảng 12 giây."],
      en: ["Yellow label “Auto IP (DHCP) — may change”: click Pin this IP.",
           "Check the Will write box, then hold the red button for 1 second. The module restarts in about 12 seconds."],
      fr: ["Étiquette jaune « IP automatique (DHCP) — peut changer » : cliquez sur Fixer cette IP.",
           "Vérifiez le cadre Sera écrit, puis maintenez le bouton rouge 1 seconde. Le module redémarre en 12 secondes environ."] } },
  { id: "pass", icon: "i-lock", target: "#settings",
    t: { vi: "Mật khẩu wifi riêng của module", en: "Module's own Wi-Fi password", fr: "Mot de passe du Wi-Fi propre du module" },
    steps: {
      vi: ["Wifi “OTL Roaster” ban đầu không có mật khẩu — ai ở gần cũng vào được.",
           "Gõ mật khẩu 8–63 ký tự vào ô Mật khẩu wifi tự phát, giữ nút ghi 1 giây, ghi lại mật khẩu ở nơi an toàn."],
      en: ["The “OTL Roaster” Wi-Fi has no password at first — anyone nearby can join.",
           "Type a password of 8–63 characters in Password for module's own Wi-Fi, hold the write button for 1 second and keep the password safe."],
      fr: ["Le Wi-Fi « OTL Roaster » n’a pas de mot de passe au départ : toute personne à proximité peut s’y connecter.",
           "Saisissez un mot de passe de 8 à 63 caractères dans Mot de passe du Wi-Fi propre du module, maintenez le bouton d’écriture 1 seconde et conservez le mot de passe en lieu sûr."] } },
  { id: "trouble", icon: "i-warn",
    t: { vi: "Xử lý sự cố", en: "Troubleshooting", fr: "Dépannage" },
    faq: {
      vi: [["Không thấy module nào", "Máy tính và máy rang phải cùng một wifi; máy rang đã bật. Thử bắt wifi “OTL Roaster”. Windows: cho phép OTL WiFi Link qua tường lửa. Mac: Cài đặt hệ thống → Quyền riêng tư & Bảo mật → Mạng cục bộ → bật Terminal."],
           ["Máy rang chưa trả lời", "Kiểm máy rang đã bật, rồi bấm Tự động dò & sửa. Dò không ra: gửi thông tin chẩn đoán cho O Tesla."],
           ["Nhãn “Tìm qua quét TCP”", "Wifi này chặn gói cài đặt nên chỉ đọc được IP. Artisan vẫn dùng được. Muốn tự sửa: bắt wifi “OTL Roaster”."],
           ["Artisan không có mục Load Settings… hoặc Port…", "Artisan đang ở chế độ Standard: chọn Config → Mode → Expert."],
           ["Artisan báo lỗi kết nối", "So IP trong OTL WiFi Link với ô Host của Artisan; Type TCP, Port 8899. Nhanh nhất: tải lại tệp .aset rồi nạp lại."],
           ["Trang báo OTL WiFi Link đã tắt", "Chương trình tự tắt khi trang đóng lâu. Mở lại chương trình."]],
      en: [["No module found", "The computer and roaster must be on the same Wi-Fi, roaster powered on. Try joining “OTL Roaster”. Windows: allow OTL WiFi Link through the firewall. Mac: System Settings → Privacy & Security → Local Network → turn on Terminal."],
           ["Roaster not answering", "Check the roaster is on, then click Auto detect & fix. If nothing is found, send diagnostics to O Tesla."],
           ["“Found by TCP sweep” label", "This Wi-Fi blocks setup packets, so only the IP is known. Artisan still works. To auto-fix, join “OTL Roaster”."],
           ["Artisan has no Load Settings… or Port… item", "Artisan is in Standard mode: choose Config → Mode → Expert."],
           ["Artisan connection error", "Compare the IP in OTL WiFi Link with Artisan's Host; Type TCP, Port 8899. Quickest: download the .aset file again and load it."],
           ["Page says OTL WiFi Link has stopped", "The program stops when its page has been closed for a while. Start it again."]],
      fr: [["Aucun module trouvé", "L’ordinateur et le torréfacteur doivent être sur le même Wi-Fi, torréfacteur allumé. Essayez de rejoindre « OTL Roaster ». Mac : Réglages Système → Confidentialité et sécurité → Réseau local → activez Terminal. Windows : autorisez OTL WiFi Link dans le pare-feu."],
           ["Le torréfacteur ne répond pas", "Vérifiez que le torréfacteur est allumé, puis cliquez sur Détecter et corriger. Si rien n’est trouvé, envoyez le diagnostic à O Tesla."],
           ["Étiquette « Trouvé par balayage TCP »", "Ce Wi-Fi bloque les paquets de configuration : seule l’IP est connue. Artisan fonctionne quand même. Pour la correction automatique, rejoignez « OTL Roaster »."],
           ["Artisan n’a pas de menu Charger les réglages… ni Port…", "Artisan est en mode Standard : choisissez Config → Mode → Expert."],
           ["Artisan signale une erreur de connexion", "Comparez l’IP affichée dans OTL WiFi Link avec le champ Hôte d’Artisan ; Type TCP, Port 8899. Le plus rapide : téléchargez de nouveau le fichier .aset et chargez-le."],
           ["La page indique « OTL WiFi Link est arrêté »", "Le programme s’arrête seul quand sa page reste fermée un moment. Relancez-le."]] } },
  { id: "remote", icon: "i-help", target: "#diag-copy",
    t: { vi: "Hỗ trợ từ xa", en: "Remote support", fr: "Assistance à distance" },
    steps: {
      vi: ["Chép thông tin chẩn đoán rồi dán gửi O Tesla qua Zalo / WhatsApp (không có mật khẩu wifi).",
           "Cần kỹ thuật viên điều khiển máy tính: cài UltraViewer hoặc TeamViewer, gửi ID và mật khẩu cho O Tesla.",
           "Chế độ kỹ thuật viên chỉ dùng khi O Tesla yêu cầu: gửi mã thử, nhận mã mở, dán vào ô (mã thử dùng trong 30 phút)."],
      en: ["Copy diagnostics and paste them to O Tesla on Zalo / WhatsApp (no Wi-Fi passwords included).",
           "Need a technician to control your computer: install UltraViewer or TeamViewer and send the ID and password to O Tesla.",
           "Technician mode only when O Tesla asks: send the challenge, receive the unlock code, paste it (a challenge lasts 30 minutes)."],
      fr: ["Copiez le diagnostic et envoyez-le à O Tesla par WhatsApp ou e-mail (aucun mot de passe Wi-Fi n’y figure).",
           "Besoin qu’un technicien prenne la main sur votre ordinateur : installez TeamViewer et envoyez l’ID et le mot de passe à O Tesla.",
           "Mode technicien uniquement à la demande d’O Tesla : envoyez le code de défi, recevez le code de déverrouillage, collez-le (un code de défi est valable 30 minutes)."] } },
];

// Chữ của mục theo ngôn ngữ đang chọn; thiếu thì lùi về tiếng Anh. Tiếng Pháp: khoảng trắng không ngắt dòng trước
// : ; ? ! % » và sau « (chính tả Pháp) — viết nguồn bằng dấu cách thường cho dễ đọc, đổi lúc hiện.
const frTypo = (v) => Array.isArray(v) ? v.map(frTypo)
  : String(v).replace(/ ([:%\u00bb])/g, "\u00a0$1").replace(/ ([;?!])/g, "\u202f$1").replace(/\u00ab /g, "\u00ab\u00a0");
const tr = (o) => { const v = o[S.lang] ?? o.en; return S.lang === "fr" ? frTypo(v) : v; };

function renderHelp() {
  const toc = document.getElementById("help-toc-list"), body = document.getElementById("help-body");
  if (!toc || !body) return;
  toc.innerHTML = GUIDE.map((g, i) =>
    `<a href="#h-${g.id}" data-sec="${g.id}" ${i === 0 ? 'aria-current="true"' : ""}><svg class="i"><use href="#${g.icon}"/></svg><span>${esc(tr(g.t))}</span></a>`).join("");
  body.innerHTML = GUIDE.map((g, i) => {
    const steps = g.steps ? `<ol class="h-steps">${tr(g.steps).map(s => `<li>${esc(s)}</li>`).join("")}</ol>` : "";
    const faq = g.faq ? `<div class="h-faq">${tr(g.faq).map(([q, a]) => `<details><summary><svg class="i"><use href="#i-chev-r"/></svg><span>${esc(q)}</span></summary><p>${esc(a)}</p></details>`).join("")}</div>` : "";
    const note = g.note ? `<p class="h-note"><svg class="i"><use href="#i-warn"/></svg><span>${esc(tr(g.note))}</span></p>` : "";
    const go = g.target ? `<button class="btn sm h-go" type="button" data-go="${g.target}"><span>${esc(t("h.go"))}</span><svg class="i"><use href="#i-chev-r"/></svg></button>` : "";
    return `<section class="card h-sec" id="h-${g.id}" data-sec="${g.id}">
      <div class="h-head"><span class="h-num num">${i + 1}</span><h2>${esc(tr(g.t))}</h2>${go}</div>${steps}${faq}${note}</section>`;
  }).join("") + `<section class="card h-sec" id="h-contact" data-sec="contact"><div class="h-head"><span class="h-num num">${GUIDE.length + 1}</span><h2>${esc(t("h.contact"))}</h2></div>
      <p class="h-contact">${esc(t("co.name2"))} · <a href="tel:+84936198938">+84 936 198 938</a> · <a href="https://wa.me/84936198938" target="_blank" rel="noopener">WhatsApp +84 936 198 938</a> · <a href="mailto:otlpro.com@gmail.com">otlpro.com@gmail.com</a> · <a href="https://otlpro.com" target="_blank" rel="noopener">otlpro.com</a></p></section>`;
  body.querySelectorAll("[data-go]").forEach(b => b.addEventListener("click", () => goTo(b.dataset.go)));
  toc.querySelectorAll("a").forEach(a => a.addEventListener("click", (e) => {
    e.preventDefault();
    document.getElementById("h-" + a.dataset.sec)?.scrollIntoView({ behavior: M.on() ? "smooth" : "auto", block: "start" });
  }));
  // Hiện dần từng mục khi cuộn tới + thanh TOC trượt theo mục đang đọc
  const io = new IntersectionObserver((ents) => ents.forEach(en => {
    if (en.isIntersecting) en.target.classList.add("in");
  }), { threshold: 0.12 });
  body.querySelectorAll(".h-sec").forEach(s => io.observe(s));
  const spy = new IntersectionObserver((ents) => {
    const vis = ents.filter(e => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
    if (!vis) return;
    toc.querySelectorAll("a").forEach(a => a.setAttribute("aria-current", String(a.dataset.sec === vis.target.dataset.sec)));
    tocThumb();
  }, { rootMargin: "-20% 0px -60% 0px" });
  body.querySelectorAll(".h-sec").forEach(s => spy.observe(s));
  requestAnimationFrame(tocThumb);
}

// Ô nền trượt dọc theo mục lục (cùng kiểu thanh trượt nút gạt).
function tocThumb() {
  const toc = document.getElementById("help-toc-list"); if (!toc) return;
  let th = toc.querySelector(".toc-thumb");
  if (!th) { th = document.createElement("span"); th.className = "toc-thumb"; toc.prepend(th); }
  const a = toc.querySelector('a[aria-current="true"]'); if (!a) return;
  th.style.height = a.offsetHeight + "px";
  th.style.transform = `translateY(${a.offsetTop}px)`;
}

// Từ hướng dẫn nhảy sang tab Kết nối và làm nổi khu liên quan (mở sẵn Cài đặt module nếu khu nằm trong đó).
function goTo(sel) {
  showView("main").then(() => {
    let el = document.querySelector(sel);
    if (el && el.closest("#set-body") && $("#set-toggle").getAttribute("aria-expanded") !== "true") $("#set-toggle").click();
    if (el && el.offsetParent === null) el = el.closest(".card") || el;
    setTimeout(() => M.highlight(el), 120);
  });
}
