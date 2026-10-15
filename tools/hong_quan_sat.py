# -*- coding: utf-8 -*-
"""CHỈ ĐỌC: ghi log 1 Hz từ panel khi anh Thành tự lái (15/10/2026). Không ghi thanh ghi nào.
    python tools/hong_quan_sat.py <csv> [--phut 30]
    python tools/hong_quan_sat.py <csv> --rang 1 [--phut 40]     # MẺ RANG THẬT: tự nhận CHARGE / TP / DROP, dừng DROP + 2 phút
Dừng (chế độ về 200) khi: anh không đổi Nhiệt/gió/trống/Lệnh 3 phút VÀ BT trong 200 ± 1,5 ≥ 2 phút; hoặc quá --phut; hoặc file <csv>.dung xuất hiện.
Ngưỡng an toàn tuyệt đối (BT > 245 / ET > 255): in CANH BAO + thoát mã 3 (người gọi quyết an_toan)."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hong_qua_panel as hq  # noqa: E402

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    pos, opt = hq._tach_opt(sys.argv[1:])
    duong, phut = pos[0], float(opt.get("phut", 30))
    rang = opt.get("rang", "0") == "1"
    ls, moc = [], {}
    p = hq.Panel()
    moi = not os.path.exists(duong)
    f = open(duong, "a", encoding="utf-8")
    if moi:
        f.write("gio,t,bt,et,buong,dat_nhiet,nhiet,lenh,dat_gio,gio,dat_trong,trong,ma,pc,man\n")
    t0 = t_ok = time.time()
    t_doi = t0
    t_trong = None
    cu = None
    while True:
        now = time.time()
        try:
            d = p.doc_tat_ca()
            t_ok = now
        except (OSError, ValueError) as e:
            if now - t_ok > 10:
                print("MAT SO PANEL > 10 s (%s)" % e, flush=True)
            time.sleep(1)
            continue
        dk = (d["dat_nhiet"], d["lenh_nhiet"], d["dat_gio"], d["dat_trong"])
        if cu is not None and dk != cu:
            t_doi = now
            print("%s THAO TAC: %s -> %s · BT %.1f ET %.1f buong %s" % (time.strftime("%H:%M:%S"), cu, dk, d["bt"], d["et"],
                                                                     d["buong"]), flush=True)
        cu = dk
        if abs(d["bt"] - 200.0) <= 1.5:
            t_trong = t_trong or now
        else:
            t_trong = None
        f.write("%s,%.1f,%.1f,%.1f,%s,%d,%.1f,%d,%d,%.1f,%d,%.1f,%d,%d,%d\n" % (
            time.strftime("%H:%M:%S"), now - t0, d["bt"], d["et"], d["buong"], d["dat_nhiet"], d["nhiet"], d["lenh_nhiet"],
            d["dat_gio"], d["gio"], d["dat_trong"], d["trong"], d["ma"], d["pc_control"], d["man"]))
        f.flush()
        if d["bt"] > hq.BT_TUYET_DOI or d["et"] > hq.ET_MAX:
            print("CANH BAO AN TOAN: BT %.1f ET %.1f" % (d["bt"], d["et"]), flush=True)
            sys.exit(3)
        if rang:
            ls.append((now, d["bt"]))
            ls = [x for x in ls if now - x[0] <= 30]
            rot = max(b for _, b in ls) - d["bt"]
            if "CHARGE" not in moc and rot >= 25:
                moc["CHARGE"] = now
                moc["_tp"] = (d["bt"], now)
                print("%s MOC CHARGE (BT rơi %.0f °C/30 s) · BT %.1f" % (time.strftime("%H:%M:%S"), rot, d["bt"]), flush=True)
            elif "CHARGE" in moc and "TP" not in moc:
                if d["bt"] < moc["_tp"][0]:
                    moc["_tp"] = (d["bt"], now)
                elif d["bt"] > moc["_tp"][0] + 1.0:
                    moc["TP"] = moc["_tp"][1]
                    print("%s MOC TP %.1f (lúc %s)" % (time.strftime("%H:%M:%S"), moc["_tp"][0],
                                                     time.strftime("%H:%M:%S", time.localtime(moc["_tp"][1]))), flush=True)
            elif "TP" in moc and "DE" not in moc and d["bt"] >= 155:
                moc["DE"] = now
                print("%s MOC ~DE BT 155 · %.0f s sau CHARGE" % (time.strftime("%H:%M:%S"), now - moc["CHARGE"]), flush=True)
            elif "CHARGE" in moc and "DROP" not in moc and now - moc["CHARGE"] > 360 and rot >= 15:
                moc["DROP"] = now
                print("%s MOC DROP (BT rơi %.0f °C/30 s) · BT %.1f · %.0f s sau CHARGE" % (
                    time.strftime("%H:%M:%S"), rot, d["bt"], now - moc["CHARGE"]), flush=True)
            if "DROP" in moc and now - moc["DROP"] >= 120:
                print("%s KET THUC: DROP + 2 phút" % time.strftime("%H:%M:%S"), flush=True)
                break
        elif t_trong and now - t_trong >= 120 and now - t_doi >= 180:
            print("%s KET THUC: anh không đổi 3 phút, BT trong 200 ± 1,5 đã %.0f s" % (time.strftime("%H:%M:%S"), now - t_trong))
            break
        if now - t0 > phut * 60 or os.path.exists(duong + ".dung"):
            print("%s KET THUC: hết giờ / được báo dừng" % time.strftime("%H:%M:%S"))
            break
        time.sleep(max(0.0, 1.0 - (time.time() - now)))
    f.close()
