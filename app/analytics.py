from __future__ import annotations
import numpy as np
import pandas as pd


def prepare_numeric(df: pd.DataFrame) -> pd.DataFrame:
    out=df.copy()
    for c in ["likes","comments","shares","views","author_followers","relevance_score"]:
        out[c]=pd.to_numeric(out.get(c),errors="coerce")
    out["engagement"] = out[["likes","comments","shares"]].fillna(0).sum(axis=1)
    return out


def share_of_voice(df: pd.DataFrame) -> pd.DataFrame:
    x=df.dropna(subset=["brand"]).copy()
    if x.empty: return pd.DataFrame(columns=["brand","mentions","share_of_voice_pct"])
    g=x.groupby("brand",dropna=False).size().rename("mentions").reset_index().sort_values("mentions",ascending=False)
    g["share_of_voice_pct"]=(g["mentions"]/g["mentions"].sum()*100).round(1)
    return g


def volume_daily(df: pd.DataFrame) -> pd.DataFrame:
    x=df.dropna(subset=["published_at"]).copy()
    if x.empty: return pd.DataFrame(columns=["date","mentions"])
    x["date"]=pd.to_datetime(x["published_at"],utc=True).dt.date
    return x.groupby("date").size().rename("mentions").reset_index()


def detect_peaks(df: pd.DataFrame, z_threshold: float=1.5) -> pd.DataFrame:
    v=volume_daily(df)
    if len(v)<3: return v.iloc[0:0].assign(z_score=pd.Series(dtype=float))
    std=float(v["mentions"].std(ddof=0))
    if std==0: return v.iloc[0:0].assign(z_score=pd.Series(dtype=float))
    v["z_score"]=(v["mentions"]-v["mentions"].mean())/std
    return v[v["z_score"]>=z_threshold].sort_values("z_score",ascending=False)


def top_content(df: pd.DataFrame, n:int=20) -> pd.DataFrame:
    x=prepare_numeric(df)
    # Cross-platform ranking: log views + engagement; avoids views dominating everything.
    x["impact_score"]=(np.log1p(x["views"].fillna(0))*2 + np.log1p(x["engagement"])*3 + x["relevance_score"].fillna(.5)*2).round(2)
    cols=["platform","published_at","brand","author","text","url","views","engagement","sentiment","topic","impact_score"]
    return x.sort_values("impact_score",ascending=False)[cols].head(n)


def top_creators(df: pd.DataFrame, n:int=20) -> pd.DataFrame:
    x=prepare_numeric(df).dropna(subset=["author"])
    if x.empty: return pd.DataFrame(columns=["author","platform","mentions","engagement","views"])
    g=x.groupby(["author","platform"],dropna=False).agg(mentions=("raw_id","count"),engagement=("engagement","sum"),views=("views","sum"),followers=("author_followers","max")).reset_index()
    g["creator_score"]=(np.log1p(g["engagement"])*3+np.log1p(g["views"])*2+np.log1p(g["followers"].fillna(0))).round(2)
    return g.sort_values("creator_score",ascending=False).head(n)


def topic_table(df: pd.DataFrame) -> pd.DataFrame:
    x=df.dropna(subset=["topic"])
    if x.empty: return pd.DataFrame(columns=["topic","mentions"])
    return x.groupby("topic").size().rename("mentions").reset_index().sort_values("mentions",ascending=False)


def sentiment_table(df: pd.DataFrame) -> pd.DataFrame:
    x=df.dropna(subset=["sentiment"])
    if x.empty: return pd.DataFrame(columns=["sentiment","mentions","pct"])
    g=x.groupby("sentiment").size().rename("mentions").reset_index().sort_values("mentions",ascending=False)
    g["pct"]=(g.mentions/g.mentions.sum()*100).round(1)
    return g
