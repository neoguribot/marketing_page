"""소니코리아 검색광고 마케팅 대시보드 (Streamlit)."""

from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data_loader import load_all

# ---- 팔레트 (dataviz 스킬 기본 팔레트) ----
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100",
    "#e87ba4", "#008300", "#4a3aa7", "#e34948",
)
INK_SECONDARY = "#52514e"
GRID = "#e1e0d9"

st.set_page_config(page_title="소니코리아 검색광고 대시보드", layout="wide", page_icon="📊")

PLOT_LAYOUT = dict(
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color="#0b0b0b", size=13),
    plot_bgcolor="#fcfcfb",
    paper_bgcolor="#fcfcfb",
    margin=dict(l=10, r=10, t=40, b=10),
    xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, tickfont=dict(color=INK_SECONDARY),
               title=dict(font=dict(color=INK_SECONDARY))),
    yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, tickfont=dict(color=INK_SECONDARY),
               title=dict(font=dict(color=INK_SECONDARY))),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                font=dict(color="#0b0b0b")),
)


@st.cache_data
def get_data():
    return load_all()


data = get_data()
daily = data["campaign_daily"]
keywords = data["keywords"]
search_terms = data["search_terms"]
ad_groups = data["ad_groups"]
device = data["device"]
hourly = data["hourly"]
meta = data["account_meta"]

# ---------------- 사이드바 ----------------
with st.sidebar:
    st.header("계정 정보")
    st.write(f"**업체**: {meta.get('업체', '-')}")
    st.write(f"**업종**: {meta.get('업종', '-')}")
    st.write(f"**캠페인**: {meta.get('캠페인', '-')}")
    st.write(f"**목표**: {meta.get('목표', '-')}")
    st.write(f"**입찰 전략**: {meta.get('입찰 전략', '-')}")
    st.write(f"**기간**: {meta.get('기간', '-')}")

min_d, max_d = daily["날짜"].min().date(), daily["날짜"].max().date()

st.title("소니코리아 검색광고 마케팅 대시보드")
st.markdown(
    f"<span style='color:{INK_SECONDARY};font-size:0.95em'>"
    f"데이터 기준: {meta.get('기간', '-')} · 네이버 검색광고 리포트</span>",
    unsafe_allow_html=True,
)

# ---------------- KPI (전체 기간 기준) ----------------
impressions = int(daily["노출수"].sum())
clicks = int(daily["클릭수"].sum())
cost = int(daily["비용"].sum())
purchases = daily["구매"].sum()
ctr = clicks / impressions * 100 if impressions else 0
cpa = cost / purchases if purchases else 0
avg_cpc = cost / clicks if clicks else 0

k1, k2, k3 = st.columns(3)
k1.metric("노출수", f"{impressions:,}")
k2.metric("클릭수", f"{clicks:,}")
k3.metric("CTR", f"{ctr:.2f}%")

k4, k5, k6 = st.columns(3)
k4.metric("총비용", f"₩{cost/10000:,.0f}만")
k5.metric("구매(전환)", f"{purchases:,.0f}건")
k6.metric("전환당비용(CPA)", f"₩{cpa:,.0f}")

st.divider()

# ---------------- 일별 성과 히트맵 ----------------
st.subheader("일별 성과 히트맵")
st.markdown(
    f"<span style='color:{INK_SECONDARY};font-size:0.9em'>"
    f"색은 지표별(열) 상대값입니다 — 진할수록 그 지표에서 상대적으로 높은 날입니다. "
    f"🌱 표시는 자동입찰 학습 기간(초반 7일)입니다. 정확한 값은 히트맵 아래 표를 참고하세요.</span>",
    unsafe_allow_html=True,
)

BLUE_SEQ = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
            "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
