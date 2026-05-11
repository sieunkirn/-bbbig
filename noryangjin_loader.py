"""
노량진.pdf에서 표·텍스트를 추출해 대시보드와 결합합니다.
PDF 구조가 달라도 앱이 동작하도록, 실패 시 빈 결과를 반환합니다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_PDF = Path(__file__).resolve().parent / '노량진.pdf'


def load_noryangjin_pdf(
    pdf_path: Path | str | None = None,
) -> dict[str, Any]:
    """
    반환:
      - ok: PDF 열기 성공 여부
      - path: 사용한 경로
      - tables: [{page, table_index, columns, rows}, ...]
      - full_text: 전 페이지 텍스트 연결(언급 여부 검사용)
      - error: 실패 시 메시지
    """
    path = Path(pdf_path) if pdf_path else DEFAULT_PDF
    out: dict[str, Any] = {
        'ok': False,
        'path': str(path),
        'tables': [],
        'full_text': '',
        'error': None,
    }

    if not path.is_file():
        out['error'] = f'PDF 파일이 없습니다: {path.name} (프로젝트 폴더에 두면 자동으로 읽습니다.)'
        return out

    try:
        import pdfplumber
    except ImportError:
        out['error'] = 'pdfplumber 패키지가 필요합니다. pip install pdfplumber'
        return out

    tables_out: list[dict[str, Any]] = []
    text_chunks: list[str] = []

    try:
        with pdfplumber.open(path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                text_chunks.append(page.extract_text() or '')
                for t_idx, table in enumerate(page.extract_tables() or []):
                    if not table or len(table) < 1:
                        continue
                    header = table[0]
                    body = table[1:]
                    if header and all(c is None or str(c).strip() == '' for c in header):
                        header = [f'열{j}' for j in range(len(table[0]))]
                    try:
                        df = pd.DataFrame(body, columns=header)
                    except Exception:
                        df = pd.DataFrame(table)
                    tables_out.append(
                        {
                            'page': page_idx + 1,
                            'table_index': t_idx + 1,
                            'df': df,
                        }
                    )
    except Exception as e:
        out['error'] = f'PDF 읽기 오류: {e}'
        return out

    out['ok'] = True
    out['tables'] = tables_out
    out['full_text'] = '\n'.join(text_chunks)
    return out


def pdf_mentions_species(full_text: str, species_name: str) -> bool:
    if not full_text or not species_name:
        return False
    return str(species_name) in full_text


def tables_preview_dfs(tables: list[dict[str, Any]], max_tables: int = 5) -> list[pd.DataFrame]:
    """미리보기용으로 앞쪽 몇 개 표만 DataFrame 리스트로."""
    dfs = []
    for item in tables[:max_tables]:
        dfs.append(item['df'])
    return dfs
