"""쇼츠 영상 제작: script.json -> short.mp4 (1080x1920, 자막 + AI 음성 + 배경음악)

사용법: python tools/make_short.py shorts/drafts/<폴더>
- AI 음성: edge-tts (무료). 설치 안 됐거나 접속 실패 시 무음 + 글자 수 기준 길이로 대체.
- 배경음악: assets/bgm.mp3 가 있으면 사용, 없으면 직접 만든 기본 음원(저작권 문제 없음)을 생성해 사용.
"""
import json, os, subprocess, sys, wave, math, struct, random, asyncio, shutil
sys.path.insert(0, os.path.dirname(__file__))
import render as R
from PIL import Image, ImageDraw

W, H = 1080, 1920
FPS = 30
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sh(*args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        sys.exit("명령 실패: " + " ".join(args[:3]) + "\n" + r.stderr[-1500:])
    return r.stdout


def duration(path):
    return float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path).strip())


# ---------- 음성 ----------
def tts(text, out, voice, rate):
    try:
        import edge_tts
        async def go():
            await edge_tts.Communicate(text, voice, rate=rate).save(out)
        asyncio.run(go())
        return True
    except Exception as e:
        print("AI 음성 실패, 무음으로 대체:", type(e).__name__, str(e)[:120])
        secs = max(2.0, len(text) * 0.13)
        sh("ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", f"{secs:.2f}", out)
        return False


# ---------- 기본 배경음악 (직접 합성한 원본) ----------
def make_bgm(path, secs=70, bpm=88):
    sr = 44100
    beat = 60 / bpm
    chords = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [196.0, 246.94, 293.66], [164.81, 207.65, 246.94]]
    n = int(sr * secs)
    random.seed(7)
    frames = bytearray()
    for i in range(n):
        t = i / sr
        bar = int(t / (beat * 4)) % 4
        tb = t % beat
        pad = sum(math.sin(2 * math.pi * f * t) + 0.3 * math.sin(2 * math.pi * f * 2 * t) for f in chords[bar]) / 6
        pad *= 0.55 + 0.45 * math.sin(2 * math.pi * t / (beat * 8)) ** 2
        kick = math.sin(2 * math.pi * (55 + 90 * math.exp(-tb * 30)) * tb) * math.exp(-tb * 9) if int(t / beat) % 2 == 0 else 0
        hat = (random.random() * 2 - 1) * math.exp(-((t + beat / 2) % beat) * 60) * 0.25
        pluck_f = chords[bar][int(t / (beat / 2)) % 3] * 2
        tp = t % (beat / 2)
        pluck = math.sin(2 * math.pi * pluck_f * tp) * math.exp(-tp * 7) * 0.35
        v = 0.32 * pad + 0.45 * kick + hat * 0.6 + pluck
        frames += struct.pack("<h", int(max(-1, min(1, v * 0.6)) * 32767))
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(bytes(frames))


# ---------- 사장님 마무리 장면 (방학 폰 성지 쇼츠, 2026-10-28 추가) ----------
def owner_enabled(cfg, folder):
    """방학 폰 성지 쇼츠면 마지막 장면을 사장님 사진으로 바꾼다 (picks 등 다른 계정 제외, script.json 의 owner_end:false 로 끔)."""
    return (cfg.get("store_tag", ["방학", "폰 성지"]) == ["방학", "폰 성지"]
            and "picks" not in os.path.abspath(folder).split(os.sep) and cfg.get("owner_end", True))


def apply_owner(cfg, folder):
    if owner_enabled(cfg, folder) and cfg.get("scenes"):
        last = cfg["scenes"][-1]
        last["owner"] = True
        last["headline"] = ""  # 사진 안에 '구매 상담은 방학 폰 성지' 제목이 있으므로 겹치지 않게 비운다
        last.setdefault("caption", "DM·카톡 편하게 문의 주세요")
        last.pop("visual", None)


