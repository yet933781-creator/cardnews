# 쇼츠 V2 (시험 단계)

기존 쇼츠 제작(`tools/make_short.py` + `remotion/`)과 **완전히 분리된** 개선판. 운영 게시에는 아직 쓰지 않는다.

- `config/features.json`: 전체 `enabled: false` (운영 미적용). 기능별 ON/OFF.
- `config/account-presets.json`: 계정별 색·태그·광고 표시·금지 표현·안전 영역.
- `remotion/`: V2 전용 Remotion 프로젝트 (4.0.539 고정, Remotion Free License — 1인 사업장).
  - `src/camera.ts`: 카메라 7종 (slow_zoom_in/out, pan_left/right, push_in, parallax_2d, static). 검은 여백 없는 이동량 계산.
  - `src/numbers.ts`: 숫자 카운트업 (끝 값은 항상 입력 원문 그대로).
  - `src/components/`: CameraMotion, Graphics(AnimatedNumber·비교·체크리스트·타임라인·특징·CTA), Chrome(태그·진행막대·광고/AI 표시·자막).
  - `tests/`: `node --experimental-strip-types --test tests/camera.test.ts tests/numbers.test.ts`
- `audio/effects.py`: 효과음 직접 합성 (외부 음원 없음).
- `render_v2.py`: 샘플 JSON → 검사 → 음성(기존 Edge TTS 재사용) → 리모션 → 배경음악 자동 줄임(덕킹) → `out/`.
- `samples/`: 매장(SKT 해지율) · 꿀템(뽁뽁이 5번) 시험 대본.
- 시험 실행: GitHub Actions "쇼츠 V2 시험 렌더 (게시 없음)" → 결과는 `v2-preview` 브랜치와 artifact.

## 기존 시스템에 주는 영향
- 기존 파일 수정 없음. 기존 워크플로 경로(`shorts/drafts/**`, `tools/make_short.py` 등)와 겹치지 않아 기존 제작·게시가 실행되지 않는다.
- 시험 워크플로는 게시 비밀키를 쓰지 않는다.

## 되돌리기
1. `video-v2/` 폴더와 `.github/workflows/video-v2-test.yml` 삭제 → 완전 원상복구.
2. 원격 `v2-preview` 브랜치는 시험 결과만 있음 (삭제해도 무방).
3. 작업 전 백업: `backup/before-v2-2026-10-29` 브랜치.

## 샘플 장면 규칙 (요약)
- `visual.type`: generated_video / generated_photo / original_product_photo / licensed_official_asset / motion_graphics / owner_photo
- AI 생성 장면은 자동으로 "AI 생성 장면/이미지" 표시. 상품 원본·공식 자료는 `source` 필수.
- 숫자·가격 그래픽(`number`, `compare`)은 `facts`(주장·출처·날짜) 필수, 비교는 `conditions` 필수.
- 상품 원본은 잘리지 않게 전체 표시 + 같은 사진을 흐리게 깐 배경(합성 아님). 이동·확대만.
