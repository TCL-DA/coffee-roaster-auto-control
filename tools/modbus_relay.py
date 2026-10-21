"""
Modbus RTU cho module relay 8 kênh Waveshare "Modbus RTU Relay (B)" — giao thức V3.

Tách hẳn khỏi giao diện để test được bằng thiết bị giả:
  • dựng khung + CRC16 Modbus,
  • giao dịch hỏi–đáp trên cổng của OTL Serial Terminal (SerialManager),
    lọc rác đầu khung và tiếng dội (echo) của bộ chuyển USB-485,
  • dò tìm thiết bị (baud × parity × ID) và ghi cấu hình có kiểm tra lại.

Mọi hàm ở đây chạy trên LUỒNG PHỤ — không bao giờ đụng tới Tk.

Bản đồ thanh ghi (tài liệu hãng, V3):
  coil 0x0000–0x0007  relay CH1–CH8   FF00 bật · 0000 tắt · 5500 đảo   FC 01/05/0F
  coil 0x00FF         cả 8 relay       FF00 / 0000 / 5500                FC 05
  coil 0x0200+ch      bật rồi tự tắt   giá trị × 100 ms (tối đa 0x7FFF)  FC 05
  coil 0x0400+ch      tắt rồi tự bật   giá trị × 100 ms                  FC 05
  hold 0x2000         UART             byte cao = parity, byte thấp = mã baud
  hold 0x4000         địa chỉ          0x0001–0x00FF
  hold 0x8000         phiên bản        0x012C = V3.00
"""

import threading
import time

CHANNELS = 8

REG_UART = 0x2000
REG_ADDRESS = 0x4000
REG_VERSION = 0x8000
COIL_ALL = 0x00FF
FLASH_ON_BASE = 0x0200
FLASH_OFF_BASE = 0x0400
FLASH_MAX_TENTHS = 0x7FFF

ON, OFF, TOGGLE = 0xFF00, 0x0000, 0x5500

BAUD_CODES = {4800: 0, 9600: 1, 19200: 2, 38400: 3, 57600: 4, 115200: 5, 128000: 6, 256000: 7}
CODE_BAUDS = {code: baud for baud, code in BAUD_CODES.items()}
BAUD_SCAN_ORDER = [9600, 38400, 115200, 19200, 57600, 4800, 128000, 256000]

# Tài liệu hãng ghi NGƯỢC nhau giữa hai bảng: bảng 1 ghi 01 = Even, 02 = Odd;
# bảng 2 ghi 01 = Odd, 02 = Even. Lấy bảng 1 làm mặc định. Lúc ghi cấu hình,
# write_config() thử cả hai phía và tự sửa nếu module thật làm ngược.
PARITY_NAMES = ("None", "Even", "Odd")
DOC_PARITY_CODES = {"None": 0, "Even": 1, "Odd": 2}

EXCEPTION_NAMES = {
    0x01: "function không hỗ trợ",
    0x02: "sai địa chỉ thanh ghi",
    0x03: "giá trị không hợp lệ",
    0x04: "lỗi thiết bị",
    0x05: "đã nhận, đang xử lý",
    0x06: "thiết bị bận",
}


