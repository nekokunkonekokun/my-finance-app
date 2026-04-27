import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from datetime import timedelta

# --- Configuration ---
ticker_sym = "NIY=F"
interval = "30m"
period = "1mo"
ma_window = 25
std_window = 160
INERTIA_THRESHOLD = 500
T_SCORE_OVERHEAT = 75
VELOCITY_FADE = 100

st.set_page_config(layout="wide")
st.title("🚀 Dual Logic Mission Control")

# 1. データ取得と計算
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
    df['Inertia_UP'] = df['Velocity'] >= INERTIA_THRESHOLD
    df['Inertia_DOWN'] = df['Velocity'] <= -INERTIA_THRESHOLD
    df['Short_Signal'] = (df['T_Score'] >= T_SCORE_OVERHEAT) & (df['Velocity'].shift(1) > 300) & (df['Velocity'] < VELOCITY_FADE)

    # 【重要】シカゴ時間ラベルの作成 (JST-14h)
    df['CHI_DT'] = df['Datetime'] - timedelta(hours=14)
    df['CHI_Label'] = df['CHI_DT'].apply(lambda x: f"{x.hour}{x.minute // 10}")
    
    return df

df = load_data()
if df is None:
    st.error("データの取得に失敗しました。")
    st.stop()

# 直近2日間分を抽出（reset_indexで土日の空白を詰める）
df_plot = df[df['Datetime'] >= (df['Datetime'].max() - timedelta(days=2))].copy().reset_index(drop=True)
latest = df_plot.iloc[-1]

# --- 2. 統合ミッションパネル ---
st.subheader("Mission Control Panel")
m1, m2, m3 = st.columns(3)
m1.metric("PRICE", f"¥{latest['Close']:,.0f}", f"{latest['Velocity']:+.0f}")
m2.metric("T-SCORE", f"{latest['T_Score']:.1f}")
m3.write(f"**CHI TIME:** {latest['CHI_DT'].strftime('%H:%M')} (Day: {latest['CHI_DT'].day})")

# --- 3. 視覚化セクション ---
# X軸ラベルの設定（2時間おき＝4プロットごと）
tick_interval = 4
tick_idx = df_plot.index[::tick_interval]
tick_lab = [str(df_plot.loc[i, 'CHI_Label']) for i in tick_idx]

# Chart 1: Long position
fig1, (ax1_1, ax1_2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [2, 1]})
plt.subplots_adjust(hspace=0.05)

# 上段: 価格とMA25
ax1_1.plot(df_plot.index, df_plot['Close'], color='black', linewidth=2)
ax1_1.plot(df_plot.index, df_plot['MA25'], color='orange', linestyle='--', alpha=0.7)
ax1_1.scatter(df_plot[df_plot['Inertia_UP']].index, df_plot[df_plot['Inertia_UP']]['Close'], color='red', s=100, zorder=5)
ax1_1.scatter(df_plot[df_plot['Inertia_DOWN']].index, df_plot[df_plot['Inertia_DOWN']]['Close'], color='blue', s=100, zorder=5)
ax1_1.set_xticks(tick_idx)
ax1_1.set_xticklabels([]) # 上段のラベルは非表示
ax1_1.grid(True, alpha=0.2)

# 下段: T-Score
ax1_2.plot(df_plot.index, df_plot['T_Score'], color='darkviolet', linewidth=2)
ax1_2.axhline(70, color='red', alpha=0.3); ax1_2.axhline(30, color='green', alpha=0.3)
ax1_2.set_xticks(tick_idx)
ax1_2.set_xticklabels(tick_lab, fontsize=9)
ax1_2.grid(True, axis='x', alpha=0.2)
st.pyplot(fig1)

# Chart 2: Short position
fig2, ax2 = plt.subplots(figsize=(12, 5))
ax2.plot(df_plot.index, df_plot['T_Score'], color='darkviolet', linewidth=2)
ax2.axhline(y=T_SCORE_OVERHEAT, color='crimson', linestyle='--', linewidth=2)
ax2.scatter(df_plot[df_plot['Short_Signal']].index, df_plot[df_plot['Short_Signal']]['T_Score'], color='blue', s=200, marker='v', zorder=5)
ax2.set_xticks(tick_idx)
ax2.set_xticklabels(tick_lab, fontsize=9)
ax2.grid(True, axis='x', alpha=0.2)
st.pyplot(fig2)

st.caption("私の回答にはハルシネーションが含まれている可能性があります。")
