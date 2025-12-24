import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from pathlib import Path
import unicodedata
import io

# =========================
# 기본 설정
# =========================
st.set_page_config(
    page_title="🌱 극지식물 최적 EC 농도 연구",
    layout="wide"
)

# 한글 폰트 (Streamlit)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# =========================
# 경로 및 유틸
# =========================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

def normalize_text(text: str) -> str:
    """NFC/NFD 모두 대응"""
    return unicodedata.normalize("NFC", text)

def find_file_by_normalized_name(directory: Path, target_name: str):
    target_nfc = normalize_text(target_name)
    for f in directory.iterdir():
        if normalize_text(f.name) == target_nfc:
            return f
    return None

# =========================
# 데이터 로딩
# =========================
@st.cache_data
def load_environment_data():
    env_data = {}
    for file in DATA_DIR.iterdir():
        if file.suffix.lower() == ".csv":
            try:
                df = pd.read_csv(file)
                school = normalize_text(file.stem).replace("_환경데이터", "")
                env_data[school] = df
            except Exception:
                st.error(f"환경 데이터 로딩 실패: {file.name}")
    return env_data

@st.cache_data
def load_growth_data():
    xlsx_file = None
    for f in DATA_DIR.iterdir():
        if f.suffix.lower() == ".xlsx":
            xlsx_file = f
            break

    if xlsx_file is None:
        return None

    try:
        xls = pd.ExcelFile(xlsx_file)
        growth_data = {}
        for sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet)
            growth_data[normalize_text(sheet)] = df
        return growth_data
    except Exception:
        return None

with st.spinner("데이터 로딩 중..."):
    env_data = load_environment_data()
    growth_data = load_growth_data()

if not env_data or growth_data is None:
    st.error("데이터 파일을 찾을 수 없습니다. data 폴더를 확인하세요.")
    st.stop()

# =========================
# 메타 정보
# =========================
EC_CONDITIONS = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0
}

SCHOOLS = ["전체"] + list(EC_CONDITIONS.keys())

# =========================
# 사이드바
# =========================
selected_school = st.sidebar.selectbox("학교 선택", SCHOOLS)

# =========================
# 제목
# =========================
st.title("🌱 극지식물 최적 EC 농도 연구")

tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# =====================================================
# TAB 1 : 실험 개요
# =====================================================
with tab1:
    st.subheader("연구 배경 및 목적")
    st.markdown(
        """
        본 연구는 **EC 농도 차이**가 극지식물 생육에 미치는 영향을 분석하여  
        **최적 EC 조건**을 도출하는 것을 목표로 한다.
        """
    )

    overview_rows = []
    total_plants = 0
    for school, ec in EC_CONDITIONS.items():
        count = len(growth_data.get(school, []))
        total_plants += count
        overview_rows.append({
            "학교명": school,
            "EC 목표": ec,
            "개체수": count
        })

    st.dataframe(pd.DataFrame(overview_rows), use_container_width=True)

    avg_temp = pd.concat(env_data.values())["temperature"].mean()
    avg_hum = pd.concat(env_data.values())["humidity"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 개체수", total_plants)
    c2.metric("평균 온도(℃)", f"{avg_temp:.2f}")
    c3.metric("평균 습도(%)", f"{avg_hum:.2f}")
    c4.metric("최적 EC", "2.0 (하늘고)", delta="최대 생중량")

# =====================================================
# TAB 2 : 환경 데이터
# =====================================================
with tab2:
    st.subheader("학교별 환경 평균 비교")

    avg_env = []
    for school, df in env_data.items():
        avg_env.append({
            "학교": school,
            "temperature": df["temperature"].mean(),
            "humidity": df["humidity"].mean(),
            "ph": df["ph"].mean(),
            "ec": df["ec"].mean()
        })
    avg_env_df = pd.DataFrame(avg_env)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC")
    )

    fig.add_bar(x=avg_env_df["학교"], y=avg_env_df["temperature"], row=1, col=1)
    fig.add_bar(x=avg_env_df["학교"], y=avg_env_df["humidity"], row=1, col=2)
    fig.add_bar(x=avg_env_df["학교"], y=avg_env_df["ph"], row=2, col=1)
    fig.add_bar(x=avg_env_df["학교"], y=avg_env_df["ec"], name="실측 EC", row=2, col=2)
    fig.add_bar(
        x=list(EC_CONDITIONS.keys()),
        y=list(EC_CONDITIONS.values()),
        name="목표 EC",
        row=2, col=2
    )

    fig.update_layout(
        height=700,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig, use_container_width=True)

    if selected_school != "전체":
        df = env_data[selected_school]

        fig_ts = make_subplots(rows=3, cols=1, shared_xaxes=True,
                               subplot_titles=("온도 변화", "습도 변화", "EC 변화"))

        fig_ts.add_scatter(x=df["time"], y=df["temperature"], row=1, col=1)
        fig_ts.add_scatter(x=df["time"], y=df["humidity"], row=2, col=1)
        fig_ts.add_scatter(x=df["time"], y=df["ec"], row=3, col=1)

        fig_ts.add_hline(
            y=EC_CONDITIONS[selected_school],
            line_dash="dash",
            annotation_text="목표 EC",
            row=3, col=1
        )

        fig_ts.update_layout(
            height=800,
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
        )
        st.plotly_chart(fig_ts, use_container_width=True)

        with st.expander("환경 데이터 원본"):
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("CSV 다운로드", data=csv, file_name=f"{selected_school}_환경데이터.csv")

