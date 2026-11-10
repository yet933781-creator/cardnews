"""직접 그린 오리지널 마스코트 캐릭터 (2026-11-10 추가, 외부 그림·IP 사용 없음).

카드뉴스(chat 장)와 쇼츠(상황극 대사)에 쓰인다. 모두 Pillow 도형으로만 그린다.

  kind : phone(폰이) / basket(장구) / coin(동전이) / box(택배) / sim(유심이) / sponge(뽀득이)
  mood : normal / talk / wow / happy / angry / sad
사용: draw("phone", 300, "talk") -> RGBA 이미지 (size x size)
"""
from PIL import Image, ImageDraw, ImageEnhance

SS = 3  # 계단 현상 없애기 위한 확대 배율

KINDS = {
    "phone":  {"name": "폰이",   "body": (96, 170, 255),  "dark": (40, 88, 170)},
    "basket": {"name": "장구",   "body": (255, 138, 76),  "dark": (176, 78, 30)},
    "coin":   {"name": "동전이", "body": (255, 212, 56),  "dark": (186, 140, 10)},
    "box":    {"name": "택배",   "body": (214, 164, 108), "dark": (140, 98, 52)},
    "sim":    {"name": "유심이", "body": (80, 226, 186),  "dark": (24, 132, 104)},
    "sponge": {"name": "뽀득이", "body": (255, 226, 110), "dark": (60, 170, 120)},
}
INK = (24, 26, 40)
WHITE = (255, 255, 255)


def guess_mood(text):
    """대사 문장으로 표정을 고른다 (script 에 face 를 안 썼을 때)."""
    t = text or ""
    if any(k in t for k in ("헐", "?!", "!?", "진짜?", "네?", "뭐?", "에이", "설마")):
        return "wow"
    if any(k in t for k in ("ㅠ", "아이고", "어휴", "하...", "망했", "큰일")):
        return "sad"
    if any(k in t for k in ("안 돼", "하지 마", "또?", "몇 번", "그만")):
        return "angry"
    if any(k in t for k in ("좋아", "대박", "오~", "오!", "굿", "감사", "됐다", "부탁")):
        return "happy"
    return "talk"


def _face(d, cx, cy, u, mood):
    """u: 얼굴 단위 길이. 눈·볼·입을 그린다."""
    ex = int(u * 0.55); er = int(u * 0.2)
    ey = cy - int(u * 0.15)
    lw = max(3, int(u * 0.09))
    for sx in (-1, 1):
        x = cx + sx * ex
        if mood == "happy":  # 웃는 눈 (∩)
            d.arc([x - er * 1.2, ey - er, x + er * 1.2, ey + er * 1.4], 200, 340, fill=INK, width=lw)
        elif mood == "wow":
            d.ellipse([x - er * 1.25, ey - er * 1.25, x + er * 1.25, ey + er * 1.25], fill=WHITE, outline=INK, width=lw)
            d.ellipse([x - er * 0.5, ey - er * 0.5, x + er * 0.5, ey + er * 0.5], fill=INK)
        else:
            d.ellipse([x - er, ey - er * 1.15, x + er, ey + er * 1.15], fill=INK)
            d.ellipse([x - er * 0.15, ey - er * 0.8, x + er * 0.45, ey - er * 0.2], fill=WHITE)
        if mood == "sad":  # 처진 눈썹
            d.line([x - sx * er * 1.5, ey - er * 2.3, x + sx * er * 0.9, ey - er * 1.3], fill=INK, width=lw)
        if mood == "angry":  # 화난 눈썹
            d.line([x - sx * er * 1.5, ey - er * 1.4, x + sx * er * 0.9, ey - er * 2.2], fill=INK, width=lw)
    for sx in (-1, 1):  # 볼터치
        x = cx + sx * int(u * 0.95)
        d.ellipse([x - er * 0.9, cy + er * 0.6, x + er * 0.9, cy + er * 1.5], fill=(255, 150, 150))
    my = cy + int(u * 0.5); mw = int(u * 0.34)
    if mood == "talk":
        d.ellipse([cx - mw * 0.8, my - mw * 0.55, cx + mw * 0.8, my + mw * 0.85], fill=(150, 40, 50), outline=INK, width=lw)
    elif mood == "wow":
        d.ellipse([cx - mw * 0.55, my - mw * 0.5, cx + mw * 0.55, my + mw * 1.0], fill=(150, 40, 50), outline=INK, width=lw)
    elif mood == "happy":
        d.chord([cx - mw * 1.2, my - mw * 1.1, cx + mw * 1.2, my + mw * 1.1], 0, 180, fill=(150, 40, 50), outline=INK, width=lw)
    elif mood in ("angry", "sad"):
        d.arc([cx - mw, my, cx + mw, my + mw * 1.3], 200, 340, fill=INK, width=lw)
    else:
        d.arc([cx - mw, my - mw * 0.9, cx + mw, my + mw * 0.5], 20, 160, fill=INK, width=lw)


