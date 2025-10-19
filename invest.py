
# prerequisites: pip install streamlit yfinance newspaper3k

import streamlit as st
import yfinance as yf
import requests
from newspaper import Article

import json
import datetime


# Google Gemini API Key
GEMINI_API_KEY = "AIzaSyAWCFqEi2s977vs-dCHZATNT608sKXb7bk"

def fetch_price_history(ticker, period="6mo", interval="1d"):
    df = yf.download(ticker, period=period, interval=interval)
    return df

def fetch_news_headlines(keyword, api_key="69651ce6aec84ed28b9aacfb28d9e59d", page=1):
    url = ("https://newsapi.org/v2/everything?"
           f"q={keyword}&language=en&sortBy=publishedAt&pageSize=5&page={page}&apiKey={api_key}")
    r = requests.get(url).json()
    articles = r.get("articles", [])
    return articles

def summarize_article(url):
    try:
        art = Article(url)
        art.download(); art.parse(); art.nlp()
        return art.summary
    except:
        return ""

def prepare_prompt(ticker, price_df, news_summaries):
    latest = float(price_df.tail(1)["Close"].iloc[0])
    returns_30 = float((price_df["Close"].iloc[-1] / price_df["Close"].iloc[0] - 1) * 100)
    prompt = f"""
You are a financial analyst assistant. Provide a concise investment recommendation for ticker {ticker}.
Latest close: {latest:.2f}. 6-month return: {returns_30:.2f}%.
News summaries:
{news_summaries if isinstance(news_summaries, str) else str(news_summaries)}

Please answer in Traditional Chinese: give (1) short recommendation: BUY / SELL / HOLD, (2) top 3 reasons, (3) main risks, (4) confidence level 0-100.
Be explicit about sources and say "This is not financial advice."
"""
    return prompt

def call_llm(prompt):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=" + GEMINI_API_KEY
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature": 0.0,
            "topK": 1,
            "topP": 1.0,
            "maxOutputTokens": 2048
        }
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    print(response.text)  # 新增這行，檢查 API 回傳內容
    if response.status_code == 200:
        result = response.json()
        try:
            # 檢查 parts 是否存在
            parts = result["candidates"][0]["content"].get("parts")
            if parts and "text" in parts[0]:
                return parts[0]["text"]
            else:
                return "Gemini API 沒有回傳內容，請檢查 token 設定或 API 狀態。"
        except Exception:
            return "Gemini API response parsing error."
    else:
        return f"Gemini API error: {response.status_code} {response.text}"

def run_agent_once(ticker):
    prices = fetch_price_history(ticker)
    news = fetch_news_headlines(ticker)
    summaries = []
    for a in news:
        s = summarize_article(a["url"])
        summaries.append(f"- {a['source']['name']}: {a['title']} -> {s}")
    news_text = "\n".join(summaries)
    prompt = prepare_prompt(ticker, prices, news_text)
    ans = call_llm(prompt)
    print(ans)


# Streamlit 介面
st.title("AI 投資分析助理")
st.markdown("""
請輸入你有興趣的公司股票代碼（如 NVDA、AAPL、TSLA），系統會自動抓取股價與新聞，並用 Gemini AI 生成投資建議。
""")

with st.form(key='stock_form'):
    ticker = st.text_input("股票代碼", "NVDA").strip().upper()
    run_btn = st.form_submit_button("分析")

if run_btn and ticker:
    with st.spinner("分析中，請稍候..."):
        try:
            prices = fetch_price_history(ticker)
            news = fetch_news_headlines(ticker)
            summaries = []
            for a in news:
                s = summarize_article(a["url"])
                summaries.append(f"- {a['source']['name']}: {a['title']} -> {s}")
            news_text = "\n".join(summaries)
            prompt = prepare_prompt(ticker, prices, news_text)
            ans = call_llm(prompt)
            st.markdown(f"### {ticker} 分析結果")
            st.write(ans)
        except Exception as e:
            st.error(f"分析過程出現錯誤：{e}")
