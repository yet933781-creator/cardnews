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


# ---------- 장면 이미지 ----------
def scene_image(sc, idx, total, cfg, out):
    img = Image.new("RGB", (W, H))
    R.gradient(img, (6, 8, 20), (16, 20, 48), 0, H)
    # 비주얼: 카드뉴스용 그림을 만들어 상단에 배치
    if sc.get("visual"):
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
    y = 1190
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


def build(folder):
    cfg = json.load(open(os.path.join(folder, "script.json"), encoding="utf-8"))
    work = os.path.join(folder, "_work"); os.makedirs(work, exist_ok=True)
    voice = cfg.get("voice", "ko-KR-SunHiNeural"); rate = cfg.get("rate", "+12%")
    scenes = cfg["scenes"]; clips = []; voiced = True
    for i, sc in enumerate(scenes):
        png = os.path.join(work, f"s{i:02d}.png"); scene_image(sc, i, len(scenes), cfg, png)
        mp3 = os.path.join(work, f"v{i:02d}.mp3")
        voiced &= tts(sc.get("narration") or sc.get("caption", ""), mp3, voice, rate)
        dur = duration(mp3) + 0.35
        clip = os.path.join(work, f"c{i:02d}.mp4")
        frames = int(dur * FPS)
        zoom = "min(zoom+0.0007,1.07)" if i % 2 == 0 else "if(eq(on,0),1.07,max(zoom-0.0007,1.0))"
        sh("ffmpeg", "-y", "-loop", "1", "-i", png, "-i", mp3,
           "-filter_complex",
           f"[0:v]scale=2160:3840,zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},format=yuv420p[v];"
           f"[1:a]aresample=44100,apad=pad_dur=0.35[a]",
           "-map", "[v]", "-map", "[a]", "-t", f"{dur:.2f}",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-c:a", "aac", "-b:a", "160k", "-ac", "2", clip)
        clips.append(clip)
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
    Image.open(os.path.join(work, "s00.png")).convert("RGB").save(os.path.join(folder, "cover.jpg"), quality=90)
    shutil.rmtree(work)
    import hashlib
    sha = hashlib.sha1(open(os.path.join(folder, "script.json"), "rb").read()).hexdigest()
    info = {"seconds": round(total, 1), "ai_voice": voiced, "size_mb": round(os.path.getsize(out) / 1e6, 2), "script_sha": sha}
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
        for f in sorted(glob.glob("shorts/drafts/*/script.json")):
            d = os.path.dirname(f)
            if needs_build(d):
                build(d)
    else:
        build(sys.argv[1])
