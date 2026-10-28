"""인스타 계정 현황 수집: 계정 정보 + 최근 게시물 반응 (+ 가능하면 도달·저장 인사이트)."""
import json, os, sys, datetime
sys.path.insert(0, os.path.dirname(__file__))
import post_instagram as IG
import urllib.parse, urllib.request


def get(path, **params):
    params["access_token"] = IG.TOKEN
    url = f"{IG.BASE}/{path}?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"_error": e.read().decode(errors="replace")[:300]}


IG.main_setup()
uid = IG.USER_ID
acct = get(uid, fields="username,name,biography,website,followers_count,follows_count,media_count,account_type")
media = get(f"{uid}/media", fields="id,caption,media_type,media_product_type,timestamp,like_count,comments_count,permalink", limit=50)
rows = media.get("data", [])
for m in rows[:25]:
    ins = get(f"{m['id']}/insights", metric="reach,saved,shares,views,total_interactions")
    if "data" in ins:
        m["insights"] = {d["name"]: (d.get("values") or [{}])[0].get("value", d.get("total_value", {}).get("value")) for d in ins["data"]}
    else:
        m["insights_error"] = ins.get("_error", "")[:160]
    if m.get("caption"):
        m["caption"] = m["caption"][:120]
acct_ins = get(f"{uid}/insights", metric="reach,profile_views,follower_count,website_clicks", period="day",
               metric_type="total_value", since=int((datetime.datetime.utcnow() - datetime.timedelta(days=28)).timestamp()),
               until=int(datetime.datetime.utcnow().timestamp()))
out = {"collected_at": datetime.datetime.utcnow().isoformat() + "Z", "account": acct, "account_insights_28d": acct_ins,
       "media": rows}
os.makedirs("reports", exist_ok=True)
json.dump(out, open("reports/ig_report.json", "w"), ensure_ascii=False, indent=2)
print("수집 완료:", acct.get("username"), "게시물", len(rows))
