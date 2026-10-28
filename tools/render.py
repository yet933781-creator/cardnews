"""카드뉴스 렌더러 v2: content.json -> 1080x1350 JPG.
사용법: python render.py content.json out_dir

슬라이드 type:
  cover     : 상단 일러스트(휴대폰+문자) + 하단 태그·큰 제목
  list      : 라벨·제목 + 항목 카드 (badges 있으면 통신사 배지 줄 추가)
  timeline  : 라벨·제목 + 세로 타임라인 (steps: [[날짜, 설명], ...])
  compare   : 라벨·제목 + 전후 금액 비교 (before/after/save)
  checklist : 라벨·제목 + 체크 항목
"""
import json, sys, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1350
M = 80
FD = "/usr/share/fonts/opentype/noto/"
C = {
    "bg": (12, 18, 40), "bg2": (22, 32, 70), "text": (246, 248, 252), "sub": (168, 180, 212),
    "accent": (255, 212, 56), "mint": (80, 226, 186), "coral": (255, 112, 102), "sky": (96, 170, 255),
    "card": (30, 44, 90), "tagred": (232, 52, 60),
}
BADGE_COLORS = [C["coral"], C["sky"], C["accent"]]


def font(weight, size):
    files = {"black": "NotoSansCJK-Black.ttc", "bold": "NotoSansCJK-Bold.ttc",
             "medium": "NotoSansCJK-Medium.ttc", "regular": "NotoSansCJK-Regular.ttc"}
    for i in range(6):
        f = ImageFont.truetype(FD + files[weight], size, index=i)
        if "KR" in f.getname()[0]:
            return f
    return ImageFont.truetype(FD + files[weight], size)


def wrap(d, text, f, maxw):
    out = []
    for para in text.split("\n"):
        line = ""
        for w in para.split(" "):
            t = (line + " " + w).strip()
            if d.textlength(t, font=f) <= maxw:
                line = t
            else:
                if line:
                    out.append(line)
                line = w
        out.append(line)
    return out


def text_block(d, x, y, text, f, fill, maxw, gap=1.3):
    for ln in wrap(d, text, f, maxw):
        d.text((x, y), ln, font=f, fill=fill)
        y += int(f.size * gap)
    return y


def gradient(img, top, bottom, y0=0, y1=H):
    d = ImageDraw.Draw(img)
    for y in range(y0, y1):
        t = (y - y0) / max(1, y1 - y0)
        d.line([(0, y), (W, y)], fill=tuple(int(top[k] * (1 - t) + bottom[k] * t) for k in range(3)))


