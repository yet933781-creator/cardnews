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


R = {"cover": render_cover, "list": render_list, "timeline": render_timeline,
     "compare": render_compare, "checklist": render_checklist}


def main(cfg_path, out):
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    os.makedirs(out, exist_ok=True)
    slides = cfg["slides"]
    for f in os.listdir(out):
        if f.startswith("card_") and f.endswith(".jpg"):
            os.remove(os.path.join(out, f))
    for i, s in enumerate(slides, 1):
        img = R[s.get("type", "list")](s, i, len(slides), cfg["brand"])
        p = os.path.join(out, f"card_{i:02d}.jpg")
        img.save(p, "JPEG", quality=92)
        print(p)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