HEAT_COLORSCALE = [[i / (len(BLUE_SEQ) - 1), c] for i, c in enumerate(BLUE_SEQ)]
HEAT_METRICS = [
    ("노출수", "{:,.0f}"),
    ("클릭수", "{:,.0f}"),
    ("CTR", "{:.2f}%"),
    ("비용", "₩{:,.0f}"),
    ("구매", "{:,.0f}건"),
    ("전환율", "{:.2f}%"),
    ("전환당비용", "₩{:,.0f}"),
]

heat_df = daily.copy()
heat_df["전환당비용"] = heat_df["비용"] / heat_df["구매"].replace(0, float("nan"))
heat_df["날짜라벨"] = heat_df.apply(
    lambda r: ("🌱 " if r["학습 기간"] else "") + f"{r['날짜'].strftime('%m/%d')} ({r['요일']})", axis=1,
)

z_cols, text_cols = [], []
for name, fmt in HEAT_METRICS:
    col = heat_df[name]
    vmin, vmax = col.min(skipna=True), col.max(skipna=True)
    if pd.isna(vmin) or vmax == vmin:
        norm = col.apply(lambda v: 0.5 if pd.notna(v) else None)
    else:
        norm = ((col - vmin) / (vmax - vmin)).where(col.notna(), None)
    z_cols.append(norm.tolist())
    text_cols.append(col.apply(lambda v: fmt.format(v) if pd.notna(v) else "-").tolist())

heat_fig = go.Figure(go.Heatmap(
    x=[m for m, _ in HEAT_METRICS],
    y=heat_df["날짜라벨"],
    z=list(map(list, zip(*z_cols))),
    customdata=list(map(list, zip(*text_cols))),
    colorscale=HEAT_COLORSCALE,
    hovertemplate="%{y}<br>%{x}: %{customdata}<extra></extra>",
    xgap=2, ygap=2,
    showscale=False,
))
heat_layout = {**PLOT_LAYOUT, "yaxis": {**PLOT_LAYOUT["yaxis"], "autorange": "reversed"}}
heat_fig.update_layout(height=max(360, len(heat_df) * 22 + 60), **heat_layout)
st.plotly_chart(heat_fig, use_container_width=True)

with st.expander("일별 데이터 표로 보기"):
    show_df = heat_df[["날짜", "요일", "학습 기간", "노출수", "클릭수", "CTR", "비용", "구매", "전환율", "전환당비용"]]
    st.dataframe(show_df, use_container_width=True, hide_index=True)

st.divider()

# ---------------- 일별 추이 ----------------
st.subheader("일별 성과 추이")

filt_col1, filt_col2 = st.columns([1, 1.4])
with filt_col1:
    preset = st.radio(
        "기간 프리셋", ["전체 기간", "최근 7일", "최근 14일", "직접 선택"],
        index=0, horizontal=True, key="trend_preset",
    )
if preset == "전체 기간":
    date_range = (min_d, max_d)
elif preset == "최근 7일":
    date_range = (max(min_d, max_d - timedelta(days=6)), max_d)
elif preset == "최근 14일":
    date_range = (max(min_d, max_d - timedelta(days=13)), max_d)
else:
    with filt_col2:
        date_range = st.date_input(
            "날짜 범위 (달력에서 시작일·종료일 선택)",
            value=(min_d, max_d), min_value=min_d, max_value=max_d, key="trend_date_range",
        )

if len(date_range) == 2:
    start, end = date_range
    mask = (daily["날짜"].dt.date >= start) & (daily["날짜"].dt.date <= end)
    daily_f = daily.loc[mask]
else:
    daily_f = daily

c1, c2 = st.columns(2)

with c1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daily_f["날짜"], y=daily_f["노출수"], name="노출수",
                              mode="lines", line=dict(color=BLUE, width=2)))
    fig.update_layout(title="노출수 추이", **PLOT_LAYOUT)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daily_f["날짜"], y=daily_f["클릭수"], name="클릭수",
                              mode="lines", line=dict(color=ORANGE, width=2)))
    fig.update_layout(title="클릭수 추이", **PLOT_LAYOUT)
    st.plotly_chart(fig, use_container_width=True)

