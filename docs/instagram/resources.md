# 도구 및 준비 상태
GitHub: yet933781-creator/cardnews, main.
확인된 README: 기존 휴대폰·통신 이슈 카드뉴스 프로젝트. drafts/<날짜>/ → 승인 → approved/<날짜>/ → GitHub Actions 게시 및 posted.json 기록이라는 설계가 적혀 있음. 실제 자동 게시 성공 여부는 미검증.
README에 tools/render.py, tools/post_instagram.py 및 GitHub Actions 비밀값 IG_USER_ID, IG_ACCESS_TOKEN이 언급됨. 실제 구현과 인증 상태는 별도 점검 필요.
기존 사용자/Codex 점검에서 카드뉴스 이미지 생성은 확인됐으나 릴스·음성·게시 자동화는 미검증.
추가 준비: 허용된 상품·검색 데이터 출처, 쿠팡 제휴 링크/성과 접근, 인스타그램 전문 계정 및 공식 게시 권한, 게시 승인 대기열, 이미지 사용 권한 확인, 실게시 테스트.
Metricool은 선택적 도구로 추천됐으나 연결 완료 확인 없음. 비밀값은 GitHub Secrets 등 적절한 보안 저장소에만 보관.
