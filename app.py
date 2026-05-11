"""
모두의 창업 — 수산물 가격 서비스 (Streamlit)

실행: streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from fair_price import (
    DEFAULT_CSV,
    appropriate_purchase_price,
    build_live_species_price_per_kg,
)
from noryangjin_loader import load_noryangjin_pdf, pdf_mentions_species

ENCODING = 'cp949'
ANALYSIS_COLS = ('수산물표준코드명', '어종상태명', '물량(킬로그램)', '평균가')

# 토스/핀테크 느낌 · 하늘색 계열
# 주의: [class*="st"] 전체에 한 폰트만 강제하면 이모지가 글자/이름으로 깨짐 → 본문만 Pretendard, 이모지는 OS 컬러 폰트로 폴백
APP_CSS = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css" />
<style>
    html, body {
        font-family: "Pretendard Variable", Pretendard, -apple-system, BlinkMacSystemFont,
            "Malgun Gothic", "Apple SD Gothic Neo", system-ui,
            "Segoe UI Emoji", "Segoe UI Symbol", "Apple Color Emoji", "Noto Color Emoji", sans-serif;
    }
    /* 이모지·심볼은 반드시 컬러 이모지 폰트를 뒤에 둠 */
    .stButton > button,
    [data-testid="stMarkdown"] p,
    [data-testid="stMarkdown"] span,
    .stCaption, label, [data-baseweb="tab"] {
        font-family: "Pretendard Variable", Pretendard, -apple-system, BlinkMacSystemFont,
            "Malgun Gothic", "Apple SD Gothic Neo", system-ui,
            "Segoe UI Emoji", "Segoe UI Symbol", "Apple Color Emoji", "Noto Color Emoji", sans-serif !important;
    }
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(180deg, #e8f4fc 0%, #f0f9ff 35%, #f8fafc 100%) !important;
        min-height: 100vh;
    }
    [data-testid="stHeader"] { background: transparent !important; }
    .main .block-container {
        max-width: min(1180px, 100%) !important;
        padding-top: 1.25rem !important;
        padding-left: clamp(1rem, 3vw, 2rem) !important;
        padding-right: clamp(1rem, 3vw, 2rem) !important;
        padding-bottom: 5rem !important;
    }
    h1, h2, h3, h4, h5 { color: #0f172a !important; letter-spacing: -0.02em !important; }
    [data-testid="stSidebar"] {
        background: linear-gradient(195deg, #dbeafe 0%, #e0f2fe 45%, #f0f9ff 100%) !important;
        border-right: 1px solid rgba(14, 165, 233, 0.15) !important;
    }
    [data-testid="stSidebar"] .block-container { padding-top: 1.5rem !important; }
    div[data-testid="stMetricValue"],
    div[data-testid="stMetricLabel"] {
        font-family: "Pretendard Variable", Pretendard, -apple-system, "Malgun Gothic",
            "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", sans-serif !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
        font-weight: 700 !important;
        color: #0369a1 !important;
    }
    div[data-testid="stMetricLabel"] { font-weight: 600 !important; color: #64748b !important; }
    .hero-emoji {
        font-family: "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", sans-serif !important;
        font-size: 2.5rem;
        line-height: 1.2;
        margin-bottom: 0.25rem;
    }
    .stButton > button {
        border-radius: 14px !important;
        font-weight: 600 !important;
        padding: 0.65rem 1rem !important;
        border: none !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0ea5e9 0%, #38bdf8 50%, #7dd3fc 100%) !important;
        color: #ffffff !important;
        box-shadow: 0 4px 14px rgba(14, 165, 233, 0.35) !important;
    }
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 6px 20px rgba(14, 165, 233, 0.45) !important;
        transform: translateY(-1px);
    }
    .stButton > button[kind="secondary"] {
        background: #ffffff !important;
        color: #0369a1 !important;
        border: 1px solid #bae6fd !important;
    }
    [data-baseweb="tab-list"] {
        gap: 6px !important;
        background: rgba(255,255,255,0.55) !important;
        padding: 6px !important;
        border-radius: 16px !important;
        border: 1px solid rgba(14, 165, 233, 0.2) !important;
    }
    [data-baseweb="tab"] {
        border-radius: 12px !important;
        font-weight: 600 !important;
    }
    .toss-card {
        background: rgba(255, 255, 255, 0.92);
        border: 1px solid rgba(14, 165, 233, 0.18);
        border-radius: 20px;
        padding: 1.25rem 1.35rem;
        margin: 0.85rem 0 1.25rem 0;
        box-shadow: 0 8px 30px rgba(15, 23, 42, 0.06);
    }
    .hero-title { font-size: 1.75rem; font-weight: 800; color: #0c4a6e; margin: 0; }
    .hero-sub { color: #64748b; font-size: 1.05rem; margin-top: 0.5rem; line-height: 1.55; }
    footer { visibility: hidden; height: 0; }
    [data-testid="stExpander"] {
        background: rgba(255,255,255,0.6);
        border-radius: 14px;
        border: 1px solid rgba(14, 165, 233, 0.15);
    }
    /* 차트 영역이 잘리는 현상 완화 */
    [data-testid="stLineChart"] {
        min-height: 320px !important;
    }
    iframe[title="streamlit_line_chart"] {
        min-height: 340px !important;
    }
</style>
"""