c3, c4 = st.columns(2)
with c3:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=daily_f["날짜"], y=daily_f["비용"], name="비용", marker_color=AQUA))
    fig.update_layout(title="일별 비용", **PLOT_LAYOUT)
    st.plotly_chart(fig, use_container_width=True)

with c4:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=daily_f["날짜"], y=daily_f["구매"], name="구매", marker_color=VIOLET))
    fig.update_layout(title="일별 구매(전환)", **PLOT_LAYOUT)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------- 기간 비교 모니터링 ----------------
st.subheader("기간 비교 모니터링")
st.markdown(
    f"<span style='color:{INK_SECONDARY};font-size:0.9em'>"
    f"두 기간을 각각 선택하면 핵심 지표와 추이를 나란히 비교합니다. "
    f"증감률은 기간 A 대비 기간 B 기준입니다.</span>",
    unsafe_allow_html=True,
)

span_days = (max_d - min_d).days + 1
mid_d = min_d + timedelta(days=span_days // 2)
default_a = (min_d, mid_d - timedelta(days=1)) if mid_d > min_d else (min_d, min_d)
default_b = (mid_d, max_d)

pa_col, pb_col = st.columns(2)
with pa_col:
    period_a = st.date_input(
        "기간 A", value=default_a, min_value=min_d, max_value=max_d, key="period_a",
    )
with pb_col:
    period_b = st.date_input(
        "기간 B", value=default_b, min_value=min_d, max_value=max_d, key="period_b",
    )


def _summarize(df: pd.DataFrame) -> dict:
    imp = int(df["노출수"].sum())
    clk = int(df["클릭수"].sum())
    cost_sum = int(df["비용"].sum())
    buy = float(df["구매"].sum())
    return dict(
        days=len(df), impressions=imp, clicks=clk, cost=cost_sum, purchases=buy,
        ctr=clk / imp * 100 if imp else 0.0,
        cvr=buy / clk * 100 if clk else 0.0,
        cpa=cost_sum / buy if buy else 0.0,
    )


def _delta_pct(base: float, new: float):
    if not base:
        return None
    return (new - base) / base * 100


if len(period_a) == 2 and len(period_b) == 2:
    a_start, a_end = period_a
    b_start, b_end = period_b
    sub_a = daily[(daily["날짜"].dt.date >= a_start) & (daily["날짜"].dt.date <= a_end)]
    sub_b = daily[(daily["날짜"].dt.date >= b_start) & (daily["날짜"].dt.date <= b_end)]

    if sub_a.empty or sub_b.empty:
        st.info("선택한 기간 중 데이터가 없는 구간이 있습니다. 날짜를 다시 선택해주세요.")
    else:
        sa, sb = _summarize(sub_a), _summarize(sub_b)
        st.markdown(
            f"<span style='color:{INK_SECONDARY};font-size:0.85em'>"
            f"기간 A: {a_start} ~ {a_end} ({sa['days']}일) &nbsp;|&nbsp; "
            f"기간 B: {b_start} ~ {b_end} ({sb['days']}일)</span>",
            unsafe_allow_html=True,
        )

        metric_defs = [
            ("노출수", "impressions", "{:,.0f}", "normal"),
            ("클릭수", "clicks", "{:,.0f}", "normal"),
            ("CTR", "ctr", "{:.2f}%", "normal"),
            ("총비용", "cost", "₩{:,.0f}", "inverse"),
            ("구매", "purchases", "{:,.0f}건", "normal"),
            ("전환율", "cvr", "{:.2f}%", "normal"),
            ("CPA", "cpa", "₩{:,.0f}", "inverse"),
        ]
        cmp_cols = st.columns(len(metric_defs))
        for col, (label, key, fmt, dcolor) in zip(cmp_cols, metric_defs):
            delta = _delta_pct(sa[key], sb[key])
            col.metric(
                label, fmt.format(sb[key]),
                delta=f"{delta:+.1f}%" if delta is not None else "N/A",
                delta_color=dcolor,
            )

        metric_choice = st.selectbox(
            "추이 비교 지표", ["노출수", "클릭수", "비용", "구매", "CTR", "전환율"], key="cmp_metric",
        )
        sub_a2 = sub_a.assign(경과일=(sub_a["날짜"] - pd.Timestamp(a_start)).dt.days + 1)
        sub_b2 = sub_b.assign(경과일=(sub_b["날짜"] - pd.Timestamp(b_start)).dt.days + 1)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=sub_a2["경과일"], y=sub_a2[metric_choice], name=f"기간 A ({a_start}~{a_end})",
            mode="lines+markers", line=dict(color=BLUE, width=2), marker=dict(size=6),
            hovertemplate="경과일 %{x}일<br>" + metric_choice + " %{y}<extra>기간 A</extra>",
        ))
        fig.add_trace(go.Scatter(
            x=sub_b2["경과일"], y=sub_b2[metric_choice], name=f"기간 B ({b_start}~{b_end})",
            mode="lines+markers", line=dict(color=ORANGE, width=2), marker=dict(size=6),
            hovertemplate="경과일 %{x}일<br>" + metric_choice + " %{y}<extra>기간 B</extra>",
        ))
        cmp_layout = {
            **PLOT_LAYOUT,
            "margin": dict(l=10, r=10, t=40, b=10),
            "legend": dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5,
                           font=dict(color="#0b0b0b")),
        }
        fig.update_layout(
            title=f"{metric_choice} 추이 비교 (경과일 기준)", xaxis_title="경과일",
            **cmp_layout,
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("기간 A와 기간 B 각각 시작일과 종료일을 선택해주세요.")

st.divider()

# ---------------- 기기 / 시간대 ----------------
st.subheader("기기 · 시간대별 성과")
c5, c6 = st.columns([1, 2])

with c5:
    fig = go.Figure(go.Pie(
        labels=device["값"], values=device["노출수"],
        marker=dict(colors=[BLUE, ORANGE, AQUA]),
        hole=0.5,
    ))
    pie_layout = {k: v for k, v in PLOT_LAYOUT.items() if k not in ("xaxis", "yaxis", "legend")}
    fig.update_layout(
        title="기기별 노출수 비중",
        legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5),
        **pie_layout,
    )
    st.plotly_chart(fig, use_container_width=True)

