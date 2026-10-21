# Đường rang dự kiến — đợt nâng cấp 13/09/2026

Hộp **Sửa hồ sơ → Đường rang dự kiến**. Đợt này làm hai việc: vá ba lỗi nền khiến
kế hoạch và máy nói hai điều khác nhau, rồi nâng phần xem trước từ "vẽ cho đẹp"
thành một thứ thợ rang dùng được để ra quyết định.

Gốc phát hiện: Codex soát chéo code hai bên (OTL và Artisan `master` commit
`58be9351`) tối 12/09 — xem
[đối chiếu với Artisan Designer](duong-rang-du-kien-vs-artisan-designer-design-critique.md).

---

## 1. Ba lỗi nền đã vá

### 1.1 Preview nói một đằng, máy chấm một nẻo

`loadProfile()` chỉ đẩy **nhiệt xả** sang `R.mileSet.DROP`. `p.deT` và `p.fcsT`
không được đẩy sang, nên bản xem trước báo "DE 146° · FCs 192°" trong khi màn rang
vẫn chấm mốc theo ngưỡng **cũ của hồ sơ khác** còn nằm trong `otl_milset`. Không có
cảnh báo nào; và `%phát triển` tổng kết cuối mẻ được tính trên cái mốc sai đó.

**Nay:** nạp hồ sơ là cả ba ngưỡng đi theo hồ sơ.

| Hồ sơ | `R.mileSet` sau khi nạp |
|---|---|
| Có `deT`/`fcsT`/`temp` | Đặt đúng ba số đó |
| Không có `deT`/`fcsT` | **XOÁ** ngưỡng DE/FCs — mốc chấm tay, không để ngưỡng thừa của mẻ trước chấm bậy |

Ghi vào `opLog` mỗi lần đổi. Bộ soi kế hoạch còn nhắc riêng nếu hồ sơ đang sửa
chính là hồ sơ đã nạp mà ngưỡng lệch.

### 1.2 Mục tiêu trôi qua từng mẻ

Cuối mẻ, `finishRoast()` ghi đè `p.temp = dropT` và `p.time = fmtMMSS(dropSec)`
— ngay dưới dòng chú thích nói "mẻ sau vẫn so với hồ sơ chuẩn". Lần nạp kế tiếp
`buildTarget()` dựng mục tiêu từ chính mẻ vừa rang; sau chục mẻ thì "hồ sơ chuẩn"
không còn là cái thợ đặt ra.

**Nay:** kế hoạch giữ nguyên. Kết quả thật ghi riêng vào `p.last`
(`{temp, time, dev, code, date}`), và bản xem trước đối chiếu hộ: lệch quá 5°C hoặc
45 giây thì hiện một thẻ nhắc.

### 1.3 Hai công thức RoR trên cùng một đường

Bản xem trước dùng cửa sổ ±15 giây cứng; màn rang dùng cửa sổ + thuật toán thợ cài
trong Cài đặt. Tại DROP: preview 3,21 — demo `curveAt()` 0 — đạo hàm thật ≈6,67.
Con số "RoR lúc nổ" trong kế hoạch **không so được** với con số thợ lái theo lúc rang.

**Nay:** `buildTarget()` trả thêm `rorSeries()`/`rorAt()`, tính bằng chính
`rorRaw()` + `rorDecay()` của màn rang, cùng `ro_span` / `ro_algo` / `ro_csmooth` /
`ro_smooth`. Đổi cửa sổ trong Cài đặt là RoR dự kiến đổi theo. Đầu mẻ chưa đủ một
cửa sổ thì `null` — đường **đứt**, không bịa số 0. `curveAt()` của mẻ mô phỏng cũng
lấy chung nguồn này.

---

## 2. Phần nâng cấp

**Giờ mốc do thợ đặt.** Hai ô mới `deTime` / `fcsTime` (mm:ss, tuỳ chọn). Trước đây
hồ sơ chỉ nói được *nhiệt* của mốc, còn giờ thì app suy bằng tỉ lệ cứng (FCs = 90%
mẻ, DE = 64% quãng tới FCs). Thợ nghĩ theo đồng hồ — "vào nổ 9:30" — nên nay nói
thẳng được. Đặt rồi thì giờ đó **thắng** `%phát triển`, và `%phát triển` hiển thị
được tính ngược lại từ giờ nổ để hai con số không nói hai điều khác nhau.

**Mẻ nền thật trong bản xem trước.** Hồ sơ có ghim mẻ nền thì kéo curve BT của mẻ
đó về, vẽ nét đứt **dưới** đường kế hoạch (màu chốt ở §2b). Đây đúng
chỗ Artisan Designer mạnh hơn — bên đó dựng đường *từ* một mẻ có sẵn. Trục nhiệt ôm
cả hai đường; mẻ nền dài hơn kế hoạch thì cắt ở mép và bộ soi nói lệch bao nhiêu giây.

