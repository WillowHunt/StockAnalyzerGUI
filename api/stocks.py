from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from data.fetcher import fetch_and_store, list_stored_tickers, load_prices

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("")
def get_stocks():
    rows = list_stored_tickers()
    return [{"ticker": t, "name": n, "span": s} for t, n, s in rows]


@router.post("/{ticker}/fetch")
def fetch_stock(
    ticker: str,
    period: str = Query("1y"),
    interval: str = Query("1d"),
):
    try:
        new_rows = fetch_and_store(ticker.upper(), period=period, interval=interval)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"ticker": ticker.upper(), "new_rows": new_rows}


@router.get("/{ticker}/prices")
def get_prices(ticker: str, limit: int = Query(default=0, ge=0)):
    df = load_prices(ticker.upper())
    if df.empty:
        raise HTTPException(status_code=404, detail=f"{ticker} ikke fundet i databasen")
    if limit:
        df = df.tail(limit)
    df["date"] = df["date"].astype(str)
    return Response(content=df.to_json(orient="records"), media_type="application/json")
