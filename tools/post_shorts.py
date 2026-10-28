"""shorts/approved/<폴더>/ 의 short.mp4 를 인스타 릴스 + 유튜브 쇼츠로 게시한다.

- 게시 기록은 posted.json 에 대상별로 남기며, 이미 올라간 대상은 다시 올리지 않는다.
- 필요한 비밀값: IG_USER_ID, IG_ACCESS_TOKEN (인스타)
                 YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN (유튜브, 없으면 유튜브는 건너뜀)
"""
import glob, json, os, sys, time, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
import post_instagram as IG   # 토큰·API·캡션 조립 공용 사용


def ig_reel(folder, caption):
    video = IG.public_url(os.path.join(folder, "short.mp4"))
    params = dict(media_type="REELS", video_url=video, caption=caption, share_to_feed="true")
    if os.path.exists(os.path.join(folder, "cover.jpg")):
        params["cover_url"] = IG.public_url(os.path.join(folder, "cover.jpg"))
    c = IG.api("POST", f"{IG.USER_ID}/media", **params)
    for _ in range(60):  # 영상 처리 최대 약 5분 대기
        st = IG.api("GET", c["id"], fields="status_code,status")
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") == "ERROR":
            IG.fail(f"릴스 처리 실패: {st}")
        time.sleep(5)
    else:
        IG.fail("릴스 처리 시간 초과")
    pub = IG.api("POST", f"{IG.USER_ID}/media_publish", creation_id=c["id"])
    info = IG.api("GET", pub["id"], fields="permalink")
    print("릴스 게시 완료:", info.get("permalink"))
    return {"media_id": pub["id"], "permalink": info.get("permalink")}


def http(method, url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        IG.fail(f"유튜브 오류 {e.code}: {e.read().decode(errors='replace')[:600]}")


def yt_short(folder, cfg, description):
    cid, sec, ref = (os.environ.get(k, "").strip() for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))
    if not (cid and sec and ref):
        print("::warning::유튜브 비밀값이 없어 쇼츠 업로드를 건너뜁니다.")
        return None
    _, _, body = http("POST", "https://oauth2.googleapis.com/token", urllib.parse.urlencode(
        dict(client_id=cid, client_secret=sec, refresh_token=ref, grant_type="refresh_token")).encode())
    token = json.loads(body)["access_token"]
    title = cfg.get("yt_title") or cfg["title"]
    if "#shorts" not in title.lower():
        title = (title + " #Shorts")
    meta = {"snippet": {"title": title[:100], "description": description[:4900],
                        "tags": cfg.get("yt_tags", []), "categoryId": os.environ.get("YT_CATEGORY", "28"), "defaultLanguage": "ko"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
    try:  # 사장님 AI 사진이 실제로 들어간 영상인지 (make_short 가 build.json 에 기록)
        _b = json.load(open(os.path.join(folder, "build.json")))
        owner = _b.get("owner_end", False) or _b.get("ai_images", False)  # 사장님 사진·AI 장면 이미지
    except Exception:
        owner = False
    if any(sc.get("clip") for sc in cfg.get("scenes", [])) or owner:  # AI 생성 영상·사장님 AI 사진 포함 → 합성 콘텐츠 표시
        meta["status"]["containsSyntheticMedia"] = True
    path = os.path.join(folder, "short.mp4")
    size = os.path.getsize(path)
    hdr = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8",
           "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)}
    base = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part="
    h = None
    if os.environ.get("YT_PAID_PROMO") == "1":  # 쿠팡 파트너스 등 대가성 콘텐츠: '유료 프로모션 포함' 표시
        m2 = dict(meta, paidProductPlacementDetails={"hasPaidProductPlacement": True})
        req = urllib.request.Request(base + "snippet,status,paidProductPlacementDetails", data=json.dumps(m2).encode(),
                                     method="POST", headers=hdr)
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                h = dict(r.headers)
        except urllib.error.HTTPError as e:
            print("::warning::유료 프로모션 표시를 API로 못 넣었습니다(스튜디오에서 직접 체크 필요):", e.code, e.read().decode(errors="replace")[:300])
    if h is None and meta["status"].get("containsSyntheticMedia"):
        req = urllib.request.Request(base + "snippet,status", data=json.dumps(meta).encode(), method="POST", headers=hdr)
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                h = dict(r.headers)
        except urllib.error.HTTPError as e:
            print("::warning::AI 합성 표시를 API로 못 넣었습니다(스튜디오에서 직접 체크 필요):", e.code, e.read().decode(errors="replace")[:300])
            meta["status"].pop("containsSyntheticMedia")
    if h is None:
        _, h, _ = http("POST", base + "snippet,status", json.dumps(meta).encode(), hdr)
    loc = h.get("Location") or h.get("location")
    _, _, body = http("PUT", loc, open(path, "rb").read(), {"Content-Type": "video/mp4", "Content-Length": str(size)})
    vid = json.loads(body)["id"]
    url = f"https://youtube.com/shorts/{vid}"
    print("쇼츠 게시 완료:", url)
    return {"video_id": vid, "url": url}


def main():
    IG.main_setup()
    for d in sorted(glob.glob(os.environ.get("SHORTS_DIR", "shorts/approved") + "/*/")):
        d = d.rstrip("/")
        if not due(d):
            continue
        rec_path = os.path.join(d, "posted.json")
        rec = json.load(open(rec_path)) if os.path.exists(rec_path) else {}
        cfg = json.load(open(os.path.join(d, "script.json"), encoding="utf-8"))
        caption = IG.build_caption(cfg["caption"], cfg.get("link_no"))
        changed = False
        if "instagram" not in rec:
            rec["instagram"] = ig_reel(d, caption); changed = True
            json.dump(rec, open(rec_path, "w"), ensure_ascii=False, indent=2)
        if "youtube" not in rec:
            y = yt_short(d, cfg, caption)
            if y:
                rec["youtube"] = y; changed = True
        if changed:
            json.dump(rec, open(rec_path, "w"), ensure_ascii=False, indent=2)


def due(folder):
    from datetime import datetime, timezone
    rec = os.path.join(folder, "posted.json")
    if os.path.exists(rec):
        r = json.load(open(rec))
        yt_ready = all(os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))
        if "instagram" in r and ("youtube" in r or not yt_ready):
            return False
    if not os.path.exists(os.path.join(folder, "short.mp4")):
        print("영상 없음(제작 대기):", folder)
        return False
    at = json.load(open(os.path.join(folder, "script.json"), encoding="utf-8")).get("post_at")
    if at and datetime.fromisoformat(at) > datetime.now(timezone.utc):
        print("예약 대기:", folder, at)
        return False
    return True


if __name__ == "__main__":
    main()