**RoR tại từng mốc.** Thẻ mốc dưới hình thêm một dòng RoR dự kiến. Thợ không lái
theo hình, họ lái theo số: *"vào nổ mà RoR còn 8 là ổn"*.

**Thang RoR tính từ đáy TP.** Đoạn trước TP là cú rơi nhiệt lúc nạp (RoR −60…−80),
không phải thứ thợ lái. Để nó vào thang thì cả đoạn có nghĩa bị ép dẹp — thang cũ
±65, nay ±25 trên cùng một hồ sơ.

**Bộ soi kế hoạch** (dải thẻ dưới hình, `peAudit()`). Đọc chính đường vừa dựng rồi
nói bằng tiếng thợ. Ba mức: đỏ (sai chắc) · vàng (nên xem lại) · xanh (không có gì
để nhắc). **Không mục nào chặn nút Lưu** — là lời nhắc, không phải luật.

| Nhóm | Bắt được |
|---|---|
| Gõ sai | `00:99` (giây ≥ 60) ở cả ba ô giờ |
| Số vô lý | xả ≤ charge · DE ≥ FCs · FCs ≥ xả — kèm **số app đã tự hạ xuống** |
| Khung mẻ | dưới 6 phút · trên 25 phút |
| Tỉ lệ | phát triển <10% (đỏ) · <15% · >30% · sấy <35% · >58% |
| RoR | về 0 trước nổ (baking) · <2 lúc nổ · >12 lúc nổ · cuối mẻ ≤0 · vọt lại sau nổ (flick) · đầu mẻ >35 |
| TP | đáy nhiệt tới sau 2:30 |
| Mẻ nền | lệch tổng thời gian >45s · lệch nhiệt xả >6° · lệch đường tới >12° (kèm giờ) |
| Mẻ gần nhất | `p.last` lệch kế hoạch >5° hoặc >45s |
| Đồng bộ | `R.mileSet` khác hồ sơ đang sửa |

Giữ 5 mục nặng nhất, dư thì gộp thành `+N mục nữa` — nhiều quá thì thợ không đọc.

---

## 2b. Đợt soi lại theo bản thiết kế Claude Design

Chủ máy yêu cầu soi lại bằng Claude Design. `DesignSync` đòi `/design-login` (chỉ
chạy được trong phiên **tương tác**) nên đợt này soi bằng **bản mirror trên đĩa**
`docs/ui/design-web/Rang - Sua lai.dc.html`. Bản thiết kế **không có** hộp "Sửa hồ
sơ", nhưng màn Rang của nó có hai thành phần mà khung xem trước đang thiếu — lấy
đúng khuôn đó áp sang:

**Dải 3 pha thành khối riêng dưới hình.** Bản thiết kế cho mỗi pha một ô, **bề rộng
theo thời gian**, ghi *tên · độ dài · phần trăm* bằng IBM Plex Mono, bo góc ngoài
`10px 4px 4px 10px`. Trước đây ba con số này nằm **chìm trong lòng đồ thị** và bị bỏ
khi dải hẹp dưới 70px — mà dải hẹp thường đúng là **Phát triển**, ô thợ cần đọc nhất
(thấy rõ ở hồ sơ DTR 6%). Đưa ra ngoài thì không bao giờ mất, lại có thêm **độ dài
từng pha** (`06:00 · 03:36 · 02:24`) — thứ thợ hỏi ngay sau tỉ lệ.

**Chú giải đường.** Khung có tới ba đường (kế hoạch · RoR · mẻ nền); bản thiết kế đã
có sẵn khuôn chip màu 14×3 + tên. Chú giải chỉ kê đường **đang thực sự vẽ**.

**Mẻ nền đổi sang xám đứt.** Bản thiết kế dùng xám `#84848F` đứt cho đường tham
chiếu, cam đặc cho đường đang nói tới. Ở khung này thứ đang nói tới là *kế hoạch*
(thợ đang sửa nó) nên kế hoạch giữ cam đặc, mẻ nền lấy xám. Hai đường cùng cam —
một đặc một đứt — không tách được bằng mắt ở đúng chỗ cần nhìn kỹ: chỗ chúng bám
sát nhau.

**Đơn vị trên thẻ mốc.** Dòng RoR thêm `°/′`; trước đó là một con số trần, thợ không
biết là RoR hay chênh nhiệt.

**Một lỗi tràn do đợt này đẻ ra, đã vá:** ô pha chia bề rộng theo thời gian nên pha
10% trên hộp thoại 1024px co tới mức chữ lòi khỏi viền 4px (`test_ui_dialog_layout`
bắt được). Nay `min-width:max-content` + cho xuống dòng — thà xuống dòng còn hơn cắt
mất số.

