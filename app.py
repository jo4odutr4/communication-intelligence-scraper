import base64, hmac, io, math, os, re
from pathlib import Path
from datetime import date, timedelta
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from app.collectors import google_news, youtube, x_api, tiktok_research, apify_generic, refetcher
from app.utils import combine, filter_dates
from app.query_expansion import build_queries
from app.enrichment import enrich
from app.analytics import share_of_voice, volume_daily, detect_peaks, top_content, top_creators, topic_table, sentiment_table
from app.report import generate as generate_report

load_dotenv()

def embedded_font(filename: str) -> str:
    """Embed official brand fonts so Streamlit Cloud renders them reliably."""
    path = Path(__file__).parent / "assets" / "fonts" / filename
    if not path.exists():
        return ""
    return base64.b64encode(path.read_bytes()).decode("ascii")

centrale_bold=embedded_font("Centrale_Sans_Bold.otf")
centrale_light=embedded_font("Centrale_Sans_Light.otf")

def get_secret(name: str) -> str:
    """Read local environment variables or Streamlit Community Cloud secrets."""
    value = os.getenv(name, "")
    if value:
        return value
    try:
        return str(st.secrets.get(name, ""))
    except Exception:
        return ""

def excel_safe(frame: pd.DataFrame) -> pd.DataFrame:
    """Remove timezone information unsupported by Excel from every table."""
    result = frame.copy()
    for column in result.columns:
        if pd.api.types.is_datetime64_any_dtype(result[column]):
            result[column] = result[column].dt.tz_localize(None)
        elif result[column].dtype == "object":
            result[column] = result[column].map(
                lambda value: value.tz_localize(None)
                if isinstance(value, pd.Timestamp) and value.tzinfo is not None
                else value
            )
    return result

@st.cache_data(ttl=900, show_spinner=False)
def collect_google_news_cached(query: str, limit: int) -> pd.DataFrame:
    return google_news.collect(query, limit=limit)

@st.cache_data(ttl=3600, show_spinner=False)
def collect_youtube_cached(
    query: str,
    start_iso: str,
    end_iso: str,
    limit: int,
    _api_key: str,
) -> pd.DataFrame:
    return youtube.collect(query, _api_key, start_iso, end_iso, limit=limit)

st.set_page_config(page_title="Ampfy Escuta",page_icon="⚡",layout="wide")

