import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from scipy.stats import pearsonr
import pydeck as pdk
import matplotlib.pyplot as plt
from matplotlib import patches
import matplotlib.font_manager as fm

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'  # 윈도우 기본 한글 폰트
plt.rcParams['axes.unicode_minus'] = False     # 음수 깨짐 방지

from streamlit_option_menu import option_menu

# 🛠️ 페이지 설정
st.set_page_config(page_title="EV 인프라 분석", layout="wide")

#  샘플 데이터 생성
regions = {
    "서울": [37.5665, 126.9780],
    "부산": [35.1796, 129.0756],
    "대구": [35.8714, 128.6014],
    "광주": [35.1595, 126.8526],
    "인천": [37.4563, 126.7052]
}

np.random.seed(42)
months = pd.date_range(start="2022-01", periods=24, freq="ME").to_pydatetime()
data = []
for region, (lat, lon) in regions.items():
    for month in months:
        data.append({
            "지역": region,
            "월": month,
            "전기차등록수": np.random.randint(1500, 5000),
            "충전기수": np.random.randint(300, 900),
            "충전소수": np.random.randint(50, 200),
            "위도": lat,
            "경도": lon
        })
df = pd.DataFrame(data)
df["월"] = pd.to_datetime(df["월"])

# 🔥 임의 히트맵용 충전소 위치 생성
points = []
for _ in range(50):
    region = np.random.choice(list(regions.keys()))
    lat_c, lon_c = regions[region]
    lat = lat_c + np.random.normal(0, 0.03)
    lon = lon_c + np.random.normal(0, 0.03)
    points.append({"지역": region, "lat": lat, "lon": lon})
heatmap_df = pd.DataFrame(points)

#  사이드바 메뉴 (옵션 메뉴)
with st.sidebar:
    selected = option_menu(
        menu_title="분석 항목",
        options=[
            "메인", "커뮤니티 분석", "지역별 EV 인프라 현황",
            "인프라 진단", "상관분석", "결론"
        ],
        icons=["house", "people", "map", "tools", "graph-up", "patch-check"],
        default_index=0,
        orientation="vertical"
    )

# 🎛️ 필터 영역
st.sidebar.markdown("### 지역 및 연도 필터")

# ✅ 체크박스 그리드 (2열)
st.sidebar.markdown("**지역 선택**")

cols = st.sidebar.columns(2)
selected_regions = []

region_list = list(regions.keys())
for idx, region in enumerate(region_list):
    col = cols[idx % 2]
    if col.checkbox(region, value=True):
        selected_regions.append(region)

# ✅ 연도 슬라이더
df["연도"] = df["월"].dt.year
min_year, max_year = int(df["연도"].min()), int(df["연도"].max())

start_year, end_year = st.sidebar.slider(
    "연도 선택 (범위)", min_value=min_year, max_value=max_year,
    value=(min_year, max_year), step=1
)

# 📌 필터링
filtered_df = df[
    (df["지역"].isin(selected_regions)) &
    (df["연도"] >= start_year) & (df["연도"] <= end_year)
]

# 📍 페이지별 콘텐츠
if selected == "메인":
    st.title("EV 인프라 분석 대시보드")
    st.markdown("""
    이 대시보드는 전기차 등록 수와 충전 인프라(충전소/충전기) 간의 관계를 분석하고,
    지역별 진단과 시사점을 제공합니다.

    왼쪽 메뉴에서 항목을 선택해 탐색을 시작하세요!
    """)

elif selected == "커뮤니티 분석":
    st.title("커뮤니티 기반 EV 분석")
    st.info("현재 샘플 데이터에는 커뮤니티 정보가 없어 분석 탭만 구성됨 (실데이터 반영 시 확장 가능)")

elif selected == "지역별 EV 인프라 현황":
    st.title("지역별 EV 및 충전기 현황")
    for region in selected_regions:
        r_df = filtered_df[filtered_df["지역"] == region]
        if r_df.empty: continue
        st.subheader(f" {region}")
        st.area_chart(r_df.set_index("월")[["전기차등록수", "충전기수"]])

