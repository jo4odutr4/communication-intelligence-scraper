from __future__ import annotations
import requests
import pandas as pd
from app.schema import COLUMNS

URL="https://open.tiktokapis.com/v2/research/video/query/"
FIELDS="id,video_description,create_time,region_code,share_count,view_count,like_count,comment_count,hashtag_names,username,video_duration"

def collect(keyword: str, token: str, start_date: str, end_date: str, limit: int=500) -> pd.DataFrame:
    if not token: raise ValueError("TIKTOK_RESEARCH_TOKEN ausente")
    headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"}
    rows=[]; cursor=0
    while len(rows)<limit:
        body={"query":{"and":[{"operation":"IN","field_name":"keyword","field_values":[keyword]}]},
              "start_date":start_date,"end_date":end_date,"max_count":min(100,limit-len(rows)),"cursor":cursor}
        r=requests.post(URL,headers=headers,params={"fields":FIELDS},json=body,timeout=45); r.raise_for_status(); data=r.json().get("data",{})
        for v in data.get("videos",[]):
            username=v.get("username")
            rows.append({"platform":"tiktok","published_at":v.get("create_time"),"author":"@"+username if username else None,
                "author_followers":None,"text":v.get("video_description"),"url":f"https://www.tiktok.com/@{username}/video/{v.get('id')}" if username else None,
                "content_type":"video","query_match":keyword,"likes":v.get("like_count"),"comments":v.get("comment_count"),
                "shares":v.get("share_count"),"views":v.get("view_count"),"hashtags":",".join(v.get("hashtag_names",[]) or []),
                "brand":None,"topic":None,"sentiment":None,"intent":None,"earned_or_owned":None,"relevance_score":None,"raw_id":v.get("id")})
        if not data.get("has_more"): break
        cursor=data.get("cursor",cursor+len(data.get("videos",[])))
    return pd.DataFrame(rows,columns=COLUMNS)
