from __future__ import annotations
import feedparser
import pandas as pd
from urllib.parse import quote_plus
from app.schema import COLUMNS


def collect(query: str, lang: str = "pt-BR", country: str = "BR", limit: int = 200) -> pd.DataFrame:
    # Google News RSS is useful for discovery; dates are filtered later by the app.
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl={lang}&gl={country}&ceid={country}:pt-419"
    feed = feedparser.parse(url)
    rows = []
    for entry in feed.entries[:limit]:
        rows.append({
            "platform":"google_news",
            "published_at":getattr(entry, "published", None),
            "author":getattr(entry, "source", {}).get("title") if isinstance(getattr(entry, "source", {}), dict) else None,
            "author_followers":None,
            "text":entry.get("title"),
            "url":entry.get("link"),
            "content_type":"news",
            "query_match":query,
            "likes":None,"comments":None,"shares":None,"views":None,
            "hashtags":None,"brand":None,"topic":None,"sentiment":None,"intent":None,
            "earned_or_owned":None,"relevance_score":None,
            "raw_id":entry.get("id") or entry.get("link")
        })
    return pd.DataFrame(rows, columns=COLUMNS)
