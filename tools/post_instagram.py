"""approved/ 폴더의 카드뉴스를 인스타그램 캐러셀로 게시한다.

- approved/<날짜>/ 안에 card_*.jpg 와 caption.txt 가 있어야 한다.
- 이미 posted.json 이 있는 폴더는 건너뛴다 (중복 게시 방지).
- 중복 게시 방지 3중 장치 (2026-11-16, 꿀템 33번 카드가 15분마다 반복 게시된 사고 이후 추가):
  1) 게시 전에 계정의 최근 게시물을 조회해 같은 캡션이 이미 있으면 올리지 않고 기록만 남긴다.
  2) 게시(media_publish)를 누르기 직전에 attempt.json 을 남긴다. 그 뒤 결과를 확인하지 못하면
     그 폴더는 '게시 잠금' 상태가 되어 자동으로 다시 시도하지 않는다(사람이 확인 후 attempt.json 삭제).
  3) 게시 API 가 오류를 돌려줘도 실제로 올라갔는지 다시 조회해, 올라갔으면 게시 완료로 기록한다.
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
    url = f"https://cdn.jsdelivr.net/gh/{REPO}@{SHA}/{path}"
    # 저장소가 50MB 를 넘으면 jsDelivr 가 403 을 준다(2026-11-02 확인) → GitHub raw 주소로 대체
    try:
        import urllib.request
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=20) as r:
            if r.status == 200:
                return url
    except Exception:
        pass
    return f"https://raw.githubusercontent.com/{REPO}/{SHA}/{path}"


# ───────── 중복 게시 방지: 게시 잠금(attempt.json) + 실제 게시 여부 조회 ─────────
LOCK_FILE = "attempt.json"
MAX_PREP_TRIES = 3   # 게시 버튼 전 단계(이미지 등록 등)에서 실패해도 자동 재시도는 3번까지만


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


def lock_load(folder):
    try:
        return json.load(open(os.path.join(folder, LOCK_FILE), encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def _lock_save(folder, data):
    path = os.path.join(folder, LOCK_FILE)
    if data:
        json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    elif os.path.exists(path):
        os.remove(path)


def lock_blocked(folder, target="instagram"):
    """이 폴더·대상을 자동으로 다시 시도하면 안 되는 상태인지."""
    a = lock_load(folder).get(target)
    if not a:
        return False
    return a.get("stage") == "publish" or a.get("tries", 0) >= MAX_PREP_TRIES


def lock_mark(folder, target, stage):
    """stage: 'prepare'(게시 전 준비 시작, 시도 횟수 +1) / 'publish'(게시 버튼 누르기 직전 → 이후 자동 재시도 금지)."""
    data = lock_load(folder)
    a = data.get(target, {"tries": 0})
    if stage == "prepare":
        a["tries"] = a.get("tries", 0) + 1
    a["stage"] = stage
    a["at"] = _now().isoformat(timespec="seconds")
    data[target] = a
    _lock_save(folder, data)


def lock_clear(folder, target):
    data = lock_load(folder)
    data.pop(target, None)
    _lock_save(folder, data)


def warn_blocked(folder, target):
    a = lock_load(folder).get(target, {})
    print(f"::warning::게시 잠금 — {folder} ({target}): 이전 시도({a.get('at')}, 단계 {a.get('stage')}, {a.get('tries')}회)가 "
          f"실패했거나 결과를 확인하지 못해 자동으로 다시 올리지 않습니다. 계정에서 실제 게시 여부를 확인한 뒤 "
          f"{LOCK_FILE} 을 지우면(이미 올라갔으면 posted.json 을 만들면) 풀립니다.")


def recent_media(limit=25):
    """계정의 최근 게시물 목록. 조회에 실패하면 None (오류 내용에 토큰이 섞이지 않게 종류만 출력)."""
    q = urllib.parse.urlencode({"fields": "id,caption,timestamp,permalink", "limit": str(limit), "access_token": TOKEN})
    try:
        with urllib.request.urlopen(urllib.request.Request(f"{BASE}/{USER_ID}/media?{q}"), timeout=60) as r:
            return json.load(r).get("data", [])
    except Exception as e:
        print("::warning::최근 게시물 조회 실패:", type(e).__name__, getattr(e, "code", ""))
        return None


def _norm(text):
    return " ".join((text or "").split())


def find_posted(caption, items):
    """최근 게시물 중 캡션 전체가 같은 것(= 같은 콘텐츠가 이미 올라간 것)."""
    want = _norm(caption)
    for it in items or []:
        if want and _norm(it.get("caption")) == want:
            return it
    return None


def already_posted(caption):
    """게시 전 확인. 이미 올라가 있으면 그 게시물, 없으면 None. 조회 자체가 안 되면 게시하지 않고 멈춘다."""
    items = recent_media()
    if items is None:
        fail("최근 게시물을 조회하지 못해 중복 여부를 확인할 수 없습니다. 게시하지 않고 멈춥니다(다음 실행 때 다시 확인).")
    return find_posted(caption, items)


CARDS_DIR = os.environ.get("CARDS_DIR", "approved")
FOOTER_FILE = os.environ.get("FOOTER_FILE", "shop_footer.txt")
DISCLOSURE_FILE = os.environ.get("DISCLOSURE_FILE", "")  # 쿠팡 파트너스 등 대가성 문구 (있으면 무조건 첫 줄)


LINKS_FILE = os.environ.get("LINKS_FILE", "")  # 꿀템: 상품 번호 -> 쿠팡 파트너스 링크
LINKS_PAGE = os.environ.get("LINKS_PAGE", "")


def link_block(link_no):
    """오늘 상품 바로가기 + 전체 모음 페이지 안내 (꿀템 계정)."""
    if not (LINKS_FILE and link_no):
        return ""
    items = {i["no"]: i for i in json.load(open(LINKS_FILE, encoding="utf-8")).get("items", [])}
    it = items.get(int(link_no))
    if not it:
        fail(f"links.json 에 {link_no}번 링크가 없습니다")
    if not it["url"].startswith("https://link.coupang.com/"):
        fail(f"{link_no}번 링크가 쿠팡 파트너스 링크가 아닙니다")
    lines = [f"🛒 {link_no}번 {it['name']} 바로가기 (복사해서 열기)", it["url"]]
    if LINKS_PAGE:
        lines += ["", "📋 지금까지 소개한 꿀템 전체 보기 (프로필 링크와 같은 페이지)", LINKS_PAGE]
    return "\n".join(lines)


def build_caption(body, link_no=None):
    """[대가성 문구] + 본문 + [상품 링크] + 꼬리말(매장 안내 등) + 해시태그 순으로 캡션 조립."""
    paras = body.strip().split("\n\n")
    tags = paras.pop() if paras and paras[-1].lstrip().startswith("#") else ""
    footer = open(FOOTER_FILE, encoding="utf-8").read().strip() if FOOTER_FILE and os.path.exists(FOOTER_FILE) else ""
    disclosure = ""
    if DISCLOSURE_FILE:
        if not os.path.exists(DISCLOSURE_FILE):
            fail(f"대가성 문구 파일이 없습니다: {DISCLOSURE_FILE}")
        disclosure = open(DISCLOSURE_FILE, encoding="utf-8").read().strip()
        if tags and "#광고" not in tags:  # 해시태그를 쓰면 첫 해시태그는 #광고
            tags = "#광고 #쿠팡파트너스 " + tags.replace("#쿠팡파트너스", "").strip()
        body_text = "\n\n".join(paras)
        if disclosure in body_text:  # 중복 방지: 본문에 이미 있으면 빼고 맨 앞에 다시 둔다
            paras = [x for x in paras if x.strip() != disclosure]
    bottom = disclosure if os.environ.get("DISCLOSURE_BOTTOM") == "1" else ""  # 본문 맨 아래에도 한 번 더
    caption = "\n\n".join(p for p in [disclosure, "\n\n".join(paras), link_block(link_no), footer, tags, bottom] if p)
    if len(caption) > 2200:
        fail(f"캡션이 인스타 한도(2200자)를 넘습니다: {len(caption)}자")
    if caption.count("#") > 30:
        fail("해시태그가 30개를 넘습니다")
    return caption


def publish(creation_id, caption=None):
    """media_publish. '아직 준비 안 됨(9007)'이면 잠시 기다렸다 다시 시도.
    오류가 나도 실제로는 올라가는 경우가 있어(2026-11 꿀템 계정 403 사고), caption 을 주면 오류 뒤에 실제 게시 여부를 조회한다."""
    for k in range(8):
        params = {"creation_id": creation_id, "access_token": TOKEN}
        req = urllib.request.Request(f"{BASE}/{USER_ID}/media_publish", data=urllib.parse.urlencode(params).encode(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            if '"code":9007' in body and k < 7:
                print("게시 준비 대기 중… 다시 시도", k + 1)
                time.sleep(15)
                continue
            if caption:
                for wait in (10, 20):  # 늦게 나타나는 경우를 위해 두 번 확인
                    time.sleep(wait)
                    hit = find_posted(caption, recent_media())
                    if hit:
                        print(f"::warning::게시 API 는 오류({e.code})였지만 실제로는 게시되어 있습니다 → 게시 완료로 기록: {hit.get('permalink')}")
                        return {"id": hit["id"], "error_but_posted": True}
            fail(f"API 오류 {e.code} (media_publish): {body}")
        except Exception as e:  # 시간 초과·연결 끊김: 올라갔는지 알 수 없음 → 조회로 확인
            if caption:
                time.sleep(20)
                hit = find_posted(caption, recent_media())
                if hit:
                    print("::warning::게시 응답을 받지 못했지만 실제로는 게시되어 있습니다 → 게시 완료로 기록:", hit.get("permalink"))
                    return {"id": hit["id"], "error_but_posted": True}
            fail(f"게시 요청 응답 없음 (media_publish): {type(e).__name__}")


def write_posted(folder, media_id, info, note=None):
    rec = {"media_id": media_id, **info}
    if note:
        rec["note"] = note
    json.dump(rec, open(os.path.join(folder, "posted.json"), "w"), ensure_ascii=False, indent=2)
    lock_clear(folder, "instagram")


def post(folder):
    if lock_blocked(folder, "instagram"):
        warn_blocked(folder, "instagram")
        return
    imgs = sorted(glob.glob(os.path.join(folder, "card_*.jpg")))
    if not 2 <= len(imgs) <= 10:
        fail(f"{folder}: 캐러셀은 이미지 2~10장이 필요합니다 (현재 {len(imgs)}장)")
    cj = os.path.join(folder, "content.json")
    link_no = json.load(open(cj, encoding="utf-8")).get("link_no") if os.path.exists(cj) else None
    caption = build_caption(open(os.path.join(folder, "caption.txt"), encoding="utf-8").read(), link_no)

    hit = already_posted(caption)  # 1) 같은 캡션이 이미 올라가 있으면 다시 올리지 않는다
    if hit:
        print(f"::warning::{folder}: 같은 게시물이 이미 계정에 있습니다 → 올리지 않고 기록만 남김: {hit.get('permalink')}")
        write_posted(folder, hit["id"], {"permalink": hit.get("permalink"), "timestamp": hit.get("timestamp")},
                     note="이미 게시되어 있어 기록만 남김")
        return

    lock_mark(folder, "instagram", "prepare")
    children = []
    for p in imgs:
        r = api("POST", f"{USER_ID}/media", image_url=public_url(p), is_carousel_item="true")
        wait_ready(r["id"])
        children.append(r["id"])
        print("이미지 등록:", p)

    car = api("POST", f"{USER_ID}/media", media_type="CAROUSEL",
              children=",".join(children), caption=caption)
    wait_ready(car["id"])
    lock_mark(folder, "instagram", "publish")  # 2) 여기부터는 실패해도 자동 재시도 금지
    pub = publish(car["id"], caption)          # 3) 오류여도 실제 게시 여부 확인
    info = api("GET", pub["id"], fields="permalink,timestamp")
    print("게시 완료:", info.get("permalink"))
    write_posted(folder, pub["id"], info)


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
