from fastapi import APIRouter, HTTPException, Query
from analysis.backtester import (
    generate_signals,
    load_signal_details,
    run_backtest,
    run_atr_backtest,
)

router = APIRouter(prefix="/api/stocks", tags=["analysis"])


@router.post("/{ticker}/signals")
def create_signals(ticker: str):
    count = generate_signals(ticker.upper())
    if count == 0:
        raise HTTPException(status_code=404, detail=f"Ingen data eller signaler for {ticker}")
    return {"ticker": ticker.upper(), "signals_generated": count}


@router.get("/{ticker}/signals")
def get_signals(ticker: str):
    rows = load_signal_details(ticker.upper())
    if not rows:
        raise HTTPException(status_code=404, detail=f"Ingen signaler for {ticker}")
    return rows


@router.post("/{ticker}/backtest")
def backtest(ticker: str, hold_days: int = Query(default=20, ge=1)):
    summary = run_backtest(ticker.upper(), hold_days=hold_days)
    if not summary:
        raise HTTPException(status_code=404, detail=f"Ingen data for backtest af {ticker}")
    return summary


@router.post("/{ticker}/backtest/atr")
def backtest_atr(
    ticker: str,
    atr_mult: float = Query(default=2.0, gt=0),
    max_days: int = Query(default=60, ge=1),
):
    summary, details = run_atr_backtest(ticker.upper(), atr_mult=atr_mult, max_days=max_days)
    if not summary:
        raise HTTPException(status_code=404, detail=f"Ingen data for ATR-backtest af {ticker}")
    return {"summary": summary, "details": details}
