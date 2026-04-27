import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta, datetime

st.set_page_config(layout="wide")

# --- Configuration ---
ticker_sym = "NIY=F"
interval = "30m"
period = "1mo"
ma_window = 25
std_window = 160
T_SCORE_OVERHEAT = 75

st.title("🚀 Dual Logic: Mission Control")

@st.cache_data(ttl=600)
def load_data():
    data = yf.download(ticker_sym, period=period, interval=interval, auto_adjust=True)
    if data.empty: return None
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    df = data.copy().dropna(subset=['Close']).reset_index()
    
    # 指標計算
    df['MA25'] = df['Close'].rolling(window=ma_window).mean()
    df['Bias'] = (df['Close'] - df['MA25']) / df['MA25'] * 100
    df['Bias_Mean'] = df['Bias'].rolling(window=std_window).mean()
    df['Bias_Std'] = df['Bias'].rolling(window=std_window).std()
    df['T_Score'] = ((df['Bias'] - df['Bias_Mean']) / df['Bias_Std']) * 10 + 50
    df['Velocity'] = df['Close'].diff()
    
    # シグナル
    df['Short_Signal'] = (df['T_Score'] >= T_SCORE_OVERHEAT) & (df['Velocity'].shift(1) > 300) & (df['Velocity'] < 100)
    
    # シカゴ時間(JST-14h)
    df['CHI_DT'] = df['Datetime'] - timedelta(hours=14)
    return df

df = load_data()
if df is None:
    st.stop()

# 直近150本（約3日分強）を抽出し、欠損を詰めてリセット
df_plot = df.tail(150).copy().reset_index(drop=True)
latest = df_plot.iloc[-1]

# --- 新ロジック：現在時刻から遡る2時間刻みのラベル作成 ---
# 現在のシカゴ時刻
now_chi = latest['CHI_DT']
# 現在時刻を含む「2時間枠」の終点を計算（例：7:48なら9:00）
anchor_hour = ((now_chi.hour // 2) + 1) * 2
anchor_time = now_chi.replace(hour=anchor_hour % 24, minute=0, second=0, microsecond=0)

# 目盛りを打つインデックスを特定（2時間おき＝4本ごと）
tick_indices = []
tick_labels = []

# 右端（最新）から遡って、30分足4本ごとにラベルを貼る
# インデックスはそのまま残し、その直下のラベルだけを指定
for i in range(len(df_plot) - 1, -1, -4):
    dt = df_plot.loc[i, 'CHI_DT']
    # 2時間ごとのキリの良い時間に最も近いインデックスを探す
    if dt.minute == 0 or dt.minute == 30: # 30分足の特性に合わせる
        tick_indices.append(i)
        # ラベル形式：7時なら "7", 9時なら "9"
        tick_labels.append(f"{dt.hour}")

# --- 描画セクション ---
# Chart 1
fig1, (ax1_1, ax1_2) = plt.subplots(2, 1, figsize=(12, 7), gridspec_kw={'height_ratios': [2, 1]})
plt.subplots_adjust(hspace=0.3, bottom=0.15) # 下部にラベル用の余白

ax1_1.plot(df_plot.index, df_plot['Close'], color='black', linewidth=2)
ax1_1.plot(df_plot.index, df_plot['MA25'], color='orange', linestyle='--', alpha=0.7)
ax1_1.grid(True, alpha=0.2)

ax1_2.plot(df_plot.index, df_plot['T_Score'], color='darkviolet')
ax1_2.axhline(70, color='red', alpha=0.3)
ax1_2.axhline(30, color='green', alpha=0.3)

# 【二段表示ロジック】
ax1_2.set_xticks(tick_indices)
# 1段目（Index番号）は自動、2段目（時刻）をその下に手動で添えるイメージ
# ここでは「時刻」を優先表示し、IndexはMatplotlibのデフォルトに任せる設定
ax1_2.set_xticklabels(tick_labels, fontsize=10, fontweight='bold')
ax1_2.set_xlabel("Chicago Time (2h intervals)", fontsize=9, color='gray')
ax1_2.grid(True, axis='x', alpha=0.2)

st.pyplot(fig1)

# Chart 2
fig2, ax2 = plt.subplots(figsize=(12, 4))
plt.subplots_adjust(bottom=0.2)
ax2.plot(df_plot.index, df_plot['T_Score'], color='darkviolet', linewidth=2)
ax2.axhline(y=T_SCORE_OVERHEAT, color='crimson', linestyle='--')
ax2.scatter(df_plot[df_plot['Short_Signal']].index, df_plot[df_plot['Short_Signal']]['T_Score'], color='blue', s=200, marker='v')

ax2.set_xticks(tick_indices)
ax2.set_xticklabels(tick_labels, fontsize=10, fontweight='bold')
ax2.grid(True, axis='x', alpha=0.2)

st.pyplot(fig2)

# パネル表示
st.write(f"**LATEST CHI:** {now_chi.strftime('%H:%M')} | **T-SCORE:** {latest['T_Score']:.1f}")
st.caption("私の回答にはハルシネーションが含まれている可能性があります。")
