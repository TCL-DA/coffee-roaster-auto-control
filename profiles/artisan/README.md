# Kho profile Artisan — O Tesla

Toàn bộ profile Artisan (`.alog`) gom từ các máy làm việc của O Tesla, **bỏ bản trùng theo nội dung** (SHA-1), giữ nguyên tên và cấu trúc thư mục gốc để còn lần lại nguồn.

| | |
|:--|--:|
| Profile trong thư mục này | **361** |
| Profile đã có sẵn ở `docs/profile/` (không chép lại) | 37 |
| Có mốc DROP (mẻ rang trọn) | 282 |
| Thời gian rang (DROP) trung vị | 13:15 |
| Nhiệt xả trung vị | 215.9 °C |
| Tỉ lệ phát triển (DTR) trung vị | 26.3 % |
| File hỏng không đưa lên (toàn byte 0) | 126 |

Theo năm rang: **2020** 9 · **2021** 13 · **2022** 35 · **2023** 71 · **2024** 71 · **2025** 17 · **2026** 134 (không tính file thiếu ngày).

## Dùng thế nào

- **Mở trong Artisan:** `File → Open` chọn tệp `.alog`.
- **Làm đường nền để bám khi rang:** `Roast → Background → Load`.
- **Tìm nhanh:** mở [`INDEX.csv`](INDEX.csv) bằng Excel, lọc theo máy / ngày / hạt / nhiệt xả. Mỗi dòng một profile: ngày giờ, tên mẻ, hạt, khối lượng vào/ra, CHARGE, TP, DRY, FCs, DROP (giờ + nhiệt), DTR, bản Artisan và số bản sao từng thấy trên máy.
- **Nạp cho máy OTL chạy AUTO:** chuyển sang `.csv` bằng công cụ chuyển profile, rồi chép vào thẻ SD. ⚠ Bản xuất từ Artisan còn **đuôi làm nguội** sau DROP — xem case [CS-01](../../docs/case-study/CS-01_auto-dung-sat-nhiet-xa-khong-drop.md).

## Thư mục

Thư mục đánh số (`45_120_Auto`, `74_CMS_60`…) là thư mục theo **công trình / máy**, đặt tên như lúc làm. `_tu-du-an/` là profile nằm rải trong các dự án khác, `_o-D/` và `_may-ca-nhan/` là bản chỉ có ở ổ D và thư mục người dùng.