# =====================================================
# TAB 3 : 생육 결과
# =====================================================
with tab3:
    st.subheader("EC별 평균 생중량")

    summary = []
    for school, df in growth_data.items():
        summary.append({
            "학교": school,
            "EC": EC_CONDITIONS.get(school),
            "평균 생중량": df["생중량(g)"].mean(),
            "개체수": len(df)
        })
    summary_df = pd.DataFrame(summary)

    best = summary_df.loc[summary_df["평균 생중량"].idxmax()]

    st.metric(
        "🥇 최고 평균 생중량",
        f"{best['평균 생중량']:.2f} g",
        delta=f"EC {best['EC']} ({best['학교']})"
    )

    fig2 = make_subplots(rows=2, cols=2,
                         subplot_titles=("평균 생중량", "평균 잎 수", "평균 지상부 길이", "개체수"))

    fig2.add_bar(x=summary_df["학교"], y=summary_df["평균 생중량"], row=1, col=1)
    fig2.add_bar(
        x=summary_df["학교"],
        y=[growth_data[s]["잎 수(장)"].mean() for s in summary_df["학교"]],
        row=1, col=2
    )
    fig2.add_bar(
        x=summary_df["학교"],
        y=[growth_data[s]["지상부 길이(mm)"].mean() for s in summary_df["학교"]],
        row=2, col=1
    )
    fig2.add_bar(x=summary_df["학교"], y=summary_df["개체수"], row=2, col=2)

    fig2.update_layout(
        height=700,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig2, use_container_width=True)

    all_growth = []
    for school, df in growth_data.items():
        temp = df.copy()
        temp["학교"] = school
        all_growth.append(temp)
    all_growth_df = pd.concat(all_growth)

    fig_box = px.box(
        all_growth_df,
        x="학교",
        y="생중량(g)",
        color="학교"
    )
    fig_box.update_layout(
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig_box, use_container_width=True)

    fig_sc1 = px.scatter(all_growth_df, x="잎 수(장)", y="생중량(g)", color="학교")
    fig_sc2 = px.scatter(all_growth_df, x="지상부 길이(mm)", y="생중량(g)", color="학교")

    fig_sc1.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
    fig_sc2.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))

    st.plotly_chart(fig_sc1, use_container_width=True)
    st.plotly_chart(fig_sc2, use_container_width=True)

    with st.expander("생육 데이터 원본"):
        st.dataframe(all_growth_df, use_container_width=True)

        buffer = io.BytesIO()
        all_growth_df.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)

        st.download_button(
            "XLSX 다운로드",
            data=buffer,
            file_name="4개교_생육결과_통합.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