# ---------- Kling AI 실사 오프닝 (2026-10-29 추가) ----------
# script.json 맨 위에 아래처럼 넣으면, 영상 맨 앞(0~3초)에 Kling 실사 영상이 자동으로 붙는다.
#   "opening": {"prompt": "Cinematic, photorealistic, 8k ...", "seconds": 3,
#               "headline": "선택: 영상 위 큰 글자", "caption": "선택: 자막", "narration": "선택: 읽어줄 문장"}
# 키는 GitHub 비밀값 KLING_API_KEY. 키가 없거나 생성에 실패하면 오프닝 없이 기존 방식 그대로 만든다.
# 한 번 만든 영상은 폴더의 opening.mp4 로 저장해 두고, 프롬프트가 바뀌지 않으면 다시 돈을 쓰지 않는다.
KLING_BASE = os.environ.get("KLING_API_BASE", "https://api-singapore.klingai.com")
KLING_MODEL = os.environ.get("KLING_MODEL", "kling-3.0")


def _kling_auth():
    """KLING_API_KEY 를 그대로 쓴다. 예전 방식 키('액세스키:시크릿키')면 JWT 토큰을 만들어 쓴다."""
    key = os.environ.get("KLING_API_KEY", "").strip()
    if ":" not in key:
        return key
    import base64, hashlib, hmac, time
    ak, sk = key.split(":", 1)
    b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()
    now = int(time.time())
    head = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = b64(json.dumps({"iss": ak, "exp": now + 1800, "nbf": now - 5}).encode())
    sig = b64(hmac.new(sk.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest())
    return f"{head}.{body}.{sig}"


def _kling_call(method, path, data=None):
    import urllib.request, urllib.error
    req = urllib.request.Request(KLING_BASE + path, method=method,
                                 data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Authorization": f"Bearer {_kling_auth()}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            res = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}")
    if res.get("code", 0) != 0:
        raise RuntimeError(f"code {res.get('code')}: {res.get('message')}")
    return res.get("data")


def kling_video(prompt, out, seconds=3, timeout_s=900):
    """Kling 으로 9:16 실사 영상을 만들어 out(mp4)에 저장한다. 실패하면 예외."""
    import time, urllib.request
    task = _kling_call("POST", f"/text-to-video/{KLING_MODEL}", {
        "prompt": prompt,
        "settings": {"resolution": "1080p", "aspect_ratio": "9:16", "duration": max(3, int(math.ceil(seconds))),
                     "audio": "off", "multi_shot": False},
        "options": {"watermark_info": {"enabled": False}}})
    tid = task["id"]
    print("Kling 오프닝 생성 요청:", tid)
    end = time.time() + timeout_s
    while time.time() < end:
        time.sleep(10)
        t = (_kling_call("GET", f"/tasks?task_ids={tid}") or [{}])[0]
        st = t.get("status")
        if st == "failed":
            raise RuntimeError("생성 실패: " + str(t.get("message", ""))[:300])
        if st == "succeeded":
            url = next(o["url"] for o in t.get("outputs", []) if o.get("type") == "video")
            raw = out + ".raw.mp4"
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=120) as r, open(raw, "wb") as f:
                shutil.copyfileobj(r, f)
            # 쇼츠 규격(1080x1920, 30fps, 소리 없음)으로 맞추고 정확히 seconds 초로 자른다
            sh("ffmpeg", "-y", "-i", raw, "-t", f"{seconds:.2f}", "-an",
               "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", out)
            os.remove(raw)
            return out
    raise RuntimeError(f"{timeout_s}초 안에 영상이 완성되지 않았습니다 (작업 ID {tid})")


