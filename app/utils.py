from __future__ import annotations
import pandas as pd
from app.schema import COLUMNS

def combine(frames):
    frames=[f for f in frames if f is not None and not f.empty]
    if not frames: return pd.DataFrame(columns=COLUMNS)
    df=pd.concat(frames,ignore_index=True)
    df["published_at"]=pd.to_datetime(df["published_at"],errors="coerce",utc=True)
    # Prefer platform+raw_id; URL/text are fallbacks.
    key=df["platform"].astype(str)+"|"+df["raw_id"].fillna(df["url"]).fillna(df["text"]).astype(str)
    return df.loc[~key.duplicated()].reset_index(drop=True)

def filter_dates(df,start,end):
    if df.empty: return df
    s=pd.Timestamp(start,tz="UTC"); e=pd.Timestamp(end,tz="UTC")+pd.Timedelta(days=1)
    mask=df["published_at"].isna() | ((df["published_at"]>=s)&(df["published_at"]<e))
    return df.loc[mask].copy()
