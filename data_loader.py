"""소니코리아 네이버 검색광고 리포트 데이터 로딩/정제 모듈."""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "raw_data"


def _pct_to_float(series: pd.Series) -> pd.Series:
    """'8.21%' -> 8.21 (float, 퍼센트 단위 그대로 유지)"""
    return (
        series.astype(str)
        .str.replace("%", "", regex=False)
        .str.strip()
        .replace({"": None, "nan": None})
        .astype(float)
    )


def load_campaign_daily() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "campaign_daily.csv", encoding="utf-8-sig")
    df = df[df["날짜"] != "합계"].copy()
    df["날짜"] = pd.to_datetime(df["날짜"])
    df["CTR"] = _pct_to_float(df["CTR"])
    df["전환율"] = _pct_to_float(df["전환율"])
    for col in ["예산 소진", "학습 기간"]:
        df[col] = df[col].map({"Y": True, "N": False})
    return df.sort_values("날짜").reset_index(drop=True)


def load_keywords() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "keywords.csv", encoding="utf-8-sig")
    df["CTR"] = _pct_to_float(df["CTR"])
    df["전환율"] = (df["구매"] / df["클릭수"] * 100).round(2)
    cost_per_purchase = df["비용"] / df["구매"].replace(0, float("nan"))
    df["전환당비용"] = cost_per_purchase.round(0)
    return df


def load_search_terms() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "search_terms.csv", encoding="utf-8-sig")
    df["CTR"] = _pct_to_float(df["CTR"])
    return df


def load_ad_groups() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "ad_groups.csv", encoding="utf-8-sig")
    df["CTR"] = _pct_to_float(df["CTR"])
    return df


def load_placements() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "placements.csv", encoding="utf-8-sig")
    if not df.empty:
        df["CTR"] = _pct_to_float(df["CTR"])
    return df


def load_device_hour() -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(DATA_DIR / "device_hour.csv", encoding="utf-8-sig")
    df["CTR"] = _pct_to_float(df["CTR"])
    device = df[df["구분"] == "기기"].reset_index(drop=True)
    hourly = df[df["구분"] == "시간대"].reset_index(drop=True)
    hourly["시"] = hourly["값"].str.slice(0, 2).astype(int)
    return device, hourly


def load_diagnosis() -> tuple[dict, pd.DataFrame]:
    """diagnosis.csv는 상단 계정 메타정보 + 하단 진단 이슈 표, 두 블록으로 구성."""
    raw = (DATA_DIR / "diagnosis.csv").read_text(encoding="utf-8-sig")
    lines = [l for l in raw.splitlines()]

    meta = {}
    table_start = None
    for i, line in enumerate(lines):
        if not line.strip():
            table_start = i + 1
            break
        key, _, val = line.partition(",")
        meta[key.strip()] = val.strip()

    table_text = "\n".join(lines[table_start:])
    from io import StringIO

    issues = pd.read_csv(StringIO(table_text))
    severity_order = {"높음": 0, "보통": 1, "낮음": 2}
    issues["_순위"] = issues["심각도"].map(severity_order)
    issues = issues.sort_values("_순위").drop(columns="_순위").reset_index(drop=True)
    return meta, issues


def load_all() -> dict:
    device, hourly = load_device_hour()
    meta, issues = load_diagnosis()
    return {
        "campaign_daily": load_campaign_daily(),
        "keywords": load_keywords(),
        "search_terms": load_search_terms(),
        "ad_groups": load_ad_groups(),
        "placements": load_placements(),
        "device": device,
        "hourly": hourly,
        "account_meta": meta,
        "issues": issues,
    }
