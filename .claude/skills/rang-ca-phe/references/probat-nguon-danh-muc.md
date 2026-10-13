# PROBAT — danh mục nguồn, độ phủ và cách tra lại

Bản tổng hợp ngày 16–17/09/2026 từ kho Codex quét ngày 14–16/09/2026. Skill chỉ giữ **tóm lược diễn giải tiếng Việt**; không chép transcript nguyên văn (repo public).

## 1. Kho gốc

- Transcript YouTube kênh PROBAT Global (171 mục): `artifacts/probat-youtube-corpus-20260914/` — `manifest.csv` (id, title, caption_status, track_type, word_count) + `transcripts/<id>.txt`.
- Kho đa nền tảng (Codex): `F:\Research\Coffee-Roasting\probat\`
  - `PROBAT_EXTERNAL_PLATFORMS_REPORT.md`, `PROBAT_VIDEO_ARCHIVE_REPORT.md`, `PROBAT_LIVESTREAM_INDEX.md` (56 livestream, 431 đoạn timeline có mốc giờ và chủ đề — dùng để nhảy đúng phút trong video dài).
  - `indexes/`: `youtube_content_map.csv` (300 video 3 kênh chính), `youtube_external_probat_*.csv` (103 bên thứ ba), `bilibili_probat_catalog.csv`, `vimeo_probatwerke.csv`, `linkedin_public_posts.csv`, `website_sitemap_catalog.csv`, `platforms.csv`, `probat_search.sqlite`.
- Đường dẫn trên có thể đổi nếu thư mục `F:\Research` được sắp xếp lại; khi không thấy, tìm theo tên file.

## 2. Độ phủ theo nền tảng

| Nền tảng | Số mục | Đã xử lý | Ghi chú |
|---|---|---|---|
| YouTube PROBAT Global | 171 (115 video + 56 livestream) | 171/171 | Kỹ thuật đọc đầy đủ; doanh nghiệp/sự kiện quét từ khoá; 10 video không lời (xác minh bằng ASR): -A_PD1zYr2o, ATf81ThKfnE, dbd645zapjc, fMMiBLeVRvM, hy_Ucb8t-iw, HZFsShWrIYc, kw6ZDUKGaLI, LdL31n3i6Rs, SjHGFXB1XG8, TA_kGrkt2fg |
| YouTube Probat USA | 59 | 59/59 | Loạt sửa lỗi/bảo trì P-series đọc đầy đủ; 4 video chỉ nhạc (PNlwpLNwkP0, zz1GO-Y67EU, xE-ryVFDXBk, 8EpNv18cIxQ); 4 video không phụ đề đã ASR: 3 chỉ nhạc (6P7BFJfh4ck Px120, JckDeeQ4dVo Neptune, LufJNYr2fo4 Jupiter), cL8qlXQWyFg chỉ là lời khen P12 của một quán |
| YouTube Probat Indonesia | 70 | 70/70 | Phụ đề tự động tiếng Indonesia (nhiều lỗi): #TEKNISPROBAT/#SERVISPROBAT/#INSIGHTPROBAT đọc kỹ; #SOBATPROBAT (thăm roastery) quét; LJlyDxV25FU và iVRDVgv2z7w chỉ nhạc; 3 video không phụ đề (Ys71uKGFPmc, X8T-uccBk1A, CjlcxU13IDY) nay YouTube báo "not available" — không lấy được |
| YouTube bên thứ ba | 103 (8 truy vấn, không đầy đủ) | 25 có phụ đề | 8 hữu ích (4LLYNbQDlXA, g3eWzww1nbU, RLCuXoVv6qo, h-76WVk6Rcg, poKN-j_MunI, pWMUtIWzFjE, nWj0ewy0h1M, aROPuAEnsLw); còn lại nhạc/quảng cáo máy tân trang (Exapro, Blacksmith…); 6 video SEO gắn chữ "Probat" nhưng **không phải PROBAT** (v_WoEERSqEE, bck7UEpXb1E, MbtnJp37_dg, bqgNeQ6FkEY, ilE2OD0Zaec, ibSmPAHJrY8); 78 video không phụ đề chưa phiên âm (chủ yếu người bán máy cũ, có link chết) |
| Bilibili | 21 | 20/21 | Đa số là bản lồng phụ đề Trung của video YouTube (物理 ①–⑤ = A6qXyYOPf_A; UG vs P 01–05 = zdEXgD9jwCs; P05 III điện = WyOQ3IxMDx8). Nội dung mới: BV1MbsdeZEyg (vị trí thermocouple P-series), BV1yB8RehEGy (thí sinh giải rang châu Á trên P01), BV1WB8RehE9Z (roastery Lhasa). BV1Nz3TeSELR (Px120 101 s) tải lỗi |
| Vimeo Probatwerke | 4 | 0/4 | Nền tảng đòi đăng nhập; theo catalog là phim quảng bá 2014–2018 |
| probat.com | 347 URL | 115 trang | 99 trang được Codex gắn "high" + 16 trang bổ sung (máy, cảm biến, môi trường, đào tạo, webinar); bỏ trang hội chợ/tuyển dụng/nhân sự. Trang FAQ còn trống |
| LinkedIn | 29 bài | 0 | Chỉ có URL; nội dung cần đăng nhập |
| Instagram, Facebook | — | 0 | Nền tảng chặn truy cập tự động/đăng nhập |

Công cụ: yt-dlp lấy phụ đề; faster-whisper `small` int8 chạy cục bộ cho video không phụ đề (không gửi âm thanh ra ngoài). Phụ đề tự động sai nhiều ở tên máy, số liệu, tiếng Đức/Indonesia/Trung → con số quan trọng phải nghe lại đoạn gốc.

## 3. Việc còn mở

- 3 video Probat Indonesia không còn truy cập được (Ys71uKGFPmc thăm roastery TTKR, X8T-uccBk1A hành vi khách specialty, CjlcxU13IDY dịch vụ ở First Crack) — theo tiêu đề là nội dung thăm khách/kinh doanh.
- Vimeo, LinkedIn, Instagram, Facebook: cần tài khoản; chưa làm.
- 78 video bên thứ ba không phụ đề: giá trị kỹ thuật thấp theo khảo sát metadata; chưa phiên âm.
- Bilibili BV1Nz3TeSELR (Px120, 101 s): tải lỗi; bản YouTube tương ứng của hãng không lời.

## 4. Bản đồ video theo file chủ đề

| File skill | Video/trang gốc chính |
|---|---|
| `probat-vat-ly-thiet-bi.md` | A6qXyYOPf_A, 503cxjURIZA, 7qI-Mpbts2Q, FPOAPrp65bo, zdEXgD9jwCs, e3A6OdVI0C8, vUR5xwN6Zj8, KSViq0NP3_g, 5JA8Wdot9Lg, WyOQ3IxMDx8, c85OMeT3BAc, lJbzjR2Ci98, QiEYXnpqves, ibmuIvdV5GI, Indonesia gVbKt1jQyvY/Q8zWVguQT0E/oaukQGc6riQ, Bilibili BV1MbsdeZEyg/BV1yB8RehEGy, web customer-project-ks-espresso |
| `probat-dieu-khien-du-lieu.md` | 503cxjURIZA, _n6K5SBoUWw, 68jFMr-8irM, 3HXG9vEyLyc, 7qI-Mpbts2Q, qRiHoUgYGJM, m8DEQc2AkCM, j7sUB4XNhOw, r0sxeu-IMKs, hv1z75fJVDs, L0P5Ae3nvoU, BvoyhFCWKjA, NhW8F1kej40, PRNsn0Jv-hY, MmVuMpGIv74, HrUUR5Z_xF0, 0-IryC4eXFM, USA UaSO05HMSYc/VzZBqpgJzKc, web colour-control/moisture-control/how-mathematical-models/software-control-system |
| `probat-van-hanh-hat-xanh.md` | e3A6OdVI0C8, zXmmPYQIIKY, NFr1iwyzfFk, kcFujr-izRY, nZ11BaI7WS8, WiAUHmbeFjM, EmOB39wJx3I, Indonesia 5LwhZV1rdMs/SV_oGlPU8uA/rxu2w66NhNU/ghxuq_80os4/8pDrxPUsmvo/_NJHv6yDOtE/ClMQQLwlnPk, USA 7g310Xq0AwE |
| `probat-sau-rang-xay-khu-khi.md` | Z9-x0jmOW9o, KSViq0NP3_g, kFoJamPWRkQ, 6b6J0r9eBw0, DhUtggX36Sg, nlzeIjeGWxg, Z-TLM2zgabU, web ground-coffee-degassing/gt-series |
| `probat-khi-thai-nang-luong.md` | aF8nX9mRqn8, a6RpYK9yNtQ, PYv2KCPh02A, PGNirqit0Gs, l6KSzwlcRwQ, ljDcBLbrujw, DNuvjAE0zqE, eJFRbcAE6cA, web proforte-frto/proair/tvr-nvk/green-coffee-preheating-rkv |
| `probat-bao-tri-ma-loi.md` | EFlimcdVmsQ, loạt Probat USA (q-POR3fsvYs, eyJ7KZQvJDQ, nLOYAoZbBQY, NsCu0lCCjgM, 2Isz-wd0Kmc, 7g310Xq0AwE, 19NmsDlAZLE, GUoLCQbKGpI, dW-aPlICWdA, 4UMU5RkfOog…), Indonesia 3jXJbi_5rMk/qWWKmCfC5Yw/KA3LW3n7SCw, r0sxeu-IMKs, service chapters flJe18yhM9o/Iljb9vdvpYc/I_57SuMOcpI |
| `probat-cacao-san-pham-khac.md` | T7o9lfDf1uM, ekmHpJU8FG8, eQarIkIm0tM, MVdFNjOPhww, BaPJTBAb-DQ, web batch-roaster-nibs/continuous-roaster-louver/continuous-roaster-shaft |
