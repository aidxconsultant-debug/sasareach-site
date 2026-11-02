# -*- coding: utf-8 -*-
"""noteの新しい記事を、LPのコラム欄に自動で反映する。
GitHub Actions から1時間ごとに動く。記事が増えたときだけ index.html を書きかえる。
"""
import html, json, re, sys, urllib.request
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
import xml.etree.ElementTree as ET

RSS = "https://note.com/aidx_consultant/rss"
SINCE = datetime.fromisoformat("2026-11-01T00:00:00+09:00")  # これより前の古い記事は出さない
MAX = 6
ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
DESC = ROOT / "scripts" / "note_desc.json"   # 説明文を手で書きたい記事だけ { "記事のキー": "説明" }
START, END = "<!-- note-cols:start -->", "<!-- note-cols:end -->"
GREET = re.compile(r"^(本文$|こんにちは|こんばんは|はじめまして|おはようございます)")


def fetch():
    req = urllib.request.Request(RSS, headers={"User-Agent": "Mozilla/5.0 (sasareach.com note sync)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def desc_from(raw):
    paras = [html.unescape(re.sub(r"<[^>]+>", "", p)).strip()
             for p in re.findall(r"<p[^>]*>(.*?)</p>", raw or "", re.S)]
    paras = [p for p in paras if p and not GREET.match(p)]
    text = "".join(paras)
    return text[:90] + ("…" if len(text) > 90 else "")


def main():
    ns = {"media": "http://search.yahoo.com/mrss/"}
    root = ET.fromstring(fetch())
    manual = json.loads(DESC.read_text(encoding="utf-8")) if DESC.exists() else {}
    cards = []
    for it in root.iter("item"):
        link = (it.findtext("link") or "").strip()
        title = (it.findtext("title") or "").strip()
        when = parsedate_to_datetime(it.findtext("pubDate"))
        if not link or when < SINCE:
            continue
        key = link.rstrip("/").split("/")[-1]
        thumb = (it.findtext("media:thumbnail", namespaces=ns) or "").strip()
        desc = manual.get(key) or desc_from(it.findtext("description"))
        img = (f'<img src="{html.escape(thumb)}" width="640" height="335" alt="" loading="lazy">'
               if thumb else "")
        d = f'<span class="c-desc">{html.escape(desc)}</span>' if desc else ""
        cards.append(f'''      <li class="col"><a href="{html.escape(link)}" target="_blank" rel="noopener">
        {img}
        <span><span class="c-date">{when:%Y.%m.%d}</span><span class="c-title">{html.escape(title)}</span>{d}</span>
      </a></li>''')
        if len(cards) >= MAX:
            break
    if not cards:
        print("記事なし。変更しません")
        return
    s = INDEX.read_text(encoding="utf-8")
    a, b = s.index(START) + len(START), s.index(END)
    block = "\n" + "\n".join(cards) + "\n      "
    if s[a:b] == block:
        print("変更なし")
        return
    INDEX.write_text(s[:a] + block + s[b:], encoding="utf-8")
    print(f"{len(cards)}本でコラム欄を更新しました")


if __name__ == "__main__":
    main()
