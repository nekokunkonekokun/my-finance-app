import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta

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
    df['CHI_Label'] = df['CHI_DT'].apply(lambda x: f"{x.hour}")
    return df

df = load_data()
if df is None:
    st.stop()

# 直近150本を抽出
df_plot = df.tail(150).copy().reset_index(drop=True)
latest = df_plot.iloc[-1]
now_chi = latest['CHI_DT']

# --- パネル表示（スクロールの起点） ---
st.subheader("Mission Control Panel")
m1, m2, m3 = st.columns(3)
m1.metric("PRICE", f"¥{latest['Close']:,.0f}", f"{latest['Velocity']:+.0f}")
m2.metric("T-SCORE", f"{latest['T_Score']:.1f}")
# 最終取得時刻を大きく表示
m3.metric("LAST UPDATE (CHI)", now_chi.strftime('%H:%M'))

# --- X軸ラベル設定（2時間おき） ---
tick_interval = 4
tick_idx = df_plot.index[::tick_interval]
tick_lab = [df_plot.loc[i, 'CHI_Label'] for i in tick_idx]

# --- Chart 1: Long position（縦幅を大きく確保） ---
st.subheader("1. Long position: Inertia & Deviation Grid")
fig1, (ax1_1, ax1_2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [2, 1]})
plt.subplots_adjust(hspace=0.2, bottom=0.1)

ax1_1.plot(df_plot.index, df_plot['Close'], color='black', linewidth=2.5)
ax1_1.plot(df_plot.index, df_plot['MA25'], color='orange', linestyle='--', alpha=0.8)
ax1_1.grid(True, alpha=0.2)

ax1_2.plot(df_plot.index, df_plot['T_Score'], color='darkviolet', linewidth=2)
ax1_2.axhline(70, color='red', alpha=0.3)
ax1_2.axhline(30, color='green', alpha=0.3)
ax1_2.set_xticks(tick_idx)
ax1_2.set_xticklabels(tick_lab, fontsize=11, fontweight='bold')
ax1_2.grid(True, axis='x', alpha=0.2)
st.pyplot(fig1)

# --- Chart 2: Short position（スクロールして見る） ---
st.subheader("2. Short position: Gravity Sniper Scope")
fig2, ax2 = plt.subplots(figsize=(14, 6))
plt.subplots_adjust(bottom=0.15)
ax2.plot(df_plot.index, df_plot['T_Score'], color='darkviolet', linewidth=2.5)
ax2.axhline(y=T_SCORE_OVERHEAT, color='crimson', linestyle='--', linewidth=2)
ax2.scatter(df_plot[df_plot['Short_Signal']].index, df_plot[df_plot['Short_Signal']]['T_Score'], color='blue', s=300, marker='v', zorder=5)

ax2.set_xticks(tick_idx)
ax2.set_xticklabels(tick_lab, fontsize=11, fontweight='bold')
ax2.grid(True, axis='x', alpha=0.2)
st.pyplot(fig2)

st.success(f"Final Data Point: Chicago Time {now_chi.hour}:{now_chi.minute:02d}")
