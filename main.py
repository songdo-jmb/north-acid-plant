import streamlit as st
import pandas as pd
from pathlib import Path
import unicodedata
import io

import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# ===============================
# 기본 설정
# ===============================
st.set_page_config(
    page_title="EC값에 따른 상하부 길이의 성장률 차이",
    layout="wide"
)

# 한글 폰트 (CSS)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# ===============================
# 경로 설정
# ===============================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
IMAGE_DIR = BASE_DIR / "images"

# 학교별 EC 조건
EC_MAP = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0
}

# ===============================
# 유니코드 안전 파일 탐색
# ===============================
def normalize_name(name: str) -> set:
    return {
        unicodedata.normalize("NFC", name),
        unicodedata.normalize("NFD", name)
    }

def find_file_by_keyword(directory: Path, keyword: str):
    keyword_set = normalize_name(keyword)
    for p in directory.iterdir():
        if not p.is_file():
            continue
        name_set = normalize_name(p.name)
        if keyword_set & name_set:
            return p
    return None

# ===============================
# 데이터 로딩
# ===============================
@st.cache_data
def load_environment_data():
    data = {}
    for school in EC_MAP.keys():
        file_path = find_file_by_keyword(DATA_DIR, f"{school}_환경데이터")
        if file_path is None:
            continue
        df = pd.read_csv(file_path)
        df["학교"] = school
        data[school] = df
    return data

@st.cache_data
def load_growth_data():
    xlsx = find_file_by_keyword(DATA_DIR, "생육결과")
    if xlsx is None:
        return None

    sheets = pd.read_excel(xlsx, sheet_name=None)
    result = []

    for sheet_name, df in sheets.items():
        df["학교"] = sheet_name
        df["EC"] = EC_MAP.get(sheet_name)
        result.append(df)

    return pd.concat(result, ignore_index=True)

@st.cache_data
def load_images():
    if not IMAGE_DIR.exists():
        return []
    images = []
    for p in IMAGE_DIR.iterdir():
        if p.suffix.lower() in [".png", ".jpg", ".jpeg"]:
            images.append(p)
    return images

# ===============================
# 데이터 로딩 UI
# ===============================
with st.spinner("데이터 로딩 중..."):
    env_data = load_environment_data()
    growth_df = load_growth_data()
    image_files = load_images()

if not env_data or growth_df is None:
    st.error("❌ 데이터 파일을 찾을 수 없습니다. data 폴더를 확인하세요.")
    st.stop()

# ===============================
# 사이드바
# ===============================
st.sidebar.title("학교 선택")
school_option = st.sidebar.selectbox(
    "학교",
    ["전체"] + list(EC_MAP.keys())
)

# ===============================
# 제목
# ===============================
st.title("🌱 EC값에 따른 상하부 길이의 성장률 차이")

# ===============================
# 탭 구성
# ===============================
tab1, tab2, tab3 = st.tabs([
    "📊 평균 환경 데이터 분석",
    "📈 EC값에 따른 성장량",
    "🔬 지상부-지하부 관계"
])

# ===============================
# TAB 1
# ===============================
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

    # 다운로드
    buffer = io.BytesIO()
    avg_df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    st.download_button(
        "📥 평균 환경 데이터 다운로드",
        data=buffer,
        file_name="학교별_평균_환경데이터.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    if image_files:
        st.divider()
        st.subheader("📷 참고 그래프 / 표 이미지")
        for img in image_files:
            st.image(img, caption=img.name, use_container_width=True)

# ===============================
# TAB 2
# ===============================
with tab2:
    st.subheader("EC값에 따른 성장량 비교")

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

    st.info("✅ 하늘고(EC 2.0)가 생육 최적 조건으로 관찰됨")

# ===============================
# TAB 3
# ===============================
with tab3:
    st.subheader("지상부 vs 지하부 성장 관계")

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
