import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm
import matplotlib.ticker as mticker
from datetime import timedelta

# --- Configuration (スマホ最適化：完全分離3段司令塔) ---
ticker_sym = "NIY=F"  # 日経225 CME
interval = "30m"
period = "1mo"
ma_window = 25
std_window = 160

# 判定しきい値
INERTIA_THRESHOLD = 500  # 慣性の壁
T_SCORE_OVERHEAT = 75    # 統計的過熱ライン
VELOCITY_FADE = 100       # 速度の減速ライン

# 1. データ取得 & 共通計算
data = yf.download(ticker_sym, period=period, interval=interval, auto_adjust=True)
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

# シグナル判定
df['Inertia_UP'] = df['Velocity'] >= INERTIA_THRESHOLD
df['Inertia_DOWN'] = df['Velocity'] <= -INERTIA_THRESHOLD
df['Short_Signal'] = (df['T_Score'] >= T_SCORE_OVERHEAT) & (df['Velocity'].shift(1) > 300) & (df['Velocity'] < VELOCITY_FADE)

# 表示期間を「直近2日間」に限定
last_time = df['Datetime'].max()
start_time_2d = last_time - timedelta(days=2)
df_plot = df[df['Datetime'] >= start_time_2d].copy().reset_index(drop=True)
latest = df_plot.iloc[-1]

# --- 2. 視覚化セクション：スマホ専用3段独立出力 ---

# 【1枚目：強気・物理慣性チャート（偏差値5刻みグリッド付）】
fig1, (ax1_1, ax1_2) = plt.subplots(2, 1, figsize=(16, 12), sharex=True,
                                     gridspec_kw={'height_ratios': [2, 1]})

ax1_1.plot(df_plot.index, df_plot['Close'], color='black', linewidth=2.5, label='Price')
ax1_1.plot(df_plot.index, df_plot['MA25'], color='orange', linestyle='--', alpha=0.7, label='MA25')
ax1_1.scatter(df_plot[df_plot['Inertia_UP']].index, df_plot[df_plot['Inertia_UP']]['Close'], color='red', s=300, edgecolors='black', zorder=5)
ax1_1.scatter(df_plot[df_plot['Inertia_DOWN']].index, df_plot[df_plot['Inertia_DOWN']]['Close'], color='blue', s=300, edgecolors='black', zorder=5)
ax1_1.set_title("1. Long position: Inertia & Deviation Grid", fontsize=24, fontweight='bold')
ax1_1.yaxis.set_major_formatter(mticker.StrMethodFormatter('{x:,.0f}'))
ax1_1.grid(True, alpha=0.2)
ax1_1.legend(loc='upper left', fontsize=14)

ax1_2.plot(df_plot.index, df_plot['T_Score'], color='darkviolet', linewidth=2.5)
ax1_2.yaxis.set_major_locator(mticker.MultipleLocator(5))
ax1_2.axhline(y=70, color='crimson', linestyle='-', linewidth=1.5, alpha=0.8)
ax1_2.axhline(y=30, color='darkgreen', linestyle='-', linewidth=1.5, alpha=0.8)
ax1_2.fill_between(df_plot.index, 70, 85, color='red', alpha=0.08)
ax1_2.fill_between(df_plot.index, 15, 30, color='green', alpha=0.08)
ax1_2.set_ylabel("T-Score (5-Step Grid)", fontsize=16, fontweight='bold')
ax1_2.set_ylim(20, 80)
ax1_2.grid(axis='y', which='major', color='gray', linestyle='-', alpha=0.3)

plt.tight_layout()
plt.show()

# 【2枚目：弱気・重力スナイパー（偏差値集中型）】
fig2, ax2 = plt.subplots(figsize=(16, 9))
ax2.plot(df_plot.index, df_plot['T_Score'], color='darkviolet', linewidth=3)
ax2.axhline(y=T_SCORE_OVERHEAT, color='crimson', linestyle='--', linewidth=3, label='Overheat Target (75)')
ax2.fill_between(df_plot.index, T_SCORE_OVERHEAT, 95, color='red', alpha=0.2)
ax2.scatter(df_plot[df_plot['Short_Signal']].index, df_plot[df_plot['Short_Signal']]['T_Score'],
            color='blue', s=600, marker='v', edgecolors='white', label='SNIPER READY', zorder=10)
ax2.set_title("2. Short position: Gravity Sniper Scope", fontsize=24, fontweight='bold', color='darkred')
ax2.set_ylabel("T-Score (Focus 75+)", fontsize=16)
ax2.set_ylim(20, 95)
ax2.grid(True, alpha=0.3)
ax2.legend(loc='upper left', fontsize=16)
plt.tight_layout()
plt.show()

# 【3枚目：統合ミッションパネル（強気・弱気のダブル判定）】
fig3, ax3 = plt.subplots(figsize=(16, 10))
ax3.axis('off')

bull_status = "CRUISING SPEED"; bull_adv = "Wait for Inertia."
if latest['Velocity'] >= INERTIA_THRESHOLD: bull_status = "!!! RED INERTIA (UP) !!!"; bull_adv = "MAC POWER! BUY!"
elif latest['Velocity'] <= -INERTIA_THRESHOLD: bull_status = "!!! BLUE INERTIA (DOWN) !!!"; bull_adv = "WATCH OUT! DROP!"

bear_status = "STAY CALM"; bear_adv = "No Target in Scope."
if latest['T_Score'] >= T_SCORE_OVERHEAT and latest['Velocity'] < VELOCITY_FADE:
    bear_status = "!!! SNIPER SHORT READY !!!"; bear_adv = "SHOOT THE GRAVITY!"

report_text = (
    f"--- DUAL LOGIC MISSION CONTROL ---\n\n"
    f" [MARKET DATA]\n"
    f" PRICE: ¥{latest['Close']:,.0f} | SPEED: {latest['Velocity']:+.0f} JPY | T-SCORE: {latest['T_Score']:.1f}\n\n"
    f" ------------------------------------------\n"
    f" [LOGIC-A: BULLISH INERTIA]\n"
    f" STATUS: {bull_status}\n"
    f" ADVICE: {bull_adv}\n\n"
    f" [LOGIC-B: BEARISH SNIPER]\n"
    f" STATUS: {bear_status}\n"
    f" ADVICE: {bear_adv}\n"
    f" ------------------------------------------\n\n"
    f" UPDATE: {latest['Datetime'].strftime('%Y/%m/%d %H:%M')}"
)

ax3.text(0.5, 0.5, report_text, fontsize=30, color='black', family='monospace', fontweight='bold',
         ha='center', va='center', bbox=dict(facecolor='white', edgecolor='navy', alpha=0.95, pad=35))
plt.tight_layout()
plt.show()

print("強気でロング、強気でショート！頑張れ！")
