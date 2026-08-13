from __future__ import annotations
import json, os, re
import pandas as pd
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

SENTIMENT_WORDS={
    "positivo":["bom","ótimo","excelente","amei","adoro","recomendo","parabéns","incrível","maravilhoso"],
    "negativo":["ruim","péssimo","horrível","odeio","golpe","problema","reclamação","atraso","cancelado","absurdo"]
}


def _heuristic(text: str, brands: list[str]) -> dict:
    low=(text or "").lower()
    brand=next((b for b in brands if b.lower() in low), None)
    pos=sum(low.count(w) for w in SENTIMENT_WORDS["positivo"])
    neg=sum(low.count(w) for w in SENTIMENT_WORDS["negativo"])
    sentiment="positivo" if pos>neg else "negativo" if neg>pos else "neutro"
    if any(w in low for w in ["reclamo","reclamação","problema","não funciona","cancelado","atraso"]): intent="reclamação"
    elif any(w in low for w in ["recomendo","amei","parabéns","adorei"]): intent="elogio"
    elif "?" in low or any(w in low for w in ["como ","onde ","quando ","quanto "]): intent="dúvida"
    else: intent="menção"
    relevance=0.9 if brand else 0.55
    return {"brand":brand,"topic":"outros","sentiment":sentiment,"intent":intent,"earned_or_owned":"earned","relevance_score":relevance}


def _classify_batch(client: OpenAI, items: list[dict], brands: list[str]) -> list[dict]:
    schema={
      "type":"object","additionalProperties":False,
      "properties":{"items":{"type":"array","items":{"type":"object","additionalProperties":False,
        "properties":{
          "id":{"type":"integer"},"brand":{"type":["string","null"]},"topic":{"type":"string"},
          "sentiment":{"type":"string","enum":["positivo","neutro","negativo","misto"]},
          "intent":{"type":"string"},"earned_or_owned":{"type":"string","enum":["earned","owned","paid","unknown"]},
          "relevance_score":{"type":"number","minimum":0,"maximum":1}
        },"required":["id","brand","topic","sentiment","intent","earned_or_owned","relevance_score"]}}},
      "required":["items"]}
    prompt=("Classify social/news communication mentions for strategic brand analysis. "
            "Topic should be a short reusable theme (e.g. atendimento, preço, produto, campanha, experiência, crise, promoção, reputação, viagem). "
            "Intent examples: reclamação, elogio, dúvida, notícia, meme, recomendação, publicidade, relato, anúncio. "
            "Use paid only when the content clearly looks sponsored/ad; owned when the author is clearly the brand itself; otherwise earned/unknown. "
            "Brand must be one of the provided brands when possible.\n"
            f"Brands: {brands}\nItems:\n{json.dumps(items,ensure_ascii=False)}")
    r=client.responses.create(
        model=os.getenv("OPENAI_MODEL","gpt-5.6-luna"),
        input=prompt,
        text={"format":{"type":"json_schema","name":"communication_classification","strict":True,"schema":schema}},
    )
    return json.loads(r.output_text)["items"]


def enrich(df: pd.DataFrame, brands: list[str], use_ai: bool=True, batch_size: int=30) -> pd.DataFrame:
    if df.empty: return df.copy()
    out=df.copy()
    brands=[b.strip() for b in brands if b and b.strip()]
    if use_ai and os.getenv("OPENAI_API_KEY") and OpenAI is not None:
        client=OpenAI()
        for start in range(0,len(out),batch_size):
            idxs=list(out.index[start:start+batch_size])
            items=[]
            for i,pos in enumerate(idxs):
                row=out.loc[pos]
                items.append({"id":i,"platform":str(row.get("platform","")),"author":str(row.get("author",""))[:180],"text":str(row.get("text", ""))[:3500]})
            try:
                classified=_classify_batch(client,items,brands)
                by_id={x["id"]:x for x in classified}
                for i,pos in enumerate(idxs):
                    x=by_id.get(i)
                    if not x: continue
                    for k in ["brand","topic","sentiment","intent","earned_or_owned","relevance_score"]:
                        out.at[pos,k]=x.get(k)
            except Exception:
                for pos in idxs:
                    h=_heuristic(str(out.at[pos,"text"]),brands)
                    for k,v in h.items(): out.at[pos,k]=v
    else:
        for pos in out.index:
            h=_heuristic(str(out.at[pos,"text"]),brands)
            for k,v in h.items(): out.at[pos,k]=v
    return out
