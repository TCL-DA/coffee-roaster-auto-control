"""Tạo icon Liquid Glass đỏ–đen cho Scale Simulator -> scale_icon.ico / .png.

Biến tấu từ logo khung vuông bo góc (kiểu chữ "Q/a"): vành đỏ glossy có khe hở
góc trên-trái và đuôi chéo góc dưới-phải, bên trong 2 thanh ngang + ô chữ "a".
Nền tile vuông bo góc kiểu app iOS, gradient đen, có lớp gloss kính phía trên.

Vẽ ở độ phân giải cao (supersample) rồi thu nhỏ cho cạnh mượt (anti-alias).
Chạy:  python tools/make_icon.py
"""
from PIL import Image, ImageDraw

SS = 4                      # hệ số supersample
S = 512                     # cạnh icon đích
N = S * SS                  # cạnh canvas vẽ

# ---- Bảng màu đỏ–đen ----
TILE_TOP = (38, 38, 42)     # đen hơi xám (đỉnh tile)
TILE_BOT = (8, 8, 10)       # đen sâu (đáy tile)
RED_HI = (255, 78, 64)      # đỏ sáng (gloss đỉnh vành)
RED_LO = (196, 14, 12)      # đỏ đậm (đáy vành)
INNER_HI = (255, 90, 80)    # thanh trong — đỏ sáng
INNER_LO = (214, 28, 22)


def vgrad(w, h, top, bot):
    """Ảnh gradient dọc (RGB)."""
    base = Image.new("RGB", (1, h))
    px = base.load()
    for y in range(h):
        t = y / (h - 1)
        px[0, y] = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
    return base.resize((w, h))


def rrect(draw, box, radius, fill):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


# ════════════════════════════════════════════════════════════════════════════
#  1) TILE nền: vuông bo góc + gradient đen + gloss kính trên
# ════════════════════════════════════════════════════════════════════════════
img = Image.new("RGBA", (N, N), (0, 0, 0, 0))

tile_r = int(N * 0.225)
tile_mask = Image.new("L", (N, N), 0)
ImageDraw.Draw(tile_mask).rounded_rectangle([0, 0, N - 1, N - 1], radius=tile_r, fill=255)
img.paste(vgrad(N, N, TILE_TOP, TILE_BOT).convert("RGBA"), (0, 0), tile_mask)

# Gloss kính: vệt sáng mềm phủ nửa trên, cắt theo tile
gloss = Image.new("RGBA", (N, N), (0, 0, 0, 0))
ImageDraw.Draw(gloss).ellipse([-N * 0.25, -N * 0.70, N * 1.25, N * 0.42],
                              fill=(255, 255, 255, 38))
gloss.putalpha(Image.composite(gloss.getchannel("A"), Image.new("L", (N, N), 0), tile_mask))
img = Image.alpha_composite(img, gloss)

# ════════════════════════════════════════════════════════════════════════════
#  2) MARK: vành đỏ (ring) + khe hở góc trên-trái + đuôi chéo dưới-phải
# ════════════════════════════════════════════════════════════════════════════
mark = Image.new("L", (N, N), 0)          # mask hình dấu (trắng = có mực)
md = ImageDraw.Draw(mark)

a = int(N * 0.16)                          # lề ngoài vành
w = int(N * 0.105)                         # bề dày vành
ro = int(N * 0.17)                         # bo góc ngoài
ri = int(N * 0.085)                        # bo góc trong
md.rounded_rectangle([a, a, N - a, N - a], radius=ro, fill=255)
md.rounded_rectangle([a + w, a + w, N - a - w, N - a - w], radius=ri, fill=0)

# Khe hở góc trên-trái: xoá một khối chéo (parallelogram) cắt ngang vành trên
gap = Image.new("L", (N, N), 0)
ImageDraw.Draw(gap).polygon(
    [(a - 4, a + int(w * 0.15)), (a + int(N * 0.16), a - 6),
     (a + int(N * 0.20), a + w + 6), (a - 4, a + w + int(N * 0.05))], fill=255)
mark = Image.composite(Image.new("L", (N, N), 0), mark, gap)

# Đuôi chéo góc dưới-phải (nét chữ Q): thêm một thanh chéo nhô ra ngoài
tail = Image.new("L", (N, N), 0)
td = ImageDraw.Draw(tail)
cx2 = N - a - int(w * 0.5)
cy2 = N - a - int(w * 0.5)
td.line([(cx2 - int(N * 0.02), cy2 - int(N * 0.02)),
         (cx2 + int(N * 0.14), cy2 + int(N * 0.14))],
        fill=255, width=int(w * 0.95))
mark = Image.composite(Image.new("L", (N, N), 255), mark, tail)

# ════════════════════════════════════════════════════════════════════════════
#  3) Hai thanh ngang + ô chữ "a" bên trong  (mask riêng để tô màu khác)
# ════════════════════════════════════════════════════════════════════════════
inner = Image.new("L", (N, N), 0)
nd = ImageDraw.Draw(inner)
bx0, bx1 = int(N * 0.305), int(N * 0.695)   # bề ngang khối trong
br = int(N * 0.028)
# Thanh ngang trên
nd.rounded_rectangle([bx0, int(N * 0.385), bx1, int(N * 0.455)], radius=br, fill=255)
# Khối dưới (ô chữ 'a') + lỗ hình chữ nhật
nd.rounded_rectangle([bx0, int(N * 0.475), bx1, int(N * 0.635)], radius=br, fill=255)
nd.rounded_rectangle([int(N * 0.375), int(N * 0.525), int(N * 0.625), int(N * 0.590)],
                     radius=int(br * 0.7), fill=0)

# ---- Tô màu gradient cho vành & thanh trong (liquid glass) ----
red_grad = vgrad(N, N, RED_HI, RED_LO).convert("RGBA")
inner_grad = vgrad(N, N, INNER_HI, INNER_LO).convert("RGBA")
img.paste(red_grad, (0, 0), mark)
img.paste(inner_grad, (0, 0), inner)

# Specular kính: vệt sáng trắng mảnh dọc mép trên của vành đỏ
spec = Image.new("L", (N, N), 0)
sd = ImageDraw.Draw(spec)
sd.rounded_rectangle([a + int(w * 0.2), a + int(w * 0.18),
                      N - a - int(w * 0.2), a + int(w * 0.42)],
                     radius=ro, outline=255, width=int(w * 0.16))
spec = Image.composite(spec, Image.new("L", (N, N), 0), mark)   # chỉ giữ phần trên vành
white = Image.new("RGBA", (N, N), (255, 255, 255, 90))
img.paste(white, (0, 0), spec)

# ════════════════════════════════════════════════════════════════════════════
#  4) Thu nhỏ (anti-alias) + lưu .ico nhiều cỡ + .png xem trước
# ════════════════════════════════════════════════════════════════════════════
icon = img.resize((S, S), Image.LANCZOS)
sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
icon.save("tools/scale_icon.ico", sizes=sizes)
icon.save("tools/scale_icon.png")
print("OK: tools/scale_icon.ico + scale_icon.png (Liquid Glass red-black)")
