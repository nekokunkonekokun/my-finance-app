import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm
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

st.title("Dual Logic Mission Control")

# 1. データ取得
data = yf.download(ticker_sym, period=period, interval=interval, auto_adjust=True)
if data.empty:
    st.error("データの取得に失敗しました。")
    st.stop()

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

df['Inertia_UP'] = df['Velocity'] >= INERTIA_THRESHOLD
df['Inertia_DOWN'] = df['Velocity'] <= -INERTIA_THRESHOLD
df['Short_Signal'] = (df['T_Score'] >= T_SCORE_OVERHEAT) & (df['Velocity'].shift(1) > 300) & (df['Velocity'] < VELOCITY_FADE)

last_time = df['Datetime'].max()
start_time_2d = last_time - timedelta(days=2)
df_plot = df[df['Datetime'] >= start_time_2d].copy().reset_index(drop=True)
latest = df_plot.iloc[-1]

# --- 2. 視覚化セクション ---

# 【1枚目】
fig1, (ax1_1, ax1_2) = plt.subplots(2, 1, figsize=(16, 12), sharex=True, gridspec_kw={'height_ratios': [2, 1]})
ax1_1.plot(df_plot.index, df_plot['Close'], color='black', linewidth=2.5, label='Price')
ax1_1.plot(df_plot.index, df_plot['MA25'], color='orange', linestyle='--', alpha=0.7, label='MA25')
ax1_1.scatter(df_plot[df_plot['Inertia_UP']].index, df_plot[df_plot['Inertia_UP']]['Close'], color='red', s=300, edgecolors='black', zorder=5)
ax1_1.scatter(df_plot[df_plot['Inertia_DOWN']].index, df_plot[df_plot['Inertia_DOWN']]['Close'], color='blue', s=300, edgecolors='black', zorder=5)
ax1_1.set_title("1. Long position: Inertia & Deviation Grid", fontsize=24, fontweight='bold')
ax1_1.yaxis.set_major_formatter(mticker.StrMethodFormatter('{x:,.0f}'))
ax1_1.grid(True, alpha=0.2)
ax1_2.plot(df_plot.index, df_plot['T_Score'], color='darkviolet', linewidth=2.5)
ax1_2.set_ylim(20, 80)
ax1_2.grid(axis='y', which='major', color='gray', linestyle='-', alpha=0.3)
st.pyplot(fig1)

# 【2枚目】
fig2, ax2 = plt.subplots(figsize=(16, 9))
ax2.plot(df_plot.index, df_plot['T_Score'], color='darkviolet', linewidth=3)
ax2.axhline(y=T_SCORE_OVERHEAT, color='crimson', linestyle='--', linewidth=3, label='Overheat Target (75)')
ax2.scatter(df_plot[df_plot['Short_Signal']].index, df_plot[df_plot['Short_Signal']]['T_Score'], color='blue', s=600, marker='v', edgecolors='white', zorder=10)
ax2.set_title("2. Short position: Gravity Sniper Scope", fontsize=24, fontweight='bold', color='darkred')
ax2.set_ylim(20, 95)
ax2.grid(True, alpha=0.3)
st.pyplot(fig2)

# 【3枚目：ミッションパネル】
bull_status = "CRUISING SPEED"
if latest['Velocity'] >= INERTIA_THRESHOLD: bull_status = "!!! RED INERTIA (UP) !!!"
elif latest['Velocity'] <= -INERTIA_THRESHOLD: bull_status = "!!! BLUE INERTIA (DOWN) !!!"

bear_status = "STAY CALM"
if latest['T_Score'] >= T_SCORE_OVERHEAT and latest['Velocity'] < VELOCITY_FADE: bear_status = "!!! SNIPER SHORT READY !!!"

st.info(f"STATUS: {bull_status} / {bear_status}")
st.write(f"PRICE: ¥{latest['Close']:,.0f} | SPEED: {latest['Velocity']:+.0f} | T-SCORE: {latest['T_Score']:.1f}")
st.success("強気でロング、強気でショート！頑張れ！")