with c6:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=hourly["시"], y=hourly["클릭수"], name="클릭수", marker_color=BLUE))
    fig.update_layout(title="시간대별 클릭수", xaxis_title="시", **PLOT_LAYOUT)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------- 키워드 / 검색어 ----------------
st.subheader("키워드 성과")
top_kw = keywords.sort_values("비용", ascending=False)
kw_layout = {**PLOT_LAYOUT, "yaxis": {**PLOT_LAYOUT["yaxis"], "autorange": "reversed"}}
fig = go.Figure(go.Bar(
    x=top_kw["비용"], y=top_kw["키워드"], orientation="h", marker_color=BLUE,
))
fig.update_layout(title="키워드별 비용", **kw_layout)
st.plotly_chart(fig, use_container_width=True)

st.dataframe(
    keywords[["키워드", "광고그룹", "검색유형", "품질평가점수", "노출수", "클릭수", "CTR", "평균 CPC", "비용", "구매", "전환율"]]
    .sort_values("비용", ascending=False),
    use_container_width=True, hide_index=True,
)

with st.expander("검색어 리포트 보기"):
    st.dataframe(search_terms.sort_values("비용", ascending=False), use_container_width=True, hide_index=True)

with st.expander("광고그룹 요약 보기"):
    st.dataframe(ad_groups, use_container_width=True, hide_index=True)