def render_price_trend(trend: pd.DataFrame, height: int = 360) -> None:
    """일별 물량가중 평균가 라인 차트."""
    if len(trend) == 0:
        st.info('📭 이 어종으로 그릴 시세 추이가 아직 없어요.')
        return
    chart = trend.set_index('위판일자').rename(columns={'물량가중평균가': '원/kg'})
    st.line_chart(chart, height=height)


@st.cache_data(show_spinner=False)
def load_dashboard_data():
    df_raw = pd.read_csv(DEFAULT_CSV, encoding=ENCODING)
    need = ['위판일자', *ANALYSIS_COLS]
    missing = [c for c in need if c not in df_raw.columns]
    if missing:
        raise ValueError(f'CSV에 필요한 컬럼이 없습니다: {missing}')

    df_raw = df_raw[need].copy()
    for col in ('물량(킬로그램)', '평균가'):
        df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce')
    df_raw['위판일자'] = pd.to_datetime(df_raw['위판일자'], errors='coerce')

    core = df_raw[['수산물표준코드명', '어종상태명', '물량(킬로그램)', '평균가']].copy()
    price_per_kg = build_live_species_price_per_kg(core)
    return df_raw, core, price_per_kg


@st.cache_data(show_spinner=True)
def cached_noryangjin_bundle():
    return load_noryangjin_pdf()


def daily_weighted_price_per_kg(df_raw: pd.DataFrame, species: str) -> pd.DataFrame:
    sub = df_raw[
        (df_raw['어종상태명'] == '활어')
        & (df_raw['수산물표준코드명'] == species)
        & (df_raw['물량(킬로그램)'] > 0)
        & (df_raw['평균가'].notna())
        & (df_raw['위판일자'].notna())
    ].copy()
    if sub.empty:
        return pd.DataFrame(columns=['위판일자', '물량가중평균가'])

    sub['_v'] = sub['평균가'] * sub['물량(킬로그램)']
    g = sub.groupby('위판일자', as_index=False)
    out = g.agg(물량합=('물량(킬로그램)', 'sum'), 금액합=('_v', 'sum'))
    out['물량가중평균가'] = out['금액합'] / out['물량합']
    return out[['위판일자', '물량가중평균가']].sort_values('위판일자')


def build_consumer_recommendations(
    price_per_kg: pd.Series,
    live_vol: pd.Series,
    pdf_text: str,
    top_n: int = 10,
) -> pd.DataFrame:
    rows = []
    for sp in price_per_kg.dropna().index:
        if sp not in live_vol.index:
            continue
        v = float(live_vol.loc[sp])
        p = float(price_per_kg.loc[sp])
        if v <= 0 or p <= 0:
            continue
        rows.append({'어종': sp, 'kg당_참고가': p, '거래물량_kg': v})

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    vmax = df['거래물량_kg'].max()
    pmin, pmax = df['kg당_참고가'].min(), df['kg당_참고가'].max()
    df['인기도'] = df['거래물량_kg'] / vmax if vmax else 0
    if pmax > pmin:
        df['가격밸런스'] = 1 - (df['kg당_참고가'] - pmin) / (pmax - pmin)
    else:
        df['가격밸런스'] = 1.0
    base = 0.55 * df['인기도'] + 0.45 * df['가격밸런스']
    bonus = df['어종'].apply(lambda s: 0.04 if pdf_mentions_species(pdf_text, s) else 0.0)
    df['맞춤점수'] = (base + bonus).clip(upper=1.0)
    out = df.nlargest(top_n, '맞춤점수').reset_index(drop=True)
    return out[['어종', '맞춤점수', 'kg당_참고가', '거래물량_kg']]


def reset_to_start():
    st.session_state.ui_role = None


def _basename(p) -> str:
    return Path(str(p)).name


# -----------------------------------------------------------------------------
st.set_page_config(page_title='모두의 창업', layout='wide', initial_sidebar_state='expanded')
st.markdown(APP_CSS, unsafe_allow_html=True)

if 'ui_role' not in st.session_state:
    st.session_state.ui_role = None
if 'seller_listings' not in st.session_state:
    st.session_state.seller_listings = []

pdf_bundle = cached_noryangjin_bundle()
pdf_ok = bool(pdf_bundle.get('ok'))
pdf_text = pdf_bundle.get('full_text') or ''

