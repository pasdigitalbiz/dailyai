import json, time, re, os
from datetime import datetime, timezone
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import feedparser

# ---------- Helpers ----------
def now_iso():
    return datetime.now(timezone.utc).isoformat()

def clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def categorize(text: str):
    t = text.lower()
    cats = []
    if any(k in t for k in ["image", "vision", "stable", "diffusion", "midjourney", "gen-"]):
        cats.append("Immagini")
    if any(k in t for k in ["video", "caption", "clip", "subtitle"]):
        cats.append("Video")
    if any(k in t for k in ["audio", "voice", "tts", "transcribe", "whisper"]):
        cats.append("Audio")
    if any(k in t for k in ["chat", "agent", "assistant", "copilot", "agentic"]):
        cats.append("Chat/Agent")
    if any(k in t for k in ["code", "repo", "developer", "sdk"]):
        cats.append("Dev/Code")
    if any(k in t for k in ["seo", "marketing", "ads", "content", "copy"]):
        cats.append("Marketing/Content")
    if any(k in t for k in ["ecom", "shopify", "checkout", "merchant", "store"]):
        cats.append("E-commerce")
    return cats or ["Altro"]

def score_item(it):
    score = 0
    # Sorgente
    if it["source"] == "github": score += 2
    if it["source"] == "ph": score += 3
    if it["source"] == "hn": score += 1
    # Star/points
    score += min(it.get("stars", 0), 5000) / 500  # fino a +10
    score += min(it.get("points", 0), 300) / 60   # fino a +5
    # Novità
    score += 2
    return round(score, 2)

# ---------- GitHub ----------
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
        repo_path = a.get("href","").strip()  # /owner/repo
        full_url = urljoin("https://github.com", repo_path)
        title = clean(a.get_text(" ", strip=True))
        desc_el = article.select_one("p")
        desc = clean(desc_el.get_text(" ", strip=True) if desc_el else "")
        lang_el = article.select_one('[itemprop="programmingLanguage"]')
        lang = clean(lang_el.get_text(strip=True) if lang_el else "")
        stars = fetch_github_stars(repo_path)
        cats = list(set(categorize(title + " " + desc) + ([lang] if lang else [])))
        items.append({
            "title": title,
            "summary": desc,
            "summary_it": desc,  # traduzione arriverà dopo
            "url": full_url,
            "date": now_iso(),
            "source": "github",
            "tags": cats,
            "stars": stars
        })
    return items

def fetch_github_stars(repo_path: str) -> int:
    # repo_path es: /owner/repo
    try:
        owner, repo = repo_path.strip("/").split("/")[:2]
        api = f"https://api.github.com/repos/{owner}/{repo}"
        r = requests.get(api, timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code == 200:
            return int(r.json().get("stargazers_count", 0))
    except Exception:
        pass
    return 0

# ---------- Hacker News ----------
def fetch_hn_ai():
    feed_url = "https://hnrss.org/newest?q=ai%20OR%20artificial%20intelligence"
    d = feedparser.parse(feed_url)
    items = []
    for e in d.entries[:40]:
        title = clean(e.title)
        link = e.link
        summary = clean(BeautifulSoup(e.get("summary",""), "html.parser").get_text(" ", strip=True))
        published = e.get("published_parsed") or e.get("updated_parsed")
        dt_iso = datetime.fromtimestamp(time.mktime(published), tz=timezone.utc).isoformat() if published else now_iso()
        # punteggio (se presente nei tag dell'RSS di hnrss)
        points = 0
        try:
            if "tags" in e:
                for t in e.tags:
                    if t.get("term","").startswith("points:"):
                        points = int(t["term"].split(":")[1])
        except Exception:
            pass
        cats = categorize(title + " " + summary)
        items.append({
            "title": title,
            "summary": summary,
            "summary_it": summary,
            "url": link,
            "date": dt_iso,
            "source": "hn",
            "tags": cats,
            "points": points
        })
    return items

# ---------- Product Hunt (AI topic) ----------
def fetch_producthunt_ai():
    # RSS pubblico del topic AI (senza token). Se cambi URL, aggiorna qui.
    feed_url = "https://www.producthunt.com/feeds/topics/artificial-intelligence"
    d = feedparser.parse(feed_url)
    items = []
    for e in d.entries[:30]:
        title = clean(e.title)
        link = e.link
        summary = clean(BeautifulSoup(e.get("summary",""), "html.parser").get_text(" ", strip=True))
        published = e.get("published_parsed") or e.get("updated_parsed")
        dt_iso = datetime.fromtimestamp(time.mktime(published), tz=timezone.utc).isoformat() if published else now_iso()
        cats = categorize(title + " " + summary)
        items.append({
            "title": title,
            "summary": summary,
            "summary_it": summary,
            "url": link,
            "date": dt_iso,
            "source": "ph",
            "tags": cats
        })
    return items

# ---------- Main ----------
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
    gh, hn, ph = [], [], []
    try: gh = fetch_github_trending()
    except Exception as e: print("Errore GitHub:", e)
    try: hn = fetch_hn_ai()
    except Exception as e: print("Errore HN:", e)
    try: ph = fetch_producthunt_ai()
    except Exception as e: print("Errore Product Hunt:", e)

    items = dedupe(gh + hn + ph)

    # calcolo punteggio
    for it in items:
        it["score"] = score_item(it)

    # ordina per punteggio e data
    items.sort(key=lambda x: (x.get("score",0), x.get("date","")), reverse=True)

    data = {
        "generated_at": now_iso(),
        "top5": items[:5],
        "items": items
    }
    with open("public/data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    import time as _t, time
    main()
