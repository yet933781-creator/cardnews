"""카드뉴스 렌더러: content.json -> 1080x1350 JPG 여러 장.
사용법: python render.py content.json out_dir
"""
import json, sys, os
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
M = 90  # 좌우 여백
FD = "/usr/share/fonts/opentype/noto/"

C = {
    "bg": (14, 22, 48), "bg2": (24, 36, 74), "text": (245, 247, 252),
    "sub": (170, 182, 214), "accent": (255, 214, 64), "accent2": (92, 225, 190),
    "card": (30, 44, 88), "warn": (255, 120, 110),
}


def font(weight, size):
    files = {"black": "NotoSansCJK-Black.ttc", "bold": "NotoSansCJK-Bold.ttc",
             "medium": "NotoSansCJK-Medium.ttc", "regular": "NotoSansCJK-Regular.ttc"}
    path = FD + files[weight]
    for i in range(6):
        f = ImageFont.truetype(path, size, index=i)
        if "KR" in f.getname()[0]:
            return f
    return ImageFont.truetype(path, size)


def wrap(draw, text, f, maxw):
    lines = []
    for para in text.split("\n"):
        line = ""
        for word in para.split(" "):
            test = (line + " " + word).strip()
            if draw.textlength(test, font=f) <= maxw:
                line = test
            else:
                if line:
                    lines.append(line)
                # 단어 하나가 너무 길면 글자 단위로 자름
                while draw.textlength(word, font=f) > maxw:
                    cut = len(word)
                    while draw.textlength(word[:cut], font=f) > maxw:
                        cut -= 1
                    lines.append(word[:cut]); word = word[cut:]
                line = word
        lines.append(line)
    return lines


def text_block(draw, xy, text, f, fill, maxw, gap=1.35):
    x, y = xy
    for ln in wrap(draw, text, f, maxw):
        draw.text((x, y), ln, font=f, fill=fill)
        y += int(f.size * gap)
    return y


def base(i, n, brand):
    img = Image.new("RGB", (W, H), C["bg"])
    d = ImageDraw.Draw(img)
    # 은은한 세로 그라데이션
    for yy in range(H):
        t = yy / H
        col = tuple(int(C["bg"][k] * (1 - t) + C["bg2"][k] * t) for k in range(3))
        d.line([(0, yy), (W, yy)], fill=col)
    # 상단 바
    d.rectangle([0, 0, W, 14], fill=C["accent"])
    # 하단: 브랜드 + 페이지
    fb = font("bold", 30)
    d.text((M, H - 80), brand, font=fb, fill=C["sub"])
    pg = f"{i}/{n}"
    d.text((W - M - d.textlength(pg, font=fb), H - 80), pg, font=fb, fill=C["sub"])
    # 페이지 점
    for k in range(n):
        cx = W // 2 - (n - 1) * 14 + k * 28
        d.ellipse([cx - 6, H - 66, cx + 6, H - 54], fill=C["accent"] if k == i - 1 else C["card"])
    return img, d


def render_cover(s, i, n, brand):
    img, d = base(i, n, brand)
    y = 230
    tag = s.get("tag", "")
    if tag:
        ft = font("bold", 36)
        tw = d.textlength(tag, font=ft)
        d.rounded_rectangle([M, y, M + tw + 48, y + 66], 33, fill=C["accent"])
        d.text((M + 24, y + 9), tag, font=ft, fill=C["bg"])
        y += 120
    y = text_block(d, (M, y), s["title"], font("black", 92), C["text"], W - 2 * M, 1.25)
    y += 40
    d.rectangle([M, y, M + 120, y + 10], fill=C["accent"])
    y += 60
    text_block(d, (M, y), s.get("subtitle", ""), font("medium", 44), C["sub"], W - 2 * M, 1.45)
    if s.get("footer"):
        text_block(d, (M, H - 230), s["footer"], font("bold", 38), C["accent2"], W - 2 * M)
    return img


def render_body(s, i, n, brand):
    img, d = base(i, n, brand)
    y = 140
    fn = font("black", 40)
    d.text((M, y), s.get("label", f"POINT {i-1}"), font=fn, fill=C["accent"])
    y += 80
    y = text_block(d, (M, y), s["title"], font("black", 72), C["text"], W - 2 * M, 1.28)
    y += 50
    fbody = font("medium", 42)
    fbold = font("bold", 42)
    for item in s.get("items", []):
        # 카드 박스
        lines = wrap(d, item, fbody, W - 2 * M - 110)
        h = int(len(lines) * 42 * 1.45) + 36
        if y + h > H - 200:
            raise SystemExit(f'slide {i}: 항목이 공간을 넘침 -> 내용 줄이기')
        d.rounded_rectangle([M, y, W - M, y + h], 26, fill=C["card"])
        d.ellipse([M + 32, y + 30, M + 52, y + 50], fill=C["accent2"])
        yy = y + 16
        for ln in lines:
            d.text((M + 82, yy), ln, font=fbody, fill=C["text"])
            yy += int(42 * 1.45)
        y += h + 20
    if s.get("highlight"):
        y += 10
        text_block(d, (M, y), s["highlight"], fbold, C["accent"], W - 2 * M, 1.4)
    if s.get("note"):
        text_block(d, (M, H - 200), s["note"], font("regular", 28), C["sub"], W - 2 * M, 1.4)
    return img


def main(cfg_path, out):
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    os.makedirs(out, exist_ok=True)
    slides = cfg["slides"]; n = len(slides); paths = []
    for i, s in enumerate(slides, 1):
        img = render_cover(s, i, n, cfg["brand"]) if s.get("type") == "cover" else render_body(s, i, n, cfg["brand"])
        p = os.path.join(out, f"card_{i:02d}.jpg")
        img.save(p, "JPEG", quality=92)
        paths.append(p)
    print("\n".join(paths))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
