"""인스타 연결 시험: 게시하지 않고 토큰으로 계정 정보만 읽는다."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import post_instagram as IG
IG.main_setup()
a = IG.api("GET", IG.USER_ID, fields="username,account_type,followers_count,media_count")
print(f"::notice::인스타 연결 성공: @{a.get('username')} ({a.get('account_type')}) 팔로워 {a.get('followers_count')} · 게시물 {a.get('media_count')}")
