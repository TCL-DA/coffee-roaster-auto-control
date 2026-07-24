"""
Ed25519 thuần Python (RFC 8032) — ký/kiểm license OTL Roast Lab (GĐ2 §16.4).

VÌ SAO TỰ VIẾT THAY VÌ pip install cryptography:
    App chỉ cần verify chữ ký ĐÚNG MỘT LẦN lúc mở (và sign trong tool admin của
    người bán). Gói `cryptography` kéo theo ~3MB native wheel + đau đầu PyInstaller;
    bản tham chiếu RFC 8032 ~100 dòng, chậm (~100ms/verify) nhưng chạy 1 lần thì
    không ai thấy. Cùng triết lý với otl_link tự viết Modbus thay pymodbus.

⚠ KHÔNG dùng cho hệ cần chống side-channel (đây là license offline, không phải
TLS). Ai cần tốc độ/độ an toàn kênh kề hãy dùng thư viện thật.
"""

import hashlib

_p = 2 ** 255 - 19
_q = 2 ** 252 + 27742317777372353535851937790883648493


def _H(m: bytes) -> bytes:
    return hashlib.sha512(m).digest()


def _inv(x: int) -> int:
    return pow(x, _p - 2, _p)


_d = -121665 * _inv(121666) % _p
_I = pow(2, (_p - 1) // 4, _p)


def _xrecover(y: int) -> int:
    xx = (y * y - 1) * _inv(_d * y * y + 1)
    x = pow(xx, (_p + 3) // 8, _p)
    if (x * x - xx) % _p != 0:
        x = x * _I % _p
    if x % 2 != 0:
        x = _p - x
    return x


_By = 4 * _inv(5) % _p
_Bx = _xrecover(_By)
_B = (_Bx, _By)


def _add(P, Q):
    x1, y1 = P
    x2, y2 = Q
    x3 = (x1 * y2 + x2 * y1) * _inv(1 + _d * x1 * x2 * y1 * y2)
    y3 = (y1 * y2 + x1 * x2) * _inv(1 - _d * x1 * x2 * y1 * y2)
    return (x3 % _p, y3 % _p)


def _mul(P, e: int):
    """Nhân vô hướng — lặp (không đệ quy, khỏi lo giới hạn stack)."""
    Q = (0, 1)
    while e:
        if e & 1:
            Q = _add(Q, P)
        P = _add(P, P)
        e >>= 1
    return Q


def _bit(h: bytes, i: int) -> int:
    return (h[i // 8] >> (i % 8)) & 1


def _encodepoint(P) -> bytes:
    x, y = P
    return (y | ((x & 1) << 255)).to_bytes(32, "little")


def _decodepoint(s: bytes):
    y = int.from_bytes(s, "little") & ((1 << 255) - 1)
    x = _xrecover(y)
    if x & 1 != _bit(s, 255):
        x = _p - x
    P = (x, y)
    if (-x * x + y * y - 1 - _d * x * x * y * y) % _p != 0:
        raise ValueError("điểm không nằm trên curve")
    return P


def _clamp(h: bytes) -> int:
    a = 2 ** 254 + sum(2 ** i * _bit(h, i) for i in range(3, 254))
    return a


def _hint(m: bytes) -> int:
    return int.from_bytes(_H(m), "little")


def publickey(sk: bytes) -> bytes:
    """Khoá công khai 32 byte từ khoá bí mật 32 byte."""
    a = _clamp(_H(sk))
    return _encodepoint(_mul(_B, a))


def sign(msg: bytes, sk: bytes, pk: bytes) -> bytes:
    """Chữ ký 64 byte (R‖S)."""
    h = _H(sk)
    a = _clamp(h)
    r = _hint(h[32:64] + msg) % _q
    R = _mul(_B, r)
    S = (r + _hint(_encodepoint(R) + pk + msg) * a) % _q
    return _encodepoint(R) + S.to_bytes(32, "little")


def verify(sig: bytes, msg: bytes, pk: bytes) -> bool:
    """True nếu chữ ký hợp lệ. Mọi lỗi định dạng → False, không nổ exception."""
    try:
        if len(sig) != 64 or len(pk) != 32:
            return False
        R = _decodepoint(sig[:32])
        A = _decodepoint(pk)
        S = int.from_bytes(sig[32:64], "little")
        if S >= _q:
            return False
        h = _hint(sig[:32] + pk + msg) % _q
        return _mul(_B, S) == _add(R, _mul(A, h))
    except Exception:
        return False
