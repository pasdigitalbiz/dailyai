import json, time, re
from datetime import datetime, timezone
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import feedparser

def fetch_github_trending():
    url = "https://github.com/trending?since=daily"
    r = requests.get(url, timeout=20, headers={"User-Agent":"Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    items = []
    for article in soup.select("article.Box-row"):
        a = article.select_one("h2 a")
        if not a:
            continue
        repo_path = a.get("href","").strip()
        full_url = urljoin("https://github.com", repo_path)
        title = re.sub(r"\s+"," ", a.get_text(strip=True))
        desc_el = article.select_one("p")
        desc = desc_el.get_text(" ", strip=True) if desc_el else ""
        lang_el = article.select_one('[itemprop="programmingLanguage"]')
        lang = lang_el.get_text(strip=True) if lang_el else ""
        items.append({
            "title": title,
            "summary": desc,
            "summary_it": desc,
            "url": full_url,
            "date": datetime.now(timezone.utc).isoformat(),
            "source": "github",
            "tags": [t for t in [lang, "trending"] if t]
        })
    return items

def fetch_hn_ai():
    feed_url = "https://hnrss.org/newest?q=ai%20OR%20artificial%20intelligence"
    d = feedparser.parse(feed_url)
    items = []
    for e in d.entries[:50]:
        title = e.title
        link = e.link
        summary = BeautifulSoup(e.get("summary",""), "html.parser").get_text(" ", strip=True)
        published = e.get("published_parsed") or e.get("updated_parsed")
        dt_iso = datetime.fromtimestamp(time.mktime(published), tz=timezone.utc).isoformat() if published else datetime.now(timezone.utc).isoformat()
        items.append({
            "title": title,
            "summary": summary,
            "summary_it": summary,
            "url": link,
            "date": dt_iso,
            "source": "hn",
            "tags": ["hn", "ai"]
        })
    return items

def dedupe(items):
    seen = set()
    out = []
    for it in items:
        key = it["url"].lower().strip()
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out

def main():
    gh = []
    hn = []
    try:
        gh = fetch_github_trending()
    except Exception as e:
        print("Errore GitHub:", e)
    try:
        hn = fetch_hn_ai()
    except Exception as e:
        print("Errore HN:", e)

    items = dedupe(gh + hn)
    items.sort(key=lambda x: x["date"], reverse=True)

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": items
    }
    with open("public/data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
