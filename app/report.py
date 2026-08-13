from __future__ import annotations
import json, os
import pandas as pd
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None
from app.analytics import share_of_voice, topic_table, sentiment_table, detect_peaks, top_content


def _fallback(df: pd.DataFrame, title: str) -> str:
    sov=share_of_voice(df); topics=topic_table(df); sent=sentiment_table(df); peaks=detect_peaks(df)
    lines=[f"# {title}","",f"**Base analisada:** {len(df):,} conteúdos em {df.platform.nunique()} plataformas.",""]
    if not sov.empty: lines += ["## Share of voice", *[f"- {r.brand}: {r.share_of_voice_pct}% ({r.mentions} menções)" for r in sov.itertuples()], ""]
    if not topics.empty: lines += ["## Principais temas", *[f"- {r.topic}: {r.mentions}" for r in topics.head(10).itertuples()], ""]
    if not sent.empty: lines += ["## Sentimento", *[f"- {r.sentiment}: {r.pct}%" for r in sent.itertuples()], ""]
    if not peaks.empty: lines += ["## Picos de conversa", *[f"- {r.date}: {r.mentions} menções" for r in peaks.head(10).itertuples()], ""]
    return "\n".join(lines)


def generate(df: pd.DataFrame, title: str="Relatório de Communication Intelligence", use_ai: bool=True) -> str:
    if df.empty: return f"# {title}\n\nNenhum conteúdo para analisar."
    if not (use_ai and os.getenv("OPENAI_API_KEY") and OpenAI is not None):
        return _fallback(df,title)
    summary={
        "total":len(df),"platforms":df.platform.value_counts().to_dict(),
        "share_of_voice":share_of_voice(df).head(12).to_dict("records"),
        "topics":topic_table(df).head(15).to_dict("records"),
        "sentiment":sentiment_table(df).to_dict("records"),
        "peaks":detect_peaks(df).head(10).astype(str).to_dict("records"),
        "top_content":top_content(df,12).fillna("").astype(str).to_dict("records"),
    }
    client=OpenAI()
    r=client.responses.create(
        model=os.getenv("OPENAI_MODEL","gpt-5.6-luna"),
        input=("Write a concise executive communication-intelligence report in Brazilian Portuguese for a senior strategist. "
               "Use only the supplied evidence. Identify 5-10 insights, explain likely drivers of conversation without overclaiming causality, "
               "call out platform differences, risks/opportunities and recommended next research questions. Use Markdown.\n\n"
               f"Title: {title}\nData summary:\n{json.dumps(summary,ensure_ascii=False)}")
    )
    return r.output_text