| Thư mục | Số profile | Từ | Đến | Có DROP | DROP trung vị |
|:--|--:|:--|:--|--:|--:|
| `1-3kg-auto-QN` | 2 | 2022-11-28 | 2022-11-28 | 2 | 12:44 |
| `10-OTL-03-EU-JPN` | 3 | 2023-04-13 | 2023-04-13 | 3 | 11:09 |
| `11_OTL-03-Auto-LanBuonMe` | 5 | 2023-04-17 | 2023-04-18 | 5 | 13:36 |
| `18_5kg_QN_APHAP` | 1 | 2023-05-24 | 2023-05-24 | 1 | 13:39 |
| `2-1kg-auto-TB` | 3 | 2022-11-29 | 2022-11-29 | 3 | 12:24 |
| `20_Test_Multi` | 9 | 2023-05-30 | 2023-06-12 | 9 | 13:24 |
| `22_OTL-03-Dalat` | 1 | 2023-06-07 | 2023-06-07 | 1 | 12:00 |
| `26-1KG-AUTO-PHILIPPINES` | 7 | 2023-06-27 | 2023-06-29 | 7 | 14:56 |
| `28_OTL_03_VN_DAKNONG` | 1 | 2023-07-07 | 2023-07-07 | 1 | 13:06 |
| `3-auto-15kg-ductrong` | 1 | 2022-12-31 | 2022-12-31 | 1 | 8:37 |
| `31_OTL_01_EU_CYLINDER` | 2 | 2023-08-29 | 2023-08-29 | 2 | 13:33 |
| `32_OTL_06_EU_AUTO` | 1 | 2023-07-18 | 2023-07-18 | 1 | 11:44 |
| `33_OTL_01_EU` | 4 | 2023-07-21 | 2023-08-16 | 4 | 13:09 |
| `34_OTL_03_HCM` | 1 | 2023-08-10 | 2023-08-10 | 1 | 13:46 |
| `35_OTL_01_EU_PRESSURE` | 1 | 2023-09-10 | 2023-09-10 | 1 | 12:30 |
| `38_OTL_06_HAO_HN` | 1 | 2023-10-03 | 2023-10-03 | 1 | 13:51 |
| `4-12kg-athang` | 2 | 2023-01-06 | 2023-01-06 | 2 | 13:32 |
| `4-1kg-lamha-MrsQuynh` | 2 | 2023-01-05 | 2023-01-05 | 2 | 15:29 |
| `40_OTL-06-AUS-CYLINDER` | 1 | 2023-10-08 | 2023-10-08 | 1 | 11:42 |
| `41_OTL-30-AUS-CYLINDER` | 1 | 2023-10-09 | 2023-10-09 | 1 | 16:50 |
| `44_120KG_Manual` | 2 | 2023-10-28 | 2023-10-28 | 1 | 13:13 |
| `45_120_Auto` | 11 | 2023-12-11 | 2023-12-20 | 11 | 12:22 |
| `46_3KG_EU_171123` | 2 | 2023-11-17 | 2023-11-17 | 2 | 13:36 |
| `5-3kg-eu-auto` | 8 | 2023-01-12 | 2023-02-07 | 8 | 15:57 |
| `51_OTL_03_EU_DALAT` | 1 | 2024-01-02 | 2024-01-02 | 1 | 12:52 |
| `52_OTL_01_AROVIN` | 2 | 2024-01-04 | 2024-01-04 | 2 | 16:06 |
| `55_1KG_VU_DAO` | 1 | 2024-01-24 | 2024-01-24 | 1 | 11:58 |
| `56_OTL-01-Phil-310124` | 2 | 2024-01-31 | 2024-01-31 | 2 | 15:22 |
| `57_OTL_AUTO` | 5 | 2024-04-07 | 2025-03-22 | 5 | 10:13 |
| `58_OTL_6KG_AUTO` | 1 | 2024-03-14 | 2024-03-14 | 1 | 15:14 |
| `60_1kg_aTrung` | 5 | 2024-03-17 | 2024-03-17 | 5 | 15:12 |
| `61_1kg_LongXuyen` | 2 | 2024-03-21 | 2024-03-21 | 2 | 15:56 |
| `62_Auto_test` | 3 | 2024-04-03 | 2024-04-11 | 3 | 9:20 |
| `63_3KG_EU` | 1 | 2024-04-03 | 2024-04-03 | 1 | 14:24 |
| `64_15kg_Phil` | 3 | 2024-04-10 | 2024-04-10 | 3 | 12:40 |
| `65_OTL_06_Auto_Mr_Park` | 2 | 2024-04-11 | 2024-04-11 | 2 | 14:00 |
| `68_OTL_03_Auto` | 2 | 2024-05-12 | 2024-09-07 | 2 | 6:41 |
| `69_OTL_AUTO_15` | 1 | 2024-06-19 | 2024-06-19 | 1 | 13:21 |
| `70_OTL_VIXI` | 4 | 2024-06-21 | 2024-06-22 | 4 | 13:29 |
| `72_VCC_1KG` | 4 | 2024-07-29 | 2024-07-29 | 4 | 13:42 |
| `74_CMS_60` | 7 | 2024-08-23 | 2024-08-26 | 6 | 9:30 |
| `8-Artisan-CMS` | 3 | 2023-04-19 | 2023-04-21 | 3 | 16:18 |
| `89_OTL_01_Intenso_25` | 1 | 2025-10-10 | 2025-10-10 | 1 | 15:06 |
| `94_120_SIE` | 2 | 2026-03-05 | 2026-03-05 | 2 | 16:12 |
| `95_OTL-01-EU` | 1 | 2026-04-22 | 2026-04-22 | 1 | 16:43 |
| `99_CMS_12A_0826` | 2 | 2026-08-13 | 2026-08-13 | 2 | 20:49 |
| `_may-ca-nhan` | 2 | 2024-05-03 | 2026-10-17 | 1 | 12:40 |
| `_o-D` | 3 | 2024-07-29 | 2025-05-07 | 2 | 15:30 |
| `_tu-du-an` | 19 | 2021-11-22 | 2026-10-12 | 16 | 13:26 |
| `Linh-tinh` | 45 | 2020-07-15 | 2024-03-06 | 42 | 13:16 |
| `Profile` | 53 | 2026-10-14 | 2026-10-17 | 15 | 16:39 |
| `Profile-aDanh` | 11 |  |  | 0 |  |
| `Thanh` | 101 | 2024-09-10 | 2026-08-13 | 81 | 7:16 |

## File hỏng không đưa lên

Các tệp dưới đây trên ổ đĩa chỉ còn **toàn byte 0** (hỏng khi cứu dữ liệu ổ cũ), không có bản lành nào khác trên máy nên không đưa vào kho. Ghi lại để biết là đã từng có.