brand_css="""
<style>
@font-face {
  font-family: "Centrale Sans";
  src: url(data:font/otf;base64,__CENTRALE_BOLD__) format("opentype");
  font-weight: 700;
}
@font-face {
  font-family: "Centrale Sans";
  src: url(data:font/otf;base64,__CENTRALE_LIGHT__) format("opentype");
  font-weight: 300;
}
:root {
  --ampfy-bg: #181716;
  --ampfy-deep: #0E0D0B;
  --ampfy-surface: #1F1C18;
  --ampfy-tint: #221C0C;
  --ampfy-border: #2A2620;
  --ampfy-amber: #FBBA00;
  --ampfy-text: #F5F2EC;
  --ampfy-muted: #A6A099;
}
html, body, [class*="css"], .stApp {
  font-family: "Centrale Sans", sans-serif;
  font-weight: 300;
  color: var(--ampfy-text);
}
p, label, [data-testid="stWidgetLabel"], [data-testid="stCaptionContainer"],
[data-testid="stMarkdownContainer"] {
  color: var(--ampfy-text);
}
[data-testid="stWidgetLabel"] p, [data-testid="stCaptionContainer"] p {
  color: var(--ampfy-muted) !important;
}
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
  background: var(--ampfy-bg);
}
[data-testid="stSidebar"] {
  background: var(--ampfy-deep);
  border-right: 1px solid var(--ampfy-border);
}
h1, h2, h3, h4, .ampfyca-name {
  font-family: "Centrale Sans", sans-serif !important;
  font-weight: 700 !important;
  text-transform: uppercase;
  letter-spacing: -0.02em;
  color: var(--ampfy-text) !important;
}
.ampfyca-hero {
  border-top: 8px solid var(--ampfy-amber);
  border-bottom: 1px solid var(--ampfy-border);
  padding: 24px 0 20px;
  margin: 0 0 24px;
}
.ampfyca-kicker {
  color: var(--ampfy-amber);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: .12em;
  text-transform: uppercase;
}
.ampfyca-name {
  font-size: clamp(42px, 7vw, 84px);
  line-height: .95;
  margin: 8px 0 10px;
}
.ampfyca-tagline {
  color: var(--ampfy-muted);
  font-size: 15px;
  letter-spacing: .02em;
}
[data-testid="stForm"], [data-testid="stExpander"], [data-testid="stMetric"],
[data-testid="stDataFrame"], [data-testid="stAlertContainer"] {
  background: var(--ampfy-surface);
  border: 1px solid var(--ampfy-border);
  border-radius: 0 !important;
}
.stTextInput input, .stTextArea textarea, .stNumberInput input,
[data-baseweb="select"] > div, [data-baseweb="input"] > div {
  background: var(--ampfy-deep) !important;
  color: var(--ampfy-text) !important;
  border-color: var(--ampfy-border) !important;
  border-radius: 0 !important;
}
.stButton > button, .stDownloadButton > button {
  background: var(--ampfy-amber) !important;
  color: var(--ampfy-deep) !important;
  border: 0 !important;
  border-radius: 999px !important;
  font-family: "Centrale Sans", sans-serif !important;
  font-size: 14px !important;
  font-weight: 600 !important;
  letter-spacing: .06em;
  text-transform: uppercase;
}
.stButton > button:hover, .stDownloadButton > button:hover {
  filter: brightness(.9);
  transform: translateY(-1px);
  transition: 220ms ease-out;
}
a, [data-testid="stLink"] { color: var(--ampfy-amber) !important; }
hr { border-color: var(--ampfy-border) !important; }
[data-testid="stMetricValue"] { color: var(--ampfy-amber); }
[data-testid="stAlertContainer"] p, [data-testid="stAlertContainer"] a,
[data-testid="stNotificationContentInfo"] p {
  color: var(--ampfy-amber) !important;
}
[data-testid="stAlertContainer"] svg { fill: var(--ampfy-amber) !important; }
[data-baseweb="tab-list"] { border-bottom: 1px solid var(--ampfy-border); }
[data-baseweb="tab"] { border-radius: 0 !important; }
[aria-selected="true"] { color: var(--ampfy-amber) !important; }
</style>
""".replace("__CENTRALE_BOLD__",centrale_bold).replace("__CENTRALE_LIGHT__",centrale_light)
st.markdown(brand_css,unsafe_allow_html=True)

def require_password() -> None:
    """Protect the public application with a password stored outside GitHub."""
    expected = get_secret("APP_PASSWORD")
    if not expected:
        return
    if st.session_state.get("authenticated"):
        return
    st.markdown('<div class="ampfyca-hero"><div class="ampfyca-kicker">inteligência de comunicação</div><div class="ampfyca-name">AMPFY ESCUTA</div><div class="ampfyca-tagline">escuta, encontra, entende</div></div>',unsafe_allow_html=True)
    st.caption("Acesso protegido")
    supplied = st.text_input("Senha", type="password")
    if st.button("Entrar", type="primary"):
        if hmac.compare_digest(supplied, expected):
            st.session_state.authenticated = True
            st.rerun()
        st.error("Senha incorreta.")
    st.stop()

require_password()

youtube_key=get_secret("YOUTUBE_API_KEY")
x_token=get_secret("X_BEARER_TOKEN")
tiktok_token=get_secret("TIKTOK_RESEARCH_TOKEN")
apify_token=get_secret("APIFY_TOKEN")
instagram_actor=get_secret("APIFY_INSTAGRAM_ACTOR_ID")
tiktok_actor=get_secret("APIFY_TIKTOK_ACTOR_ID")
openai_key=get_secret("OPENAI_API_KEY")
refetcher_key=get_secret("REFETCHER_API_KEY")

connector_status={
    "Google News": (True,"Pronto sem credencial"),
    "YouTube": (bool(youtube_key),"Pronto" if youtube_key else "Falta chave da API do YouTube"),
    "X": (bool(x_token),"Credencial presente, pode exigir saldo" if x_token else "Falta credencial e pode exigir saldo"),
    "TikTok Research": (bool(tiktok_token),"Credencial presente" if tiktok_token else "Exige aprovação do TikTok"),
    "Instagram com Apify": (bool(apify_token and instagram_actor),"Pronto, pode consumir créditos" if apify_token and instagram_actor else "Faltam credencial e coletor da Apify"),
    "TikTok com Apify": (bool(apify_token and tiktok_actor),"Pronto, pode consumir créditos" if apify_token and tiktok_actor else "Faltam credencial e coletor da Apify"),
    "Redes sociais com Refetcher": (bool(refetcher_key),"Pronto, usa crédito pré-pago" if refetcher_key else "Falta chave gratuita da Refetcher"),
}
available_platforms=[name for name,(ready,_) in connector_status.items() if ready]

