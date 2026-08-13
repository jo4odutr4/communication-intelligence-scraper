from __future__ import annotations
import requests
import pandas as pd
from app.schema import COLUMNS

# Generic adapter: actor input/output shapes vary by actor. Configure actor IDs in .env.
def run_actor(actor_id: str, token: str, actor_input: dict) -> list[dict]:
    if not actor_id or not token: raise ValueError("APIFY_TOKEN/actor ID ausente")
    run = requests.post(f"https://api.apify.com/v2/acts/{actor_id}/runs?token={token}&waitForFinish=120",json=actor_input,timeout=150)
    run.raise_for_status(); info=run.json()["data"]; ds=info.get("defaultDatasetId")
    if not ds: return []
    rr=requests.get(f"https://api.apify.com/v2/datasets/{ds}/items?token={token}&clean=true",timeout=60); rr.raise_for_status()
    return rr.json()

def normalize(items: list[dict], platform: str, query: str) -> pd.DataFrame:
    rows=[]
    for x in items:
        text=x.get("caption") or x.get("text") or x.get("description") or x.get("title")
        url=x.get("url") or x.get("webVideoUrl") or x.get("postUrl")
        author=x.get("ownerUsername") or x.get("username") or x.get("author")
        rows.append({"platform":platform,"published_at":x.get("timestamp") or x.get("createTime") or x.get("date"),
            "author":author,"author_followers":x.get("followersCount"),"text":text,"url":url,"content_type":x.get("type") or "post",
            "query_match":query,"likes":x.get("likesCount") or x.get("diggCount"),"comments":x.get("commentsCount") or x.get("commentCount"),
            "shares":x.get("sharesCount") or x.get("shareCount"),"views":x.get("videoViewCount") or x.get("playCount") or x.get("views"),
            "hashtags":None,"brand":None,"topic":None,"sentiment":None,"intent":None,"earned_or_owned":None,"relevance_score":None,
            "raw_id":x.get("id") or x.get("shortCode") or url})
    return pd.DataFrame(rows,columns=COLUMNS)
