import streamlit as st
import pandas as pd
from pathlib import Path
import unicodedata
import io

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ======================================================
# 기본 설정
# ======================================================
st.set_page_config(
    page_title="EC값에 따른 상하부 길이의 성장률 차이",
    layout="wide"
)

# 한글 폰트 + 이미지 스타일
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
img {
    border-radius: 12px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.15);
}
</style>
""", unsafe_allow_html=True)

# ======================================================
# 경로 설정
# ======================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
IMAGE_DIR = BASE_DIR / "images"

EC_MAP = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0
}

# ======================================================
# 한글 파일명 안전 탐색 함수
# ======================================================
def find_file_containing(directory: Path, keywords: list, suffix: str):
    for p in directory.iterdir():
        if not p.is_file():
            continue
        if not p.name.lower().endswith(suffix):
            continue

        name_nfc = unicodedata.normalize("NFC", p.name)
        name_nfd = unicodedata.normalize("NFD", p.name)

        if all((k in name_nfc) or (k in name_nfd) for k in keywords):
            return p
    return None

# ======================================================
# 데이터 로딩
# ======================================================
@st.cache_data
def load_environment_data():
    data = {}
    for school in EC_MAP.keys():
        file_path = find_file_containing(
            DATA_DIR,
            keywords=[school, "환경데이터"],
            suffix=".csv"
        )
        if file_path is None:
            continue
        df = pd.read_csv(file_path)
        df["학교"] = school
        data[school] = df
    return data

@st.cache_data
def load_growth_data():
    xlsx_path = find_file_containing(
        DATA_DIR,
        keywords=["생육결과"],
        suffix=".xlsx"
    )
    if xlsx_path is None:
        return None

    sheets = pd.read_excel(xlsx_path, sheet_name=None)
    result = []

    for sheet_name, df in sheets.items():
        df["학교"] = sheet_name
        df["EC"] = EC_MAP.get(sheet_name)
        result.append(df)

    return pd.concat(result, ignore_index=True)

# ======================================================
# 데이터 로딩 UI
# ======================================================
with st.spinner("데이터 로딩 중..."):
    env_data = load_environment_data()
    growth_df = load_growth_data()

if not env_data or growth_df is None:
    st.error("❌ data 폴더에서 필요한 파일을 찾을 수 없습니다.")
    st.stop()

# ======================================================
# 사이드바
# ======================================================
st.sidebar.title("학교 선택")
school_option = st.sidebar.selectbox(
    "학교",
    ["전체"] + list(EC_MAP.keys())
)

# 🔥 실습용 이미지 (아무 데나 넣기)
st.sidebar.divider()
st.sidebar.subheader("🧪 실습용 이미지")

practice_img = IMAGE_DIR / "practice_image.png"
if practice_img.exists():
    st.sidebar.image(practice_img, use_container_width=True)
else:
    st.sidebar.info("images/practice_image.png 파일을 추가하세요.")

# ======================================================
# 제목
# ======================================================
st.title("🌱 EC값에 따른 상하부 길이의 성장률 차이")

# ======================================================
# 탭 구성
# ======================================================
tab1, tab2, tab3 = st.tabs([
    "📊 평균 환경 데이터",
    "📈 EC값에 따른 성장량",
    "🔬 지상부-지하부 관계"
])

# ======================================================
# TAB 1: 평균 환경 데이터
# ======================================================
with tab1:
    st.subheader("학교별 평균 환경 데이터")

    rows = []
    for school, df in env_data.items():
        rows.append({
            "학교": school,
            "온도 평균": df["temperature"].mean(),
            "습도 평균": df["humidity"].mean(),
            "pH 평균": df["ph"].mean(),
            "EC 평균": df["ec"].mean()
        })

    avg_df = pd.DataFrame(rows)
    st.dataframe(avg_df, use_container_width=True)

    buffer = io.BytesIO()
    avg_df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    st.download_button(
        "📥 평균 환경 데이터 다운로드",
        data=buffer,
        file_name="학교별_평균_환경데이터.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ======================================================
# TAB 2: EC값에 따른 성장량
# ======================================================
with tab2:
    st.subheader("EC값에 따른 지상부 성장")

    df = growth_df.copy()
    if school_option != "전체":
        df = df[df["학교"] == school_option]

    fig = px.scatter(
        df,
        x="EC",
        y="지상부 길이(mm)",
        color="학교",
        size="생중량(g)",
        title="EC값에 따른 지상부 성장"
    )

    fig.update_layout(
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )

    st.plotly_chart(fig, use_container_width=True)
    st.info("✅ 하늘고(EC 2.0) 조건에서 생육이 가장 안정적으로 나타남")

# ======================================================
# TAB 3: 지상부 vs 지하부
# ======================================================
with tab3:
    st.subheader("지상부 길이 vs 지하부 길이")

    fig = make_subplots()

    for school in df["학교"].unique():
        sdf = df[df["학교"] == school]
        fig.add_trace(
            go.Scatter(
                x=sdf["지상부 길이(mm)"],
                y=sdf["지하부길이(mm)"],
                mode="markers",
                name=school
            )
        )

    fig.update_layout(
        xaxis_title="지상부 길이 (mm)",
        yaxis_title="지하부 길이 (mm)",
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )

    st.plotly_chart(fig, use_container_width=True)
