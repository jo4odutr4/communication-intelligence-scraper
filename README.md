# Communication Intelligence Scraper

Aplicativo Streamlit para coletar, organizar e analisar conteúdos públicos.

## Modo gratuito

O aplicativo inicia com Google News e YouTube selecionados. Google News não exige credencial. YouTube exige uma chave da YouTube Data API.

X, TikTok Research, Apify e OpenAI são conectores opcionais. Eles permanecem desativados por padrão e podem exigir aprovação, saldo ou contratação.

## Execução local

Crie um ambiente virtual Python, instale `requirements.txt`, configure as variáveis necessárias em um arquivo `.env` e execute:

```bash
streamlit run app.py
```

## Publicação no Streamlit Community Cloud

Use `app.py` como arquivo principal. Cadastre `YOUTUBE_API_KEY` na área de segredos do aplicativo. Nunca envie arquivos `.env` ou `secrets.toml` ao GitHub.

## Variáveis reconhecidas

```text
YOUTUBE_API_KEY
X_BEARER_TOKEN
TIKTOK_RESEARCH_TOKEN
APIFY_TOKEN
APIFY_INSTAGRAM_ACTOR_ID
APIFY_TIKTOK_ACTOR_ID
OPENAI_API_KEY
OPENAI_MODEL
```

Somente `YOUTUBE_API_KEY` é necessária para o modo gratuito padrão com YouTube.