def glow(img, cx, cy, r, color, alpha=120):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse([cx - r, cy - r, cx + r, cy + r], fill=color + (alpha,))
    layer = layer.filter(ImageFilter.GaussianBlur(r // 2))
    img.paste(layer, (0, 0), layer)


def pill(d, x, y, text, f, bg, fg, padx=26, h=None, anchor_right=False):
    tw = d.textlength(text, font=f)
    h = h or int(f.size * 1.75)
    w = tw + padx * 2
    if anchor_right:
        x = x - w
    d.rounded_rectangle([x, y, x + w, y + h], h // 2, fill=bg)
    d.text((x + padx, y + (h - f.size) / 2 - f.size * 0.18), text, font=f, fill=fg)
    return x + w


def frame(i, n, brand):
    img = Image.new("RGB", (W, H))
    gradient(img, C["bg"], C["bg2"])
    d = ImageDraw.Draw(img)
    # 페이지 표시 (참고 이미지처럼 우측 상단 둥근 배지)
    pill(d, W - 50, 44, f"{i}/{n}", font("bold", 30), (0, 0, 0), C["text"], padx=22, anchor_right=True)
    footer(d, i, n, brand)
    return img, d


def footer(d, i, n, brand):
    d.text((M, H - 74), brand, font=font("bold", 28), fill=C["sub"])
    for k in range(n):
        cx = W // 2 - (n - 1) * 14 + k * 28
        d.ellipse([cx - 6, H - 60, cx + 6, H - 48], fill=C["accent"] if k == i - 1 else (60, 76, 130))


def header(d, s, y=120):
    d.text((M, y), s.get("label", ""), font=font("black", 40), fill=C["accent"])
    return text_block(d, M, y + 78, s["title"], font("black", 74), C["text"], W - 2 * M, 1.25) + 40


def draw_phone(img, cx, top, s):
    """원본 일러스트: 휴대폰 화면 속 통신사 안내 문자."""
    d = ImageDraw.Draw(img)
    pw, ph = 430, 640
    x0, y0 = cx - pw // 2, top
    glow(img, cx, top + ph // 2, 330, C["sky"], 90)
    glow(img, cx + 160, top + 140, 180, C["accent"], 70)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x0, y0, x0 + pw, y0 + ph], 64, fill=(8, 10, 20))
    d.rounded_rectangle([x0 + 14, y0 + 14, x0 + pw - 14, y0 + ph - 14], 52, fill=(236, 240, 248))
    d.rounded_rectangle([cx - 60, y0 + 30, cx + 60, y0 + 62], 16, fill=(8, 10, 20))  # 카메라 섬
    # 메시지 앱 상단
    d.text((x0 + 50, y0 + 96), "‹  통신사 고객센터", font=font("bold", 30), fill=(40, 48, 70))
    d.line([(x0 + 30, y0 + 150), (x0 + pw - 30, y0 + 150)], fill=(205, 212, 226), width=2)
    # 말풍선
    bx0, by0 = x0 + 40, y0 + 185
    d.rounded_rectangle([bx0, by0, x0 + pw - 50, by0 + 250], 34, fill=(255, 255, 255))
    d.text((bx0 + 28, by0 + 26), "[요금제 안내]", font=font("black", 30), fill=C["tagred"])
    text_block(d, bx0 + 28, by0 + 76, s.get("sms", ""), font("medium", 27), (40, 48, 70), pw - 150, 1.4)
    # 절약 강조 말풍선
    sx0, sy0 = x0 + 70, by0 + 280
    d.rounded_rectangle([sx0, sy0, x0 + pw - 40, sy0 + 120], 34, fill=C["accent"])
    d.text((sx0 + 30, sy0 + 22), s.get("save_bubble", ""), font=font("black", 48), fill=(20, 24, 40))


def badges_row(d, x, y, names, size=44, center=False):
    f = font("black", size)
    widths = [d.textlength(nm, font=f) + 64 for nm in names]
    total = sum(widths) + 22 * (len(names) - 1)
    if center:
        x = (W - total) // 2
    for nm, col in zip(names, BADGE_COLORS):
        x = pill(d, x, y, nm, f, col, (16, 20, 38), padx=32) + 22
    return y + int(size * 1.75)


def render_cover(s, i, n, brand):
    img, d = frame(i, n, brand)
    draw_phone(img, W // 2 + 150, 150, s)
    d = ImageDraw.Draw(img)
    # 왼쪽 위 통신사 배지 세로 배치
    f = font("black", 44)
    y = 230
    for nm, col in zip(s.get("badges", []), BADGE_COLORS):
        pill(d, M, y, nm, f, col, (16, 20, 38), padx=34)
        y += 104
    # 하단 어둡게 (제목 가독성)
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    for yy in range(760, H):
        a = min(235, int((yy - 760) / 200 * 235))
        sd.line([(0, yy), (W, yy)], fill=C["bg"] + (a,))
    img.paste(shade, (0, 0), shade)
    d = ImageDraw.Draw(img)
    # 태그 (참고 이미지의 빨간 태그 + 카테고리)
    ty = 880
    nx = pill(d, M, ty, s.get("tag", "이슈"), font("black", 32), C["tagred"], (255, 255, 255), padx=20)
    d.text((nx + 16, ty + 9), s.get("tag2", ""), font=font("bold", 32), fill=C["text"])
    text_block(d, M, ty + 84, s["title"], font("black", 86), C["text"], W - 2 * M, 1.22)
    footer(d, i, n, brand)
    return img


def render_list(s, i, n, brand):
    img, d = frame(i, n, brand)
    y = header(d, s)
    if s.get("badges"):
        y = badges_row(d, M, y, s["badges"]) + 30
    fb = font("medium", 42)
    for item in s["items"]:
        lines = wrap(d, item, fb, W - 2 * M - 110)
        h = int(len(lines) * 42 * 1.42) + 40
        if y + h > H - 150:
            raise SystemExit(f"{i}번 카드: 내용이 넘칩니다")
        d.rounded_rectangle([M, y, W - M, y + h], 26, fill=C["card"])
        d.ellipse([M + 32, y + 32, M + 54, y + 54], fill=C["mint"])
        yy = y + 18
        for ln in lines:
            d.text((M + 82, yy), ln, font=fb, fill=C["text"])
            yy += int(42 * 1.42)
        y += h + 20
    if s.get("note"):
        text_block(d, M, H - 170, s["note"], font("regular", 28), C["sub"], W - 2 * M)
    return img


def render_timeline(s, i, n, brand):
    img, d = frame(i, n, brand)
    y = header(d, s) + 10
    x = M + 30
    steps = s["steps"]
    gap = 175
    d.line([(x, y + 20), (x, y + 20 + gap * (len(steps) - 1))], fill=C["card"], width=10)
    for k, (when, what) in enumerate(steps):
        cy = y + 20 + gap * k
        col = [C["mint"], C["accent"], C["coral"]][k % 3]
        d.ellipse([x - 26, cy - 26, x + 26, cy + 26], fill=col)
        d.text((x + 60, cy - 34), when, font=font("black", 46), fill=col)
        text_block(d, x + 60, cy + 26, what, font("medium", 38), C["text"], W - x - 60 - M)
    if s.get("note"):
        text_block(d, M, H - 170, s["note"], font("regular", 28), C["sub"], W - 2 * M)
    return img


def render_compare(s, i, n, brand):
    img, d = frame(i, n, brand)
    y = header(d, s) + 10
    bw = (W - 2 * M - 40) // 2
    for k, (lab, amt, col) in enumerate([(s["before"][0], s["before"][1], C["card"]),
                                          (s["after"][0], s["after"][1], C["mint"])]):
        x0 = M + k * (bw + 40)
        d.rounded_rectangle([x0, y, x0 + bw, y + 260], 30, fill=col)
        fg = C["text"] if k == 0 else (16, 20, 38)
        d.text((x0 + 36, y + 34), lab, font=font("bold", 36), fill=fg)
        d.text((x0 + 36, y + 110), amt, font=font("black", 84), fill=fg)
    # 화살표
    ax = M + bw + 20
    d.polygon([(ax - 26, y + 110), (ax + 26, y + 130), (ax - 26, y + 150)], fill=C["accent"])
    y += 300
    d.rounded_rectangle([M, y, W - M, y + 150], 30, fill=C["accent"])
    st = s["save"]
    f = font("black", 64)
    d.text(((W - d.textlength(st, font=f)) / 2, y + 30), st, font=f, fill=(16, 20, 38))
    y += 200
    text_block(d, M, y, s.get("highlight", ""), font("bold", 40), C["text"], W - 2 * M, 1.42)
    if s.get("note"):
        text_block(d, M, H - 170, s["note"], font("regular", 28), C["sub"], W - 2 * M)
    return img


def render_checklist(s, i, n, brand):
    img, d = frame(i, n, brand)
    y = header(d, s)
    fb = font("medium", 40)
    for item in s["items"]:
        lines = wrap(d, item, fb, W - 2 * M - 120)
        h = int(len(lines) * 40 * 1.42) + 36
        d.rounded_rectangle([M, y, W - M, y + h], 24, fill=C["card"])
        bx, by = M + 28, y + h // 2 - 24
        d.rounded_rectangle([bx, by, bx + 48, by + 48], 12, fill=C["mint"])
        d.line([(bx + 11, by + 25), (bx + 21, by + 35), (bx + 38, by + 14)], fill=(16, 20, 38), width=7)
        yy = y + 16
        for ln in lines:
            d.text((M + 100, yy), ln, font=fb, fill=C["text"])
            yy += int(40 * 1.42)
        y += h + 18
    if s.get("cta"):
        y += 12
        d.rounded_rectangle([M, y, W - M, y + 110], 55, fill=C["accent"])
        f = font("black", 44)
        d.text(((W - d.textlength(s["cta"], font=f)) / 2, y + 22), s["cta"], font=f, fill=(16, 20, 38))
        if y + 110 > H - 100:
            raise SystemExit(f"{i}번 카드: 내용이 넘칩니다")
    return img


# ---------- v3: 벤치마킹 스타일 (큰 비주얼 + 짧은 글, 한 장에 한 포인트) ----------

def phone_back(img, cx, cy, h, color, tilt=0):
    """원본 일러스트: 특정 제품이 아닌 일반적인 스마트폰 뒷면."""
    w = int(h * 0.48)
    layer = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r = int(w * 0.16)
    shade = tuple(max(0, c - 40) for c in color)
    d.rounded_rectangle([20, 20, 20 + w, 20 + h], r, fill=shade)
    d.rounded_rectangle([26, 26, 14 + w, 14 + h], r - 6, fill=color)
    hi = tuple(min(255, c + 35) for c in color)
    d.rounded_rectangle([26, 26, 26 + w * 0.18, 14 + h], r - 6, fill=hi)  # 측면 하이라이트
    # 카메라 섬
    cs = int(w * 0.20)
    for k, (ox, oy) in enumerate([(0.12, 0.05), (0.12, 0.05 + 0.13), (0.12, 0.05 + 0.26)]):
        x0, y0 = 20 + int(w * ox), 20 + int(h * oy)
        d.ellipse([x0, y0, x0 + cs, y0 + cs], fill=(18, 18, 22))
        d.ellipse([x0 + cs * 0.22, y0 + cs * 0.22, x0 + cs * 0.78, y0 + cs * 0.78], fill=(40, 46, 70))
        d.ellipse([x0 + cs * 0.38, y0 + cs * 0.34, x0 + cs * 0.5, y0 + cs * 0.46], fill=(150, 170, 220))
    if tilt:
        layer = layer.rotate(tilt, resample=Image.BICUBIC, expand=True)
    img.paste(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)), layer)


def stage(img, top=0, bottom=760, glow_col=None):
    """비주얼 영역 배경: 어두운 무대 + 빛 번짐."""
    glow(img, W // 2, (top + bottom) // 2 + 60, 420, glow_col or C["sky"], 110)
    glow(img, W // 2, bottom - 40, 300, (180, 120, 255), 70)


BASE_DIR = "."


def photo(img, v):
    """사용자가 준 사진을 위쪽에 가로 띠로 배치하고 아래를 배경에 녹인다. overlay 가 있으면 큰 글자를 얹는다."""
    src = Image.open(os.path.join(BASE_DIR, v["src"])).convert("RGB")
    if v.get("card"):  # 작은 상품 사진: 늘려서 흐려지지 않게 흰 카드 위에 적당한 크기로 둔다
        side = v.get("size", 600)
        sc = min(side / src.width, side / src.height)
        p = src.resize((int(src.width * sc), int(src.height * sc)), Image.LANCZOS)
        pad = 34
        cw, ch = p.width + pad * 2, p.height + pad * 2
        x0, y0 = (W - cw) // 2, v.get("top", 150)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], 36, fill=(255, 255, 255))
        img.paste(p, (x0 + pad, y0 + pad))
        return
    top = v.get("top", 120)
    maxh = v.get("max_h", 700)
    w = W
    h = int(src.height * w / src.width)
    if h > maxh:  # 너무 세로로 길면 가운데를 잘라낸다
        src = src.crop((0, (src.height - int(maxh * src.width / w)) // 2, src.width,
                        (src.height + int(maxh * src.width / w)) // 2))
        h = maxh
    p = src.resize((w, h), Image.LANCZOS)
    if v.get("overlay"):
        p = Image.blend(p, Image.new("RGB", p.size, (6, 8, 20)), 0.45)
    mask = Image.new("L", (w, h), 255)
    md = ImageDraw.Draw(mask)
    fade = min(260, h // 2)
    for yy in range(h - fade, h):
        md.line([(0, yy), (w, yy)], fill=int(255 * (h - yy) / fade))
    for yy in range(0, 40):
        md.line([(0, yy), (w, yy)], fill=int(255 * yy / 40))
    img.paste(p, (0, top), mask)
    o = v.get("overlay")
    if o:
        d = ImageDraw.Draw(img)
        f = font("black", o.get("size", 190))
        t = o["text"]; tw = d.textlength(t, font=f)
        if tw > W - 120:
            f = font("black", int(f.size * (W - 120) / tw)); tw = d.textlength(t, font=f)
        cy = top + h // 2 - 40
        col = tuple(o.get("color", C["accent"]))
        for dx, dy in ((4, 4), (3, 3)):
            d.text(((W - tw) / 2 + dx, cy - f.size * 0.62 + dy), t, font=f, fill=(0, 0, 0))
        d.text(((W - tw) / 2, cy - f.size * 0.62), t, font=f, fill=col)
        if o.get("sub"):
            fs = font("bold", 46)
            sw = d.textlength(o["sub"], font=fs); sy = cy + f.size * 0.62
            d.rounded_rectangle([(W - sw) / 2 - 22, sy - 8, (W + sw) / 2 + 22, sy + 66], 20, fill=(6, 8, 20))
            d.text(((W - sw) / 2, sy), o["sub"], font=fs, fill=C["text"])


def credit(img, v):
    """사진 출처를 사진 오른쪽 아래에 작게 표시한다 (visual.credit)."""
    t = v.get("credit")
    if not t:
        return
    d = ImageDraw.Draw(img)
    f = font("regular", 24)
    tw = d.textlength(t, font=f)
    y = v.get("credit_y", 780)
    d.text((W - 48 - tw + 2, y + 2), t, font=f, fill=(0, 0, 0))
    d.text((W - 48 - tw, y), t, font=f, fill=(225, 230, 240))


def visual(img, v):
    """v: {"kind": "phones"|"phone"|"big"|"badges"|"sms"|"photo", ...}"""
    k = v.get("kind", "big")
    if k == "photo":
        photo(img, v)
        return credit(img, v)
    if k == "tag":  # 상품 이름표: 사진 없이 상품을 보여줄 때
        stage(img, glow_col=C["accent"])
        d = ImageDraw.Draw(img)
        x0, y0, x1, y1 = 150, 170, W - 150, 640
        d.rounded_rectangle([x0, y0, x1, y1], 44, fill=(255, 251, 245))
        d.ellipse([x0 + 40, y0 + 40, x0 + 76, y0 + 76], outline=C["accent"], width=8)
        d.text((x0 + 96, y0 + 34), v.get("kicker", "오늘의 꿀템"), font=font("bold", 34), fill=C["accent"])
        yy = text_block(d, x0 + 48, y0 + 120, v["name"], font("black", 64), (30, 24, 20), x1 - x0 - 96, 1.2) + 20
        if v.get("point"):
            text_block(d, x0 + 48, yy, v["point"], font("medium", 38), (110, 98, 88), x1 - x0 - 96, 1.4)
        return
    d = ImageDraw.Draw(img)
    d = ImageDraw.Draw(img)
    if k == "phones":
        cols = [tuple(c) for c in v.get("colors", [[40, 42, 48], [235, 190, 180], [90, 130, 220], [190, 170, 230], [235, 236, 240]])]
        n = len(cols)
        stage(img)
        mid = (n - 1) / 2
        order = sorted(range(n), key=lambda i: -abs(i - mid))
        for i in order:
            off = i - mid
            h = 560 - int(abs(off) * 50)
            phone_back(img, W // 2 + off * 175, 400 + abs(off) * 25, h, cols[i], tilt=-off * 4)
    elif k == "phone":
        stage(img, glow_col=tuple(v.get("glow", C["sky"])))
        phone_back(img, W // 2, 400, 620, tuple(v.get("color", [60, 70, 100])), tilt=v.get("tilt", -8))
    elif k == "sms":
        stage(img)
        draw_phone(img, W // 2, 90, v)
    elif k == "badges":
        stage(img)
        d = ImageDraw.Draw(img)
        badges_row(d, 0, 320, v["items"], size=v.get("size", 76), center=True)
        if v.get("caption"):
            f = font("bold", 40)
            t = v["caption"]
            d.text(((W - d.textlength(t, font=f)) / 2, 480), t, font=f, fill=C["sub"])
    elif k == "big":
        stage(img, glow_col=tuple(v.get("glow", C["accent"])))
        d = ImageDraw.Draw(img)
        f = font("black", v.get("size", 210))
        t = v["text"]
        tw = d.textlength(t, font=f)
        if tw > W - 120:
            f = font("black", int(f.size * (W - 120) / tw)); tw = d.textlength(t, font=f)
        d.text(((W - tw) / 2, 380 - f.size * 0.62), t, font=f, fill=tuple(v.get("color", C["accent"])))
        if v.get("sub"):
            fs = font("bold", 46)
            d.text(((W - d.textlength(v["sub"], font=fs)) / 2, 420 + f.size * 0.45), v["sub"], font=fs, fill=C["text"])


def bottom_shade(img, y0=700):
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    for yy in range(y0, H):
        a = min(245, int((yy - y0) / 220 * 245))
        sd.line([(0, yy), (W, yy)], fill=(6, 8, 18, a))
    img.paste(shade, (0, 0), shade)


def dark_frame():
    img = Image.new("RGB", (W, H))
    gradient(img, C.get("frame1", (6, 8, 20)), C.get("frame2", (14, 18, 42)))
    return img


def store_tag(d, x, y, brand_tag):
    """참고 게시물의 '지역 + 매장명' 작은 태그."""
    a, b = brand_tag
    nx = pill(d, x, y, a, font("black", 30), C["text"], (10, 12, 24), padx=12, h=46)
    d.text((nx + 12, y + 5), b, font=font("bold", 30), fill=C["text"])


def render_hero(s, i, n, brand, cfg):
    img = dark_frame()
    visual(img, s["visual"])
    bottom_shade(img, 640)
    d = ImageDraw.Draw(img)
    y = 900
    store_tag(d, M, y, cfg.get("store_tag", ["방학", "폰 성지"]))
    text_block(d, M, y + 80, s["title"], font("black", 92), C["text"], W - 2 * M, 1.2)
    footer(d, i, n, brand)
    return img


def render_point(s, i, n, brand, cfg):
    img = dark_frame()
    visual(img, s["visual"])
    bottom_shade(img, 700)
    d = ImageDraw.Draw(img)
    y = 860
    if s.get("label"):
        pill(d, M, y, s["label"], font("black", 30), C["accent"], (16, 20, 38), padx=18)
        y += 76
    d.text((M, y), s["title"], font=font("black", 72), fill=C["text"])
    y += 108
    y = text_block(d, M, y, s.get("desc", ""), font("bold", 38), (222, 228, 242), W - 2 * M, 1.45)
    if s.get("note"):
        text_block(d, M, max(y + 24, H - 150), s["note"], font("regular", 24), C["sub"], W - 2 * M, 1.4)
    footer(d, i, n, brand)
    return img


def _cta(d, s, cfg):
    """참여 유도 띠 (좋아요·댓글·저장·유튜브 구독)."""
    cta = s.get("cta", cfg.get("cta", "좋아요 · 댓글 · 저장 / 유튜브 구독도 부탁드려요"))
    if not cta:
        return
    f = font("bold", 36)
    tw = d.textlength(cta, font=f)
    if tw > W - 120:
        f = font("bold", int(36 * (W - 120) / tw)); tw = d.textlength(cta, font=f)
    d.rounded_rectangle([(W - tw) / 2 - 30, 1125, (W + tw) / 2 + 30, 1195], 35, fill=C["accent"])
    d.text(((W - tw) / 2, 1138), cta, font=f, fill=(16, 18, 30))


def render_follow(s, i, n, brand, cfg):
    """마지막 장: 우리 계정 팔로우 유도 (프로필 카드 그림은 직접 그린 것)."""
    img = dark_frame()
    stage(img, 300, 1000)
    d = ImageDraw.Draw(img)
    for k, line in enumerate(s.get("head", ["더 많은 휴대폰 꿀팁이 궁금하다면", f"{brand} 팔로우하세요!"])):
        f = font("black" if k else "bold", 58 if k else 44)
        d.text(((W - d.textlength(line, font=f)) / 2, 150 + k * 80), line, font=f, fill=C["accent"] if k else C["text"])
    # 실제 프로필 화면 이미지가 있으면 그림 대신 사용 (매장 계정 기본값: assets/store_profile.png)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fimg = cfg.get("follow_image") or {"@bpj0901": "assets/store_profile.png", "@jangbaguni0916": "assets/picks_profile.png"}.get(brand, "")
    if fimg and os.path.exists(os.path.join(root, fimg)):
        src = Image.open(os.path.join(root, fimg)).convert("RGB")
        bw_ = W - 140
        p = src.resize((bw_, int(src.height * bw_ / src.width)), Image.LANCZOS)
        pad = 26
        cx0, cy0 = 70 - pad, 300 + (800 - p.height) // 2 - pad
        d.rounded_rectangle([cx0, cy0, cx0 + p.width + pad * 2, cy0 + p.height + pad * 2], 36, fill=(255, 255, 255))
        m = Image.new("L", p.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, p.width, p.height], 18, fill=255)
        img.paste(p, (cx0 + pad, cy0 + pad), m)
        ay = cy0 + p.height + pad * 2 + 20
        d.polygon([(W // 2, ay), (W // 2 - 26, ay + 40), (W // 2 + 26, ay + 40)], fill=C["accent"])
        _cta(d, s, cfg)
        footer(d, i, n, brand)
        return img
    # 프로필 카드
    x0, y0, x1, y1 = 150, 380, W - 150, 1080
    d.rounded_rectangle([x0, y0, x1, y1], 40, fill=(250, 251, 254))
    d.text((x0 + 50, y0 + 40), brand.lstrip("@"), font=font("black", 40), fill=(20, 24, 40))
    d.ellipse([x0 + 50, y0 + 120, x0 + 210, y0 + 280], fill=C["accent"])
    f = font("black", 46); t = cfg.get("avatar_text", "폰")
    d.text((x0 + 130 - d.textlength(t, font=f) / 2, y0 + 168), t, font=f, fill=(20, 24, 40))
    name = cfg.get("store_name", "방학 폰 성지")
    d.text((x0 + 250, y0 + 150), name, font=font("black", 44), fill=(20, 24, 40))
    d.text((x0 + 250, y0 + 214), cfg.get("store_sub", "휴대폰 꿀팁 · 구매 상담"), font=font("medium", 30), fill=(90, 98, 120))
    yy = y0 + 330
    for line in cfg.get("profile_lines", []):
        d.text((x0 + 50, yy), line, font=font("medium", 32), fill=(40, 48, 70)); yy += 54
    by = y1 - 140
    bw = (x1 - x0 - 140) // 2
    d.rounded_rectangle([x0 + 50, by, x0 + 50 + bw, by + 86], 22, fill=(70, 110, 250))
    f = font("black", 36)
    d.text((x0 + 50 + (bw - d.textlength("팔로우", font=f)) / 2, by + 20), "팔로우", font=f, fill=(255, 255, 255))
    d.rounded_rectangle([x0 + 90 + bw, by, x1 - 50, by + 86], 22, fill=(232, 236, 244))
    d.text((x0 + 90 + bw + (bw - d.textlength("메시지", font=f)) / 2, by + 20), "메시지", font=f, fill=(20, 24, 40))
    # 손가락 대신 강조 화살표
    d.polygon([(x0 + 50 + bw // 2, by + 110), (x0 + 30 + bw // 2, by + 150), (x0 + 70 + bw // 2, by + 150)], fill=C["accent"])
    _cta(d, s, cfg)
    footer(d, i, n, brand)
    return img


# ---------- 사장님 마무리 장 (방학 폰 성지 카드뉴스·쇼츠 공통, 2026-10-28 추가) ----------
OWNER_IMG = "assets/owner_end.jpg"  # 인물 얼굴은 절대 바꾸지 않는다: 이 사진 픽셀을 그대로 쓰고 주변 배경만 바꾼다
OWNER_THEMES = [  # (위 색, 아래 색, 빛 번짐 색) — 게시물마다 하나씩 돌아가며 쓴다
    ((8, 10, 28), (22, 28, 70), (96, 170, 255)),
    ((10, 8, 24), (48, 18, 60), (255, 112, 160)),
    ((6, 16, 22), (12, 52, 60), (80, 226, 186)),
    ((14, 12, 8), (60, 44, 12), (255, 212, 56)),
    ((10, 10, 14), (34, 34, 44), (180, 120, 255)),
    ((18, 8, 8), (64, 18, 22), (255, 112, 102)),
]


def owner_theme(seed):
    import hashlib
    return OWNER_THEMES[int(hashlib.md5(str(seed).encode()).hexdigest(), 16) % len(OWNER_THEMES)]


def owner_photo(width, radius=0):
    src = Image.open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), OWNER_IMG)).convert("RGB")
    p = src.resize((width, int(src.height * width / src.width)), Image.LANCZOS)
    if radius:
        m = Image.new("L", p.size, 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, p.width - 1, p.height - 1], radius, fill=255)
        return p, m
    return p, None


def ai_pill(d, x, y):
    pill(d, x, y, "AI 생성 이미지", font("bold", 24), (255, 255, 255), (16, 18, 30), padx=14)


def render_owner(s, i, n, brand, cfg):
    top, bottom, gl = owner_theme(cfg.get("post_at") or cfg.get("slides", [{}])[0].get("title", ""))
    img = Image.new("RGB", (W, H))
    gradient(img, top, bottom, 0, H)
    glow(img, W // 2, 560, 520, gl, 120)
    p, m = owner_photo(980, 34)
    x0, y0 = (W - p.width) // 2, 50
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x0 - 6, y0 - 6, x0 + p.width + 5, y0 + p.height + 5], 40, fill=gl)
    img.paste(p, (x0, y0), m)
    d = ImageDraw.Draw(img)
    ai_pill(d, x0 + 20, y0 + p.height - 64)
    y = y0 + p.height + 46
    f = font("black", 70)
    a, b = "DM·카톡 ", "편하게 문의 주세요"
    tw = d.textlength(a + b, font=f)
    x = (W - tw) / 2
    d.text((x, y), a, font=f, fill=(255, 232, 0), stroke_width=4, stroke_fill=(0, 0, 0))
    d.text((x + d.textlength(a, font=f), y), b, font=f, fill=(70, 232, 100), stroke_width=4, stroke_fill=(0, 0, 0))
    footer(d, i, n, brand)
    return img


def owner_enabled_card(cfg):
    return cfg.get("brand") == "@bpj0901" and cfg.get("owner_end", True)


R = {"cover": render_cover, "list": render_list, "timeline": render_timeline,
     "compare": render_compare, "checklist": render_checklist}
R3 = {"hero": render_hero, "point": render_point, "follow": render_follow, "owner": render_owner}


def main(cfg_path, out):
    global BASE_DIR
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    for k, v in (cfg.get("theme") or {}).items():  # 계정별 색 테마 (예: 꿀템 계정)
        C[k] = tuple(v)
    BASE_DIR = os.path.dirname(os.path.abspath(cfg_path))
    os.makedirs(out, exist_ok=True)
    slides = cfg["slides"]
    if owner_enabled_card(cfg) and not any(x.get("type") == "owner" for x in slides):
        slides = slides + [{"type": "owner"}]  # 방학 폰 성지 카드뉴스: 마지막 장에 사장님 사진 자동 추가
    for f in os.listdir(out):
        if f.startswith("card_") and f.endswith(".jpg"):
            os.remove(os.path.join(out, f))
    for i, s in enumerate(slides, 1):
        t = s.get("type", "list")
        img = R3[t](s, i, len(slides), cfg["brand"], cfg) if t in R3 else R[t](s, i, len(slides), cfg["brand"])
        if cfg.get("ad_label"):  # 대가성 표시: 모든 장 왼쪽 위
            pill(ImageDraw.Draw(img), 50, 44, cfg["ad_label"], font("black", 28), (255, 255, 255), (16, 18, 30), padx=18)
        p = os.path.join(out, f"card_{i:02d}.jpg")
        img.save(p, "JPEG", quality=92)
        print(p)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
