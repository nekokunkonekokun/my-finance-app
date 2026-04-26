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
st.title("Dual Logic Mission Control")

# 1. データ取得と計算
data = yf.download(ticker_sym, period=period, interval=interval, auto_adjust=True)
if data.empty:
    st.error("データの取得に失敗しました。")
    st.stop()

if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)

df = data.copy().dropna(subset=['Close']).reset_index()

# 指標計算 (全データで行うことで前日の値を引き継ぐ)
df['MA25'] = df['Close'].rolling(window=ma_window).mean()
df['Bias'] = (df['Close'] - df['MA25']) / df['MA25'] * 100
df['Bias_Mean'] = df['Bias'].rolling(window=std_window).mean()
df['Bias_Std'] = df['Bias'].rolling(window=std_window).std()
df['T_Score'] = ((df['Bias'] - df['Bias_Mean']) / df['Bias_Std']) * 10 + 50
df['Velocity'] = df['Close'].diff()

df['Inertia_UP'] = df['Velocity'] >= INERTIA_THRESHOLD
df['Inertia_DOWN'] = df['Velocity'] <= -INERTIA_THRESHOLD
df['Short_Signal'] = (df['T_Score'] >= T_SCORE_OVERHEAT) & (df['Velocity'].shift(1) > 300) & (df['Velocity'] < VELOCITY_FADE)

# 直近150本（約3日分強）を抽出して連続性を確保
df_plot = df.tail(150).copy().reset_index(drop=True)
latest = df_plot.iloc[-1]

# --- 短縮時刻ラベル関数の定義 ---
def format_short_label(dt):
    h = dt.hour
    m = dt.minute
    return f"{h}{3 if m==30 else ''}"

# 2. 視覚化セクション
plt.rcdefaults() 
plt.rcParams['figure.facecolor'] = 'white'

# 【Chart 1: Long position】
fig1, (ax1_1, ax1_2) = plt.subplots(2, 1, figsize=(16, 10), sharex=True, gridspec_kw={'height_ratios': [2, 1]})
fig1.patch.set_facecolor('white')

# 価格とMA
ax1_1.plot(df_plot.index, df_plot['Close'], color='black', linewidth=2, label='Price')
ax1_1.plot(df_plot.index, df_plot['MA25'], color='orange', linewidth=1.5, linestyle='--', label='MA25')

# 慣性ドット
up_idx = df_plot[df_plot['Inertia_UP']].index
ax1_1.scatter(up_idx, df_plot.loc[up_idx, 'Close'], color='red', s=200, edgecolors='black', zorder=5, label='Inertia UP')
down_idx = df_plot[df_plot['Inertia_DOWN']].index
ax1_1.scatter(down_idx, df_plot.loc[down_idx, 'Close'], color='blue', s=200, edgecolors='black', zorder=5, label='Inertia DOWN')

ax1_1.set_title("1. Long position: Inertia & Deviation Grid", fontsize=18, fontweight='bold')
ax1_1.grid(True, color='gray', alpha=0.2)
ax1_1.yaxis.set_major_formatter(mticker.StrMethodFormatter('{x:,.0f}'))

# T-Score (サブ)
ax1_2.plot(df_plot.index, df_plot['T_Score'], color='darkviolet', linewidth=2)
ax1_2.axhline(y=50, color='gray', linestyle='-', alpha=0.5)
ax1_2.set_ylim(20, 80)
ax1_2.grid(True, color='gray', alpha=0.2)

# 【Chart 2: Short position】
fig2, ax2 = plt.subplots(figsize=(16, 6))
fig2.patch.set_facecolor('white')
ax2.plot(df_plot.index, df_plot['T_Score'], color='darkviolet', linewidth=2.5)
ax2.axhline(y=T_SCORE_OVERHEAT, color='crimson', linestyle='--', linewidth=2, label='Overheat (75)') # 偏差値破線
ax2.fill_between(df_plot.index, T_SCORE_OVERHEAT, 95, color='crimson', alpha=0.1) # 警告ゾーン塗り

# スナイパーシグナル
short_idx = df_plot[df_plot['Short_Signal']].index
ax2.scatter(short_idx, df_plot.loc[short_idx, 'T_Score'], color='blue', s=400, marker='v', edgecolors='white', zorder=10)

ax2.set_title("2. Short position: Gravity Sniper Scope", fontsize=18, fontweight='bold', color='darkred')
ax2.set_ylim(20, 95)
ax2.grid(True, color='gray', alpha=0.2)

# --- X軸ラベルの共通設定（短縮表記） ---
tick_spacing = 6 # 3時間おき
tick_indices = df_plot.index[::tick_spacing]
tick_labels = [format_short_label(df_plot.loc[i, 'Datetime']) for i in tick_indices]

for ax in [ax1_2, ax2]:
    ax.set_xticks(tick_indices)
    ax.set_xticklabels(tick_labels, fontsize=10)

st.pyplot(fig1)
st.pyplot(fig2)

# 3. ミッションパネル
col1, col2 = st.columns(2)
with col1:
    bull_status = "CRUISING"
    if latest['Velocity'] >= INERTIA_THRESHOLD: bull_status = "!!! RED INERTIA !!!"
    elif latest['Velocity'] <= -INERTIA_THRESHOLD: bull_status = "!!! BLUE INERTIA !!!"
    st.metric("BULL STATUS", bull_status)

with col2:
    bear_status = "CALM"
    if latest['T_Score'] >= T_SCORE_OVERHEAT and latest['Velocity'] < VELOCITY_FADE: bear_status = "!!! SNIPER READY !!!"
    st.metric("BEAR STATUS", bear_status)

st.write(f"**LATEST DATA:** PRICE: ¥{latest['Close']:,.0f} | SPEED: {latest['Velocity']:+.0f} | T-SCORE: {latest['T_Score']:.1f}")
st.success("強気でロング、強気でショート！")

