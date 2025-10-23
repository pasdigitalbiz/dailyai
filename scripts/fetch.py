import json, time, re
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import feedparser
import requests

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def get_image_from_page(url):
    """Cerca un'immagine di anteprima nell'articolo"""
    try:
        r = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return ""
        soup = BeautifulSoup(r.text, "html.parser")
        # meta og:image
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            return og["content"]
        tw = soup.find("meta", attrs={"name": "twitter:image"})
        if tw and tw.get("content"):
            return tw["content"]
    except Exception:
