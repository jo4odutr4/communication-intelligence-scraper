from __future__ import annotations
import json, os, re
from typing import Iterable
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def _split_terms(value: str | Iterable[str] | None) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        parts = re.split(r"[,\n;]+", value)
    else:
        parts = list(value)
    out=[]
    for p in parts:
        p=str(p).strip()
        if p and p.lower() not in {x.lower() for x in out}:
            out.append(p)
    return out


def build_queries(primary: str, aliases=None, competitors=None, use_ai: bool=False, max_queries: int=12) -> list[str]:
    base=_split_terms(primary) + _split_terms(aliases) + _split_terms(competitors)
    if not base:
        return []
    queries=[]
    # First query keeps the user's own syntax intact.
    if primary.strip(): queries.append(primary.strip())
    for term in base:
        q=f'"{term}"' if " " in term and not term.startswith('"') else term
        if q not in queries: queries.append(q)
    if use_ai and os.getenv("OPENAI_API_KEY") and OpenAI is not None:
        try:
            client=OpenAI()
            schema={
                "type":"object","additionalProperties":False,
                "properties":{"queries":{"type":"array","items":{"type":"string"},"maxItems":max_queries}},
                "required":["queries"]
            }
            r=client.responses.create(
                model=os.getenv("OPENAI_MODEL","gpt-5.6-luna"),
                input=("Generate search-query variants for social listening in Brazilian Portuguese. "
                       "Include likely aliases, hashtags, handles-style mentions, product/campaign variants and common spelling forms. "
                       "Do not invent unrelated brands. Return concise queries only.\n\n"
                       f"Seed terms: {base}\nOriginal query: {primary}"),
                text={"format":{"type":"json_schema","name":"query_expansion","strict":True,"schema":schema}},
            )
            payload=json.loads(r.output_text)
            for q in payload.get("queries",[]):
                q=q.strip()
                if q and q not in queries: queries.append(q)
        except Exception:
            pass
    return queries[:max_queries]