<details><summary>126 tệp</summary>

- `Linh-tinh/Roasting Profile/20-08-14_1639.alog`
- `Linh-tinh/Roasting Profile/20-08-14_1700.alog`
- `Linh-tinh/Roasting Profile/Ara DB-g20-09-15_1152.alog`
- `Linh-tinh/Roasting Profile/Ara HoNey Sonla 1kg202,13p30g.alog`
- `Linh-tinh/Roasting Profile/Ara Natural DB  French Press Capella_20-07-15_1609.alog`
- `Linh-tinh/Roasting Profile/Ara Natural DB French Press Capella_20-07-15_1741.alog`
- `Linh-tinh/Roasting Profile/Ara W VN 1kgR2.alog`
- `Linh-tinh/Roasting Profile/Ara Washed DB French Press (Crema)_20-07-15_1440.alog`
- `Linh-tinh/Roasting Profile/Ara Washed DB French Press (Crema)_20-07-15_1537.alog`
- `Linh-tinh/Roasting Profile/Ara Washed Dien Bien 600g_20-07-13_1419.alog`
- `Linh-tinh/Roasting Profile/Ara Washed Dien Bien_1000g_20-07-13_1402.alog`
- `Linh-tinh/Roasting Profile/Ara cau dat R1202,15p24g.alog`
- `Linh-tinh/Roasting Profile/AraSonla1kg06g202R2.alog`
- `Linh-tinh/Roasting Profile/AraVN W R1.alog`
- `Linh-tinh/Roasting Profile/AraVN W1kgR3.alog`
- `Linh-tinh/Roasting Profile/Bi vao165ok.alog`
- `Linh-tinh/Roasting Profile/Brasil Natural20-09-06_1212.alog`
- `Linh-tinh/Roasting Profile/Brazial R1.alog`
- `Linh-tinh/Roasting Profile/COLOMBIA SUPREMO_ESPRESSO__20-07-22_1726.alog`
- `Linh-tinh/Roasting Profile/COLOMBIA SUPREMO_chinh lua theo giai doan20-07-22_1743.alog`
- `Linh-tinh/Roasting Profile/Cau Dat HONEY TYPICA_20-07-22_1505.alog`
- `Linh-tinh/Roasting Profile/CoLomSupermo vao185.alog`
- `Linh-tinh/Roasting Profile/Colom May R3.alog`
- `Linh-tinh/Roasting Profile/Colom May R4,12p21g.alog`
- `Linh-tinh/Roasting Profile/Colom may R1.alog`
- `Linh-tinh/Roasting Profile/Colombia Decaffeinated EA Process_20-07-15_1918.alog`
- `Linh-tinh/Roasting Profile/Colombia Decaffeinated EA Process_20-07-15_2125.alog`
- `Linh-tinh/Roasting Profile/Colombia Decaffeinated EA Process_Espresso__20-07-15_2139.alog`
- `Linh-tinh/Roasting Profile/Colombia May 207,13p50g.alog`
- `Linh-tinh/Roasting Profile/Colombia San Lui Estaste Pink Bourbon Anaerobic Honey 300g_20-07-13_1658.alog`
- `Linh-tinh/Roasting Profile/Colombia Supermo1kg,202,13p26g.alog`
- `Linh-tinh/Roasting Profile/Colombia Supremo_20-07-22_1559.alog`
- `Linh-tinh/Roasting Profile/Comlom Supremo vao 180.alog`
- `Linh-tinh/Roasting Profile/DECAFF.alog`
- `Linh-tinh/Roasting Profile/ETHIOPIA GUJI HAMBELLA_20-09-06_1346.alog`
- `Linh-tinh/Roasting Profile/EThy Gediyo Waseh R2.alog`
- `Linh-tinh/Roasting Profile/EThy Gediyo Waseh R3 7p57g.alog`
- `Linh-tinh/Roasting Profile/EThy Gediyo Waseh R5 7p45g.alog`
- `Linh-tinh/Roasting Profile/EThy Guji Uraga hada W 7p30g.alog`
- `Linh-tinh/Roasting Profile/EThy Guji Uraga hada W 7p48 189'6.alog`
- `Linh-tinh/Roasting Profile/EThy Yirgache Uraga Natural R2.alog`
- `Linh-tinh/Roasting Profile/EThy Yirgache Uraga Natural R3.alog`
- `Linh-tinh/Roasting Profile/EThy500g Gediyo Waseh.alog`
- `Linh-tinh/Roasting Profile/Ethi natural/20-10-11_1914.alog`
- `Linh-tinh/Roasting Profile/Ethi natural/ethi 20-10-11_1947.alog`
- `Linh-tinh/Roasting Profile/Ethiopia 500g Hoa.alog`
- `Linh-tinh/Roasting Profile/Ethiopia Yirgacheffe Kochere Bolje Bonde Washed Semi-Shade_20-07-13_1454.alog`
- `Linh-tinh/Roasting Profile/Ethiopia Yirgacheffe worka banko gotiti natural G1 300g_20-07-13_1533.alog`
- `Linh-tinh/Roasting Profile/Ethiopia Yirgacheffe worka banko gotiti natural G1 300g_20-07-13_1603.alog`
- `Linh-tinh/Roasting Profile/Ethy Hada 189,9p30g.alog`
- `Linh-tinh/Roasting Profile/Ethy W194,8p15g.alog`
- `Linh-tinh/Roasting Profile/Ethy hada 189,8p30g.alog`
- `Linh-tinh/Roasting Profile/Ethy sidamo 194,8p00g.alog`
- `Linh-tinh/Roasting Profile/EthyGediyo YIR189,8p00g.alog`
- `Linh-tinh/Roasting Profile/EthyGediyoYIR,W189,8p15g.alog`
- `Linh-tinh/Roasting Profile/EthySadio9p39g192.alog`
- `Linh-tinh/Roasting Profile/EthySammdio9p00g94,5.alog`
- `Linh-tinh/Roasting Profile/EthyYirgache500g lua moi.alog`
- `Linh-tinh/Roasting Profile/KENYA/KENYA WASHED 20-07-31_1703.alog`
- `Linh-tinh/Roasting Profile/KENYA/KENYA WASHED20-07-31_1703.alog`
- `Linh-tinh/Roasting Profile/Keynya Nyeshun 7p36g.alog`
- `Linh-tinh/Roasting Profile/Nicaraguo R1 500g.alog`
- `Linh-tinh/Roasting Profile/OK_Colombia Decaffeinated EA Process_20-07-15_2213.alog`
- `Linh-tinh/Roasting Profile/PANAMA NATURAL 9p30g.alog`
- `Linh-tinh/Roasting Profile/PANAMA NATURAL_20-08-01_1514.alog`
- `Linh-tinh/Roasting Profile/Panma Natural R1 8p00.alog`
- `Linh-tinh/Roasting Profile/ROB SM CLASSICO_20-08-01_1500 MEDIUM.alog`
- `Linh-tinh/Roasting Profile/Ro R1.alog`
- `Linh-tinh/Roasting Profile/Ro Se fin 14p06g.alog`
- `Linh-tinh/Roasting Profile/Ro se may 14p06g.alog`
- `Linh-tinh/Roasting Profile/Ro se may2 14p06g.alog`
- `Linh-tinh/Roasting Profile/Ro se16 ok1.alog`
- `Linh-tinh/Roasting Profile/Ro se16 ok2.alog`
- `Linh-tinh/Roasting Profile/Ro12kgR2.alog`
- `Linh-tinh/Roasting Profile/Ro13,210.alog`
- `Linh-tinh/Roasting Profile/Robusta Natural Yem Khi_20-07-13_1227.alog`
- `Linh-tinh/Roasting Profile/Sample_Ara Natural DB French Press Capella_20-07-15_1642.alog`
- `Linh-tinh/Roasting Profile/Setting/ARa W12kg200R1.alog`
- `Linh-tinh/Roasting Profile/Setting/Ara12kg219R2.alog`
- `Linh-tinh/Roasting Profile/Setting/Ro12kg R1se 14p50g.alog`
- `Linh-tinh/Roasting Profile/Setting/Ro12kg14p30g223ok.alog`
- `Linh-tinh/Roasting Profile/Setting/Ro12kg14p33gok223,8.alog`
- `Linh-tinh/Roasting Profile/Setting/Ro12kg14p42g.alog`
- `Linh-tinh/Roasting Profile/Setting/Ro12kg14p42g223 ok.alog`
- `Linh-tinh/Roasting Profile/Setting/Ro12kg14p45g223 ok.alog`
- `Linh-tinh/Roasting Profile/Setting/Ro12kg14p48g223 ok.alog`
- `Linh-tinh/Roasting Profile/Setting/Ro12kg14p50g223 ok.alog`
- `Linh-tinh/Roasting Profile/Setting/Ro12kg14p50g224.alog`
- `Linh-tinh/Roasting Profile/Setting/Ro12kg14p51g223 R9 ok.alog`
- `Linh-tinh/Roasting Profile/Setting/Ro12kg14p57g222.alog`
- `Linh-tinh/Roasting Profile/Setting/Ro12kg15p07g223.alog`
- `Linh-tinh/Roasting Profile/Setting/Ro12kg15p21g222R10.alog`
- `Linh-tinh/Roasting Profile/Setting/Ro12kg15p21g222R9.alog`
- `Linh-tinh/Roasting Profile/Setting/RoSe 14p35g224ok.alog`
- `Linh-tinh/Roasting Profile/Setting/RoSe12kg224,15p00g.alog`
- `Linh-tinh/Roasting Profile/TEst/rob test 2 15-45.alog`
- `Linh-tinh/Roasting Profile/TEst/rob test 320-10-11_1834.alog`
- `Linh-tinh/Roasting Profile/TEst/rob.alog`
- `Linh-tinh/Roasting Profile/Toan/ARA DARK.alog`
- `Linh-tinh/Roasting Profile/Toan/ARA NATURAL DARK STARBUCK CCCP20-07-31_1636.alog`
- `Linh-tinh/Roasting Profile/Toan/Ara Wash perfect 20-08-23_1359.alog`
- `Linh-tinh/Roasting Profile/Toan/Ara Washed Espresso 500G_20-07-31_1449.alog`
- `Linh-tinh/Roasting Profile/Toan/Ara Washed Espresso_20-07-31_1449.alog`
- `Linh-tinh/Roasting Profile/Toan/Ara Washed Espresso_20-07-31_1525.alog`
- `Linh-tinh/Roasting Profile/Toan/Brasil Natural 20-12-10_1607.alog`
- `Linh-tinh/Roasting Profile/Toan/Brazil/brazil 500g 21-02-10_1144.alog`
- `Linh-tinh/Roasting Profile/Toan/CCCP ARA WASH STARBUCK 2 CRACK_20-08-01_1058.alog`
- `Linh-tinh/Roasting Profile/Toan/COLOMBIA DECAFFE.alog`
- `Linh-tinh/Roasting Profile/Toan/Colombuia/Colombia San Washed21-02-10_1158.alog`
- `Linh-tinh/Roasting Profile/Toan/FINE ROB NATURAL 20-09-06_1127.alog`
- `Linh-tinh/Roasting Profile/Toan/Guji Hambella 196R1 Hoa.alog`
- `Linh-tinh/Roasting Profile/Toan/Guji hambella light 20-09-15_1447.alog`
- `Linh-tinh/Roasting Profile/Toan/KENYA 21-01-27_1341.alog`
- `Linh-tinh/Roasting Profile/Toan/KENYA AA20-12-10_1636.alog`
- `Linh-tinh/Roasting Profile/Toan/Kenya/Kenya 21-02-10_1216.alog`
- `Linh-tinh/Roasting Profile/Toan/ROB HONEY CLASSICO DAI LOAN_20-07-31_1602.alog`
- `Linh-tinh/Roasting Profile/Toan/ROB SEMI CCCP US 20-08-23_1304.alog`
- `Linh-tinh/Roasting Profile/Toan/ROB SM 1620-09-15_1305.alog`
- `Linh-tinh/Roasting Profile/Toan/ROB SM CLASSICO_20-08-01_1417+ rob sm dARK.alog`
- `Linh-tinh/Roasting Profile/Toan/ethi uraga/20-12-31_1801.alog`
- `Linh-tinh/Roasting Profile/colom may R2, 208.alog`
- `_o-D/Design/Digital-Control/Artisan Controller/Artisan_Profiles/EtYrga_Roastuino_Ideal.alog`
- `_o-D/Design/Digital-Control/Artisan Controller/Artisan_Profiles/EtYrga_Roastuino_Real.alog`
- `_o-D/Design/Digital-Control/Artisan Controller/Artisan_Roast/Roast_1_EthYrga.alog`
- `_o-D/Design/Digital-Control/Artisan Controller/Artisan_Test/Artisan_WiFi_BAT_Test/Test2/artisan_540min_WiFi+BAT_test_OFF.alog`
- `_tu-du-an/CV/Logo Otesla/CAD/21-03-30_1528.alog`

</details>

## Cập nhật kho

Gom lại khi có profile mới: quét mọi ổ tìm `*.alog`, bỏ trùng SHA-1, bỏ tệp hỏng, sinh lại `INDEX.csv` và README này. File mới nằm đúng thư mục gốc của nó trong `F:\Artisan\`.

