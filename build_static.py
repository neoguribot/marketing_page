"""Streamlit 대시보드를 GitHub Pages용 정적 HTML(docs/index.html)로 빌드.

날짜 필터·기간 비교는 Python 서버 없이 브라우저 내 JS(Plotly.js)로 동작하도록
데이터를 JSON으로 통째로 임베드한다.
"""

import json
from pathlib import Path

from data_loader import load_all

OUT_DIR = Path(__file__).parent / "docs"

BLUE, ORANGE, AQUA, VIOLET = "#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7"
INK_SECONDARY = "#52514e"
HEAT_COLORS = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
               "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]


def build_json_payload(data: dict) -> str:
    daily = data["campaign_daily"]
    daily_records = [
        {
            "date": row["날짜"].strftime("%Y-%m-%d"),
            "weekday": row["요일"],
            "learning": bool(row["학습 기간"]),
            "impressions": int(row["노출수"]),
            "clicks": int(row["클릭수"]),
            "ctr": float(row["CTR"]),
            "cost": int(row["비용"]),
            "purchases": float(row["구매"]),
            "cvr": float(row["전환율"]),
            "cpa": None if row["구매"] == 0 else round(row["비용"] / row["구매"]),
        }
        for _, row in daily.iterrows()
    ]
    device_records = [
        {"name": row["값"], "impressions": int(row["노출수"])}
        for _, row in data["device"].iterrows()
    ]
    hourly_records = [
        {"hour": int(row["시"]), "clicks": int(row["클릭수"])}
        for _, row in data["hourly"].sort_values("시").iterrows()
    ]
    return json.dumps(
        {"daily": daily_records, "device": device_records, "hourly": hourly_records},
        ensure_ascii=False,
    )


def render_table(df, columns) -> str:
    head = "".join(f"<th>{c}</th>" for c in columns)
    body_rows = []
    for _, r in df.iterrows():
        cells = "".join(f"<td>{r[c]}</td>" for c in columns)
        body_rows.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def main():
    data = load_all()
    daily = data["campaign_daily"]
    keywords = data["keywords"].sort_values("비용", ascending=False)
    search_terms = data["search_terms"].sort_values("비용", ascending=False)
    ad_groups = data["ad_groups"]
    meta = data["account_meta"]

    impressions = int(daily["노출수"].sum())
    clicks = int(daily["클릭수"].sum())
    cost = int(daily["비용"].sum())
    purchases = daily["구매"].sum()
    ctr = clicks / impressions * 100 if impressions else 0
    cpa = cost / purchases if purchases else 0

    kw_table = render_table(
        keywords[["키워드", "광고그룹", "검색유형", "품질평가점수", "노출수", "클릭수", "CTR", "평균 CPC", "비용", "구매", "전환율"]],
        ["키워드", "광고그룹", "검색유형", "품질평가점수", "노출수", "클릭수", "CTR", "평균 CPC", "비용", "구매", "전환율"],
    )
    st_table = render_table(
        search_terms,
        ["검색어", "관련도", "일치 키워드", "광고그룹", "검색유형", "노출수", "클릭수", "CTR", "비용", "구매"],
    )
    ag_table = render_table(
        ad_groups,
        ["광고그룹", "키워드 수", "평균 품질평가점수", "노출수", "클릭수", "CTR", "평균 CPC", "비용", "구매"],
    )

    daily_disp = daily.copy()
    daily_disp["전환당비용"] = (daily_disp["비용"] / daily_disp["구매"].replace(0, float("nan"))).round(0)
    daily_disp["학습 기간"] = daily_disp["학습 기간"].map({True: "🌱", False: ""})
    daily_disp["날짜"] = daily_disp["날짜"].dt.strftime("%Y-%m-%d")
    daily_table = render_table(
        daily_disp,
        ["날짜", "요일", "학습 기간", "노출수", "클릭수", "CTR", "비용", "구매", "전환율", "전환당비용"],
    )
    heatmap_height = max(360, len(daily) * 22 + 60)

    payload = build_json_payload(data)
    min_date = daily["날짜"].min().strftime("%Y-%m-%d")
    max_date = daily["날짜"].max().strftime("%Y-%m-%d")

    html = HTML_TEMPLATE.format(
        meta_company=meta.get("업체", "-"),
        meta_industry=meta.get("업종", "-"),
        meta_campaign=meta.get("캠페인", "-"),
        meta_goal=meta.get("목표", "-"),
        meta_bid=meta.get("입찰 전략", "-"),
        meta_period=meta.get("기간", "-"),
        impressions=f"{impressions:,}",
        clicks=f"{clicks:,}",
        ctr=f"{ctr:.2f}%",
        cost=f"₩{cost/10000:,.0f}만",
        purchases=f"{purchases:,.0f}건",
        cpa=f"₩{cpa:,.0f}",
        kw_chart_data=json.dumps(
            {"labels": keywords["키워드"].tolist(), "values": keywords["비용"].tolist()},
            ensure_ascii=False,
        ),
        kw_table=kw_table,
        st_table=st_table,
        ag_table=ag_table,
        daily_table=daily_table,
        heatmap_height=heatmap_height,
        payload=payload,
        min_date=min_date,
        max_date=max_date,
        BLUE=BLUE, ORANGE=ORANGE, AQUA=AQUA, VIOLET=VIOLET,
        INK_SECONDARY=INK_SECONDARY,
        heat_colorscale=json.dumps(HEAT_COLORS, ensure_ascii=False),
    )

    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "index.html").write_text(html, encoding="utf-8")
    print(f"Wrote {OUT_DIR / 'index.html'} ({len(html):,} bytes)")