elif selected == "인프라 진단":

    st.title("인프라 적정성 진단")

    #  최신월 기준 데이터 필터링
    latest = filtered_df["월"].max()
    latest_df = filtered_df[filtered_df["월"] == latest]

    # 💡 진단 지표 계산
    diagnosis_rows = []
    for region in selected_regions:
        row = latest_df[latest_df["지역"] == region]
        if not row.empty:
            ev = int(row["전기차등록수"].values[0])
            chargers = int(row["충전기수"].values[0])
            ratio = ev / chargers if chargers else None
            diagnosis_rows.append({
                "지역": region,
                "전기차등록수": ev,
                "충전기수": chargers,
                "EV/충전기": f"{ratio:.2f} 대/기" if ratio else "N/A"
            })

    diagnosis_df = pd.DataFrame(diagnosis_rows)
    ev_values = diagnosis_df["전기차등록수"]
    labels = [
        f"{row['지역']} ({row['EV/충전기']})"
        for _, row in diagnosis_df.iterrows()
    ]
    total_ev = ev_values.sum()

    # 탭 구성
    tab1, tab2, tab3, tab4, tab5, tab6, tap7 = st.tabs([
        "진단 표",
        "현재(파이 차트)",
        "현재(도넛 차트)",
        "다중도넛 차트",
        "다중도넛 차트2",
        "도넛증감률 차트",
        "연도별 변화 비교"])

    with tab1:
        st.subheader("지역별 인프라 적정성 지표")
        st.table(diagnosis_df)

    with tab2:
        st.subheader("전기차 등록 비율 (파이 차트)")
        fig1, ax1 = plt.subplots()
        ax1.pie(ev_values, labels=labels, autopct="%1.1f%%", startangle=90)
        ax1.axis("equal")
        st.pyplot(fig1)

    with tab3:
        st.subheader("전기차 등록 비율 (도넛 차트)")
        fig2, ax2 = plt.subplots()
        wedges, texts, autotexts = ax2.pie(
            ev_values,
            labels=labels,
            autopct="%1.1f%%",
            startangle=90,
            wedgeprops=dict(width=0.7)
        )
        ax2.axis("equal")
        ax2.text(0, 0, f"{total_ev:,}\n대", ha='center', va='center', fontsize=14, weight='bold')
        st.pyplot(fig2)
    
    with tab4:
        # 예제 데이터
        labels_outer = ['서울', '부산', '대구']
        sizes_outer = [3000, 2500, 1500]

        labels_inner = ['급속', '완속', '급속', '완속', '급속', '완속']
        sizes_inner = [1800, 1200, 1500, 1000, 900, 600]

        # 스타일 설정
        fig, ax = plt.subplots()
        ax.axis('equal')

        # 바깥쪽 도넛 (전기차 등록 수)
        outer, _ = ax.pie(sizes_outer, radius=1.2, labels=labels_outer, labeldistance=0.8,
                        wedgeprops=dict(width=0.3, edgecolor='w'), startangle=90)

        # 안쪽 도넛 (충전소 유형)
        inner, _ = ax.pie(sizes_inner, radius=0.9,
                        labels=labels_inner, labeldistance=0.6,
                        wedgeprops=dict(width=0.3, edgecolor='w'), startangle=90)

        st.pyplot(fig)

    with tab5:

        st.subheader("🍥 지역별 EV/충전소 게이지형 도넛 비교")

        # 최신 월 데이터
        latest = filtered_df["월"].max()
        latest_df = filtered_df[filtered_df["월"] == latest]

        # 사용할 지역 필터링
        regions = [r for r in ["서울", "부산", "대구", "광주", "인천"] if r in selected_regions]
        data = []
        ev_list = []
        ch_list = []

        for region in regions:
            row = latest_df[latest_df["지역"] == region]
            if not row.empty:
                ev = int(row["전기차등록수"].values[0])
                ch = int(row["충전소수"].values[0])
                data.append((region, ev, ch))
                ev_list.append(ev)
                ch_list.append(ch)

        # 기준값: 각각 따로 스케일링
        max_ev = max(ev_list) * 1.1
        max_ch = max(ch_list) * 1.1

        # 시각화: 270도 기준 게이지형 도넛
        fig, axs = plt.subplots(1, len(data), figsize=(len(data) * 2.6, 3.5), constrained_layout=True)
        if len(data) == 1:
            axs = [axs]

        for ax, (region, ev, ch) in zip(axs, data):
            ax.set_aspect("equal")
            ax.set_xlim(-1.2, 1.2)
            ax.set_ylim(-1.2, 1.2)
            ax.axis('off')

            # 각도 계산 (최대값 대비 270도 비율)
            ev_theta = (ev / max_ev) * 270
            ch_theta = (ch / max_ch) * 270

            # EV 바깥 도넛
            ax.add_patch(patches.Wedge(
                (0, 0), r=1.0,
                theta1=135, theta2=135 + ev_theta,
                width=0.22, facecolor="#4F81BD", alpha=0.9
            ))

            # 충전소 안쪽 도넛
            ax.add_patch(patches.Wedge(
                (0, 0), r=0.7,
                theta1=135, theta2=135 + ch_theta,
                width=0.22, facecolor="#C0504D", alpha=0.85
            ))

            # 라벨 표시
            ax.text(0, -1.1, region, ha='center', va='top', fontsize=10, weight='bold')
            ax.text(0, -1.3, f"EV: {ev:,}", ha='center', fontsize=9, color="#4F81BD")
            ax.text(0, -1.45, f"충전소: {ch:,}", ha='center', fontsize=9, color="#C0504D")

        st.pyplot(fig)

    with tab6:
        st.subheader("📈 전월 대비 EV 등록수 증감률 (도넛 스타일)")

        # 최신 월과 전월 필터링
        latest = filtered_df["월"].max()
        prev = latest - pd.DateOffset(months=1)

        regions = [r for r in ["서울", "부산", "대구", "광주", "인천"] if r in selected_regions]
        data = []

        for region in regions:
            latest_row = filtered_df[(filtered_df["월"] == latest) & (filtered_df["지역"] == region)]
            prev_row = filtered_df[(filtered_df["월"] == prev) & (filtered_df["지역"] == region)]

            if not latest_row.empty and not prev_row.empty:
                ev_latest = int(latest_row["전기차등록수"].values[0])
                ev_prev = int(prev_row["전기차등록수"].values[0])
                if ev_prev > 0:
                    delta = ((ev_latest - ev_prev) / ev_prev) * 100
                else:
                    delta = 0
                data.append((region, ev_latest, delta))

        # 그래프 생성
        fig, axs = plt.subplots(1, len(data), figsize=(len(data) * 2.5, 3.2), constrained_layout=True)

        if len(data) == 1:
            axs = [axs]

        for ax, (region, val, delta) in zip(axs, data):
            ax.set_aspect("equal")
            ax.set_xlim(-1.2, 1.2)
            ax.set_ylim(-1.2, 1.2)
            ax.axis("off")

            angle = min(abs(delta), 100) / 100 * 270  # 최대 270도로 제한

            color = "#4F81BD" if delta >= 0 else "#C0504D"

            # 증감률 원호
            arc = patches.Wedge(center=(0, 0), r=1.0,
                                theta1=135, theta2=135 + angle,
                                width=0.3, facecolor=color, alpha=0.9)
            ax.add_patch(arc)

            # 중앙 텍스트
            ax.text(0, 0.2, f"{delta:+.1f}%", ha='center', fontsize=13, fontweight='bold')
            ax.text(0, -0.3, f"EV: {val:,}", ha='center', fontsize=10)
            ax.set_title(region, fontsize=11)

        st.pyplot(fig)

    with tap7:
        st.subheader(" 지역별 연도별 전기차 및 충전소 변화")

        #  연도 단위로 집계
        df_year = df.copy()
        df_year["연도"] = df_year["월"].dt.year

        region_year_summary = df_year[df_year["지역"].isin(selected_regions)].groupby(
            ["지역", "연도"]
        )[["전기차등록수", "충전소수"]].sum().reset_index()

        # 지역별 그래프
        for region in selected_regions:
            r_df = region_year_summary[region_year_summary["지역"] == region]
            if r_df.empty:
                continue
            st.markdown(f"#### 📍 {region}")
            st.line_chart(
                r_df.set_index("연도")[["전기차등록수", "충전소수"]]
            )


