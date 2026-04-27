import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta
import pytz

st.set_page_config(layout="wide")

# --- Configuration ---
ticker_sym = "NIY=F"
interval = "30m"
period = "1mo"
ma_window = 25
std_window = 160
T_SCORE_OVERHEAT = 75

st.title("🚀 Dual Logic: Mission Control [Long&Short W Mode]")

@st.cache_data(ttl=60) # 更新頻度を上げて幽霊を追い出す
def load_data():
    # データ取得
    data = yf.download(ticker_sym, period=period, interval=interval, auto_adjust=True)
    if data.empty: return None
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    df = data.copy().dropna(subset=['Close']).reset_index()
    
    # --- 重要：除霊ロジック（日本時間とシカゴ時間の同期） ---
    # Datetime列を日本時間(JST)として確定
    if df['Datetime'].dt.tz is None:
        df['Datetime'] = df['Datetime'].dt.tz_localize('UTC').dt.tz_convert('Asia/Tokyo')
    else:
        df['Datetime'] = df['Datetime'].dt.tz_convert('Asia/Tokyo')

    # シカゴ時間はJSTから一律14時間引く（サマータイム対応）
    df['CHI_DT'] = df['Datetime'] - timedelta(hours=14)
    
    # 指標計算
    df['MA25'] = df['Close'].rolling(window=ma_window).mean()
    df['Bias'] = (df['Close'] - df['MA25']) / df['MA25'] * 100
    df['Bias_Mean'] = df['Bias'].rolling(window=std_window).mean()
    df['Bias_Std'] = df['Bias'].rolling(window=std_window).std()
    df['T_Score'] = ((df['Bias'] - df['Bias_Mean']) / df['Bias_Std']) * 10 + 50
    df['Velocity'] = df['Close'].diff()
    
    df['Short_Signal'] = (df['T_Score'] >= T_SCORE_OVERHEAT) & (df['Velocity'].shift(1) > 300) & (df['Velocity'] < 100)
    
    return df

df = load_data()
if df is None:
    st.error("Data fetch failed. The market might be in a void.")
    st.stop()

# 直近150本を抽出
df_plot = df.tail(150).copy().reset_index(drop=True)
latest = df_plot.iloc[-1]
jst_now = latest['Datetime']
chi_now = latest['CHI_DT']

# --- パネル表示（現在地を明確にする） ---
st.subheader("Mission Control Panel")
m1, m2, m3 = st.columns(3)
with m1:
    st.metric("PRICE", f"¥{latest['Close']:,.0f}", f"{latest['Velocity']:+.0f}")
with m2:
    st.metric("T-SCORE", f"{latest['T_Score']:.1f}")
with m3:
    # ここで日本時間とシカゴ時間を並べて「今」を特定
    st.write(f"🇯🇵 **JST:** {jst_now.strftime('%m/%d %H:%M')}")
    st.write(f"🇺🇸 **CHI:** {chi_now.strftime('%m/%d %H:%M')}")

# --- 目盛り作成（4本＝2時間おきに強制） ---
tick_indices = df_plot.index[::4]
# ラベルにはシカゴ時間の「時」だけを入れる
tick_labels = [df_plot.loc[i, 'CHI_DT'].strftime('%H') for i in tick_indices]

# --- Chart 1: Long position（スクロール前提の巨大化） ---
st.subheader("1. Long position: Inertia & Deviation Grid")
fig1, (ax1_1, ax1_2) = plt.subplots(2, 1, figsize=(14, 12), gridspec_kw={'height_ratios': [2, 1]})
plt.subplots_adjust(hspace=0.25, bottom=0.15)

ax1_1.plot(df_plot.index, df_plot['Close'], color='black', linewidth=2.5)
ax1_1.plot(df_plot.index, df_plot['MA25'], color='orange', linestyle='--', alpha=0.8)
ax1_1.grid(True, alpha=0.2)

ax1_2.plot(df_plot.index, df_plot['T_Score'], color='darkviolet', linewidth=2)
ax1_2.axhline(70, color='red', alpha=0.3)
ax1_2.axhline(30, color='green', alpha=0.3)

# X軸除霊表示：上がIndex（座標）、下がCHI（時刻）
ax1_2.set_xticks(tick_indices)
ax1_2.set_xticklabels(tick_labels, fontsize=11, fontweight='bold')
ax1_2.set_xlabel("--- Chicago Hour (2h Interval) ---", fontsize=10, color='gray')
ax1_2.grid(True, axis='x', alpha=0.2)

st.pyplot(fig1)

# --- Chart 2: Short position ---
st.subheader("2. Short position: Gravity Sniper Scope")
fig2, ax2 = plt.subplots(figsize=(14, 7))
plt.subplots_adjust(bottom=0.2)

ax2.plot(df_plot.index, df_plot['T_Score'], color='darkviolet', linewidth=2.5)
ax2.axhline(y=T_SCORE_OVERHEAT, color='crimson', linestyle='--', linewidth=2.1)
ax2.scatter(df_plot[df_plot['Short_Signal']].index, df_plot[df_plot['Short_Signal']]['T_Score'], 
            color='blue', s=400, marker='v', zorder=5, label='Sniper Shot')

ax2.set_xticks(tick_indices)
ax2.set_xticklabels(tick_labels, fontsize=11, fontweight='bold')
ax2.grid(True, axis='x', alpha=0.2)

st.pyplot(fig2)

st.info(f"Synchronized: All systems showing data up to CHI {chi_now.strftime('%H:%M')}")
