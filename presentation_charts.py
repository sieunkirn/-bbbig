"""
발표용 시각화: 어종별 가격 편차(Boxplot), TOP 5 어종 물량 비중(파이).
실행 후 같은 폴더에 PNG 파일이 저장됩니다.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

FILE_NAME = '해양수산부_위판장별어종별위탁판매집계_20260331-1.CSV'
# 박스플롯: 전체 어종을 넣으면 가독성이 떨어져 활어·물량 상위 어종만 표시
BOX_TOP_N = 14

# --- 한글 폰트 & 스타일 ---
plt.style.use('seaborn-v0_8-darkgrid')
plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False

file_path = Path(__file__).resolve().parent / FILE_NAME
df = pd.read_csv(file_path, encoding='cp949')
df['물량(킬로그램)'] = pd.to_numeric(df['물량(킬로그램)'], errors='coerce')
df['평균가'] = pd.to_numeric(df['평균가'], errors='coerce')

df_clean = df.dropna(subset=['수산물표준코드명', '평균가', '물량(킬로그램)'])
df_clean = df_clean[df_clean['물량(킬로그램)'] > 0]

# ---------------------------------------------------------------------------
# 1) Boxplot: 활어 기준 주요 어종의 kg당 위판가(평균가) 편차
# ---------------------------------------------------------------------------
live = df_clean[df_clean['어종상태명'] == '활어']
species_vol = live.groupby('수산물표준코드명', observed=True)['물량(킬로그램)'].sum()
box_order = species_vol.nlargest(BOX_TOP_N).index.tolist()
box_df = live[live['수산물표준코드명'].isin(box_order)]

fig1, ax1 = plt.subplots(figsize=(14, 6))
sns.boxplot(
    data=box_df,
    x='수산물표준코드명',
    y='평균가',
    order=box_order,
    ax=ax1,
    palette='flare',
    linewidth=1,
    fliersize=2,
)
ax1.set_title(
    '어종별 위판가(kg당) 분포 — 같은 어종 내에서도 가격 편차가 큼 (시장 불투명성)',
    fontsize=13,
    pad=12,
)
ax1.set_xlabel('수산물표준코드명 (활어 · 거래 물량 상위 어종)')
ax1.set_ylabel('평균가 (원/kg)')
ax1.tick_params(axis='x', rotation=45)
fig1.tight_layout()
out1 = Path(__file__).resolve().parent / '발표용_01_어종별_가격편차_boxplot.png'
fig1.savefig(out1, dpi=200, bbox_inches='tight')
print(f'저장: {out1}')

# ---------------------------------------------------------------------------
# 2) Pie: 거래 물량 TOP 5 어종의 전체 시장(전체 행) 대비 비중
# ---------------------------------------------------------------------------
vol_by_species = df_clean.groupby('수산물표준코드명', observed=True)['물량(킬로그램)'].sum()
top5 = vol_by_species.nlargest(5)
other_kg = float(vol_by_species.sum() - top5.sum())

labels = list(top5.index)
sizes = [float(v) for v in top5.values]
if other_kg > 0:
    labels.append('기타 어종')
    sizes.append(other_kg)

colors = sns.color_palette('Set2', n_colors=len(labels))
explode = [0.03] * len(labels)
explode[0] = 0.06

fig2, ax2 = plt.subplots(figsize=(9, 9))
wedges, texts, autotexts = ax2.pie(
    sizes,
    labels=labels,
    autopct='%1.1f%%',
    startangle=90,
    colors=colors,
    explode=explode,
    pctdistance=0.72,
    textprops={'fontsize': 11},
)
for t in autotexts:
    t.set_fontweight('bold')
ax2.set_title(
    '거래 물량 TOP 5 어종이 차지하는 비중\n(전체 위판 물량 대비)',
    fontsize=14,
    pad=16,
)
fig2.tight_layout()
out2 = Path(__file__).resolve().parent / '발표용_02_TOP5_어종_물량비중_pie.png'
fig2.savefig(out2, dpi=200, bbox_inches='tight')
print(f'저장: {out2}')

plt.show()