HTML_TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>소니코리아 검색광고 마케팅 대시보드</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  :root {{
    --surface: #fcfcfb; --page: #f9f9f7; --ink: #0b0b0b; --ink2: {INK_SECONDARY};
    --grid: #e1e0d9; --border: rgba(11,11,11,0.10);
    --blue: {BLUE}; --orange: {ORANGE}; --aqua: {AQUA}; --violet: {VIOLET};
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--page); color: var(--ink);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  }}
  .wrap {{ max-width: 1180px; margin: 0 auto; padding: 32px 20px 80px; }}
  h1 {{ font-size: 2rem; margin: 0 0 4px; }}
  h2 {{ font-size: 1.3rem; margin: 40px 0 14px; border-top: 1px solid var(--grid); padding-top: 28px; }}
  .meta {{ color: var(--ink2); font-size: 0.95em; margin-bottom: 24px; }}
  .banner {{
    background: #eef4fc; border: 1px solid #cfe0f5; border-radius: 8px;
    padding: 12px 16px; font-size: 0.9em; color: var(--ink2); margin-bottom: 24px;
  }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px 24px; }}
  .kpi-grid .label {{ color: var(--ink2); font-size: 0.85em; }}
  .kpi-grid .value {{ font-size: 1.7rem; font-weight: 600; }}
  .card {{
    border: 1px solid var(--border); border-radius: 8px; padding: 16px 18px;
    margin-bottom: 14px; background: var(--surface);
  }}
  .badge {{
    display: inline-block; color: white; padding: 2px 8px; border-radius: 4px;
    font-size: 0.78em; font-weight: 600; margin-right: 8px;
  }}
  .card p {{ margin: 8px 0; }}
  .note-row {{ display: flex; gap: 24px; flex-wrap: wrap; font-size: 0.9em; color: var(--ink2); }}
  .chart-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
  .chart {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 8px; }}
  .controls {{ display: flex; gap: 20px; align-items: center; flex-wrap: wrap; margin-bottom: 16px; font-size: 0.92em; }}
  .controls label {{ color: var(--ink2); margin-right: 6px; }}
  button.preset {{
    border: 1px solid var(--border); background: var(--surface); border-radius: 999px;
    padding: 6px 14px; cursor: pointer; font-size: 0.88em; color: var(--ink);
  }}
  button.preset.active {{ background: var(--blue); color: white; border-color: var(--blue); }}
  input[type="date"], select {{
    border: 1px solid var(--border); border-radius: 6px; padding: 5px 8px; font-size: 0.9em;
  }}
  .cmp-grid {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 14px; margin: 18px 0; }}
  .cmp-grid .label {{ color: var(--ink2); font-size: 0.8em; }}
  .cmp-grid .value {{ font-size: 1.25rem; font-weight: 600; }}
  .cmp-grid .delta {{ font-size: 0.82em; font-weight: 600; }}
  .delta.up {{ color: #0ca30c; }} .delta.down {{ color: #d03b3b; }} .delta.flat {{ color: var(--ink2); }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
  th, td {{ text-align: right; padding: 7px 10px; border-bottom: 1px solid var(--grid); white-space: nowrap; }}
  th:first-child, td:first-child {{ text-align: left; }}
  th {{ color: var(--ink2); font-weight: 600; }}
  .table-wrap {{ overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; }}
  details {{ margin-top: 14px; border: 1px solid var(--border); border-radius: 8px; padding: 10px 14px; }}
  summary {{ cursor: pointer; font-weight: 600; }}
  footer {{ margin-top: 60px; color: var(--ink2); font-size: 0.85em; }}
  @media (max-width: 760px) {{
    .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .chart-grid {{ grid-template-columns: 1fr; }}
    .cmp-grid {{ grid-template-columns: repeat(3, 1fr); }}
  }}
</style>
</head>
<body>
<div class="wrap">
  <h1>소니코리아 검색광고 마케팅 대시보드</h1>
  <div class="meta">데이터 기준: {meta_period} · 네이버 검색광고 리포트 · 업체: {meta_company} · 업종: {meta_industry} · 목표: {meta_goal} · 입찰 전략: {meta_bid}</div>
  <div class="banner">이 페이지는 정적 스냅샷입니다. 날짜 필터와 기간 비교는 이 페이지에 포함된 데이터({min_date} ~ {max_date}) 범위 내에서 브라우저가 즉시 계산합니다. 원본 Streamlit 앱 소스코드는 이 저장소의 app.py를 참고하세요.</div>

  <div class="kpi-grid">
    <div><div class="label">노출수</div><div class="value">{impressions}</div></div>
    <div><div class="label">클릭수</div><div class="value">{clicks}</div></div>
    <div><div class="label">CTR</div><div class="value">{ctr}</div></div>
    <div><div class="label">총비용</div><div class="value">{cost}</div></div>
    <div><div class="label">구매(전환)</div><div class="value">{purchases}</div></div>
    <div><div class="label">전환당비용(CPA)</div><div class="value">{cpa}</div></div>
  </div>

  <h2>일별 성과 히트맵</h2>
  <div class="meta" style="margin-bottom:14px">색은 지표별(열) 상대값입니다 — 진할수록 그 지표에서 상대적으로 높은 날입니다. 🌱 표시는 자동입찰 학습 기간(초반 7일)입니다. 정확한 값은 히트맵 아래 표를 참고하세요.</div>
  <div class="chart" id="chart-heatmap" style="height:{heatmap_height}px"></div>
  <details><summary>일별 데이터 표로 보기</summary><div class="table-wrap">{daily_table}</div></details>

  <h2>일별 성과 추이</h2>
  <div class="controls">
    <span>
      <button class="preset active" data-preset="all">전체 기간</button>
      <button class="preset" data-preset="7">최근 7일</button>
      <button class="preset" data-preset="14">최근 14일</button>
    </span>
    <span><label>직접 선택</label><input type="date" id="trendStart" min="{min_date}" max="{max_date}" value="{min_date}"> ~
      <input type="date" id="trendEnd" min="{min_date}" max="{max_date}" value="{max_date}"></span>
  </div>
  <div class="chart-grid">
    <div class="chart" id="chart-impressions" style="height:320px"></div>
    <div class="chart" id="chart-clicks" style="height:320px"></div>
    <div class="chart" id="chart-cost" style="height:320px"></div>
    <div class="chart" id="chart-purchases" style="height:320px"></div>
  </div>

  <h2>기간 비교 모니터링</h2>
  <div class="controls">
    <span><label>기간 A</label><input type="date" id="aStart" min="{min_date}" max="{max_date}"> ~ <input type="date" id="aEnd" min="{min_date}" max="{max_date}"></span>
    <span><label>기간 B</label><input type="date" id="bStart" min="{min_date}" max="{max_date}"> ~ <input type="date" id="bEnd" min="{min_date}" max="{max_date}"></span>
    <span><label>추이 비교 지표</label>
      <select id="cmpMetric">
        <option value="impressions">노출수</option>
        <option value="clicks">클릭수</option>
        <option value="cost">비용</option>
        <option value="purchases">구매</option>
        <option value="ctr">CTR</option>
        <option value="cvr">전환율</option>
      </select>
    </span>
  </div>
  <div class="cmp-grid" id="cmpGrid"></div>
  <div class="chart" id="chart-cmp" style="height:360px"></div>

  <h2>기기 · 시간대별 성과</h2>
  <div class="chart-grid">
    <div class="chart" id="chart-device" style="height:320px"></div>
    <div class="chart" id="chart-hourly" style="height:320px"></div>
  </div>

  <h2>키워드 성과</h2>
  <div class="chart" id="chart-keywords" style="height:420px"></div>
  <div class="table-wrap">{kw_table}</div>

  <details><summary>검색어 리포트 보기</summary><div class="table-wrap">{st_table}</div></details>
  <details><summary>광고그룹 요약 보기</summary><div class="table-wrap">{ag_table}</div></details>

  <footer>소니코리아 검색광고 마케팅 대시보드 &middot; 정적 스냅샷 (GitHub Pages)</footer>
</div>

<script>
const DATA = {payload};
const KW_CHART = {kw_chart_data};
const COLORS = {{ blue: "{BLUE}", orange: "{ORANGE}", aqua: "{AQUA}", violet: "{VIOLET}" }};
const INK = "#0b0b0b", INK2 = "{INK_SECONDARY}", GRID = "#e1e0d9", SURFACE = "#fcfcfb";
const HEAT_SEQ = {heat_colorscale};
const HEAT_COLORSCALE = HEAT_SEQ.map((c,i) => [i/(HEAT_SEQ.length-1), c]);

function baseLayout(opts) {{
  opts = opts || {{}};
  // 매 호출마다 새 객체를 만든다: Plotly가 렌더링 시 layout 객체(특히 xaxis/yaxis)를
  // 직접 변형(type 추론 등)하므로, 객체를 공유하면 날짜 축 차트의 변형이 숫자 축
  // 차트로 새어나가는 버그가 생긴다 (예: 시간대 0~23이 1970~2020 날짜로 표시됨).
  return {{
    title: opts.title,
    font: {{ family: "system-ui, -apple-system, 'Segoe UI', sans-serif", color: INK, size: 13 }},
    plot_bgcolor: SURFACE, paper_bgcolor: SURFACE,
    margin: {{ l: 40, r: 10, t: 40, b: 30 }},
    xaxis: Object.assign({{ gridcolor: GRID, zerolinecolor: GRID, tickfont: {{ color: INK2 }} }}, opts.xaxis || {{}}),
    yaxis: Object.assign({{ gridcolor: GRID, zerolinecolor: GRID, tickfont: {{ color: INK2 }} }}, opts.yaxis || {{}}),
    legend: opts.legend,
  }};
}}
const CONFIG = {{ displayModeBar: false, responsive: true }};

function toUTC(dstr) {{ const [y,m,d] = dstr.split("-").map(Number); return Date.UTC(y, m-1, d); }}
function fmtInt(n) {{ return Math.round(n).toLocaleString("ko-KR"); }}
function fmtWon(n) {{ return "₩" + fmtInt(n); }}
function fmtPct(n) {{ return n.toFixed(2) + "%"; }}

function filterRange(startStr, endStr) {{
  const s = toUTC(startStr), e = toUTC(endStr);
  return DATA.daily.filter(r => {{ const t = toUTC(r.date); return t >= s && t <= e; }});
}}

function renderTrend(rows) {{
  const dates = rows.map(r => r.date);
  Plotly.react("chart-impressions", [{{x: dates, y: rows.map(r=>r.impressions), mode:"lines", line:{{color:COLORS.blue,width:2}}}}],
    baseLayout({{title:"노출수 추이"}}), CONFIG);
  Plotly.react("chart-clicks", [{{x: dates, y: rows.map(r=>r.clicks), mode:"lines", line:{{color:COLORS.orange,width:2}}}}],
    baseLayout({{title:"클릭수 추이"}}), CONFIG);
  Plotly.react("chart-cost", [{{x: dates, y: rows.map(r=>r.cost), type:"bar", marker:{{color:COLORS.aqua}}}}],
    baseLayout({{title:"일별 비용"}}), CONFIG);
  Plotly.react("chart-purchases", [{{x: dates, y: rows.map(r=>r.purchases), type:"bar", marker:{{color:COLORS.violet}}}}],
    baseLayout({{title:"일별 구매(전환)"}}), CONFIG);
}}

const minDate = DATA.daily[0].date, maxDate = DATA.daily[DATA.daily.length-1].date;
document.querySelectorAll("button.preset").forEach(btn => {{
  btn.addEventListener("click", () => {{
    document.querySelectorAll("button.preset").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    const preset = btn.dataset.preset;
    let start = minDate, end = maxDate;
    if (preset !== "all") {{
      const days = parseInt(preset, 10);
      const endTs = toUTC(maxDate);
      start = new Date(endTs - (days-1)*86400000).toISOString().slice(0,10);
    }}
    document.getElementById("trendStart").value = start;
    document.getElementById("trendEnd").value = end;
    renderTrend(filterRange(start, end));
  }});
}});
["trendStart","trendEnd"].forEach(id => {{
  document.getElementById(id).addEventListener("change", () => {{
    document.querySelectorAll("button.preset").forEach(b => b.classList.remove("active"));
    renderTrend(filterRange(document.getElementById("trendStart").value, document.getElementById("trendEnd").value));
  }});
}});
renderTrend(DATA.daily);

function summarize(rows) {{
  const imp = rows.reduce((s,r)=>s+r.impressions,0);
  const clk = rows.reduce((s,r)=>s+r.clicks,0);
  const cost = rows.reduce((s,r)=>s+r.cost,0);
  const buy = rows.reduce((s,r)=>s+r.purchases,0);
  return {{
    days: rows.length, impressions: imp, clicks: clk, cost: cost, purchases: buy,
    ctr: imp ? clk/imp*100 : 0, cvr: clk ? buy/clk*100 : 0, cpa: buy ? cost/buy : 0,
  }};
}}
function deltaPct(base, val) {{ return base ? (val-base)/base*100 : null; }}

const METRIC_DEFS = [
  ["노출수","impressions", v=>fmtInt(v), "normal"],
  ["클릭수","clicks", v=>fmtInt(v), "normal"],
  ["CTR","ctr", v=>fmtPct(v), "normal"],
  ["총비용","cost", v=>fmtWon(v), "inverse"],
  ["구매","purchases", v=>fmtInt(v)+"건", "normal"],
  ["전환율","cvr", v=>fmtPct(v), "normal"],
  ["CPA","cpa", v=>fmtWon(v), "inverse"],
];

function renderComparison() {{
  const aStart = document.getElementById("aStart").value, aEnd = document.getElementById("aEnd").value;
  const bStart = document.getElementById("bStart").value, bEnd = document.getElementById("bEnd").value;
  if (!aStart || !aEnd || !bStart || !bEnd) return;
  const rowsA = filterRange(aStart, aEnd), rowsB = filterRange(bStart, bEnd);
  if (!rowsA.length || !rowsB.length) return;
  const sa = summarize(rowsA), sb = summarize(rowsB);

  const grid = document.getElementById("cmpGrid");
  grid.innerHTML = "";
  METRIC_DEFS.forEach(([label, key, fmt, dcolor]) => {{
    const d = deltaPct(sa[key], sb[key]);
    let cls = "flat", arrow = "→";
    if (d !== null && Math.abs(d) > 0.05) {{
      const isUp = d > 0;
      arrow = isUp ? "↑" : "↓";
      const good = dcolor === "inverse" ? !isUp : isUp;
      cls = good ? "up" : "down";
    }}
    const dtext = d === null ? "N/A" : `${{arrow}} ${{d>=0?"+":""}}${{d.toFixed(1)}}%`;
    grid.innerHTML += `<div><div class="label">${{label}}</div><div class="value">${{fmt(sb[key])}}</div><div class="delta ${{cls}}">${{dtext}}</div></div>`;
  }});

  const metric = document.getElementById("cmpMetric").value;
  const aTs = toUTC(aStart), bTs = toUTC(bStart);
  const xA = rowsA.map(r => Math.round((toUTC(r.date)-aTs)/86400000)+1);
  const xB = rowsB.map(r => Math.round((toUTC(r.date)-bTs)/86400000)+1);
  Plotly.react("chart-cmp", [
    {{x:xA, y:rowsA.map(r=>r[metric]), mode:"lines+markers", name:`기간 A (${{aStart}}~${{aEnd}})`, line:{{color:COLORS.blue,width:2}}, marker:{{size:6}}}},
    {{x:xB, y:rowsB.map(r=>r[metric]), mode:"lines+markers", name:`기간 B (${{bStart}}~${{bEnd}})`, line:{{color:COLORS.orange,width:2}}, marker:{{size:6}}}},
  ], baseLayout({{
      title: document.getElementById("cmpMetric").selectedOptions[0].text + " 추이 비교 (경과일 기준)",
      xaxis: {{title:"경과일"}},
      legend: {{orientation:"h", yanchor:"top", y:-0.2, xanchor:"center", x:0.5}},
    }}), CONFIG);
}}

(function initComparisonDefaults() {{
  const all = DATA.daily;
  const mid = Math.floor(all.length/2);
  document.getElementById("aStart").value = all[0].date;
  document.getElementById("aEnd").value = all[mid-1].date;
  document.getElementById("bStart").value = all[mid].date;
  document.getElementById("bEnd").value = all[all.length-1].date;
}})();
["aStart","aEnd","bStart","bEnd","cmpMetric"].forEach(id => document.getElementById(id).addEventListener("change", renderComparison));
renderComparison();

Plotly.newPlot("chart-device", [{{
  labels: DATA.device.map(d=>d.name), values: DATA.device.map(d=>d.impressions), type:"pie", hole:0.5,
  marker: {{colors:[COLORS.blue, COLORS.orange, COLORS.aqua]}},
}}], {{
  title: "기기별 노출수 비중",
  font: {{ family: "system-ui, -apple-system, 'Segoe UI', sans-serif", color: INK, size: 13 }},
  plot_bgcolor: SURFACE, paper_bgcolor: SURFACE, margin: {{l:10,r:10,t:40,b:10}},
  legend: {{orientation:"h", yanchor:"top", y:-0.05, xanchor:"center", x:0.5}},
}}, CONFIG);

const HEAT_METRICS = [
  ["노출수","impressions", v => fmtInt(v)],
  ["클릭수","clicks", v => fmtInt(v)],
  ["CTR","ctr", v => fmtPct(v)],
  ["비용","cost", v => fmtWon(v)],
  ["구매","purchases", v => fmtInt(v)+"건"],
  ["전환율","cvr", v => fmtPct(v)],
  ["CPA","cpa", v => (v===null||v===undefined) ? "-" : fmtWon(v)],
];
function renderHeatmap() {{
  const rows = DATA.daily;
  const y = rows.map(r => (r.learning ? "🌱 " : "") + r.date.slice(5) + ` (${{r.weekday}})`);
  const zByMetric = [], cdByMetric = [];
  HEAT_METRICS.forEach(([label, key, fmt]) => {{
    const vals = rows.map(r => r[key]);
    const present = vals.filter(v => v !== null && v !== undefined);
    const vmin = Math.min(...present), vmax = Math.max(...present);
    zByMetric.push(vals.map(v => (v===null||v===undefined) ? null : (vmax===vmin ? 0.5 : (v-vmin)/(vmax-vmin))));
    cdByMetric.push(vals.map(v => fmt(v)));
  }});
  const z = rows.map((_, ri) => HEAT_METRICS.map((_, ci) => zByMetric[ci][ri]));
  const customdata = rows.map((_, ri) => HEAT_METRICS.map((_, ci) => cdByMetric[ci][ri]));
  Plotly.newPlot("chart-heatmap", [{{
    x: HEAT_METRICS.map(m => m[0]), y: y, z: z, customdata: customdata,
    type: "heatmap", colorscale: HEAT_COLORSCALE, showscale: false, xgap: 2, ygap: 2,
    hovertemplate: "%{{y}}<br>%{{x}}: %{{customdata}}<extra></extra>",
  }}], {{
    font: {{ family: "system-ui, -apple-system, 'Segoe UI', sans-serif", color: INK, size: 13 }},
    plot_bgcolor: SURFACE, paper_bgcolor: SURFACE, margin: {{l:90,r:10,t:10,b:30}},
    xaxis: {{ gridcolor: GRID, zerolinecolor: GRID, tickfont: {{color: INK2}} }},
    yaxis: {{ gridcolor: GRID, zerolinecolor: GRID, tickfont: {{color: INK2}}, autorange: "reversed" }},
  }}, CONFIG);
}}
renderHeatmap();

Plotly.newPlot("chart-hourly", [{{x: DATA.hourly.map(h=>h.hour), y: DATA.hourly.map(h=>h.clicks), type:"bar", marker:{{color:COLORS.blue}}}}],
  baseLayout({{title:"시간대별 클릭수", xaxis:{{title:"시"}}}}), CONFIG);

Plotly.newPlot("chart-keywords", [{{x: KW_CHART.values, y: KW_CHART.labels, type:"bar", orientation:"h", marker:{{color:COLORS.blue}}}}],
  baseLayout({{title:"키워드별 비용", yaxis:{{autorange:"reversed"}}}}), CONFIG);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
