import json, time, re
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import feedparser, requests
from urllib.parse import urlparse

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def get_image(url):
    """Prova a recuperare un’immagine og:image o twitter:image"""
    try:
        r = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return ""
        soup = BeautifulSoup(r.text, "html.parser")
        for sel, attr in [
            ("meta[property='og:image']", "content"),
            ("meta[name='twitter:image']", "content"),
            ("meta[property='og:image:url']", "content"),
        ]:
            tag = soup.select_one(sel)
            if tag and tag.get(attr):
                return tag.get(attr).strip()
    except Exception:
        pass
    return ""

def is_article(url):
    """Scarta repository, documentazioni o forum"""
    blocked_domains = [
        "github.com", "gitlab.com", "reddit.com", "hnrss.org",
        "twitter.com", "x.com", "stackoverflow.com",
        "medium.com/@", "producthunt.com"
    ]
    domain = urlparse(url).netloc.lower()
    # blocca se contiene domini “tecnici”
    if any(b in url.lower() for b in blocked_domains):
        return False
    # scarta link troppo brevi o senza path (es. homepage)
    path = urlparse(url).path
    if len(path) < 5:
        return False
    return True

def fetch_hn_ai(limit=30):
    feed = "https://hnrss.org/newest?q=ai%20OR%20artificial%20intelligence"
    d = feedparser.parse(feed)
    items = []
    for e in d.entries[:limit]:
        title = e.title
        link = e.link
        if not is_article(link):
            continue
        summary = BeautifulSoup(e.get("summary",""), "html.parser").get_text(" ", strip=True)
        ts = e.get("published_parsed") or e.get("updated_parsed")
        date_iso = datetime.fromtimestamp(time.mktime(ts), tz=timezone.utc).isoformat() if ts else now_iso()
        img = get_image(link)
        items.append({
            "title": title,
            "summary": summary,
            "url": link,
            "image": img,
            "date": date_iso
        })
    return items

def main():
    data = {"generated_at": now_iso(), "items": fetch_hn_ai()}
    with open("public/data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Aggiornati {len(data['items'])} articoli.")

if __name__ == "__main__":
    main()
