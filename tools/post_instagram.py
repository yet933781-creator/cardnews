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
SHA = os.environ["GITHUB_SHA"]
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


def post(folder):
    imgs = sorted(glob.glob(os.path.join(folder, "card_*.jpg")))
    if not 2 <= len(imgs) <= 10:
        fail(f"{folder}: 캐러셀은 이미지 2~10장이 필요합니다 (현재 {len(imgs)}장)")
    caption = open(os.path.join(folder, "caption.txt"), encoding="utf-8").read().strip()

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


def main():
    global USER_ID
    if not USER_ID or not TOKEN:
        fail("IG_USER_ID 또는 IG_ACCESS_TOKEN 비밀값이 비어 있습니다")
    me = api("GET", "me", fields="user_id,username" if "instagram" in HOST else "id,username")
    real_id = str(me.get("user_id") or me.get("id"))
    print("토큰 계정:", me.get("username"), "| ID 일치:", real_id == USER_ID)
    USER_ID = real_id  # 토큰에서 조회한 정확한 ID 사용
    todo = [d for d in sorted(glob.glob("approved/*/"))
            if not os.path.exists(os.path.join(d, "posted.json"))]
    if not todo:
        print("게시할 새 카드뉴스가 없습니다.")
        return
    for d in todo:
        post(d.rstrip("/"))


if __name__ == "__main__":
    main()
