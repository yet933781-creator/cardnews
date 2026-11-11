"""사진 1장 -> 세로 실사 장면 영상(켄 번스: 천천히 확대 + 좌우/상하 이동).

사용법: python3 tools/photo_clip.py <사진> <출력.mp4> [--seconds 8] [--move left|right|up|down]
- 1080x1920 이 아니라 720x1280(쇼츠 장면 클립 기준)으로 만든다. 제작 단계에서 다시 1080x1920 으로 맞춘다.
- 사진 픽셀은 바꾸지 않고 잘라 보여주는 위치만 움직인다(상품 사진도 그대로 안전하게 쓸 수 있음).
"""
import argparse, subprocess, sys

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("out")
ap.add_argument("--seconds", type=float, default=8)
ap.add_argument("--move", choices=["left", "right", "up", "down"], default="right")
ap.add_argument("--crop", help="사진의 일부만 쓰기: x,y,w,h (0~1 비율). 예: 0,0.5,1,0.5 = 아래 절반")
ap.add_argument("--fit", action="store_true", help="사진 전체가 보이게(풀샷): 위아래는 같은 사진을 흐리게 깔아 채운다")
ap.add_argument("--zoom", type=float, default=0.15, help="확대 정도 (기본 0.15)")
a = ap.parse_args()
if a.crop or a.fit:  # 잘라 보여주는 위치·배치만 바꾼다(사진 픽셀 수정·합성 아님)
    import os, tempfile
    pre = []
    if a.crop:
        x, y, w, h = [float(v) for v in a.crop.split(",")]
        pre.append(f"crop=iw*{w}:ih*{h}:iw*{x}:ih*{y}")
    head = ",".join(pre) + "," if pre else ""
    if a.fit:
        fc = (f"[0:v]{head}split[p][q];[p]scale=1440:2560:force_original_aspect_ratio=increase,crop=1440:2560,"
              f"gblur=sigma=45,eq=brightness=-0.12[bg];[q]scale=1440:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2")
    else:
        fc = f"[0:v]{head}scale=1440:2560:force_original_aspect_ratio=increase,crop=1440:2560"
    tmp = os.path.join(tempfile.mkdtemp(), "pre.png")
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.src, "-filter_complex", fc, "-frames:v", "1", tmp],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr[-800:])
    a.src = tmp
fps = 30; n = int(a.seconds * fps)
# 2배 해상도로 키운 뒤 zoompan: 1.0 -> 1.15 확대, 동시에 한쪽으로 이동
z = f"1+{a.zoom}*on/{n}"
cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
shift = f"(iw-iw/zoom)/2*(on/{n})"
x = {"left": f"{cx}+{shift}", "right": f"{cx}-{shift}"}.get(a.move, cx)
y = {"up": f"ih/2-(ih/zoom/2)+(ih-ih/zoom)/2*(on/{n})", "down": f"ih/2-(ih/zoom/2)-(ih-ih/zoom)/2*(on/{n})"}.get(a.move, cy)
vf = (f"scale=1440:2560:force_original_aspect_ratio=increase,crop=1440:2560,"
      f"zoompan=z='{z}':x='{x}':y='{y}':d={n}:s=720x1280:fps={fps}")
r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", a.src, "-vf", vf, "-t", str(a.seconds),
                    "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", a.out], capture_output=True, text=True)
if r.returncode:
    sys.exit(r.stderr[-800:])
print("만듦:", a.out)
