# 카드뉴스 자동 게시 (@bpj0901)

휴대폰·통신 이슈를 카드뉴스로 만들어 인스타그램에 올리는 저장소입니다.

## 흐름
1. Claude가 이슈를 조사하고 카드뉴스를 만들어 `drafts/<날짜>/`에 올립니다.
2. 사용자가 확인 후 "승인"하면 Claude가 그 폴더를 `approved/<날짜>/`로 옮깁니다.
3. GitHub Actions가 자동으로 인스타그램 캐러셀로 게시하고 `posted.json`에 기록합니다.

## 폴더
- `drafts/` 확인 전 초안
- `approved/` 승인된 게시물 (여기에 들어오면 자동 게시)
- `tools/render.py` 카드 이미지 생성
- `tools/post_instagram.py` 인스타그램 게시

## 필요한 비밀값 (Settings → Secrets and variables → Actions)
- `IG_USER_ID`
- `IG_ACCESS_TOKEN`
