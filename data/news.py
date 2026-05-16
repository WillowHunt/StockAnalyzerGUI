import datetime
import hashlib
import yfinance as yf
import finnhub
from config import FINNHUB_API_KEY
from data.predefined import FINNHUB_SYMBOL_MAP
from database.connection import get_session
from database.models import NewsArticle


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def load_from_db(ticker: str) -> list[dict]:
    session = get_session()
    try:
        rows = (
            session.query(NewsArticle)
            .filter_by(ticker=ticker)
            .order_by(NewsArticle.date.desc())
            .all()
        )
        return [
            {"date": r.date, "title": r.title, "source": r.source, "url": r.url}
            for r in rows
        ]
    finally:
        session.close()


def save_to_db(ticker: str, source_symbol: str, articles: list[dict]) -> int:
    session = get_session()
    try:
        existing = {
            r.url_hash
            for r in session.query(NewsArticle.url_hash).filter_by(ticker=ticker).all()
        }
        new_rows = []
        for a in articles:
            h = _url_hash(a["url"])
            if h not in existing:
                new_rows.append(
                    NewsArticle(
                        ticker=ticker,
                        source_symbol=source_symbol,
                        date=a["date"],
                        title=a["title"],
                        source=a["source"],
                        url=a["url"],
                        url_hash=h,
                    )
                )
        if new_rows:
            session.bulk_save_objects(new_rows)
            session.commit()
        return len(new_rows)
    finally:
        session.close()


def fetch_finnhub(ticker: str, date_from=None, date_to=None) -> list[dict]:
    client = finnhub.Client(api_key=FINNHUB_API_KEY)
    from_str = date_from.strftime("%Y-%m-%d") if date_from else "2020-01-01"
    to_str = date_to.strftime("%Y-%m-%d") if date_to else datetime.date.today().isoformat()
    raw = client.company_news(ticker, _from=from_str, to=to_str)
    articles = []
    for a in raw:
        try:
            pub_date = datetime.datetime.fromtimestamp(a["datetime"])
        except Exception:
            pub_date = None
        articles.append({
            "date": pub_date,
            "title": a.get("headline", ""),
            "source": a.get("source", ""),
            "url": a.get("url", ""),
        })
    return articles


def fetch_yfinance(ticker: str) -> list[dict]:
    try:
        news = yf.Ticker(ticker).news or []
    except Exception:
        return []
    articles = []
    for item in news:
        content = item.get("content", {})
        title = content.get("title", "")
        pub_date_str = content.get("pubDate", "")
        source = content.get("provider", {}).get("displayName", "")
        url = (content.get("clickThroughUrl") or content.get("canonicalUrl") or {}).get("url", "")
        try:
            pub_date = datetime.datetime.fromisoformat(
                pub_date_str.replace("Z", "+00:00")
            ).replace(tzinfo=None)
        except Exception:
            pub_date = None
        if title and url:
            articles.append({"date": pub_date, "title": title, "source": source, "url": url})
    return articles


def refresh_news(ticker: str, date_from=None, date_to=None) -> dict:
    is_danish = ticker.upper().endswith(".CO")
    finnhub_symbol = FINNHUB_SYMBOL_MAP.get(ticker.upper()) if is_danish else ticker
    use_finnhub = bool(FINNHUB_API_KEY and finnhub_symbol)

    if use_finnhub:
        fresh = fetch_finnhub(finnhub_symbol, date_from, date_to)
        new_count = save_to_db(ticker, finnhub_symbol, fresh)
        source = f"finnhub:{finnhub_symbol}"
    else:
        fresh = fetch_yfinance(ticker)
        new_count = save_to_db(ticker, ticker, fresh)
        source = "yfinance"

    return {"new_articles": new_count, "source": source}
