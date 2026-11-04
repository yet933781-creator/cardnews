"""상황극 대사 -> 대사별 AI 음성 mp3 (edge-tts, 무료).

사용법: python tools/tts_lines.py tts/<폴더>/lines.json
lines.json 형식:
{
  "voices": {"엄마": "ko-KR-SunHiNeural", "아들": "ko-KR-InJoonNeural"},
  "rate": "+10%",
  "lines": [{"id": "s2_1", "who": "엄마", "text": "...", "rate": "+5%", "pitch": "+0Hz"}, ...]
}
- 같은 폴더에 <id>.mp3 를 만든다. 이미 있고 대사가 그대로면 건너뛴다.
- durations.json 에 대사별 길이(초)를 적는다 (영상 타이밍 맞추기용).
- 기존 카드뉴스/쇼츠 자동화와는 별개로 동작한다.
"""
import asyncio, json, os, subprocess, sys

import edge_tts

FALLBACK = "ko-KR-InJoonNeural"


def dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    return round(float(r.stdout.strip() or 0), 3)


async def say(text, voice, rate, pitch, out):
    await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(out)


def main(path):
    folder = os.path.dirname(path)
    cfg = json.load(open(path, encoding="utf-8"))
    voices = cfg.get("voices", {})
    base_rate = cfg.get("rate", "+10%")
    stamp_path = os.path.join(folder, "durations.json")
    old = json.load(open(stamp_path, encoding="utf-8")) if os.path.exists(stamp_path) else {}
    result = {}
    for ln in cfg["lines"]:
        out = os.path.join(folder, ln["id"] + ".mp3")
        key = f'{ln["who"]}|{ln["text"]}|{ln.get("rate", base_rate)}|{ln.get("pitch", "+0Hz")}'
        if os.path.exists(out) and old.get(ln["id"], {}).get("key") == key:
            result[ln["id"]] = old[ln["id"]]
            continue
        voice = voices.get(ln["who"], FALLBACK)
        try:
            asyncio.run(say(ln["text"], voice, ln.get("rate", base_rate), ln.get("pitch", "+0Hz"), out))
        except Exception as e:  # 목소리 이름이 안 맞으면 기본 목소리로 다시
            print("다시 시도:", ln["id"], e)
            asyncio.run(say(ln["text"], FALLBACK, ln.get("rate", base_rate), ln.get("pitch", "+0Hz"), out))
        result[ln["id"]] = {"key": key, "seconds": dur(out), "voice": voice}
        print("만듦:", out, result[ln["id"]]["seconds"], "초")
    json.dump(result, open(stamp_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)