elif selected == "상관분석":
    st.title(" EV ↔ 충전기 상관관계")
    for region in selected_regions:
        r_df = filtered_df[filtered_df["지역"] == region]
        if len(r_df) >= 2:
            corr, _ = pearsonr(r_df["전기차등록수"], r_df["충전기수"])
            st.markdown(f"✅ **{region}** 상관계수: **{corr:.2f}**")
            fig, ax = plt.subplots()
            ax.scatter(r_df["전기차등록수"], r_df["충전기수"], alpha=0.7)
            ax.set_xlabel("전기차 등록 수")
            ax.set_ylabel("충전기 수")
            ax.set_title(f"{region} 산점도")
            m, b = np.polyfit(r_df["전기차등록수"], r_df["충전기수"], 1)
            ax.plot(r_df["전기차등록수"], m * r_df["전기차등록수"] + b, color="red")
            st.pyplot(fig)
        else:
            st.warning(f" {region} - 데이터 부족")

elif selected == "결론":
    st.title(" 결론 및 제언")
    st.markdown("""
    - ✅ **충전기 수와 전기차 등록 수는 지역에 따라 상관관계가 상이함**
    - ⚠️ 일부 지역은 인프라가 빠르게 늘었음에도 차량 수 증가가 지체됨 (시차 분석 필요)
    - 📍 향후에는 **EV 수요 예측 기반 인프라 확충 계획**이 필요
    """)
