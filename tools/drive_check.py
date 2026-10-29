"""드라이브 연결 점검: 서비스 계정으로 폴더를 읽고, 영상 하나를 받아 재생 정보를 확인한다.
사용법: python tools/drive_check.py [확인할 파일 이름]   (GitHub Actions '드라이브 연결 점검'에서 실행)
비밀값(GDRIVE_SA_JSON, GDRIVE_FOLDER_ID)의 내용은 출력하지 않는다.
"""
import json, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
import make_short as M


def note(kind, msg):
    print(f"::{kind}::{msg}")


def main():
    want = sys.argv[1] if len(sys.argv) > 1 else "test-drive.mp4"
    if not M.drive_ready():
        note("error", "GDRIVE_SA_JSON 또는 GDRIVE_FOLDER_ID 비밀값이 비어 있습니다.")
        return 1
    try:
        email = json.loads(os.environ["GDRIVE_SA_JSON"].strip().lstrip("\ufeff")).get("client_email", "?")
    except Exception:
        note("error", "GDRIVE_SA_JSON 이 올바른 JSON 이 아닙니다. 파일 내용 전체({ 부터 } 까지)를 다시 넣어주세요.")
        return 1
    try:
        token = M._drive_token()
    except Exception as e:
        note("error", f"서비스 계정 로그인 실패 ({type(e).__name__}): 키가 꺼졌거나 잘못 붙여넣었을 수 있습니다.")
        return 1
    try:
        files = M.drive_query("mimeType != 'application/vnd.google-apps.folder'", token)
    except Exception as e:
        note("error", f"폴더 읽기 실패: {str(e)[:200]} — Drive API 사용 설정과 폴더 ID 를 확인하세요.")
        return 1
    note("notice", f"서비스 계정 {email} 로 폴더를 읽었습니다. 파일 {len(files)}개: " + ", ".join(f['name'] for f in files[:20]))
    if not files:
        note("warning", "폴더가 비어 있거나, 폴더가 서비스 계정 이메일에 공유되지 않았습니다.")
        return 1
    f = next((x for x in files if x["name"] == want), None) or next((x for x in files if x["name"].lower().endswith((".mp4", ".mov"))), None)
    if not f:
        note("warning", f"'{want}' 영상을 찾지 못했습니다. 폴더에 mp4 를 올려주세요.")
        return 1
    import urllib.request, shutil
    with tempfile.TemporaryDirectory() as d:
        raw = os.path.join(d, "v")
        with urllib.request.urlopen(urllib.request.Request(
                f"{M.DRIVE_API}/{f['id']}?alt=media&supportsAllDrives=true",
                headers={"Authorization": f"Bearer {token}"}), timeout=300) as r, open(raw, "wb") as w:
            shutil.copyfileobj(r, w)
        info = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                               "stream=width,height:format=duration", "-of", "json", raw], capture_output=True, text=True)
        try:
            j = json.loads(info.stdout); s = j["streams"][0]
            note("notice", f"'{f['name']}' 받기 성공: {s['width']}x{s['height']}, {float(j['format']['duration']):.1f}초, "
                           f"{os.path.getsize(raw) / 1e6:.1f}MB — 쇼츠에 붙일 수 있습니다.")
        except Exception:
            note("error", f"'{f['name']}' 은 받았지만 영상으로 읽을 수 없습니다.")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
