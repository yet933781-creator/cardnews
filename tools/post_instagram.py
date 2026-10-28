"""approved/ 폴더의 카드뉴스를 인스타그램 캐러셀로 게시한다.

- approved/<날짜>/ 안에 card_*.jpg 와 caption.txt 가 있어야 한다.
- 이미 posted.json 이 있는 폴더는 건너뛴다 (중복 게시 방지).
- 필요한 환경 변수(GitHub Secrets): IG_USER_ID, IG_ACCESS_TOKEN
"""
import glob, json, os, sys, time, urllib.parse, urllib.request


def fail(msg):
    # GitHub 요약(annotation)에 오류가 바로 보이도록 출력 (토큰 값은 포함되지 않음)
    print("::error::" + str(msg).replace("\n", " "))
    sys.exit(1)


USER_ID = os.environ.get("IG_USER_ID", "").strip()
TOKEN = os.environ.get("IG_ACCESS_TOKEN", "").strip()
REPO = os.environ["GITHUB_REPOSITORY"]          # 예: yet933781-creator/cardnews
SHA = os.environ.get("POST_SHA") or os.environ["GITHUB_SHA"]
# 인스타그램 로그인 방식 토큰(IGAA...)은 graph.instagram.com, 페이스북 방식은 graph.facebook.com
HOST = "https://graph.instagram.com" if TOKEN.startswith("IG") else "https://graph.facebook.com"
VER = os.environ.get("GRAPH_VERSION", "").strip()
BASE = f"{HOST}/{VER}" if VER else HOST


def api(method, path, **params):
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    url = f"{BASE}/{path}"
    if method == "GET":
        req = urllib.request.Request(url + "?" + data.decode())
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        fail(f"API 오류 {e.code} ({path}): {body}")


def wait_ready(cid):
    for _ in range(30):
        st = api("GET", cid, fields="status_code,status")
        if st.get("status_code") == "FINISHED":
            return
        if st.get("status_code") == "ERROR":
            fail(f"미디어 처리 실패: {st}")
        time.sleep(5)
    fail(f"미디어 처리 시간 초과: {cid}")


def public_url(path):
    # jsDelivr CDN: 커밋 고정 주소라 캐시 문제 없음, 이미지 형식도 정확히 전달
    return f"https://cdn.jsdelivr.net/gh/{REPO}@{SHA}/{path}"


CARDS_DIR = os.environ.get("CARDS_DIR", "approved")
FOOTER_FILE = os.environ.get("FOOTER_FILE", "shop_footer.txt")
DISCLOSURE_FILE = os.environ.get("DISCLOSURE_FILE", "")  # 쿠팡 파트너스 등 대가성 문구 (있으면 무조건 첫 줄)


def build_caption(body):
    """[대가성 문구] + 본문 + 꼬리말(매장 안내 등) + 해시태그 순으로 캡션 조립."""
    paras = body.strip().split("\n\n")
    tags = paras.pop() if paras and paras[-1].lstrip().startswith("#") else ""
    footer = open(FOOTER_FILE, encoding="utf-8").read().strip() if FOOTER_FILE and os.path.exists(FOOTER_FILE) else ""
    disclosure = ""
    if DISCLOSURE_FILE:
        if not os.path.exists(DISCLOSURE_FILE):
            fail(f"대가성 문구 파일이 없습니다: {DISCLOSURE_FILE}")
        disclosure = open(DISCLOSURE_FILE, encoding="utf-8").read().strip()
        body_text = "\n\n".join(paras)
        if disclosure in body_text:  # 중복 방지: 본문에 이미 있으면 빼고 맨 앞에 다시 둔다
            paras = [x for x in paras if x.strip() != disclosure]
    caption = "\n\n".join(p for p in [disclosure, "\n\n".join(paras), footer, tags] if p)
    if len(caption) > 2200:
        fail(f"캡션이 인스타 한도(2200자)를 넘습니다: {len(caption)}자")
    if caption.count("#") > 30:
        fail("해시태그가 30개를 넘습니다")
    return caption


def post(folder):
    imgs = sorted(glob.glob(os.path.join(folder, "card_*.jpg")))
    if not 2 <= len(imgs) <= 10:
        fail(f"{folder}: 캐러셀은 이미지 2~10장이 필요합니다 (현재 {len(imgs)}장)")
    caption = build_caption(open(os.path.join(folder, "caption.txt"), encoding="utf-8").read())

    children = []
    for p in imgs:
        r = api("POST", f"{USER_ID}/media", image_url=public_url(p), is_carousel_item="true")
        wait_ready(r["id"])
        children.append(r["id"])
        print("이미지 등록:", p)

    car = api("POST", f"{USER_ID}/media", media_type="CAROUSEL",
              children=",".join(children), caption=caption)
    wait_ready(car["id"])
    pub = api("POST", f"{USER_ID}/media_publish", creation_id=car["id"])
    info = api("GET", pub["id"], fields="permalink,timestamp")
    print("게시 완료:", info.get("permalink"))
    json.dump({"media_id": pub["id"], **info}, open(os.path.join(folder, "posted.json"), "w"),
              ensure_ascii=False, indent=2)


def is_due(folder):
    """content.json 의 post_at(예: 2026-10-29T09:00:00+09:00) 시각이 지났는지 확인. 없으면 바로 게시."""
    from datetime import datetime, timezone
    try:
        at = json.load(open(os.path.join(folder, "content.json"), encoding="utf-8")).get("post_at")
    except FileNotFoundError:
        return True
    if not at:
        return True
    due = datetime.fromisoformat(at) <= datetime.now(timezone.utc)
    if not due:
        print("예약 대기:", folder, at)
    return due


def main_setup():
    global USER_ID
    if not USER_ID or not TOKEN:
        fail("IG_USER_ID 또는 IG_ACCESS_TOKEN 비밀값이 비어 있습니다")
    me = api("GET", "me", fields="user_id,username" if "instagram" in HOST else "id,username")
    real_id = str(me.get("user_id") or me.get("id"))
    print("토큰 계정:", me.get("username"), "| ID 일치:", real_id == USER_ID)
    USER_ID = real_id  # 토큰에서 조회한 정확한 ID 사용


def main():
    main_setup()
    todo = [d for d in sorted(glob.glob(f"{CARDS_DIR}/*/"))
            if not os.path.exists(os.path.join(d, "posted.json")) and is_due(d)]
    if not todo:
        print("게시할 새 카드뉴스가 없습니다.")
        return
    for d in todo:
        post(d.rstrip("/"))


if __name__ == "__main__":
    main()
