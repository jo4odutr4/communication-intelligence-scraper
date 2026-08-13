import io, os, re
from datetime import date, timedelta
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from app.collectors import google_news, youtube, x_api, tiktok_research, apify_generic
from app.utils import combine, filter_dates
from app.query_expansion import build_queries
from app.enrichment import enrich
from app.analytics import share_of_voice, volume_daily, detect_peaks, top_content, top_creators, topic_table, sentiment_table
from app.report import generate as generate_report

load_dotenv()

def get_secret(name: str) -> str:
    """Read local environment variables or Streamlit Community Cloud secrets."""
    value = os.getenv(name, "")
    if value:
        return value
    try:
        return str(st.secrets.get(name, ""))
    except Exception:
        return ""

st.set_page_config(page_title="Communication Intelligence Scraper",layout="wide")
st.title("Communication Intelligence Scraper")
st.caption("Google News e YouTube gratuitos por padrão, com conectores opcionais para outras fontes")

DEPTH={"Quick":100,"Standard":500,"Deep":1500,"Exhaustive":5000}

with st.sidebar:
    st.header("Pesquisa")
    query=st.text_area("Marca / tema / query",value='CVC OR "CVC Viagens"')
    brands_raw=st.text_input("Marcas analisadas",value="CVC")
    competitors=st.text_input("Concorrentes",placeholder="Decolar, LATAM")
    aliases=st.text_area("Aliases / campanhas / hashtags",placeholder="CVC Viagens, #CVC, nome da campanha")
    start=st.date_input("Início",date.today()-timedelta(days=7))
    end=st.date_input("Fim",date.today())
    depth=st.selectbox("Profundidade",list(DEPTH),index=1)
    custom_limit=st.number_input("Teto por plataforma",50,20000,DEPTH[depth],50)
    platforms=st.multiselect(
        "Plataformas",
        ["Google News","YouTube","X","TikTok Research","Instagram (Apify)","TikTok (Apify)"],
        default=["Google News","YouTube"],
        help="Google News e YouTube usam as opções gratuitas configuradas. X e Apify podem consumir saldo.",
    )
    st.divider()
    use_query_ai=st.checkbox("IA: expandir queries",value=False,help="Pode gerar cobrança da OpenAI quando uma chave estiver configurada.")
    use_enrichment=st.checkbox("IA: classificar conteúdos",value=False,help="Desligado por padrão para manter custo zero. A classificação heurística continua disponível.")
    x_full=st.checkbox("X: usar Full Archive",value=False)
    run=st.button("Pesquisar e analisar",type="primary",use_container_width=True)

st.info("Modo custo zero ativo: Google News e YouTube estão prontos. X, Apify, TikTok Research e OpenAI permanecem opcionais e desmarcados.")

paid_selected=[p for p in platforms if p in {"X","Instagram (Apify)","TikTok (Apify)"}]
if paid_selected:
    st.warning("Atenção: a seleção atual inclui fontes que podem consumir saldo. Remova X e Apify para garantir custo zero.")

