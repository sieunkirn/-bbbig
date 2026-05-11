"""
Streamlit Community Cloud 배포용 진입점.

Cloud에서 Main file path를 `streamlit_app.py`로 두면 됩니다.
로컬에서는 기존처럼 `streamlit run app.py`를 써도 됩니다.
"""

from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / 'app.py'), run_name='__main__')