---

## 2c. Đợt trải nghiệm — chỉnh được bằng NGÓN TAY

Chủ máy chốt: *"tăng giảm số có thể dùng ngay trên tablet"*. Trước đợt này cả hộp
"Sửa hồ sơ" **chỉ gõ được bằng bàn phím** — trên máy panel/tablet ở xưởng nghĩa là
phải bật bàn phím ảo, mà bàn phím ảo che đúng cái đồ thị vừa vẽ, tức là mất luôn lý
do tồn tại của bản xem trước.

**Nút ± hai bên MỌI ô số** (10 ô: charge · xả · thời gian · DE · hạt vàng lúc ·
%phát triển · FCs · vào nổ lúc · gas mồi · kg). Dùng lại đúng con `.fpm` 72×72 của
trang Cài đặt và **đúng luật tăng tốc của nút ± màn Rang** (chủ máy chốt 08/09):
chạm = một bậc; giữ ≥0,45s = tự lặp mỗi 0,2s, bậc lớn dần; sang số thì kêu một tiếng
tách. Ô nhập vẫn gõ tay được y như cũ — thêm đường, không bớt đường.

| Ô | Bậc chạm | Giữ lâu |
|---|---|---|
| Nhiệt (°C), %phát triển, gas | 1 | ×5 → ×10 |
| Thời gian, giờ mốc | 5 giây | ×4 (20s) → ×12 (60s) |
| Mẻ nạp | 0,1 kg | ×5 → ×10 |

Ba chốt chép nguyên từ nút ± màn Rang: ngón ĐẦU làm chủ (ngón thứ hai không cướp
nhịp — lỗi "gas tự leo lên 100" bắt được 08/09), tài liệu và cửa sổ bắt hộ lượt nhả,
và kẹp biên trước khi ghi.

**Ô tuỳ chọn đang trống: chạm ± lần đầu LẤY CHÍNH SỐ APP ĐANG ƯỚC** làm điểm xuất
phát rồi mới nhích. Bắt thợ tự đoán "điền đại số nào bây giờ" chính là lý do hồ sơ
mỏng cứ mỏng mãi — mà hồ sơ mỏng thì mốc lệch, đúng chuỗi lỗi ở §1.1.

**Tiêu đề và hàng "Huỷ / Lưu" ra ngoài vùng cuộn.** Hộp cao hơn màn: sửa một ô ở
giữa form là phải cuộn xuống đáy bấm Lưu rồi cuộn ngược lên xem đồ thị — hai lần
vuốt cho mỗi con số. Nay chỉ ruột (`.pe2col`) cuộn.

⚠ **Đã thử `position:sticky` trước và GỠ:** nó đúng về mắt nhưng nội dung trôi *bên
dưới* hàng nút, và `test_ui_overlap` bắt đúng điểm đó. Cách đang dùng (hộp thành cột
dọc, chỉ ruột cuộn) thì hàng nút nằm NGOÀI vùng cuộn nên không bao giờ đè lên gì.

**Vá kèm:** ô "Mẻ nạp (kg)" cũ viết `parseFloat(v)||undefined` ngay trong thuộc tính
`oninput` — gõ dở số "0.5" thì ở nhịp phím đầu (`"0"`) giá trị bị xoá mất. Tách thành
`peKgIn()`.

### Hai bẫy của BỘ KIỂM lộ ra trong đợt này (không phải lỗi app)

1. **Màn đăng nhập che hết sân khấu.** `test_ui_profile_target` không đóng hộp đăng
   nhập, nên mọi cú chạm chuột rơi vào phím số PIN — trong khi phần đọc DOM vẫn đúng.
   Đọc DOM xanh mà chạm thật không ăn: rất dễ tưởng app hỏng.
2. **`test_ui_overlap` không biết "bị khung cuộn cắt".** Phần tử trôi ra ngoài khung
   cha có `overflow` ẩn thì mắt không thấy, nhưng toạ độ vẫn nằm trong cửa sổ nên bị
   tính là chồng lấn. Đã thêm `catBoiCha()` — chỉ loại khi nằm **hoàn toàn** ngoài
   khung cha, khuất một nửa thì vẫn xét như cũ.

---

## 2d. Đợt "xuất sắc" — ba thứ cuối

**KÉO MỐC NGAY TRÊN HÌNH.** Đây là chỗ Artisan Designer hơn hẳn. Bản này không mở tự
do tới mức ấy (đường vẫn dựng từ 5 neo) nhưng **ba mốc thợ thật sự mặc cả** thì kéo
thẳng bằng ngón tay:

