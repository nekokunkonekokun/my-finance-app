import streamlit as st
import feedparser
import urllib.parse
import time
import re
from datetime import datetime

# --- 設定 ---
SOURCES = ['jp.reuters.com', 'nikkei.com', 'sankei.com']
KEYWORDS = 'ホルムズ海峡 OR 原油 OR 日経平均 OR イラン OR イスラエル'
NIKKEI_THRESHOLD = 5.8
OPINION_MARKERS = ['予想', '予測', '見通し', '目標', 'ターゲット', 'ストラテジスト', '見方', '議論', '焦点', 'コラム', '解説', '強気', '弱気', 'メド', 'シナリオ']

def analyze_headline(title):
    is_opinion = any(marker in title for marker in OPINION_MARKERS)
    if re.search(r'(か|？|\?|恐れ|可能性|へ|か等)$', title):
        is_opinion = True
    num_matches = re.findall(r'(\d+(?:\.\d+)?)万', title)
    for val in num_matches:
        if float(val) >= NIKKEI_THRESHOLD:
            is_opinion = True
            break
    return "【予測/意見】" if is_opinion else "【事実/速報】"

# --- Streamlit 画面構成 ---
st.title("経済・地政学ニュース分析")
st.caption(f"最終更新: {datetime.now().strftime('%Y/%m/%d %H:%M')}")

if st.button('最新ニュースを取得'):
    timestamp = int(time.time())
    
    for site in SOURCES:
        st.subheader(f"--- {site.upper()} ---")
        
        query = f"({KEYWORDS}) site:{site}"
        rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=ja&gl=JP&ceid=JP:ja&nocache={timestamp}"
        
        try:
            feed = feedparser.parse(rss_url)
            if not feed.entries:
                st.write("該当記事なし")
            else:
                for entry in feed.entries[:10]:
                    clean_title = entry.title.rsplit(' - ', 1)[0]
                    label = analyze_headline(clean_title)
                    
                    # 判定ラベルによって色を変えて表示
                    color = "red" if "予測" in label else "blue"
                    st.markdown(f"**:{color}[{label}]** [{clean_title}]({entry.link})")
            
            time.sleep(0.5)
        except Exception as e:
            st.error(f"エラーが発生しました ({site}): {e}")


