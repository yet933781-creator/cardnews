"""유튜브 연결 시험: 영상은 올리지 않고 토큰 발급만 확인한다."""
import json, os, urllib.parse, urllib.request
cid, sec, ref = (os.environ.get(k, "").strip() for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))
missing = [k for k, v in zip(("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"), (cid, sec, ref)) if not v]
if missing:
    print("::error::비어 있는 비밀값: " + ", ".join(missing)); raise SystemExit(1)
data = urllib.parse.urlencode(dict(client_id=cid, client_secret=sec, refresh_token=ref, grant_type="refresh_token")).encode()
try:
    with urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=data), timeout=30) as r:
        tok = json.load(r)
except urllib.error.HTTPError as e:
    body = json.loads(e.read() or b"{}")
    print("::error::유튜브 연결 실패: " + body.get("error", "") + " - " + body.get("error_description", "")); raise SystemExit(1)
scope = tok.get("scope", "")
ok = "youtube.upload" in scope
print(("::notice::" if ok else "::error::") + f"유튜브 연결 {'성공' if ok else '권한 부족'} (권한: {scope})")
raise SystemExit(0 if ok else 1)
