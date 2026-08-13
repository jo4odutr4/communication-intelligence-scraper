from __future__ import annotations
import requests
import pandas as pd
from app.schema import COLUMNS

BASE = "https://www.googleapis.com/youtube/v3"

def collect(query: str, api_key: str, start_iso: str|None=None, end_iso: str|None=None,
            region: str="BR", language: str="pt", limit: int=200) -> pd.DataFrame:
    if not api_key:
        raise ValueError("YOUTUBE_API_KEY ausente")
    videos=[]; token=None
    while len(videos) < limit:
        params={"part":"snippet","q":query,"type":"video","maxResults":min(50,limit-len(videos)),
                "key":api_key,"regionCode":region,"relevanceLanguage":language,"order":"date"}
        if start_iso: params["publishedAfter"] = start_iso
        if end_iso: params["publishedBefore"] = end_iso
        if token: params["pageToken"] = token
        r=requests.get(f"{BASE}/search",params=params,timeout=30); r.raise_for_status(); data=r.json()
        videos += data.get("items",[])
        token=data.get("nextPageToken")
        if not token: break
    ids=[v["id"]["videoId"] for v in videos if v.get("id",{}).get("videoId")]
    stats={}
    for i in range(0,len(ids),50):
        p={"part":"snippet,statistics","id":",".join(ids[i:i+50]),"key":api_key}
        rr=requests.get(f"{BASE}/videos",params=p,timeout=30); rr.raise_for_status()
        for item in rr.json().get("items",[]): stats[item["id"]]=item
    rows=[]
    for v in videos:
        vid=v["id"]["videoId"]; item=stats.get(vid,v); sn=item.get("snippet",{}); st=item.get("statistics",{})
        rows.append({
            "platform":"youtube","published_at":sn.get("publishedAt"),"author":sn.get("channelTitle"),
            "author_followers":None,"text":f"{sn.get('title','')}\n{sn.get('description','')}",
            "url":f"https://www.youtube.com/watch?v={vid}","content_type":"video","query_match":query,
            "likes":st.get("likeCount"),"comments":st.get("commentCount"),"shares":None,"views":st.get("viewCount"),
            "hashtags":None,"brand":None,"topic":None,"sentiment":None,"intent":None,"earned_or_owned":None,
            "relevance_score":None,"raw_id":vid})
    return pd.DataFrame(rows,columns=COLUMNS)
