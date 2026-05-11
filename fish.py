import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# --- 설정 ---
FILE_NAME = '해양수산부_위판장별어종별위탁판매집계_20260331-1.CSV'
ANALYSIS_COLS = ['수산물표준코드명', '어종상태명', '물량(킬로그램)', '평균가']
TOP_SPECIES_N = 10  # 거래 물량 기준 주요 어종 개수

# 1. 데이터 불러오기 (cp949)
file_path = Path(__file__).resolve().parent / FILE_NAME
df = pd.read_csv(file_path, encoding='cp949')

core = df[ANALYSIS_COLS].copy()
for col in ('물량(킬로그램)', '평균가'):
    core[col] = pd.to_numeric(core[col], errors='coerce')

# 2. 결측치 확인
print('=== 결측치 (컬럼별 개수) ===')
print(core.isna().sum())
print()
print('=== 결측치 행 비율 ===')
print(f"전체 행: {len(core):,} / 결측이 하나라도 있는 행: {core.isna().any(axis=1).sum():,} "
      f"({100 * core.isna().any(axis=1).mean():.2f}%)")
print()

# 3. 기초 통계량
print('=== 데이터 타입 ===')
print(core.dtypes)
print()
print('=== 수치형 기초 통계 (물량, 평균가) ===')
print(core[['물량(킬로그램)', '평균가']].describe())
print()
print('=== 어종상태명 빈도 (상위 15) ===')
print(core['어종상태명'].value_counts(dropna=False).head(15))
print()

# 4. 활어만 필터링
live = core[core['어종상태명'] == '활어'].copy()
print(f"=== 활어 행 수: {len(live):,} (전체 대비 {100 * len(live) / len(core):.2f}%) ===")
print()

# 주요 어종: 활어 구간에서 물량 합 기준 상위 N종
top_species = (
    live.groupby('수산물표준코드명', dropna=False)['물량(킬로그램)']
    .sum()
    .nlargest(TOP_SPECIES_N)
    .index
)
plot_df = live[live['수산물표준코드명'].isin(top_species)].copy()

# 물량 가중 평균 단가(원/kg): 행별 평균가는 kg당 위판가로 해석되는 경우가 많음 → 어종별 대표 수준
weighted_avg = (
    plot_df.groupby('수산물표준코드명', dropna=False)
    .apply(
        lambda g: (g['평균가'] * g['물량(킬로그램)']).sum() / g['물량(킬로그램)'].sum(),
        include_groups=False,
    )
    .sort_values(ascending=False)
)

# 5. 시각화: 거래 단위별 가격 분포 + 어종별 물량 가중 평균가
plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False

fig, axes = plt.subplots(1, 2, figsize=(16, 6))

order = weighted_avg.index.tolist()

sns.boxplot(
    data=plot_df,
    x='수산물표준코드명',
    y='평균가',
    order=order,
    ax=axes[0],
)
axes[0].set_title('주요 어종(활어)별 위판 평균가 분포 (거래·규격 단위별 편차)')
axes[0].set_xlabel('수산물표준코드명')
axes[0].set_ylabel('평균가 (원/kg)')
axes[0].tick_params(axis='x', rotation=45)

colors = sns.color_palette('viridis', n_colors=len(order))
axes[1].bar(range(len(order)), weighted_avg.reindex(order).values, color=colors)
axes[1].set_xticks(range(len(order)), labels=order, rotation=45, ha='right')
axes[1].set_title('주요 어종(활어)별 물량 가중 평균 단가')
axes[1].set_xlabel('수산물표준코드명')
axes[1].set_ylabel('물량 가중 평균가 (원/kg)')

plt.tight_layout()
plt.show()
