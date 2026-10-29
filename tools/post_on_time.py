"""정시 게시 도우미 (.github/workflows/post-on-time.yml 에서 실행).

승인 폴더 중 아직 게시 안 된 것(posted.json 없음)의 post_at 을 모아,
지금부터 WINDOW_MIN 분 안에 오는 시각마다 기다렸다가 해당 게시 워크플로를 workflow_dispatch 로 실행한다.
- 게시 자체는 기존 post_instagram.py / post_shorts.py 가 한다(중복 방지 로직 그대로).
- 이미 시각이 지난 것은 바로 실행한다.
- 게시 API·비밀키를 직접 쓰지 않는다.
"""
import glob, json, os, subprocess, time
from datetime import datetime, timezone

WINDOW_MIN = int(os.environ.get("WINDOW_MIN", "60"))
GRACE_SEC = 20  # 게시 시각 + 20초 뒤에 실행 (is_due 판정 여유)

SOURCES = [  # (승인 폴더 패턴, 시각이 적힌 파일, 실행할 워크플로)
    ("approved/*", "content.json", "post.yml"),
    ("shorts/approved/*", "script.json", "shorts-post.yml"),
    ("picks/approved/*", "content.json", "picks-post.yml"),
    ("picks/shorts/approved/*", "script.json", "picks-post.yml"),
]


def pending():
    out = []
    for pat, fname, wf in SOURCES:
        for d in sorted(glob.glob(pat)):
            f = os.path.join(d, fname)
            if not os.path.isfile(f) or os.path.exists(os.path.join(d, "posted.json")):
                continue
            try:
                at = json.load(open(f, encoding="utf-8")).get("post_at")
                when = datetime.fromisoformat(at) if at else datetime.now(timezone.utc)
            except Exception as e:
                print(f"::warning::{f} 의 post_at 을 읽지 못함: {e}")
                continue
            out.append((when, wf, d))
    return sorted(out)


def dispatch(wf):
    if os.environ.get("DRY_RUN"):  # 시험용: 실제로 실행하지 않음
        print("(시험) 실행했을 워크플로:", wf)
        return
    r =subprocess.run(["gh", "workflow", "run", wf, "--repo", os.environ["REPO"], "--ref", "main"],
                       capture_output=True, text=True)
    print(("실행함: " if r.returncode == 0 else "::error::실행 실패: ") + wf, r.stderr.strip()[:300])


def main():
    now = datetime.now(timezone.utc)
    todo = [(w, wf, d) for w, wf, d in pending() if (w - now).total_seconds() <= WINDOW_MIN * 60]
    if not todo:
        print(f"{WINDOW_MIN}분 안에 게시할 승인 콘텐츠가 없습니다. (나머지는 기존 예약 확인이 처리)")
        return
    # 같은 시각·같은 워크플로는 한 번만 실행
    groups = {}
    for w, wf, d in todo:
        groups.setdefault((max(w, now).replace(microsecond=0), wf), []).append(d)
    for (w, wf), dirs in sorted(groups.items()):
        wait = (w - datetime.now(timezone.utc)).total_seconds() + GRACE_SEC
        print(f"{w.astimezone().isoformat()} {wf} ← {', '.join(dirs)} (대기 {max(0, int(wait))}초)")
        if wait > 0:
            time.sleep(wait)
        dispatch(wf)


if __name__ == "__main__":
    main()