def opening_scene(cfg, folder):
    """script.json 의 opening 설정으로 맨 앞 장면을 만든다. 쓸 수 없으면 None (기존 방식 그대로)."""
    op = cfg.get("opening") or {}
    prompt = (op.get("prompt") or "").strip()
    if not prompt:
        return None
    import hashlib
    seconds = float(op.get("seconds", 3))
    mp4 = os.path.join(folder, "opening.mp4"); meta = os.path.join(folder, "opening.json")
    sig = hashlib.sha1(f"{KLING_MODEL}|{seconds}|{prompt}".encode()).hexdigest()
    cached = os.path.exists(mp4) and os.path.exists(meta) and json.load(open(meta)).get("sig") == sig
    if not cached:
        if not os.environ.get("KLING_API_KEY", "").strip():
            print("::warning::KLING_API_KEY 비밀값이 없어 실사 오프닝 없이 만듭니다.")
            return None
        try:
            kling_video(prompt, mp4, seconds)
            json.dump({"sig": sig, "model": KLING_MODEL, "seconds": seconds, "prompt": prompt},
                      open(meta, "w"), ensure_ascii=False, indent=2)
        except Exception as e:
            print("::warning::Kling 오프닝 생성 실패, 오프닝 없이 만듭니다:", str(e).replace("\n", " ")[:600])
            return None
    return {"clip": os.path.relpath(mp4, ROOT), "min_dur": seconds, "opening": True,
            "headline": op.get("headline", ""), "caption": op.get("caption", ""), "narration": op.get("narration", "")}


def scene_audio(sc, mp3, voice, rate):
    """장면 음성을 만들고 (장면 길이, AI 음성 성공 여부)를 돌려준다. 내레이션 없는 오프닝은 무음."""
    text = sc.get("narration") or ("" if sc.get("opening") else sc.get("caption", ""))
    if text:
        ok = tts(text, mp3, voice, rate)
        dur = duration(mp3) + 0.35
    else:
        sh("ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", f"{sc.get('min_dur', 3):.2f}", mp3)
        ok, dur = True, 0
    sc["_dur"] = max(dur, sc.get("min_dur", 0))
    return sc["_dur"], ok


