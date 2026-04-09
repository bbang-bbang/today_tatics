"""
연도별 (2024 / 2025 / 2026) 승률 상관분석
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

import platform
if platform.system() == 'Windows':
    plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

DB_PATH = 'players.db'
conn = sqlite3.connect(DB_PATH)

df_raw = pd.read_sql_query("""
    SELECT
        event_id, team_id, is_home, result,
        substr(match_date,1,4) as year,
        temperature, humidity, wind_speed,
        rating, goals, total_shots, shots_on_target,
        big_chances_missed, expected_goals,
        accurate_passes_pct, key_passes,
        accurate_long_balls, total_long_balls,
        accurate_crosses, total_crosses,
        successful_dribbles, attempted_dribbles,
        touches, possession_lost,
        tackles, interceptions, clearances,
        duel_won, duel_lost, aerial_won,
        was_fouled, fouls, yellow_cards, red_cards
    FROM match_player_stats
    WHERE result IS NOT NULL
""", conn)

# 경기-팀 단위 집계
agg = df_raw.groupby(['event_id','team_id','is_home','result','year']).agg(
    temperature      = ('temperature','first'),
    humidity         = ('humidity','first'),
    wind_speed       = ('wind_speed','first'),
    avg_rating       = ('rating','mean'),
    goals            = ('goals','sum'),
    total_shots      = ('total_shots','sum'),
    shots_on_target  = ('shots_on_target','sum'),
    big_chances_missed=('big_chances_missed','sum'),
    xg               = ('expected_goals','sum'),
    pass_acc         = ('accurate_passes_pct','mean'),
    key_passes       = ('key_passes','sum'),
    long_ball_acc    = ('accurate_long_balls','sum'),
    total_long_balls = ('total_long_balls','sum'),
    accurate_crosses = ('accurate_crosses','sum'),
    successful_dribbles=('successful_dribbles','sum'),
    touches          = ('touches','sum'),
    possession_lost  = ('possession_lost','sum'),
    tackles          = ('tackles','sum'),
    interceptions    = ('interceptions','sum'),
    clearances       = ('clearances','sum'),
    duel_won         = ('duel_won','sum'),
    duel_lost        = ('duel_lost','sum'),
    aerial_won       = ('aerial_won','sum'),
    was_fouled       = ('was_fouled','sum'),
    fouls            = ('fouls','sum'),
    yellow_cards     = ('yellow_cards','sum'),
).reset_index()

agg['shot_acc']     = agg['shots_on_target'] / agg['total_shots'].replace(0, np.nan)
agg['duel_win_pct'] = agg['duel_won'] / (agg['duel_won'] + agg['duel_lost']).replace(0, np.nan)
agg['long_ball_pct']= agg['long_ball_acc'] / agg['total_long_balls'].replace(0, np.nan)
agg['points']       = agg['result'].map({0:0, 1:1, 2:3})

FEATURES = [
    ('avg_rating',    '평균평점'),
    ('goals',         '득점'),
    ('total_shots',   '슈팅수'),
    ('shots_on_target','유효슈팅'),
    ('shot_acc',      '슈팅정확도'),
    ('big_chances_missed','빅찬스실패'),
    ('xg',            '기대골'),
    ('pass_acc',      '패스정확도'),
    ('key_passes',    '키패스'),
    ('long_ball_pct', '롱볼성공률'),
    ('tackles',       '태클'),
    ('interceptions', '인터셉션'),
    ('clearances',    '클리어런스'),
    ('duel_win_pct',  '듀얼승률'),
    ('aerial_won',    '공중볼승리'),
    ('fouls',         '파울'),
    ('yellow_cards',  '경고'),
    ('temperature',   '기온'),
    ('humidity',      '습도'),
    ('wind_speed',    '풍속'),
    ('is_home',       '홈여부'),
]
feat_cols   = [f for f, _ in FEATURES]
feat_labels = {f: l for f, l in FEATURES}

YEARS = ['2024', '2025', '2026']

# ── 연도별 상관 계산 ──────────────────────────────────────
year_corr = {}   # {year: DataFrame}

for yr in YEARS:
    sub = agg[agg['year'] == yr].copy()
    rows = []
    for col, label in FEATURES:
        s = sub[[col, 'points']].dropna()
        if len(s) < 10:
            rows.append({'label': label, 'col': col, 'r': np.nan, 'p': np.nan, 'n': len(s)})
            continue
        r, p = stats.spearmanr(s[col], s['points'])
        rows.append({'label': label, 'col': col, 'r': round(r, 3), 'p': round(p, 4), 'n': len(s)})
    year_corr[yr] = pd.DataFrame(rows).set_index('col')


# ── 콘솔 출력 ─────────────────────────────────────────────
for yr in YEARS:
    df_yr = agg[agg['year'] == yr]
    n_match = df_yr['event_id'].nunique()
    n_team  = df_yr['team_id'].nunique()
    w = (df_yr['result']==2).sum()
    d = (df_yr['result']==1).sum()
    l = (df_yr['result']==0).sum()
    print(f"\n{'='*55}")
    print(f"{yr}년  |  경기 {n_match}  팀 {n_team}  |  승{w} 무{d} 패{l} (팀-경기 단위)")
    print(f"{'='*55}")

    dc = year_corr[yr].sort_values('r', ascending=False)
    print(f"{'지표':<12} {'r':>7}  {'p':>7}  {'유의':>4}  {'n':>5}")
    print("-"*45)
    for _, row in dc.iterrows():
        sig = 'O' if (not np.isnan(row['p']) and row['p'] < 0.05) else 'X'
        r_str = f"{row['r']:+.3f}" if not np.isnan(row['r']) else '  N/A '
        p_str = f"{row['p']:.4f}" if not np.isnan(row['p']) else '  N/A '
        print(f"{row['label']:<12} {r_str:>7}  {p_str:>7}  {sig:>4}  {int(row['n']):>5}")


# ── 시각화 1: 연도별 상관계수 히트맵 ──────────────────────
pivot = pd.DataFrame({
    yr: year_corr[yr]['r'].reindex([f for f,_ in FEATURES])
    for yr in YEARS
})
pivot.index = [feat_labels[f] for f,_ in FEATURES]

fig, ax = plt.subplots(figsize=(7, 8))
mask = pivot.isna()
sns.heatmap(pivot, annot=True, fmt='.2f', cmap='RdYlGn', center=0,
            vmin=-0.5, vmax=0.5, linewidths=0.5,
            mask=mask, ax=ax, cbar_kws={'label': 'Spearman r'})
ax.set_title('연도별 각 지표와 승점의 상관계수', fontsize=13, fontweight='bold')
ax.set_xlabel('연도')
plt.tight_layout()
plt.savefig('analysis_year_heatmap.png', dpi=150)
plt.close()
print("\n-> analysis_year_heatmap.png 저장")


# ── 시각화 2: 연도별 Top5 지표 비교 바차트 ───────────────
fig, axes = plt.subplots(1, 3, figsize=(15, 6), sharey=False)

for ax, yr in zip(axes, YEARS):
    dc = year_corr[yr].dropna(subset=['r']).sort_values('r', ascending=False)
    top5   = dc.head(5)
    bot3   = dc.tail(3)
    plot_df = pd.concat([top5, bot3])
    colors = ['#2196F3' if r > 0 else '#F44336' for r in plot_df['r']]
    bars = ax.barh(plot_df['label'], plot_df['r'], color=colors, alpha=0.8)
    ax.axvline(0, color='black', linewidth=0.8)
    for bar, (_, row) in zip(bars, plot_df.iterrows()):
        sig = 'O' if (not np.isnan(row['p']) and row['p'] < 0.05) else ''
        x = bar.get_width()
        ax.text(x + (0.005 if x >= 0 else -0.005), bar.get_y() + bar.get_height()/2,
                sig, va='center', ha='left' if x >= 0 else 'right', fontsize=10, color='green')
    n_m = agg[agg['year']==yr]['event_id'].nunique()
    ax.set_title(f'{yr}년 (경기 {n_m})', fontsize=12, fontweight='bold')
    ax.set_xlabel('Spearman r')
    ax.set_xlim(-0.5, 0.6)

plt.suptitle('연도별 상위/하위 상관 지표 (O = p<0.05)', fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig('analysis_year_bars.png', dpi=150)
plt.close()
print("-> analysis_year_bars.png 저장")


# ── 시각화 3: 주요 지표 연도별 추이 (승/무/패 평균) ────────
key_metrics = [
    ('avg_rating', '평균평점'),
    ('goals',      '득점'),
    ('total_shots','슈팅수'),
    ('tackles',    '태클'),
    ('pass_acc',   '패스정확도'),
]

fig, axes = plt.subplots(1, len(key_metrics), figsize=(16, 5))
result_map = {0: '패', 1: '무', 2: '승'}
colors_map = {0: '#F44336', 1: '#FFC107', 2: '#4CAF50'}

for ax, (col, label) in zip(axes, key_metrics):
    for res in [2, 1, 0]:
        means = []
        for yr in YEARS:
            sub = agg[(agg['year']==yr) & (agg['result']==res)][col].dropna()
            means.append(sub.mean() if len(sub) > 0 else np.nan)
        ax.plot(YEARS, means, marker='o', label=result_map[res],
                color=colors_map[res], linewidth=2, markersize=7)
    ax.set_title(label, fontsize=11)
    ax.set_xlabel('연도')
    ax.legend(fontsize=8)
    ax.grid(axis='y', alpha=0.3)

plt.suptitle('주요 지표 연도별 추이 (승/무/패 평균)', fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig('analysis_year_trend.png', dpi=150)
plt.close()
print("-> analysis_year_trend.png 저장")

conn.close()
print("\n분석 완료")