| Mốc | Kéo ngang | Kéo dọc |
|---|---|---|
| DE | giờ hạt vàng | nhiệt hạt vàng |
| FCs | giờ vào nổ | nhiệt vào nổ |
| DROP | *(không)* | nhiệt xả |

DROP **cố ý chỉ kéo dọc**: nó luôn nằm đúng cuối mẻ nên dính mép phải đồ thị — kéo
ngang thì chấm chạy theo trục chứ không theo ngón, nhìn như hỏng. Đổi tổng thời gian
thì dùng ± ở ô "Thời gian".

Bán kính bắt **34px** (ngón tay to hơn con trỏ; bắt đúng cái chấm 7px thì không ai kéo
nổi), `touch-action:none` trên canvas để kéo không cuộn trang, vẽ theo nhịp màn hình
(`requestAnimationFrame`) vì `pointermove` bắn dày hơn 60 lần/giây trên màn cảm ứng.
Đang kéo thì hiện **ô số ngay cạnh ngón** (`08:28 · 198°`) — nhìn xuống hàng thẻ thì
chỗ đó có khi đang bị chính bàn tay che. Kéo tới đâu ô nhập bên dưới nhảy số tới đó.

**⤓ LẤY MỐC THEO MẺ NỀN.** *"Mẻ này rang ngon"* → một chạm thành hồ sơ chuẩn: giờ +
nhiệt xả, mốc DE/FCs (lấy từ `mile` đã chốt trong kho, **không phải đo lại trên hình**),
nhiệt charge và gas mồi từ đầu curve, khối lượng mẻ. Hỏi lại trước khi ghi đè. Mẻ nền
không chấm DE/FCs thì nói rõ là giữ nguyên số cũ chứ không im lặng bỏ qua. Chưa ghim
mẻ nền thì nút **mờ kèm lý do** ("Ghim mẻ nền trước") — không để nút sáng rồi chạm vào
mới báo, đúng luật trạng thái chết của đợt 7.

**Chạm thẻ cảnh báo → nhảy tới đúng ô.** Hộp này có 19 ô; đọc được lời nhắc rồi còn
phải dò xem nó nói ô nào là một bước thừa. Nay mỗi lời nhắc mang theo id ô, chạm vào
là cuộn tới + đặt con trỏ + nháy viền một nhịp.

---

## 3. Kiểm

`tools/test_ui_profile_target.py` — **80 mục, tất cả ĐẠT**. Nặng nhất là ba mục giữ
chân ba lỗi trên, vì cả ba đều im lặng: không ném lỗi, không hiện gì lạ. Mười hai
mục cuối giữ phần mẻ nền, dải pha và chú giải.

Chạy lại các bộ liên quan: `test_ui_ror`, `test_ui_colors_fonts`,
`test_ui_dialog_layout`, `test_ui_overlap`, `test_ui_consistency`, `test_ui_workflow`
— đều ĐẠT.

Chạy lại **cả 29 bộ `test_ui_*`**: xanh hết, trừ `test_ui_overview_history` (nhãn ô
ngày — đỏ y hệt trên bản cũ chưa sửa gì).

⚠ `test_ui_hold_confirm` **chập chờn sẵn từ trước**, không phải do đợt này: chạy 5
lượt bản cũ đạt 2, bản mới đạt 1; dựng lại đúng trình tự của bài kiểm thì **hai bản
hỏng y hệt nhau** ở `#btnEscape`. Nguyên nhân nằm trong chính bài kiểm (bước 0 đọc
`getComputedStyle` của `.holdfill`), không phải ở cử chỉ giữ nút — gọi thẳng
`cmdEscape()` hay bấm giữ rời rạc đều gửi lệnh đúng.

## 4. Bàn giao

**EXE:** đã build và thay thẳng `tools/dist/OTL Roast Lab HMI.exe`
(md5 `73344ade…`, HTML nhúng khớp bản trên đĩa), bản cũ giữ ở
`OTL Roast Lab HMI.before-duongrang-20260913.exe`. Smoke-test chạy 9 giây không thoát.
Lối tắt Start Menu đã trỏ đúng bản mới và Windows trả về hành động **"Unpin from
Start"** — tức **đang ghim thật**, không cần ghim lại.

## 5. Còn nợ

- **Chưa chạy với máy rang thật.**
- Kéo mốc mới mở cho DE · FCs · DROP; TP và DEV vẫn là điểm suy ra, chưa kéo được.
- `saveProfEdit()` vẫn không validate trước khi lưu; bộ soi chỉ nhắc chứ không chặn.
- `DesignSync` đã có quyền nhưng UUID project trả 404 — chưa kéo được bản thiết kế
  mới, đang dùng bản mirror 07/09 trên đĩa (xem `docs/ui/design-web/SOURCE.md`).
