"""효과음 직접 합성 (외부 음원 없음 → 저작권 문제 없음).

whoosh: 장면 전환 / pop: 숫자·그래픽 등장 / click: 체크·목록
사용: python3 video-v2/audio/effects.py <출력폴더>
"""
import math, os, random, struct, sys, wave

SR = 44100


def _write(path, samples):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 32767)) for s in samples))


def whoosh(secs=0.45):
    random.seed(3)
    n = int(SR * secs); out = []; lp = 0.0
    for i in range(n):
        t = i / n
        env = math.sin(math.pi * t) ** 2
        a = 0.02 + 0.25 * t  # 시간에 따라 밝아지는 노이즈 (간단한 저역통과 계수 변화)
        lp += a * ((random.random() * 2 - 1) - lp)
        out.append(lp * env * 0.9)
    return out


def pop(secs=0.16):
    n = int(SR * secs); out = []
    for i in range(n):
        t = i / SR
        f = 520 + 380 * math.exp(-t * 40)
        out.append(math.sin(2 * math.pi * f * t) * math.exp(-t * 28) * 0.7)
    return out


def click(secs=0.05):
    n = int(SR * secs); out = []
    for i in range(n):
        t = i / SR
        out.append(math.sin(2 * math.pi * 1800 * t) * math.exp(-t * 160) * 0.6)
    return out


def make_all(folder):
    os.makedirs(folder, exist_ok=True)
    paths = {}
    for name, fn in (("whoosh", whoosh), ("pop", pop), ("click", click)):
        p = os.path.join(folder, f"sfx_{name}.wav")
        _write(p, fn()); paths[name] = p
    return paths


if __name__ == "__main__":
    print(make_all(sys.argv[1] if len(sys.argv) > 1 else "."))