def _limbs(d, s, body, dark, mood, top, bottom, left, right):
    lw = int(s * 0.035)
    ay = top + (bottom - top) * 0.55
    up = mood in ("wow", "happy")
    for sx, x in ((-1, left), (1, right)):
        hx = x + sx * s * 0.11
        hy = ay - s * 0.16 if up else ay + s * 0.1
        d.line([x, ay, hx, hy], fill=dark, width=lw)
        d.ellipse([hx - s * 0.04, hy - s * 0.04, hx + s * 0.04, hy + s * 0.04], fill=body, outline=INK, width=max(2, lw // 2))
    for sx in (-1, 1):
        x = (left + right) / 2 + sx * (right - left) * 0.22
        d.line([x, bottom - 2, x, s * 0.93], fill=dark, width=lw)
        d.ellipse([x - s * 0.07, s * 0.9, x + s * 0.07, s * 0.97], fill=dark, outline=INK, width=max(2, lw // 2))


def draw(kind="phone", size=300, mood="normal", dim=False, flip=False):
    k = KINDS.get(kind, KINDS["phone"])
    body, dark = k["body"], k["dark"]
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ow = int(s * 0.022)
    cx = s // 2
    # 바닥 그림자
    d.ellipse([s * 0.22, s * 0.93, s * 0.78, s * 0.995], fill=(0, 0, 0, 90))
    if kind == "phone":
        l, t, r, b = s * 0.26, s * 0.08, s * 0.74, s * 0.84
        _limbs(d, s, body, dark, mood, t, b, l, r)
        d.rounded_rectangle([l, t, r, b], int(s * 0.09), fill=body, outline=INK, width=ow)
        d.rounded_rectangle([l + s * 0.045, t + s * 0.07, r - s * 0.045, b - s * 0.09], int(s * 0.05), fill=(236, 246, 255), outline=INK, width=ow // 2)
        d.rounded_rectangle([cx - s * 0.05, t + s * 0.03, cx + s * 0.05, t + s * 0.048], int(s * 0.01), fill=INK)
        _face(d, cx, int(s * 0.44), int(s * 0.13), mood)
    elif kind == "coin":
        l, t, r, b = s * 0.17, s * 0.14, s * 0.83, s * 0.80
        _limbs(d, s, body, dark, mood, t, b, l, r)
        d.ellipse([l, t, r, b], fill=dark, outline=INK, width=ow)
        d.ellipse([l + s * 0.03, t + s * 0.02, r - s * 0.03, b - s * 0.045], fill=body, outline=INK, width=ow // 2)
        d.arc([l + s * 0.09, t + s * 0.08, r - s * 0.09, b - s * 0.1], 190, 260, fill=WHITE, width=ow)
        _face(d, cx, int(s * 0.47), int(s * 0.14), mood)
    elif kind == "box":
        l, t, r, b = s * 0.18, s * 0.26, s * 0.82, s * 0.84
        _limbs(d, s, body, dark, mood, t, b, l, r)
        d.polygon([(l - s * 0.05, t), (cx - s * 0.02, t), (cx - s * 0.08, t - s * 0.14), (l + s * 0.02, t - s * 0.1)], fill=dark, outline=INK)
        d.polygon([(r + s * 0.05, t), (cx + s * 0.02, t), (cx + s * 0.08, t - s * 0.14), (r - s * 0.02, t - s * 0.1)], fill=dark, outline=INK)
        d.rounded_rectangle([l, t, r, b], int(s * 0.03), fill=body, outline=INK, width=ow)
        d.rectangle([cx - s * 0.05, t + ow, cx + s * 0.05, t + s * 0.12], fill=(240, 222, 180))
        _face(d, cx, int(s * 0.58), int(s * 0.14), mood)
    elif kind == "sim":
        l, t, r, b = s * 0.22, s * 0.14, s * 0.78, s * 0.84
        _limbs(d, s, body, dark, mood, t, b, l, r)
        c = s * 0.13
        d.polygon([(l, t + s * 0.04), (l + s * 0.04, t), (r - c, t), (r, t + c), (r, b - s * 0.04), (r - s * 0.04, b), (l + s * 0.04, b), (l, b - s * 0.04)],
                  fill=body, outline=INK)
        d.line([(l, t + s * 0.04), (l + s * 0.04, t), (r - c, t), (r, t + c), (r, b - s * 0.04), (r - s * 0.04, b), (l + s * 0.04, b), (l, b - s * 0.04), (l, t + s * 0.04)],
               fill=INK, width=ow, joint="curve")
        d.rounded_rectangle([cx - s * 0.12, b - s * 0.24, cx + s * 0.12, b - s * 0.07], int(s * 0.025), fill=(255, 212, 56), outline=INK, width=ow // 2)
        d.line([cx, b - s * 0.24, cx, b - s * 0.07], fill=INK, width=ow // 3)
        d.line([cx - s * 0.12, b - s * 0.155, cx + s * 0.12, b - s * 0.155], fill=INK, width=ow // 3)
        _face(d, cx, int(s * 0.4), int(s * 0.12), mood)
    elif kind == "sponge":
        l, t, r, b = s * 0.2, s * 0.2, s * 0.8, s * 0.84
        _limbs(d, s, body, dark, mood, t, b, l, r)
        d.rounded_rectangle([l, t, r, b], int(s * 0.07), fill=body, outline=INK, width=ow)
        d.rounded_rectangle([l, t, r, t + s * 0.14], int(s * 0.07), fill=dark, outline=INK, width=ow)
        for bx, by, br in ((0.3, 0.7, 0.025), (0.68, 0.36, 0.02), (0.72, 0.72, 0.03), (0.28, 0.42, 0.018)):
            d.ellipse([s * (bx - br), s * (by - br), s * (bx + br), s * (by + br)], fill=(240, 196, 70))
        for bx, by, br in ((0.86, 0.2, 0.05), (0.12, 0.3, 0.035)):  # 비누 거품
            d.ellipse([s * (bx - br), s * (by - br), s * (bx + br), s * (by + br)], fill=(235, 248, 255, 230), outline=INK, width=ow // 3)
        _face(d, cx, int(s * 0.56), int(s * 0.14), mood)
    else:  # basket
        l, t, r, b = s * 0.16, s * 0.36, s * 0.84, s * 0.84
        _limbs(d, s, body, dark, mood, t, b, l + s * 0.04, r - s * 0.04)
        d.arc([s * 0.28, s * 0.08, s * 0.72, s * 0.62], 180, 360, fill=INK, width=int(ow * 2.4))
        d.arc([s * 0.28, s * 0.08, s * 0.72, s * 0.62], 180, 360, fill=dark, width=int(ow * 1.2))
        d.polygon([(l, t), (r, t), (r - s * 0.07, b), (l + s * 0.07, b)], fill=body)
        d.line([(l, t), (r, t), (r - s * 0.07, b), (l + s * 0.07, b), (l, t)], fill=INK, width=ow, joint="curve")
        d.rounded_rectangle([l - s * 0.03, t - s * 0.035, r + s * 0.03, t + s * 0.05], int(s * 0.03), fill=dark, outline=INK, width=ow)
        for fx in (0.3, 0.7):
            d.line([s * fx, t + s * 0.07, s * (fx + (0.02 if fx < 0.5 else -0.02)), b - s * 0.03], fill=dark, width=ow // 2)
        _face(d, cx, int(s * 0.61), int(s * 0.13), mood)
    img = img.resize((size, size), Image.LANCZOS)
    if flip:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if dim:  # 듣는 쪽: 살짝 어둡게
        a = img.getchannel("A")
        img = ImageEnhance.Brightness(img.convert("RGB")).enhance(0.62).convert("RGBA")
        img.putalpha(a)
    return img


def name(kind):
    return KINDS.get(kind, KINDS["phone"])["name"]


if __name__ == "__main__":  # 미리보기: python3 tools/characters.py out.png
    import sys
    moods = ["normal", "talk", "wow", "happy", "angry", "sad"]
    sheet = Image.new("RGB", (len(moods) * 260 + 20, len(KINDS) * 260 + 20), (20, 24, 48))
    for r_, kd in enumerate(KINDS):
        for c_, m in enumerate(moods):
            im = draw(kd, 240, m)
            sheet.paste(im, (20 + c_ * 260, 20 + r_ * 260), im)
    sheet.save(sys.argv[1] if len(sys.argv) > 1 else "characters.png")