if run:
    limit=int(custom_limit)
    brands=[x.strip() for x in re.split(r"[,;\n]+",brands_raw+","+competitors) if x.strip()]
    queries=build_queries(query,aliases=aliases,competitors=competitors,use_ai=use_query_ai,max_queries=12 if depth in ["Deep","Exhaustive"] else 6)
    st.subheader("Queries utilizadas")
    st.code("\n".join(queries),language="text")
    frames=[]; errors=[]
    start_iso=f"{start.isoformat()}T00:00:00Z"; end_iso=f"{(end+timedelta(days=1)).isoformat()}T00:00:00Z"
    per_query=max(10,limit//max(1,len(queries)))
    with st.status("Coletando…",expanded=True) as status:
        for qi,q in enumerate(queries,1):
            st.write(f"Query {qi}/{len(queries)}: {q}")
            if "Google News" in platforms:
                try: frames.append(google_news.collect(q,limit=per_query))
                except Exception as e: errors.append(f"Google News / {q}: {e}")
            if "YouTube" in platforms:
                try: frames.append(youtube.collect(q,get_secret("YOUTUBE_API_KEY"),start_iso,end_iso,limit=per_query))
                except Exception as e: errors.append(f"YouTube / {q}: {e}")
            if "X" in platforms:
                try: frames.append(x_api.collect(q,get_secret("X_BEARER_TOKEN"),start_iso,end_iso,per_query,x_full))
                except Exception as e: errors.append(f"X / {q}: {e}")
            if "TikTok Research" in platforms:
                try: frames.append(tiktok_research.collect(q,get_secret("TIKTOK_RESEARCH_TOKEN"),start.isoformat(),end.isoformat(),per_query))
                except Exception as e: errors.append(f"TikTok Research / {q}: {e}")
            if "Instagram (Apify)" in platforms:
                try:
                    items=apify_generic.run_actor(get_secret("APIFY_INSTAGRAM_ACTOR_ID"),get_secret("APIFY_TOKEN"),{"search":q,"maxItems":per_query})
                    frames.append(apify_generic.normalize(items,"instagram",q))
                except Exception as e: errors.append(f"Instagram/Apify / {q}: {e}")
            if "TikTok (Apify)" in platforms:
                try:
                    items=apify_generic.run_actor(get_secret("APIFY_TIKTOK_ACTOR_ID"),get_secret("APIFY_TOKEN"),{"search":q,"maxItems":per_query})
                    frames.append(apify_generic.normalize(items,"tiktok",q))
                except Exception as e: errors.append(f"TikTok/Apify / {q}: {e}")
        df=filter_dates(combine(frames),start,end)
        if not df.empty:
            status.update(label=f"Classificando {len(df):,} itens…",state="running")
            df=enrich(df,brands,use_ai=use_enrichment)
        status.update(label=f"Concluído — {len(df):,} itens",state="complete")

    if errors:
        with st.expander(f"{len(errors)} avisos de conectores"):
            st.write("\n\n".join(errors))
    if df.empty:
        st.warning("Nenhum resultado retornado pelos conectores configurados.")
        st.stop()

    tabs=st.tabs(["Visão geral","SOV & temas","Picos","Top conteúdos","Creators","Base","Relatório"])
    with tabs[0]:
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Conteúdos",f"{len(df):,}")
        c2.metric("Plataformas",df.platform.nunique())
        c3.metric("Autores",df.author.nunique())
        c4.metric("Marcas identificadas",df.brand.dropna().nunique())
        vol=volume_daily(df)
        if not vol.empty: st.line_chart(vol.set_index("date")["mentions"])
        plat=df.platform.value_counts().rename_axis("platform").reset_index(name="mentions")
        st.bar_chart(plat.set_index("platform")["mentions"])
    with tabs[1]:
        left,right=st.columns(2)
        sov=share_of_voice(df); topics=topic_table(df); sent=sentiment_table(df)
        with left:
            st.subheader("Share of voice")
            st.dataframe(sov,use_container_width=True,hide_index=True)
            if not sov.empty: st.bar_chart(sov.set_index("brand")["share_of_voice_pct"])
        with right:
            st.subheader("Sentimento")
            st.dataframe(sent,use_container_width=True,hide_index=True)
            st.subheader("Principais temas")
            st.dataframe(topics.head(20),use_container_width=True,hide_index=True)
    with tabs[2]:
        peaks=detect_peaks(df)
        st.dataframe(peaks,use_container_width=True,hide_index=True)
        st.caption("Pico = dia com volume pelo menos 1,5 desvio-padrão acima da média do período.")
    with tabs[3]: st.dataframe(top_content(df,50),use_container_width=True,hide_index=True,height=650)
    with tabs[4]: st.dataframe(top_creators(df,50),use_container_width=True,hide_index=True,height=650)
    with tabs[5]:
        st.dataframe(df,use_container_width=True,height=620)
        csv=df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("Baixar CSV",csv,"communication_intelligence.csv","text/csv")
        bio=io.BytesIO()
        with pd.ExcelWriter(bio,engine="openpyxl") as w:
            df.to_excel(w,index=False,sheet_name="data")
            share_of_voice(df).to_excel(w,index=False,sheet_name="share_of_voice")
            topic_table(df).to_excel(w,index=False,sheet_name="topics")
            sentiment_table(df).to_excel(w,index=False,sheet_name="sentiment")
            detect_peaks(df).to_excel(w,index=False,sheet_name="peaks")
            top_content(df,100).to_excel(w,index=False,sheet_name="top_content")
            top_creators(df,100).to_excel(w,index=False,sheet_name="top_creators")
        st.download_button("Baixar Excel completo",bio.getvalue(),"communication_intelligence.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with tabs[6]:
        title=f"Communication Intelligence — {brands_raw or query} — {start} a {end}"
        report=generate_report(df,title,use_ai=use_enrichment)
        st.markdown(report)
        st.download_button("Baixar relatório Markdown",report.encode("utf-8"),"communication_intelligence_report.md","text/markdown")