# ---------- 장면 이미지 ----------
def scene_image(sc, idx, total, cfg, out, text=True):
    clip = sc.get("clip")
    if clip:  # 영상 장면: 글자만 투명 레이어로 만들고 아래에 영상을 깐다
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sh_ = Image.new("L", (W, H), 0); sd = ImageDraw.Draw(sh_)
        for yy in range(H):  # 위·아래 글자 읽히도록 어둡게
            a = 0
            if yy < 220: a = int(150 * (220 - yy) / 220)
            if yy > 1050: a = int(200 * min(1, (yy - 1050) / 350))
            sd.line([(0, yy), (W, yy)], fill=a)
        img.paste(Image.new("RGBA", (W, H), (6, 8, 20, 255)), (0, 0), sh_)
    else:
        img = Image.new("RGB", (W, H))
        R.gradient(img, (6, 8, 20), (16, 20, 48), 0, H)
    if sc.get("image"):  # 장면 전체 이미지(글자 포함, 9:16): 꽉 채우고 위에 글자를 따로 얹지 않는다
        src = Image.open(os.path.join(ROOT, sc["image"])).convert("RGB")
        sc_ = max(W / src.width, H / src.height)
        p = src.resize((int(src.width * sc_), int(src.height * sc_)), Image.LANCZOS)
        img.paste(p, ((W - p.width) // 2, (H - p.height) // 2))
    if sc.get("owner"):  # 사장님 사진: 얼굴은 그대로, 배경색만 게시물마다 바뀐다
        top, bottom, gl = R.owner_theme(cfg.get("post_at") or cfg.get("title", ""))
        R.gradient(img, top, bottom, 0, H)
        R.glow(img, W // 2, 760, 560, gl, 120)
        p, _ = R.owner_photo(W)
        img.paste(p, (0, 170))
        R.ai_pill(ImageDraw.Draw(img), 40, 170 + p.height - 140)  # 자막 박스에 가리지 않게 위로
    # 비주얼: 카드뉴스용 그림을 만들어 상단에 배치
    if sc.get("visual") and not clip and not sc.get("owner") and not sc.get("image"):
        v = Image.new("RGB", (1080, 1350))
        R.gradient(v, (6, 8, 20), (10, 13, 32), 0, 1350)
        R.visual(v, sc["visual"])
        v = v.crop((0, 0, 1080, 1000))
        # 아래·위 가장자리를 배경에 자연스럽게 녹이는 마스크
        mask = Image.new("L", v.size, 255)
        md = ImageDraw.Draw(mask)
        for yy in range(1000):
            a = 255
            if yy > 700: a = int(255 * (1000 - yy) / 300)
            if yy < 80: a = int(255 * yy / 80)
            md.line([(0, yy), (1080, yy)], fill=max(0, a))
        img.paste(v, (0, 170), mask)
    d = ImageDraw.Draw(img)
    # 상단 매장 태그 + 진행 막대
    tag = cfg.get("store_tag", ["방학", "폰 성지"])
    R.store_tag(d, 60, 70, tag)
    bw = (W - 120) / total
    for k in range(total):
        d.rounded_rectangle([60 + k * bw + 4, 140, 60 + (k + 1) * bw - 4, 148], 4,
                            fill=R.C["accent"] if k <= idx else (50, 60, 100))
    if cfg.get("ad_label"):  # 대가성 표시: 모든 장면 오른쪽 위
        R.pill(d, W - 60, 62, cfg["ad_label"], R.font("black", 30), (255, 255, 255), (16, 18, 30), padx=18, anchor_right=True)
    if clip and sc.get("ai_label", True):  # AI 생성 영상 표시
        R.pill(d, 60, 180, "AI 생성 장면", R.font("bold", 26), (255, 255, 255), (16, 18, 30), padx=14)
    if sc.get("image") and sc.get("ai_label", True):  # AI 생성 이미지 표시 (오른쪽 위)
        R.pill(d, W - 60, 62, "AI 생성 이미지", R.font("bold", 26), (255, 255, 255), (16, 18, 30), padx=14, anchor_right=True)
    y = 1190
    if not text or sc.get("image"):  # 리모션: 글자는 애니메이션으로 따로 얹는다
        img.save(out)
        return
    if sc.get("headline"):
        y = R.text_block(d, 70, y, sc["headline"], R.font("black", 86), R.C["text"], W - 140, 1.18) + 30
    # 자막 박스 (쇼츠 스타일: 흰 박스 + 검은 글자, 하단 UI 가리지 않는 위치)
    cap = sc.get("caption", "")
    if cap:
        f = R.font("black", 54)
        lines = R.wrap(d, cap, f, W - 220)
        bh = len(lines) * 74 + 50
        by = max(y + 10, 1560 - bh // 2)
        by = min(by, 1680 - bh)
        d.rounded_rectangle([80, by, W - 80, by + bh], 28, fill=(255, 255, 255))
        yy = by + 22
        for ln in lines:
            d.text(((W - d.textlength(ln, font=f)) / 2, yy), ln, font=f, fill=(16, 18, 30))
            yy += 74
    img.save(out)


def remotion_voice(cfg, scenes, work):
    """리모션으로 글자 애니메이션·장면 전환이 들어간 영상(+내레이션)을 만든다. 실패하면 예외."""
    rdir = os.path.join(ROOT, "remotion")
    job = os.path.join(rdir, "public", "job")
    shutil.rmtree(job, ignore_errors=True); os.makedirs(job)
    voice = cfg.get("voice", "ko-KR-SunHiNeural"); rate = cfg.get("rate", "+12%")
    items = []; voiced = True
    for i, sc in enumerate(scenes):
        scene_image(sc, i, len(scenes), cfg, os.path.join(job, f"s{i:02d}.png"), text=False)
        mp3 = os.path.join(job, f"v{i:02d}.mp3")
        dur, ok = scene_audio(sc, mp3, voice, rate); voiced &= ok
        it = {"bg": f"job/s{i:02d}.png", "audio": f"job/v{i:02d}.mp3", "frames": int(round(dur * FPS)),
              "headline": "" if sc.get("image") else sc.get("headline", ""),
              "caption": "" if sc.get("image") else sc.get("caption", "")}
        if sc.get("clip"):
            sh("ffmpeg", "-y", "-stream_loop", "-1", "-i", os.path.join(ROOT, sc["clip"]), "-t", f"{dur:.2f}", "-an",
               "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", os.path.join(job, f"c{i:02d}.mp4"))
            it["clip"] = f"job/c{i:02d}.mp4"
        items.append(it)
    props = os.path.join(work, "props.json")
    json.dump({"scenes": items, "fps": FPS}, open(props, "w"), ensure_ascii=False)
    out = os.path.join(os.path.abspath(work), "voice.mp4")
    r = subprocess.run(["npx", "remotion", "render", "src/index.ts", "Short", out, f"--props={os.path.abspath(props)}",
                        "--concurrency=2", "--log=error"], cwd=rdir, capture_output=True, text=True)
    if r.returncode or not os.path.exists(out):
        raise RuntimeError((r.stderr or r.stdout)[-1200:])
    return out, voiced


def build(folder):
    cfg = json.load(open(os.path.join(folder, "script.json"), encoding="utf-8"))
    work = os.path.join(folder, "_work"); os.makedirs(work, exist_ok=True)
    voice = cfg.get("voice", "ko-KR-SunHiNeural"); rate = cfg.get("rate", "+12%")
    apply_owner(cfg, folder)
    opening = opening_scene(cfg, folder)  # Kling 실사 오프닝 (0~3초)
    if opening:
        cfg["scenes"].insert(0, opening)
    scenes = cfg["scenes"]; clips = []; voiced = True
    engine = "ffmpeg"
    if os.environ.get("SHORTS_ENGINE") == "remotion" and os.path.isdir(os.path.join(ROOT, "remotion", "node_modules")):
        try:
            voice_mp4, voiced = remotion_voice(cfg, scenes, work)
            engine = "remotion"
        except Exception as e:
            print("::warning::리모션 렌더 실패, 기존 방식으로 만듭니다:", str(e).replace("\n", " ")[:900])
    for i, sc in enumerate(scenes if engine == "ffmpeg" else []):
        png = os.path.join(work, f"s{i:02d}.png"); scene_image(sc, i, len(scenes), cfg, png)
        mp3 = os.path.join(work, f"v{i:02d}.mp3")
        dur, ok = scene_audio(sc, mp3, voice, rate); voiced &= ok
        clip = os.path.join(work, f"c{i:02d}.mp4")
        frames = int(dur * FPS)
        zoom = "min(zoom+0.0007,1.07)" if i % 2 == 0 else "if(eq(on,0),1.07,max(zoom-0.0007,1.0))"
        if sc.get("clip"):
            src = os.path.join(ROOT, sc["clip"])
            sh("ffmpeg", "-y", "-stream_loop", "-1", "-i", src, "-loop", "1", "-i", png, "-i", mp3,
               "-filter_complex",
               f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1[bg];"
               f"[bg][1:v]overlay=0:0,format=yuv420p[v];[2:a]aresample=44100,apad=pad_dur=0.35[a]",
               "-map", "[v]", "-map", "[a]", "-t", f"{dur:.2f}",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-c:a", "aac", "-b:a", "160k", "-ac", "2", clip)
            clips.append(clip)
            continue
        sh("ffmpeg", "-y", "-loop", "1", "-i", png, "-i", mp3,
           "-filter_complex",
           f"[0:v]scale=2160:3840,zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},format=yuv420p[v];"
           f"[1:a]aresample=44100,apad=pad_dur=0.35[a]",
           "-map", "[v]", "-map", "[a]", "-t", f"{dur:.2f}",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-c:a", "aac", "-b:a", "160k", "-ac", "2", clip)
        clips.append(clip)
    if engine == "ffmpeg":
        lst = os.path.join(work, "list.txt")
        open(lst, "w").write("".join(f"file '{os.path.abspath(c)}'\n" for c in clips))
        voice_mp4 = os.path.join(work, "voice.mp4")
        sh("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", voice_mp4)
    total = duration(voice_mp4)
    bgm = os.path.join(ROOT, "assets", "bgm.mp3")
    if not os.path.exists(bgm):
        bgm = os.path.join(work, "bgm.wav"); make_bgm(bgm, secs=int(total) + 3)
    out = os.path.join(folder, "short.mp4")
    sh("ffmpeg", "-y", "-i", voice_mp4, "-stream_loop", "-1", "-i", bgm, "-filter_complex",
       f"[1:a]volume={cfg.get('bgm_volume', 0.13)},afade=t=out:st={max(0, total - 1.5):.2f}:d=1.5[b];"
       "[0:a][b]amix=inputs=2:duration=first:dropout_transition=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]",
       "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
       "-movflags", "+faststart", "-t", f"{total:.2f}", out)
    # 표지(첫 장면) 이미지
    if opening:  # 실사 오프닝이 있으면 표지는 오프닝 다음 장면(원래 첫 장면)에서 뽑는다
        sh("ffmpeg", "-y", "-ss", f"{scenes[0].get('_dur', 3) + 1:.2f}", "-i", out, "-frames:v", "1", os.path.join(folder, "cover.jpg"))
    elif engine == "remotion":  # 표지: 글자가 다 나온 1초 지점
        sh("ffmpeg", "-y", "-ss", "1", "-i", out, "-frames:v", "1", os.path.join(folder, "cover.jpg"))
    elif scenes[0].get("clip"):  # 첫 장면이 영상이면 첫 프레임 + 글자로 표지
        sh("ffmpeg", "-y", "-ss", "1", "-i", os.path.join(ROOT, scenes[0]["clip"]), "-i", os.path.join(work, "s00.png"),
           "-filter_complex", f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}[b];[b][1:v]overlay=0:0",
           "-frames:v", "1", os.path.join(folder, "cover.jpg"))
    else:
        Image.open(os.path.join(work, "s00.png")).convert("RGB").save(os.path.join(folder, "cover.jpg"), quality=90)
    shutil.rmtree(work)
    import hashlib
    sha = hashlib.sha1(open(os.path.join(folder, "script.json"), "rb").read()).hexdigest()
    info = {"engine": engine, "seconds": round(total, 1), "ai_voice": voiced, "size_mb": round(os.path.getsize(out) / 1e6, 2), "script_sha": sha,
            "owner_end": bool(scenes and scenes[-1].get("owner")),
            "ai_images": any(x.get("image") and x.get("ai_label", True) for x in scenes),
            "ai_opening": bool(opening)}
    json.dump(info, open(os.path.join(folder, "build.json"), "w"), ensure_ascii=False, indent=2)
    print("완성:", out, info)


def needs_build(folder):
    import hashlib
    b = os.path.join(folder, "build.json")
    if not os.path.exists(b) or not os.path.exists(os.path.join(folder, "short.mp4")):
        return True
    sha = hashlib.sha1(open(os.path.join(folder, "script.json"), "rb").read()).hexdigest()
    return json.load(open(b)).get("script_sha") != sha


if __name__ == "__main__":
    if sys.argv[1] == "--changed":
        import glob
        for f in sorted(glob.glob("shorts/drafts/*/script.json") + glob.glob("picks/shorts/drafts/*/script.json")):
            d = os.path.dirname(f)
            if needs_build(d):
                build(d)
    else:
        build(sys.argv[1])
