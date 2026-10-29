"""카드뉴스(content.json) → 꿀템 쇼츠식 영상 대본(V2 JSON) 자동 변환.

사용법: python3 video-v2/card2video.py <카드 폴더>/content.json <출력.json> [--hook <AI 상황 영상.mp4>]
- 카드에 있는 문장·사진만 쓴다(새 주장·숫자를 만들지 않음).
- 사진은 상품 원본(original_product_photo)으로 표시하고 잘리지 않게 보여준다.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CIRCLED = re.compile(r"[①-⑳]")


def clean(t):
    lines = [l.strip() for l in (t or "").split("\n") if l.strip()]
    if any(CIRCLED.match(l) for l in lines):  # ① ② ③ 목록은 쉼표로 이어 읽기
        t = ", ".join(CIRCLED.sub("", l).strip() for l in lines)
    else:
        t = " ".join(lines)
    return re.sub(r"\s+", " ", t).strip()


def convert(content_path, hook=None):
    c = json.load(open(content_path, encoding="utf-8"))
    folder = os.path.relpath(os.path.dirname(os.path.abspath(content_path)), ROOT)
    account = "household" if c.get("ad_label") else "phone"
    slides = [s for s in c["slides"] if s.get("type") in ("hero", "point")]
    hero = slides[0]
    photo = lambda s: (s.get("visual") or {}).get("src") if (s.get("visual") or {}).get("kind") == "photo" else None
    src_label = "카드뉴스 원본 상품 사진" if account == "household" else "카드뉴스 원본 사진"
    scenes = []
    hook_title = hero.get("title", "")
    first = {"narration": clean(hook_title), "headline": hook_title}
    if hook:
        first["visual"] = {"type": "generated_video", "src": hook, "camera": "static"}
    else:
        first["visual"] = {"type": "original_product_photo", "src": f"{folder}/{photo(hero)}", "camera": "slow_zoom_in", "source": src_label}
    scenes.append(first)
    hero_photo = photo(hero)
    for s in slides[1:]:
        v = s.get("visual") or {}
        if v.get("kind") == "big" and re.search(r"\d+\s*번", v.get("text", "")) and account == "household":
            no = re.search(r"\d+\s*번", v["text"]).group(0).replace(" ", "")
            scenes.append({"narration": f"프로필 링크에서 {no}을 찾으면 오늘 가격을 확인할 수 있어요. 이 영상은 쿠팡 파트너스 활동으로 수수료를 받을 수 있어요.",
                           "visual": {"type": "motion_graphics"},
                           "overlay": {"type": "cta", "number": no, "text": "오늘 가격은 링크에서 확인"}})
            continue
        p = photo(s)
        srcs = [f"{folder}/{p}"] if p else []
        if hero_photo and not srcs:
            srcs = [f"{folder}/{hero_photo}"]
        if not srcs:
            continue
        narr = clean(s.get("title", "")) + ". " + clean(s.get("desc", ""))
        scenes.append({"narration": narr.strip(". ").strip(),
                       "visual": {"type": "original_product_photo", "srcs": srcs, "source": src_label}})
    header = hook_title.strip()  # 카드 표지 제목 그대로(줄바꿈 유지)
    return {"account": account, "style": "honey", "title": f"카드뉴스 영상화: {clean(hook_title)}", "header": header,
            "from_card": content_path, "scenes": scenes}


if __name__ == "__main__":
    a = sys.argv[1:]
    hook = a[a.index("--hook") + 1] if "--hook" in a else None
    out = convert(a[0], hook)
    json.dump(out, open(a[1], "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:2500])
