"""쇼츠 V2 시험 렌더러 (기존 tools/make_short.py 와 분리, 게시 기능 없음).

사용법: python3 video-v2/render_v2.py video-v2/samples/phone-store.json [출력.mp4]
- 결과는 video-v2/out/ 에 저장 (저장소에 커밋하지 않음).
- 기존 Edge TTS·배경음악 함수는 tools/make_short.py 에서 가져와 쓴다(기존 파일 수정 없음).
- 로그: video-v2/out/<이름>.render.log
"""
import json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(HERE, "audio"))
import make_short as M  # tts, make_bgm, duration 재사용
import effects

FPS = 30
VISUAL_TYPES = {"generated_video", "generated_photo", "original_product_photo", "licensed_official_asset", "motion_graphics", "owner_photo"}
LABEL = {"generated_video": "AI 생성 장면", "generated_photo": "AI 생성 이미지", "owner_photo": "AI 생성 이미지"}
PRESETS = {"slow_zoom_in", "slow_zoom_out", "pan_left", "pan_right", "push_in", "parallax_2d", "static"}
AUTO = ["slow_zoom_in", "pan_left", "slow_zoom_out", "pan_right", "push_in"]


def load(p):
    return json.load(open(p, encoding="utf-8"))


def texts(sc):
    o = sc.get("overlay") or {}
    parts = [sc.get("narration", ""), sc.get("headline", ""), sc.get("caption", ""), json.dumps(o, ensure_ascii=False)]
    return " ".join(parts)


def validate(cfg, preset):
    """렌더링 전 기본 검사 (Phase 4 에서 확장). 문제가 있으면 목록을 돌려준다."""
    errs = []
    for i, sc in enumerate(cfg["scenes"], 1):
        v = sc.get("visual", {})
        t = v.get("type")
        if t not in VISUAL_TYPES:
            errs.append(f"{i}번 장면: 허용되지 않은 visual.type {t!r}")
        src = v.get("src")
        if t != "motion_graphics":
            if not src or not os.path.isfile(os.path.join(ROOT, src)):
                errs.append(f"{i}번 장면: 파일 없음 {src!r}")
            elif os.path.isabs(src) or ".." in src.split("/"):
                errs.append(f"{i}번 장면: 저장소 밖 경로 금지 {src!r}")
        if t in ("original_product_photo", "licensed_official_asset") and not v.get("source"):
            errs.append(f"{i}번 장면: {t} 는 출처(visual.source) 필수")
        cam = v.get("camera", "auto")
        if cam != "auto" and cam not in PRESETS:
            errs.append(f"{i}번 장면: 알 수 없는 카메라 {cam!r}")
        o = sc.get("overlay")
        if o and o.get("type") == "compare" and not (o.get("conditions") or "").strip():
            errs.append(f"{i}번 장면: 가격·요금 비교에는 조건(conditions) 필수")
        if o and o.get("type") in ("number", "compare") and not sc.get("facts"):
            errs.append(f"{i}번 장면: 숫자·가격 그래픽에는 근거(facts: 출처·날짜) 필수")
        for w in preset.get("banned_phrases", []):
            if w in texts(sc):
                errs.append(f"{i}번 장면: 금지 표현 '{w}'")
    return errs


