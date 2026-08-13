from __future__ import annotations
import requests
import pandas as pd
from app.schema import COLUMNS


def collect(query: str, bearer: str, start_iso: str|None=None, end_iso: str|None=None,
            limit: int=500, full_archive: bool=False) -> pd.DataFrame:
    if not bearer: raise ValueError("X_BEARER_TOKEN ausente")
    endpoint = "https://api.x.com/2/tweets/search/all" if full_archive else "https://api.x.com/2/tweets/search/recent"
    headers={"Authorization":f"Bearer {bearer}"}
    rows=[]; token=None
    while len(rows) < limit:
        params={"query":query,"max_results":min(100,max(10,limit-len(rows))),
                "tweet.fields":"created_at,public_metrics,lang,entities,author_id",
                "expansions":"author_id","user.fields":"username,name,public_metrics"}
        if start_iso: params["start_time"]=start_iso
        if end_iso: params["end_time"]=end_iso
        if token: params["next_token"]=token
        r=requests.get(endpoint,headers=headers,params=params,timeout=30); r.raise_for_status(); data=r.json()
        users={u["id"]:u for u in data.get("includes",{}).get("users",[])}
        for t in data.get("data",[]):
            m=t.get("public_metrics",{}); u=users.get(t.get("author_id"),{}); ent=t.get("entities",{})
            rows.append({"platform":"x","published_at":t.get("created_at"),"author":"@"+u.get("username","") if u else None,
                "author_followers":u.get("public_metrics",{}).get("followers_count"),"text":t.get("text"),
                "url":f"https://x.com/{u.get('username','i')}/status/{t.get('id')}","content_type":"post","query_match":query,
                "likes":m.get("like_count"),"comments":m.get("reply_count"),"shares":m.get("retweet_count"),
                "views":m.get("impression_count"),"hashtags":",".join(h.get("tag","") for h in ent.get("hashtags",[])) or None,
                "brand":None,"topic":None,"sentiment":None,"intent":None,"earned_or_owned":None,
                "relevance_score":None,"raw_id":t.get("id")})
            if len(rows)>=limit: break
        token=data.get("meta",{}).get("next_token")
        if not token: break
    return pd.DataFrame(rows,columns=COLUMNS)