st.markdown('<div class="ampfyca-hero"><div class="ampfyca-kicker">inteligência de comunicação</div><div class="ampfyca-name">AMPFY ESCUTA</div><div class="ampfyca-tagline">escuta, encontra, entende</div></div>',unsafe_allow_html=True)
st.caption("Notícias, vídeos e redes sociais em uma leitura só")

DEPTH={"Quick":100,"Standard":500,"Deep":1500,"Exhaustive":5000}

with st.sidebar:
    if get_secret("APP_PASSWORD") and st.button("Sair da sessão",use_container_width=True):
        st.session_state.clear()
        st.rerun()
    with st.expander("Disponibilidade dos conectores"):
        for name,(ready,message) in connector_status.items():
            icon="✅" if ready else "🔒"
            st.write(f"{icon} **{name}:** {message}")
        ai_icon="✅" if openai_key else "🔒"
        ai_message="Pronta, pode gerar cobrança" if openai_key else "Falta chave da OpenAI"
        st.write(f"{ai_icon} **Inteligência artificial:** {ai_message}")
    st.header("Pesquisa")
    query=st.text_area("Marca, tema ou pesquisa",value='CVC OR "CVC Viagens"')
    brands_raw=st.text_input("Marcas analisadas",value="CVC")
    competitors=st.text_input("Concorrentes",placeholder="Decolar, LATAM")
    aliases=st.text_area("Variações, campanhas e hashtags",placeholder="CVC Viagens, #CVC, nome da campanha")
    social_urls=st.text_area(
        "Endereços de redes sociais",
        placeholder="Cole 1 endereço público por linha para Instagram, TikTok, Facebook, X ou YouTube",
        help="A Refetcher coleta perfis, publicações e vídeos conhecidos. Ela não pesquisa menções por palavra-chave.",
    )
    start=st.date_input("Início",date.today()-timedelta(days=7))
    end=st.date_input("Fim",date.today())
    depth=st.selectbox("Profundidade",list(DEPTH),index=1)
    custom_limit=st.number_input("Teto por plataforma",10,50,min(50,DEPTH[depth]),10,help="Limite de segurança para preservar a cota gratuita do YouTube.")
    platforms=st.multiselect(
        "Plataformas",
        available_platforms,
        default=[name for name in ["Google News","YouTube"] if name in available_platforms],
        help="Google News e YouTube usam as opções gratuitas configuradas. X e Apify podem consumir saldo.",
    )
    st.divider()
    use_query_ai=st.checkbox("Inteligência artificial: expandir pesquisas",value=False,disabled=not openai_key,help="Pode gerar cobrança da OpenAI quando uma chave estiver configurada.")
    use_enrichment=st.checkbox("Inteligência artificial: classificar conteúdos",value=False,disabled=not openai_key,help="Desligado por padrão para manter custo zero. A classificação heurística continua disponível.")
    x_full=st.checkbox("X: usar arquivo completo",value=False,disabled=not x_token)
    run=st.button("Escutar agora",type="primary",use_container_width=True)

st.info("Modo custo zero ativo: Google News e YouTube estão prontos. X, Apify, TikTok Research e OpenAI permanecem opcionais e desmarcados.")

paid_selected=[p for p in platforms if p in {"X","Instagram com Apify","TikTok com Apify","Redes sociais com Refetcher"}]
if paid_selected:
    st.warning("Atenção: a seleção atual inclui fontes que podem consumir saldo. A Refetcher usa primeiro o crédito gratuito disponível.")

