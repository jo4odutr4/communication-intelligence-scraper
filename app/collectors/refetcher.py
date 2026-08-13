from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd
import requests

from app.schema import COLUMNS


API_URL = "https://api.refetcher.com/"


def collect(urls: list[str], api_key: str) -> pd.DataFrame:
    """Collect public social URLs through Refetcher without recurring billing."""
    if not api_key:
        raise ValueError("Chave da Refetcher ausente")
    targets = [url.strip() for url in urls if url.strip()]
    if not targets:
        return pd.DataFrame(columns=COLUMNS)
    response = requests.post(
        API_URL,
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        json={"urls": targets},
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results", payload if isinstance(payload, list) else [])
    return normalize(results)


def _first(source: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value: Any = source
        for part in key.split("."):
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(part)
        if value not in (None, ""):
            return value
    return None


def normalize(items: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in items:
        data = item.get("data") if isinstance(item.get("data"), dict) else item
        post = data.get("post") if isinstance(data.get("post"), dict) else {}
        author = data.get("author") if isinstance(data.get("author"), dict) else {}
        metrics = data.get("metrics") if isinstance(data.get("metrics"), dict) else {}
        platform = str(_first(data, "platform") or "social").lower()
        url = _first(data, "url", "post.url", "profileUrl", "target")
        published = _first(data, "publishedAt", "createdAt", "post.publishedAt", "post.createdAt")
        rows.append({
            "platform": platform,
            "published_at": published or datetime.now(timezone.utc).isoformat(),
            "author": _first(author, "handle", "username", "displayName", "name") or _first(data, "username", "displayName"),
            "author_followers": _first(author, "followers", "followersCount") or _first(metrics, "followers", "followersCount"),
            "text": _first(post, "caption", "text", "description", "title") or _first(data, "caption", "biography", "description"),
            "url": url,
            "content_type": _first(data, "resource", "type") or "post",
            "query_match": url,
            "likes": _first(metrics, "likes", "likeCount"),
            "comments": _first(metrics, "comments", "commentCount"),
            "shares": _first(metrics, "shares", "shareCount"),
            "views": _first(metrics, "views", "playCount", "viewCount"),
            "hashtags": _first(post, "hashtags") or _first(data, "hashtags"),
            "brand": None, "topic": None, "sentiment": None, "intent": None,
            "earned_or_owned": None, "relevance_score": None,
            "raw_id": _first(data, "id", "post.id") or url,
        })
    return pd.DataFrame(rows, columns=COLUMNS)