df_raw, core, price_per_kg = load_dashboard_data()
live_vol = core[(core['어종상태명'] == '활어') & (core['물량(킬로그램)'] > 0)].groupby(
    '수산물표준코드명', observed=True
)['물량(킬로그램)'].sum()
candidates = [s for s in price_per_kg.dropna().index if s in live_vol.index]
species_options = sorted(candidates, key=lambda s: float(live_vol.loc[s]), reverse=True)

# ========================= 시작 =========================
if st.session_state.ui_role is None:
    st.markdown(
        '<div style="text-align:center;padding:2rem 0 1.5rem;">'
        '<div class="hero-emoji">🐟</div>'
        '<p class="hero-title">모두의 창업</p>'
        '<p class="hero-sub">시세만 알면, 거래가 쉬워져요.<br/>지금 바로 맞춤 가격을 확인해 보세요.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    a, b = st.columns(2, gap='large')
    with a:
        if st.button('🏪 판매자로 시작', type='primary', use_container_width=True, key='btn_seller_enter'):
            st.session_state.ui_role = 'seller'
            st.rerun()
    with b:
        if st.button('🛒 구매자로 시작', type='primary', use_container_width=True, key='btn_buyer_enter'):
            st.session_state.ui_role = 'consumer'
            st.rerun()

    with st.expander('앱 정보', expanded=False):
        st.markdown(
            '공개 시세를 가공한 **참고 가격**입니다. 실제 거래는 품질·시점에 따라 달라질 수 있습니다.'
        )
        st.caption('집계 데이터 파일: ' + _basename(DEFAULT_CSV))
        if pdf_ok:
            st.caption('보조 자료: ' + _basename(str(pdf_bundle['path'])))

    st.stop()

# ========================= 사이드바 =========================
with st.sidebar:
    st.markdown('##### ⚙️ 설정')
    if st.button('🏠 처음 화면', use_container_width=True):
        reset_to_start()
        st.rerun()

    selected = st.selectbox('🐠 어종', options=species_options, index=0 if species_options else None)
    weight_kg = st.slider('⚖️ 무게 (kg)', min_value=0.1, max_value=50.0, value=1.0, step=0.1)

    with st.expander('안내', expanded=False):
        st.caption('참고 시세이며, 실제 계약가와 다를 수 있습니다.')
        st.caption(_basename(DEFAULT_CSV))
        if pdf_ok:
            st.caption(_basename(str(pdf_bundle['path'])))

if not species_options or selected is None:
    st.error('표시할 어종이 없습니다.')
    st.stop()

p_kg = float(price_per_kg.loc[selected])
trend = daily_weighted_price_per_kg(df_raw, selected)
latest_wavg = float(trend['물량가중평균가'].iloc[-1]) if len(trend) else None

# ========================= 판매자 =========================
if st.session_state.ui_role == 'seller':
    st.markdown(
        f'<div class="toss-card"><p style="margin:0;font-size:1.35rem;font-weight:800;">🏪 판매자</p>'
        f'<p style="margin:0.35rem 0 0 0;color:#64748b;">{selected} · {weight_kg}kg</p></div>',
        unsafe_allow_html=True,
    )

    tab_hist, tab_reg = st.tabs(['📋 내 판매 목록', '💰 상품 등록 · 가격'])

    with tab_hist:
        st.markdown('##### 📦 등록한 상품')
        if st.session_state.seller_listings:
            disp = pd.DataFrame(st.session_state.seller_listings)
            st.dataframe(disp, use_container_width=True, hide_index=True, height=min(400, 120 + 35 * len(disp)))
            c1, c2 = st.columns(2)
            with c1:
                if st.button('🗑️ 목록 비우기', use_container_width=True):
                    st.session_state.seller_listings = []
                    st.rerun()
            with c2:
                del_idx = st.number_input(
                    '삭제할 행 (0부터)', min_value=0, max_value=max(0, len(st.session_state.seller_listings) - 1), value=0, step=1
                )
                if st.button('✂️ 해당 행 삭제', use_container_width=True):
                    if 0 <= del_idx < len(st.session_state.seller_listings):
                        st.session_state.seller_listings.pop(int(del_idx))
                        st.rerun()
        else:
            st.info('아직 등록된 상품이 없어요. 「상품 등록」에서 추가해 보세요 ✨')

    with tab_reg:
        st.markdown('##### 📈 시세 흐름')
        st.caption('최근 일별 평균(원/kg) 추이예요. 가격 책정 전에 꼭 확인해 보세요.')
        render_price_trend(trend, height=380)

        st.markdown('##### 💡 가격 제안')
        margin_pct = st.slider('📊 희망 마진 (%)', min_value=0, max_value=80, value=15, step=1, key='seller_margin_pct')

        est_seller = appropriate_purchase_price(selected, weight_kg, core=core, price_per_kg_by_species=price_per_kg)

        if est_seller.성공 and est_seller.시장추정_총액_원 is not None:
            market_total = float(est_seller.시장추정_총액_원)
            recommended = round(market_total * (1 + margin_pct / 100.0))
            s1, s2, s3, s4 = st.columns(4)
            s1.metric('📌 참고 kg당가', f'{p_kg:,.0f}원')
            s2.metric('📎 시세 기준 총액', f'{market_total:,.0f}원')
            s3.metric('✨ 추천 판매가', f'{recommended:,.0f}원')
            s4.metric('➕ 적용 마진', f'{margin_pct}%')
        else:
            st.warning('이 어종은 가격을 계산하기 어려워요. 다른 어종을 골라 주세요.')
            recommended = None
            market_total = None

        st.divider()
        st.markdown('##### ✍️ 호가 등록')
        floor_price = st.number_input('🔒 최저 받을 가격 (원)', min_value=0, value=0, step=1000)
        if st.button('✅ 등록하기', type='primary', key='btn_register_seller'):
            if floor_price <= 0:
                st.error('최저 받을 가격을 입력해 주세요.')
            elif recommended is None:
                st.error('추천가를 먼저 확인해 주세요.')
            else:
                if floor_price > recommended:
                    st.warning('최저가가 추천가보다 높아요. 한 번 더 검토해 보세요 🤔')
                st.session_state.seller_listings.append(
                    {
                        '어종': selected,
                        '무게(kg)': weight_kg,
                        '최저가(원)': floor_price,
                        '추천판매가(원)': recommended,
                        '시세기준(원)': int(market_total) if market_total else None,
                    }
                )
                st.success('목록에 반영했어요 🎉')

# ========================= 구매자 =========================
if st.session_state.ui_role == 'consumer':
    st.markdown(
        f'<div class="toss-card"><p style="margin:0;font-size:1.35rem;font-weight:800;">🛒 구매자</p>'
        f'<p style="margin:0.35rem 0 0 0;color:#64748b;">{selected} · {weight_kg}kg</p></div>',
        unsafe_allow_html=True,
    )

    tab_rec, tab_price = st.tabs(['✨ 추천 어종', '💵 가격 알아보기'])

    with tab_rec:
        st.markdown('##### 🎯 오늘의 추천')
        st.caption('인기 있으면서 부담은 덜한 편인 어종이에요.')
        rec_df = build_consumer_recommendations(price_per_kg, live_vol, pdf_text, top_n=12)
        if len(rec_df):
            show = rec_df.copy()
            show['맞춤점수'] = show['맞춤점수'].round(2)
            show['참고 kg당가(원)'] = show['kg당_참고가'].round(0).astype(int)
            show['거래 규모(kg)'] = show['거래물량_kg'].round(1)
            show = show[['어종', '맞춤점수', '참고 kg당가(원)', '거래 규모(kg)']]
            st.dataframe(show, use_container_width=True, hide_index=True, height=min(480, 80 + 35 * len(show)))
        else:
            st.warning('추천 목록을 만들 수 없어요.')

    with tab_price:
        st.markdown('##### 📊 선택한 어종 시세')
        m1, m2, m3 = st.columns(3)
        m1.metric('📌 참고 평균가 (원/kg)', f'{p_kg:,.0f}')
        if latest_wavg is not None:
            m2.metric('🗓️ 최근일 평균 (원/kg)', f'{latest_wavg:,.0f}')
        else:
            m2.metric('🗓️ 최근일 평균', '—')
        m3.metric('📅 추세 일수', f'{len(trend):,}일')

        st.markdown('##### 📈 최근 흐름')
        render_price_trend(trend, height=380)

        st.divider()
        st.markdown('##### 🧾 살 때 참고 가격')
        est_buyer = appropriate_purchase_price(selected, weight_kg, core=core, price_per_kg_by_species=price_per_kg)
        if est_buyer.성공 and est_buyer.적정_구매가_원 is not None:
            b1, b2, b3 = st.columns(3)
            b1.metric('📎 참고 총액', f'{est_buyer.시장추정_총액_원:,.0f}원')
            b2.metric('✨ 적정 구매가', f'{est_buyer.적정_구매가_원:,.0f}원')
            b3.metric('🤝 협상 여유', f'{est_buyer.시장대비_할인율_퍼센트:.0f}%')
            st.success(
                f"**{est_buyer.적정_구매가_원:,.0f}원** 부근이면 시세 대비 여유 있게 보여요 💙 "
                f"(참고 총액 대비 약 **{est_buyer.시장대비_할인율_퍼센트:.0f}%**)"
            )
        else:
            st.warning('가격을 계산할 수 없어요. 다른 어종을 선택해 주세요.')
