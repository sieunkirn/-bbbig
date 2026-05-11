"""
위판 집계 데이터 기반 적정 구매가 추정 (MVP용).

- 어종명은 CSV의 '수산물표준코드명'과 동일해야 합니다 (예: '도다리', '고등어').
- 행마다의 '평균가'를 kg당 위판가로 보고, 활어 구간에서 어종별 물량 가중 평균으로 대표 단가를 냅니다.
- 특정 무게가 데이터에 없어도 동일 단가로 총액을 추정합니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_CSV = Path(__file__).resolve().parent / '해양수산부_위판장별어종별위탁판매집계_20260331-1.CSV'
ANALYSIS_COLS = ('수산물표준코드명', '어종상태명', '물량(킬로그램)', '평균가')


def _load_core(csv_path: Path | str | None = None, encoding: str = 'cp949') -> pd.DataFrame:
    path = Path(csv_path) if csv_path else DEFAULT_CSV
    df = pd.read_csv(path, encoding=encoding)
    core = df[list(ANALYSIS_COLS)].copy()
    for col in ('물량(킬로그램)', '평균가'):
        core[col] = pd.to_numeric(core[col], errors='coerce')
    return core


def build_live_species_price_per_kg(core: pd.DataFrame) -> pd.Series:
    """활어 거래만 사용해 어종별 kg당 물량 가중 평균 위판가(원/kg)."""
    live = core[
        (core['어종상태명'] == '활어')
        & (core['물량(킬로그램)'].notna())
        & (core['물량(킬로그램)'] > 0)
        & (core['평균가'].notna())
    ].copy()
    live['_amt'] = live['평균가'] * live['물량(킬로그램)']
    g = live.groupby('수산물표준코드명', dropna=False)
    return (g['_amt'].sum() / g['물량(킬로그램)'].sum()).rename('kg당_시장추정가')


@dataclass
class PurchaseEstimate:
    성공: bool
    어종명: str
    무게_kg: float
    kg당_시장추정가_원: float | None
    시장추정_총액_원: float | None
    적정_구매가_원: float | None
    시장대비_할인율_퍼센트: float | None
    안내_메시지: str
    오류: str | None = None

    def as_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            '성공': self.성공,
            '어종명': self.어종명,
            '무게_kg': self.무게_kg,
            'kg당_시장추정가_원': self.kg당_시장추정가_원,
            '시장추정_총액_원': self.시장추정_총액_원,
            '적정_구매가_원': self.적정_구매가_원,
            '시장대비_할인율_퍼센트': self.시장대비_할인율_퍼센트,
            '안내_메시지': self.안내_메시지,
        }
        if self.오류 is not None:
            d['오류'] = self.오류
        return d


def appropriate_purchase_price(
    어종명: str,
    무게_kg: float,
    *,
    core: pd.DataFrame | None = None,
    csv_path: Path | str | None = None,
    encoding: str = 'cp949',
    price_per_kg_by_species: pd.Series | None = None,
    시장대비_목표_할인율: float = 0.10,
    금액_반올림_원: int = 10,
) -> PurchaseEstimate:
    """
    어종·무게에 대한 시장 추정 총액과 '적정 구매가' 제안.

    적정 구매가 = 시장추정_총액 × (1 - 시장대비_목표_할인율).
    안내 문구는 해당 할인율을 기준으로 생성합니다 (기본 약 10% 저렴).

    무게가 집계표에 특정 규격으로 없더라도, 어종의 kg당 대표 단가 × 무게로 총액을 추정합니다.
    """
    name = (어종명 or '').strip()
    if not name:
        return PurchaseEstimate(
            성공=False,
            어종명=어종명,
            무게_kg=무게_kg,
            kg당_시장추정가_원=None,
            시장추정_총액_원=None,
            적정_구매가_원=None,
            시장대비_할인율_퍼센트=None,
            안내_메시지='어종명을 입력해 주세요.',
            오류='empty_species',
        )

    try:
        w = float(무게_kg)
    except (TypeError, ValueError):
        return PurchaseEstimate(
            성공=False,
            어종명=name,
            무게_kg=무게_kg,
            kg당_시장추정가_원=None,
            시장추정_총액_원=None,
            적정_구매가_원=None,
            시장대비_할인율_퍼센트=None,
            안내_메시지='무게(kg)는 숫자로 입력해 주세요.',
            오류='invalid_weight',
        )

    if w <= 0:
        return PurchaseEstimate(
            성공=False,
            어종명=name,
            무게_kg=w,
            kg당_시장추정가_원=None,
            시장추정_총액_원=None,
            적정_구매가_원=None,
            시장대비_할인율_퍼센트=None,
            안내_메시지='무게(kg)는 0보다 커야 합니다.',
            오류='non_positive_weight',
        )

    if not 0 <= 시장대비_목표_할인율 < 1:
        return PurchaseEstimate(
            성공=False,
            어종명=name,
            무게_kg=w,
            kg당_시장추정가_원=None,
            시장추정_총액_원=None,
            적정_구매가_원=None,
            시장대비_할인율_퍼센트=None,
            안내_메시지='시장대비_목표_할인율은 0 이상 1 미만이어야 합니다.',
            오류='invalid_discount',
        )

    table = price_per_kg_by_species
    if table is None:
        c = core if core is not None else _load_core(csv_path, encoding=encoding)
        table = build_live_species_price_per_kg(c)

    if name not in table.index:
        return PurchaseEstimate(
            성공=False,
            어종명=name,
            무게_kg=w,
            kg당_시장추정가_원=None,
            시장추정_총액_원=None,
            적정_구매가_원=None,
            시장대비_할인율_퍼센트=None,
            안내_메시지=(
                f"데이터에 '{name}' 어종(활어)의 거래가 없습니다. "
                '수산물표준코드명과 동일한 표기로 입력했는지 확인해 주세요.'
            ),
            오류='unknown_species',
        )

    p_kg = float(table.loc[name])
    if pd.isna(p_kg):
        return PurchaseEstimate(
            성공=False,
            어종명=name,
            무게_kg=w,
            kg당_시장추정가_원=None,
            시장추정_총액_원=None,
            적정_구매가_원=None,
            시장대비_할인율_퍼센트=None,
            안내_메시지=f"'{name}' 어종의 대표 단가를 계산할 수 없습니다.",
            오류='nan_price',
        )

    market_total = p_kg * w
    fair = market_total * (1 - 시장대비_목표_할인율)
    r = max(int(금액_반올림_원), 1)
    market_total_r = round(market_total / r) * r
    fair_r = round(fair / r) * r
    pct = round(100 * 시장대비_목표_할인율)

    msg = (
        f"제안 적정 구매가는 {fair_r:,.0f}원입니다. "
        f"이 가격이면 위판 시장 평균 추정 총액({market_total_r:,.0f}원) 대비 약 {pct}% 저렴한 수준입니다."
    )

    return PurchaseEstimate(
        성공=True,
        어종명=name,
        무게_kg=w,
        kg당_시장추정가_원=p_kg,
        시장추정_총액_원=float(market_total_r),
        적정_구매가_원=float(fair_r),
        시장대비_할인율_퍼센트=float(pct),
        안내_메시지=msg,
    )


if __name__ == '__main__':
    sample = appropriate_purchase_price('도다리', 1.2)
    print(sample.as_dict())