def build(sample_path, out_path=None):
    feats = load(os.path.join(HERE, "config", "features.json"))["features"]
    presets = load(os.path.join(HERE, "config", "account-presets.json"))
    cfg = load(sample_path)
    acc = presets[cfg["account"]]
    name = os.path.splitext(os.path.basename(sample_path))[0]
    out_dir = os.path.join(HERE, "out"); os.makedirs(out_dir, exist_ok=True)
    out_path = out_path or os.path.join(out_dir, f"{name}.mp4")
    log = open(os.path.join(out_dir, f"{name}.render.log"), "w", encoding="utf-8")
    say = lambda *a: (print(*a), print(*a, file=log), log.flush())

    errs = validate(cfg, acc)
    if errs:
        say("검사 실패 → 렌더링 중단:"); [say(" -", e) for e in errs]
        sys.exit(2)

    rdir = os.path.join(HERE, "remotion")
    job = os.path.join(rdir, "public", "job"); shutil.rmtree(job, ignore_errors=True); os.makedirs(job)
    sfx = effects.make_all(job) if feats.get("audio_enhancement") else {}
    voice = cfg.get("voice", acc["voice"]); rate = cfg.get("rate", acc["rate"]); pitch = cfg.get("pitch", acc.get("pitch", "+0Hz"))
    scenes = []; voiced = True
    total = len(cfg["scenes"])
    for i, sc in enumerate(cfg["scenes"]):
        v = sc["visual"]; t = v["type"]
        mp3 = os.path.join(job, f"v{i:02d}.mp3")
        ok = M.tts(sc.get("narration", ""), mp3, voice, rate, pitch) if sc.get("narration") else False
        voiced &= ok or not sc.get("narration")
        dur = (M.duration(mp3) + 0.35) if os.path.exists(mp3) else float(sc.get("seconds", 3))
        dur = max(dur, float(sc.get("min_seconds", 0)))
        item = {"frames": int(round(dur * FPS)), "audio": f"job/v{i:02d}.mp3" if os.path.exists(mp3) else None,
                "headline": sc.get("headline", ""), "caption": sc.get("caption", ""), "labels": []}
        if acc.get("ad_label") is None and t in LABEL:
            item["labels"].append(LABEL[t])
        elif t in LABEL:
            item["labels"].append(LABEL[t])
        if t == "licensed_official_asset":
            item["labels"].append(f"사진: {v['source']}")
        src = v.get("src")
        if src:
            ext = os.path.splitext(src)[1].lower()
            dst = f"job/a{i:02d}{ext}"
            shutil.copy(os.path.join(ROOT, src), os.path.join(rdir, "public", dst))
            if ext in (".mp4", ".mov", ".webm"):
                item["clip"] = dst
            else:
                item["image"] = dst
        cam = v.get("camera", "auto")
        if cam == "auto":
            cam = "static" if item.get("clip") else AUTO[i % len(AUTO)]
        item["camera"] = cam if feats.get("camera_motion") else "static"
        if v.get("focus"): item["focus"] = v["focus"]
        if t == "original_product_photo": item["productFit"] = True
        if t == "owner_photo": item["owner"] = True
        if sc.get("overlay") and feats.get("animated_graphics"):
            item["overlay"] = sc["overlay"]
        if sfx:
            o = (sc.get("overlay") or {}).get("type")
            name_ = "pop" if o in ("number", "cta") else "click" if o in ("checklist", "features") else ("whoosh" if i else None)
            if name_: item["sfx"] = f"job/sfx_{name_}.wav"
        scenes.append(item)
        say(f"장면 {i + 1}/{total}: {t} {item['camera']} {dur:.1f}초 {item['labels']}")

    props = {"scenes": scenes, "fps": FPS, "storeTag": acc["store_tag"], "adLabel": acc.get("ad_label"), "accent": acc["accent"]}
    pj = os.path.join(out_dir, f"{name}.props.json"); json.dump(props, open(pj, "w"), ensure_ascii=False, indent=1)
    raw = os.path.join(out_dir, f"{name}.raw.mp4")
    say("리모션 렌더 시작")
    r = subprocess.run(["npx", "remotion", "render", "src/index.ts", "ShortV2", raw, f"--props={pj}", "--concurrency=2", "--log=error"],
                       cwd=rdir, capture_output=True, text=True)
    print(r.stdout[-2000:], r.stderr[-4000:], file=log)
    if r.returncode or not os.path.exists(raw):
        say("리모션 렌더 실패:", (r.stderr or r.stdout)[-1500:]); sys.exit(3)

    secs = M.duration(raw)
    bgm = os.path.join(out_dir, "bgm.wav"); M.make_bgm(bgm, secs=int(secs) + 3)
    if feats.get("audio_enhancement"):
        # 음성이 나올 때 배경음악을 자동으로 줄인다 (사이드체인 덕킹)
        fc = (f"[1:a]volume=0.22,afade=t=out:st={max(0, secs - 1.5):.2f}:d=1.5[b];"
              "[0:a]asplit=2[v1][v2];[b][v2]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=350[bd];"
              "[v1][bd]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    else:
        fc = (f"[1:a]volume=0.13,afade=t=out:st={max(0, secs - 1.5):.2f}:d=1.5[b];"
              "[0:a][b]amix=inputs=2:duration=first:dropout_transition=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    M.sh("ffmpeg", "-y", "-i", raw, "-stream_loop", "-1", "-i", bgm, "-filter_complex", fc,
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-t", f"{secs:.2f}", out_path)
    info = {"sample": sample_path, "seconds": round(secs, 1), "ai_voice": voiced, "scenes": len(scenes),
            "features": feats, "engine": "remotion-v2"}
    json.dump(info, open(out_path.replace(".mp4", ".build.json"), "w"), ensure_ascii=False, indent=1)
    say("완성:", out_path, info)
    return out_path


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