if run:
    if not platforms:
        st.error("Selecione pelo menos 1 plataforma disponível.")
        st.stop()
    limit=int(custom_limit)
    brands=[x.strip() for x in re.split(r"[,;\n]+",brands_raw+","+competitors) if x.strip()]
    queries=build_queries(query,aliases=aliases,competitors=competitors,use_ai=use_query_ai,max_queries=2)
    per_query=max(10,limit//max(1,len(queries)))
    request_keys={f"{q}|{start}|{end}|{per_query}" for q in queries}
    previous_keys=st.session_state.get("youtube_request_keys",set())
    new_keys=request_keys-previous_keys if "YouTube" in platforms else set()
    youtube_units=100*len(new_keys)*math.ceil(per_query/50)
    session_units=st.session_state.get("youtube_units",0)
    if session_units+youtube_units > 1000:
        st.error("Limite de segurança do YouTube atingido nesta sessão. Abra uma nova sessão somente se a pesquisa for necessária.")
        st.stop()
    st.session_state.youtube_units=session_units+youtube_units
    st.session_state.youtube_request_keys=previous_keys|new_keys
    st.subheader("Queries utilizadas")
    st.code("\n".join(queries),language="text")
    frames=[]; errors=[]
    refetcher_urls=[value.strip() for value in social_urls.splitlines() if value.strip()]
    if len(refetcher_urls) > 10:
        st.error("A Refetcher aceita no máximo 10 endereços por pesquisa neste aplicativo.")
        st.stop()
    start_iso=f"{start.isoformat()}T00:00:00Z"; end_iso=f"{(end+timedelta(days=1)).isoformat()}T00:00:00Z"
    if "YouTube" in platforms:
        st.caption(f"Consumo estimado do YouTube nesta sessão: {st.session_state.youtube_units} de 1.000 unidades.")
    with st.status("Coletando…",expanded=True) as status:
        for qi,q in enumerate(queries,1):
            st.write(f"Query {qi}/{len(queries)}: {q}")
            if "Google News" in platforms:
                try: frames.append(collect_google_news_cached(q,per_query))
                except Exception as e: errors.append(f"Google News / {q}: {e}")
            if "YouTube" in platforms:
                try: frames.append(collect_youtube_cached(q,start_iso,end_iso,per_query,youtube_key))
                except Exception as e: errors.append(f"YouTube / {q}: {e}")
            if "X" in platforms:
                try: frames.append(x_api.collect(q,get_secret("X_BEARER_TOKEN"),start_iso,end_iso,per_query,x_full))
                except Exception as e: errors.append(f"X / {q}: {e}")
            if "TikTok Research" in platforms:
                try: frames.append(tiktok_research.collect(q,get_secret("TIKTOK_RESEARCH_TOKEN"),start.isoformat(),end.isoformat(),per_query))
                except Exception as e: errors.append(f"TikTok Research / {q}: {e}")
            if "Instagram com Apify" in platforms:
                try:
                    items=apify_generic.run_actor(instagram_actor,apify_token,{"search":q,"maxItems":per_query})
                    frames.append(apify_generic.normalize(items,"instagram",q))
                except Exception as e: errors.append(f"Instagram/Apify / {q}: {e}")
            if "TikTok com Apify" in platforms:
                try:
                    items=apify_generic.run_actor(tiktok_actor,apify_token,{"search":q,"maxItems":per_query})
                    frames.append(apify_generic.normalize(items,"tiktok",q))
                except Exception as e: errors.append(f"TikTok/Apify / {q}: {e}")
        if "Redes sociais com Refetcher" in platforms:
            if not refetcher_urls:
                errors.append("Refetcher: cole pelo menos 1 endereço público de rede social.")
            else:
                try: frames.append(refetcher.collect(refetcher_urls,refetcher_key))
                except Exception as e: errors.append(f"Refetcher: {e}")
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

    tabs=st.tabs(["Visão geral","Voz e temas","Picos","Conteúdos","Criadores","Base","Relatório"])
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
            excel_safe(df).to_excel(w,index=False,sheet_name="data")
            excel_safe(share_of_voice(df)).to_excel(w,index=False,sheet_name="share_of_voice")
            excel_safe(topic_table(df)).to_excel(w,index=False,sheet_name="topics")
            excel_safe(sentiment_table(df)).to_excel(w,index=False,sheet_name="sentiment")
            excel_safe(detect_peaks(df)).to_excel(w,index=False,sheet_name="peaks")
            excel_safe(top_content(df,100)).to_excel(w,index=False,sheet_name="top_content")
            excel_safe(top_creators(df,100)).to_excel(w,index=False,sheet_name="top_creators")
        st.download_button("Baixar Excel completo",bio.getvalue(),"communication_intelligence.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with tabs[6]:
        title=f"Communication Intelligence — {brands_raw or query} — {start} a {end}"
        report=generate_report(df,title,use_ai=use_enrichment)
        st.markdown(report)
        st.download_button("Baixar relatório Markdown",report.encode("utf-8"),"communication_intelligence_report.md","text/markdown")
