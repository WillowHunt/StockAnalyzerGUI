from fastapi import APIRouter, HTTPException, Query
from data.news import load_from_db, refresh_news

router = APIRouter(prefix="/api/stocks", tags=["news"])


@router.get("/{ticker}/news")
def get_news(ticker: str, limit: int = Query(default=50, ge=1, le=500)):
    articles = load_from_db(ticker.upper())
    if not articles:
        raise HTTPException(status_code=404, detail=f"Ingen nyheder for {ticker}")
    result = []
    for a in articles[:limit]:
        result.append({
            "date": a["date"].isoformat() if a["date"] else None,
            "title": a["title"],
            "source": a["source"],
            "url": a["url"],
        })
    return result


@router.post("/{ticker}/news/fetch")
def fetch_news(ticker: str):
    result = refresh_news(ticker.upper())
    return {"ticker": ticker.upper(), **result}
