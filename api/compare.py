from fastapi import APIRouter, Query
from fastapi.responses import Response
import yfinance as yf
import pandas as pd
import json
import time

router = APIRouter(prefix="/api", tags=["compare"])

_cache: dict = {}
_CACHE_TTL = 3600  # 1 hour


@router.get("/compare")
def get_compare(tickers: str = Query(...)):
    result = {}
    for ticker in [t.strip().upper() for t in tickers.split(",") if t.strip()]:
        data = _fetch_ticker(ticker)
        if data is not None:
            result[ticker] = data
    return Response(content=json.dumps(result), media_type="application/json")


def _fetch_ticker(ticker: str):
    now = time.time()
    cached = _cache.get(ticker)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1]
    try:
        df = yf.download(ticker, period="max", interval="1d",
                         auto_adjust=True, progress=False)
        if df.empty:
            return None
        df = df.reset_index()
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        rows = []
        for _, row in df.iterrows():
            close = row.get("Close")
            if close is None or pd.isna(close):
                continue
            rows.append({"date": str(row["Date"])[:10], "close": float(close)})
        _cache[ticker] = (now, rows)
        return rows
    except Exception:
        return None
