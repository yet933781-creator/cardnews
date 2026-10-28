"""picks/links.json -> docs/picks/index.html (추천템 링크 모음 페이지, 맨 위에 대가성 문구)."""
import json, html, os
cfg = json.load(open("picks/links.json", encoding="utf-8"))
disc = open("picks/disclosure.txt", encoding="utf-8").read().strip()
items = cfg.get("items", [])
rows = []
for it in sorted(items, key=lambda x: -x["no"]):
    rows.append(f'''<a class="item" href="{html.escape(it["url"])}" rel="sponsored nofollow noopener" target="_blank">
  <span class="no">{it["no"]}</span>
  <span class="txt"><b>{html.escape(it["name"])}</b><small>{html.escape(it.get("note", ""))}</small></span>
  <span class="go">보기</span></a>''')
body = "\n".join(rows) or '<p class="empty">곧 첫 꿀템이 올라와요!</p>'
page = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(cfg["title"])}</title>
<style>
:root{{--bg:#fff8f0;--card:#fff;--ink:#1f1a17;--sub:#7a6f66;--acc:#ff7a45;--line:#f0e4d8}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,-apple-system,"Noto Sans KR",sans-serif}}
.wrap{{max-width:560px;margin:0 auto;padding:16px}}
.disc{{background:#1f1a17;color:#fff;border-radius:12px;padding:12px 14px;font-size:14px;line-height:1.5}}
h1{{font-size:22px;margin:20px 0 4px}} .handle{{color:var(--sub);margin:0 0 14px}}
.item{{display:flex;align-items:center;gap:12px;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px;margin:10px 0;text-decoration:none;color:inherit}}
.no{{flex:0 0 40px;height:40px;border-radius:50%;background:var(--acc);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:800}}
.txt{{flex:1;display:flex;flex-direction:column;gap:2px}} .txt small{{color:var(--sub)}}
.go{{color:var(--acc);font-weight:700}} .empty{{color:var(--sub);text-align:center;padding:40px 0}}
</style></head><body><div class="wrap">
<div class="disc">📢 {html.escape(disc)}</div>
<h1>{html.escape(cfg["title"])}</h1><p class="handle">{html.escape(cfg.get("handle", ""))} · 게시물 번호로 찾아보세요</p>
{body}
</div></body></html>'''
os.makedirs("docs/picks", exist_ok=True)
open("docs/picks/index.html", "w", encoding="utf-8").write(page)
print("링크 페이지 생성:", len(items), "개")
