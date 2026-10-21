# -*- coding: utf-8 -*-
"""Tìm THƯ MỤC DỮ LIỆU mà app Roast Lab đang chạy thực sự dùng.

Vì sao cần: `app_data_dir()` trong `roast_lab_hmi.py` trả về hai chỗ khác nhau

  * chạy dev (`python tools/roast_lab_hmi.py`) → `tools/appdata`
  * chạy bản EXE đóng gói                      → **cạnh exe**, tức `tools/dist`

Các bộ kiểm HTTP trước đây ghim cứng `tools/appdata`. Khi app đang chạy là bản
EXE thì khoá API do bộ kiểm tạo nằm ở thư mục mà máy chủ KHÔNG đọc, nên mọi khoá
hợp lệ đều bị trả 401 và bộ kiểm báo sai hàng loạt — trong khi phần quyền của app
vẫn đúng.

Cách làm ở đây là **dò chứ không đoán**: tạo một khoá chỉ-đọc tạm trong từng thư
mục ứng viên rồi gọi thử API. Thư mục nào làm khoá có tác dụng thì đó là thư mục
thật. Khoá tạm luôn được xoá, kể cả khi dò hỏng.
"""
import json
import os
import urllib.error
import urllib.request as U

from otl_apikey import ApiKeyStore

HERE = os.path.dirname(os.path.abspath(__file__))


def ung_vien():
    """Các thư mục có thể là nơi app để dữ liệu, xếp thư mục có dấu hiệu mới
    nhất lên trước để lần dò đầu tiên thường trúng luôn."""
    ds = [os.path.join(HERE, "appdata"), os.path.join(HERE, "dist")]
    ds = [d for d in ds if os.path.isdir(d)]

    def moi_nhat(d):
        t = 0.0
        for ten in ("state.json", "app_config.json", "auth.json"):
            p = os.path.join(d, ten)
            if os.path.exists(p):
                t = max(t, os.path.getmtime(p))
        return t

    return sorted(ds, key=moi_nhat, reverse=True)


def _thu_khoa(base_url, key, duong_dan="/api/snapshot", timeout=8):
    r = U.Request(base_url + duong_dan)
    r.add_header("Authorization", "Bearer " + key)
    try:
        with U.urlopen(r, timeout=timeout) as x:
            return x.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def tim_thu_muc(base_url, duong_dan="/api/snapshot"):
    """Trả về (thư_mục, kho_khoá) của app đang chạy, hoặc (None, None).

    Gọi khi app đã chạy sẵn — nếu app không chạy thì mọi lần dò đều trả 0 và hàm
    trả về (None, None) để bộ kiểm tự báo bỏ qua.
    """
    for d in ung_vien():
        co_file_truoc = os.path.exists(os.path.join(d, "apikeys.json"))
        st = ApiKeyStore(d)
        ban_ghi = None
        try:
            ban_ghi = st.add("test-do-thu-muc", ["read"])
            if _thu_khoa(base_url, ban_ghi["key"], duong_dan) == 200:
                return d, ApiKeyStore(d)
        except Exception:
            pass
        finally:
            if ban_ghi:
                try:
                    st.delete(ban_ghi["id"])
                except Exception:
                    pass
            # Không để lại file khoá rỗng ở thư mục vốn chưa hề có
            p = os.path.join(d, "apikeys.json")
            if not co_file_truoc and os.path.exists(p):
                try:
                    with open(p, encoding="utf-8") as f:
                        if not (json.load(f) or {}).get("keys"):
                            os.remove(p)
                except Exception:
                    pass
    return None, None