# ════════════════════════════════════════════════════════════════════════════
#  KHUNG & CRC
# ════════════════════════════════════════════════════════════════════════════
def crc16(data):
    """CRC16 Modbus, trả 2 byte theo thứ tự trên dây (byte thấp trước)."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return bytes((crc & 0xFF, crc >> 8))


def with_crc(body):
    body = bytes(body)
    return body + crc16(body)


def hexs(data):
    return " ".join(f"{b:02X}" for b in data)


def _u16(value):
    return bytes(((value >> 8) & 0xFF, value & 0xFF))


def req_read_coils(addr, start=0, qty=CHANNELS):
    return with_crc(bytes((addr, 0x01)) + _u16(start) + _u16(qty))


def req_read_register(addr, reg, qty=1):
    return with_crc(bytes((addr, 0x03)) + _u16(reg) + _u16(qty))


def req_write_coil(addr, coil, value):
    return with_crc(bytes((addr, 0x05)) + _u16(coil) + _u16(value))


def req_write_register(addr, reg, value):
    return with_crc(bytes((addr, 0x06)) + _u16(reg) + _u16(value))


def req_write_coils(addr, bits, start=0):
    """FC0F — ghi một lượt nhiều kênh; bits[0] là CH1."""
    mask = 0
    for i, on in enumerate(bits):
        if on:
            mask |= 1 << i
    nbytes = (len(bits) + 7) // 8
    return with_crc(bytes((addr, 0x0F)) + _u16(start) + _u16(len(bits))
                    + bytes((nbytes,)) + mask.to_bytes(nbytes, "little"))


def decode_uart(raw, parity_codes=None):
    """0x2000 → (baud | None, tên parity | None) theo bảng mã đang tin."""
    codes = parity_codes or DOC_PARITY_CODES
    parity = next((name for name, code in codes.items() if code == (raw >> 8)), None)
    return CODE_BAUDS.get(raw & 0xFF), parity


def version_text(raw):
    return f"V{raw // 100}.{raw % 100:02d}"


# ════════════════════════════════════════════════════════════════════════════
#  LỖI
# ════════════════════════════════════════════════════════════════════════════
class ModbusError(Exception):
    """Lỗi giao dịch Modbus. `code` là mã máy đọc được để UI rẽ nhánh."""
    code = "modbus_error"


class ModbusTimeout(ModbusError):
    code = "timeout"

    def __init__(self, message, garbage=b""):
        super().__init__(message)
        self.garbage = bytes(garbage)


class ModbusExceptionReply(ModbusError):
    code = "exception"

    def __init__(self, fc, exc_code, frame):
        name = EXCEPTION_NAMES.get(exc_code, "mã lạ")
        super().__init__(f"Thiết bị trả lỗi 0x{exc_code:02X} ({name}) cho FC{fc:02X}")
        self.exc_code = exc_code
        self.frame = frame


class ModbusCancelled(ModbusError):
    code = "cancelled"

    def __init__(self):
        super().__init__("Đã dừng")


# ════════════════════════════════════════════════════════════════════════════
#  TÁCH KHUNG TRẢ LỜI
# ════════════════════════════════════════════════════════════════════════════
def _expected_length(request, fc_reply, byte_count):
    """Độ dài khung trả lời hợp lệ cho request, hoặc None nếu byte đếm sai."""
    fc = request[1]
    if fc_reply == (fc | 0x80):
        return 5
    if fc in (0x01, 0x02):
        qty = int.from_bytes(request[4:6], "big")
        return 5 + byte_count if byte_count == (qty + 7) // 8 else None
    if fc in (0x03, 0x04):
        qty = int.from_bytes(request[4:6], "big")
        return 5 + byte_count if byte_count == 2 * qty else None
    return 8        # 05 / 06 / 0F / 10: trả về 8 byte


def find_reply(buf, request, any_addr=False):
    """Tìm khung trả lời hợp lệ cho `request` trong `buf`.

    Trả (frame | None, số byte rác đứng TRƯỚC). Rác = byte không thể là đầu một
    khung hợp lệ (sai địa chỉ, sai FC, byte đếm sai, sai CRC). Thấy khung thì
    frame nằm ngay sau phần rác; chưa về đủ thì trả (None, vị trí đầu khung).
    """
    addr, fc = request[0], request[1]
    i = 0
    while len(buf) - i >= 2:
        a, f = buf[i], buf[i + 1]
        if (not any_addr and a != addr) or f not in (fc, fc | 0x80):
            i += 1
            continue
        if f == fc and fc in (0x01, 0x02, 0x03, 0x04):
            if len(buf) - i < 3:
                return None, i
            n = _expected_length(request, f, buf[i + 2])
        else:
            n = _expected_length(request, f, 0)
        if n is None:
            i += 1
            continue
        if len(buf) - i < n:
            return None, i
        cand = bytes(buf[i:i + n])
        if crc16(cand[:-2]) == cand[-2:]:
            return cand, i
        i += 1
    return None, i


# ════════════════════════════════════════════════════════════════════════════
#  GIAO DỊCH HỎI–ĐÁP TRÊN CỔNG CỦA TERMINAL
# ════════════════════════════════════════════════════════════════════════════
class Reply:
    __slots__ = ("request", "frame", "elapsed_ms", "garbage")

    def __init__(self, request, frame, elapsed_ms, garbage):
        self.request, self.frame = request, frame
        self.elapsed_ms, self.garbage = elapsed_ms, garbage

    def register(self):
        return int.from_bytes(self.frame[3:5], "big")

    def coils(self, qty=CHANNELS):
        mask = int.from_bytes(self.frame[3:3 + self.frame[2]], "little")
        return [bool(mask >> i & 1) for i in range(qty)]


class ModbusRtuClient:
    """Master RTU dùng chung cổng với terminal.

    Luồng đọc của SerialManager gọi feed(chunk) cho MỌI cụm byte nhận được.
    Chỉ khi có phiên Modbus đang chạy (begin/end) thì client mới "nhận" byte
    đó (feed trả True) — terminal khỏi in lại khung nhị phân dưới dạng ASCII.
    Ngoài phiên, byte đi thẳng ra cửa sổ terminal như cũ.
    """

    def __init__(self, write, on_frame=None, gap_s=0.02):
        self._write = write                  # hàm ghi của SerialManager (chặn trần sẵn)
        self.on_frame = on_frame            # on_frame(kind, data, note) — luồng phụ gọi
        self._cond = threading.Condition()
        self._buf = bytearray()
        self._sessions = 0
        self._last_io = 0.0
        self.gap_s = gap_s                   # khoảng lặng tối thiểu giữa hai khung
        self.echo_seen = False               # bộ chuyển USB-485 dội lại lệnh gửi

    # ── phiên ──
    def begin(self):
        with self._cond:
            self._sessions += 1

    def end(self):
        with self._cond:
            self._sessions = max(0, self._sessions - 1)
            if not self._sessions:
                self._buf.clear()

    @property
    def active(self):
        with self._cond:
            return self._sessions > 0

    def feed(self, chunk):
        """Luồng đọc serial gọi. True = client đã nhận cụm byte này."""
        with self._cond:
            if self._sessions <= 0:
                return False
            self._buf += chunk
            if len(self._buf) > 4096:
                del self._buf[:-4096]
            self._cond.notify_all()
            return True

    def reset_echo(self):
        self.echo_seen = False

    # ── giao dịch ──
    def transact(self, request, timeout_s, cancel=None, any_addr=False,
                 expect_reply=True, note=""):
        if cancel is not None and cancel.is_set():
            raise ModbusCancelled()
        wait = self._last_io + self.gap_s - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        with self._cond:
            stale = bytes(self._buf)
            self._buf.clear()
        if stale and self.on_frame:
            self.on_frame("junk", stale, "byte thừa của khung trước")

        start = time.monotonic()
        written = self._write(request)
        if written != len(request):
            raise ModbusError(f"Chỉ gửi được {written}/{len(request)} byte")
        if self.on_frame:
            self.on_frame("tx", request, note)
        if not expect_reply:
            self._last_io = time.monotonic()
            return None

        deadline = start + timeout_s
        garbage = bytearray()
        echo_skipped = False
        try:
            with self._cond:
                while True:
                    if cancel is not None and cancel.is_set():
                        raise ModbusCancelled()
                    buf = self._buf
                    # Dội lại lệnh gửi: khung đọc (01/03) có dạng trả lời khác lệnh
                    # nên tự bị lọc; còn 05/06 thì trả lời GIỐNG HỆT lệnh — phải bỏ
                    # bản dội đầu tiên, nếu không thiết bị vắng mặt vẫn thành "OK".
                    if not echo_skipped and buf[:len(request)] == request:
                        if request[1] in (0x01, 0x02, 0x03, 0x04, 0x0F):
                            self.echo_seen = True
                        if self.echo_seen:
                            del buf[:len(request)]
                            echo_skipped = True
                            continue
                    frame, drop = find_reply(buf, request, any_addr)
                    if drop:
                        garbage += buf[:drop]
                        del buf[:drop]
                    if frame is not None:
                        del buf[:len(frame)]
                        break
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        garbage += buf
                        buf.clear()
                        raise ModbusTimeout("Không có trả lời" if not garbage else
                                            "Nhận rác, không giải được khung", garbage)
                    self._cond.wait(min(remaining, 0.05))
        finally:
            self._last_io = time.monotonic()

        elapsed = int((time.monotonic() - start) * 1000)
        if self.on_frame:
            if garbage:
                self.on_frame("junk", bytes(garbage), "rác trước khung trả lời")
            self.on_frame("rx", frame, f"{elapsed} ms")
        if frame[1] & 0x80:
            raise ModbusExceptionReply(request[1], frame[2], frame)
        return Reply(request, frame, elapsed, bytes(garbage))


# ════════════════════════════════════════════════════════════════════════════
#  LỆNH CẤP CAO CHO MODULE WAVESHARE
# ════════════════════════════════════════════════════════════════════════════
class WaveshareRelay:
    def __init__(self, client, baud_provider, timeout_ms=200):
        self.client = client
        self.baud_provider = baud_provider   # trả baud cổng đang chạy — để cộng thời gian truyền
        self.timeout_ms = timeout_ms
        self.parity_codes = dict(DOC_PARITY_CODES)
        self.cancel = None                   # threading.Event của tác vụ đang chạy

    def _timeout(self, request_len, reply_len):
        baud = max(300, int(self.baud_provider() or 9600))
        wire = (request_len + reply_len) * 11 / baud
        return self.timeout_ms / 1000 + wire

    def _tx(self, request, reply_len, any_addr=False, expect_reply=True, note=""):
        return self.client.transact(request, self._timeout(len(request), reply_len),
                                    cancel=self.cancel, any_addr=any_addr,
                                    expect_reply=expect_reply, note=note)

    # ── đọc ──
    def read_register(self, addr, reg, note=""):
        return self._tx(req_read_register(addr, reg), 7, any_addr=(addr == 0), note=note).register()

    def read_address(self, addr=0, note=""):
        return self.read_register(addr, REG_ADDRESS, note or ("đọc địa chỉ (broadcast)" if addr == 0
                                                             else "đọc địa chỉ"))

    def read_uart(self, addr):
        raw = self.read_register(addr, REG_UART, "đọc UART 0x2000")
        baud, parity = decode_uart(raw, self.parity_codes)
        return raw, baud, parity

    def read_version(self, addr):
        return version_text(self.read_register(addr, REG_VERSION, "đọc phiên bản"))

    def read_coils(self, addr, note="đọc trạng thái 8 kênh"):
        return self._tx(req_read_coils(addr), 6, note=note).coils()

    def read_config(self, addr):
        raw, baud, parity = self.read_uart(addr)
        return {
            "address": self.read_address(addr),
            "uart_raw": raw, "baud": baud, "parity": parity,
            "version": self.read_version(addr),
        }

    # ── relay ──
    def write_channel(self, addr, ch, value):
        name = {ON: "bật", OFF: "tắt", TOGGLE: "đảo"}[value]
        self._tx(req_write_coil(addr, ch, value), 8, expect_reply=(addr != 0),
                 note=f"CH{ch + 1} {name}")

    def write_all(self, addr, value):
        name = {ON: "bật hết", OFF: "tắt hết", TOGGLE: "đảo hết"}[value]
        self._tx(req_write_coil(addr, COIL_ALL, value), 8, expect_reply=(addr != 0), note=name)

    def write_mask(self, addr, bits):
        self._tx(req_write_coils(addr, bits), 8, expect_reply=(addr != 0), note="ghi 8 kênh")

    def flash(self, addr, ch, on_first, tenths):
        tenths = max(1, min(FLASH_MAX_TENTHS, int(tenths)))
        base = FLASH_ON_BASE if on_first else FLASH_OFF_BASE
        what = "bật rồi tự tắt" if on_first else "tắt rồi tự bật"
        self._tx(req_write_coil(addr, base + ch, tenths), 8, expect_reply=(addr != 0),
                 note=f"CH{ch + 1} {what} sau {tenths * 100} ms")

    # ── cấu hình ──
    def set_address(self, addr, new_addr):
        self._tx(req_write_register(addr, REG_ADDRESS, new_addr), 8,
                 note=f"đổi địa chỉ → {new_addr}")

    def set_uart(self, addr, baud, parity):
        value = (self.parity_codes[parity] << 8) | BAUD_CODES[baud]
        self._tx(req_write_register(addr, REG_UART, value), 8,
                 note=f"đổi UART → {baud} {parity} (0x{value:04X})")


# ════════════════════════════════════════════════════════════════════════════
#  DÒ TÌM THIẾT BỊ
# ════════════════════════════════════════════════════════════════════════════
def scan_combos(relay, configure, combos, ids=None, on_progress=None, on_log=None):
    """Dò trên MỘT cổng đã mở.

    combos: [(baud, parity)] theo thứ tự thử. configure(baud, parity) đổi cấu
    hình cổng, trả False nếu driver không nhận tốc độ đó.
    ids=None → dò nhanh bằng broadcast đọc 0x4000 (module Waveshare trả lời
    broadcast; chỉ đúng khi bus có một module). ids=[...] → hỏi lần lượt từng ID.

    Chỉ gửi lệnh ĐỌC (FC03). Tìm thấy ở một tổ hợp thì bỏ các tổ hợp còn lại —
    mọi thiết bị trên cùng bus bắt buộc chạy chung baud/parity.
    """
    found = []
    per_combo = len(ids) if ids else 1
    total = len(combos) * per_combo
    done = 0
    for baud, parity in combos:
        if relay.cancel is not None and relay.cancel.is_set():
            raise ModbusCancelled()
        if not configure(baud, parity):
            done += per_combo
            if on_log:
                on_log(f"Bỏ qua {baud} {parity[0]}: driver không nhận tốc độ này")
            continue
        noisy = False
        targets = ids or [0]
        for target in targets:
            label = "broadcast" if target == 0 else f"ID {target}"
            if on_progress:
                on_progress(done, total, f"{baud} 8{parity[0]}1 · {label}")
            done += 1
            try:
                value = relay.read_register(target, REG_ADDRESS,
                                            f"dò {baud} 8{parity[0]}1 · {label}")
            except ModbusExceptionReply as exc:
                found.append(_found(baud, parity, target, kind="other",
                                    detail=f"trả lỗi 0x{exc.exc_code:02X} khi đọc 0x4000"))
                continue
            except ModbusTimeout as exc:
                noisy = noisy or bool(exc.garbage)
                continue
            addr = value if target == 0 else target
            if target and value != target:
                found.append(_found(baud, parity, target, kind="other",
                                    detail=f"0x4000 = {value}, không phải địa chỉ"))
                continue
            if not 1 <= addr <= 0xFF:
                noisy = True
                continue
            item = _found(baud, parity, addr, kind="waveshare")
            try:
                item["version"] = relay.read_version(addr)
                raw, _, _ = relay.read_uart(addr)
                item["uart_raw"] = raw
            except ModbusCancelled:
                raise
            except ModbusError:
                pass
            found.append(item)
            if target == 0:
                break
        if noisy and on_log:
            on_log(f"{baud} 8{parity[0]}1: có tín hiệu nhưng không giải được — sai tốc độ, "
                   "sai parity hoặc nhiều thiết bị cùng trả lời broadcast")
        if found:
            done = total
            if on_progress:
                on_progress(done, total, "Đã thấy thiết bị")
            break
    return found


def _found(baud, parity, addr, kind, detail=""):
    return {"baud": baud, "parity": parity, "address": addr, "kind": kind,
            "detail": detail, "version": None, "uart_raw": None}


# ════════════════════════════════════════════════════════════════════════════
#  GHI CẤU HÌNH — CÓ KIỂM TRA LẠI
# ════════════════════════════════════════════════════════════════════════════
def write_config(relay, configure, current, target, broadcast=False, on_log=None):
    """Đổi địa chỉ và/hoặc UART rồi đọc lại để xác nhận.

    current / target: {"address", "baud", "parity"}. configure(baud, parity)
    đổi cổng. Trả {"address", "baud", "parity", "parity_swapped"} là cấu hình
    ĐÃ XÁC NHẬN bằng một lần đọc thành công.
    """
    log = on_log or (lambda _m: None)
    addr = current["address"]
    swapped = False

    if broadcast or target["address"] != current["address"]:
        sender = 0 if broadcast else addr
        try:
            relay.set_address(sender, target["address"])
        except ModbusTimeout:
            if not broadcast:
                raise
            log("Broadcast đổi địa chỉ không có trả lời — đọc lại để kiểm tra")
        time.sleep(0.15)
        got = relay.read_address(target["address"])
        if got != target["address"]:
            raise ModbusError(f"Đọc lại địa chỉ ra {got}, không phải {target['address']}")
        addr = target["address"]
        log(f"Đã xác nhận địa chỉ mới = {addr}")

    if (target["baud"], target["parity"]) != (current["baud"], current["parity"]):
        try:
            relay.set_uart(addr, target["baud"], target["parity"])
        except ModbusTimeout:
            # Module có thể đổi tốc độ trước khi kịp trả lời ở tốc độ cũ.
            log("Lệnh đổi UART không có trả lời ở tốc độ cũ — chuyển sang tốc độ mới để kiểm tra")
        time.sleep(0.3)
        want = target["parity"]
        tries = [want] + ([("Odd" if want == "Even" else "Even")] if want != "None" else [])
        confirmed = None
        for parity in tries:
            if not configure(target["baud"], parity):
                raise ModbusError(f"Driver cổng không nhận {target['baud']} baud")
            try:
                relay.read_register(addr, REG_UART, f"kiểm tra ở {target['baud']} 8{parity[0]}1")
                confirmed = parity
                break
            except ModbusCancelled:
                raise
            except ModbusError:
                continue
        if confirmed is None:
            configure(current["baud"], current["parity"])
            try:
                relay.read_register(addr, REG_UART, "kiểm tra ở cấu hình cũ")
                raise ModbusError("Thiết bị vẫn chạy cấu hình cũ — lệnh đổi UART không ăn")
            except ModbusTimeout:
                raise ModbusError("Không thấy thiết bị ở cấu hình mới lẫn cũ — tắt/bật nguồn "
                                  "module rồi bấm Quét tìm thiết bị") from None
        if confirmed != want:
            # Module làm theo bảng 2 của tài liệu: mã Even/Odd ngược. Học lại
            # bảng mã rồi ghi lần nữa cho đúng parity người dùng chọn.
            swapped = True
            relay.parity_codes["Even"], relay.parity_codes["Odd"] = (
                relay.parity_codes["Odd"], relay.parity_codes["Even"])
            log(f"Module hiểu mã parity NGƯỢC tài liệu (đang chạy {confirmed}) — ghi lại cho đúng {want}")
            try:
                relay.set_uart(addr, target["baud"], want)
            except ModbusTimeout:
                pass
            time.sleep(0.3)
            configure(target["baud"], want)
            relay.read_register(addr, REG_UART, f"kiểm tra lại ở {target['baud']} 8{want[0]}1")
        log(f"Đã xác nhận UART mới = {target['baud']} 8{want[0]}1")

    return {"address": addr, "baud": target["baud"], "parity": target["parity"],
            "parity_swapped": swapped}
