import yfinance as yf
import finnhub
import datetime
import hashlib
from config import FINNHUB_API_KEY
from data.predefined import FINNHUB_SYMBOL_MAP
from database.connection import get_session
from database.models import NewsArticle
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QCheckBox, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QColor, QFont


def _is_danish(ticker: str) -> bool:
    return ticker.upper().endswith(".CO")


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def _load_from_db(ticker: str) -> list:
    session = get_session()
    try:
        rows = session.query(NewsArticle).filter_by(ticker=ticker).order_by(NewsArticle.date.desc()).all()
        return [{"date": r.date, "title": r.title, "source": r.source, "url": r.url} for r in rows]
    finally:
        session.close()


def _save_to_db(ticker: str, source_symbol: str, articles: list):
    session = get_session()
    try:
        existing = {r.url_hash for r in session.query(NewsArticle.url_hash).filter_by(ticker=ticker).all()}
        new_rows = []
        for a in articles:
            h = _url_hash(a["url"])
            if h not in existing:
                new_rows.append(NewsArticle(
                    ticker=ticker,
                    source_symbol=source_symbol,
                    date=a["date"],
                    title=a["title"],
                    source=a["source"],
                    url=a["url"],
                    url_hash=h,
                ))
        if new_rows:
            session.bulk_save_objects(new_rows)
            session.commit()
        return len(new_rows)
    finally:
        session.close()


def _fetch_finnhub(ticker: str, date_from: datetime.datetime, date_to: datetime.datetime) -> list:
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
            "summary": a.get("summary", ""),
            "url": a.get("url", ""),
        })
    return articles


def _fetch_yfinance(ticker: str) -> list:
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
            pub_date = datetime.datetime.fromisoformat(pub_date_str.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            pub_date = None
        if title and url:
            articles.append({
                "date": pub_date,
                "title": title,
                "source": source,
                "summary": "",
                "url": url,
            })
    return articles


class NewsWindow(QDialog):
    def __init__(self, ticker: str, date_from=None, date_to=None, parent=None):
        super().__init__(parent)
        self.ticker = ticker
        self.date_from = date_from
        self.date_to = date_to
        self._all_articles = []
        self.setWindowTitle(f"Nyheder — {ticker}")
        self.setMinimumSize(950, 550)
        self._build_ui()
        self._fetch()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        self.title_label = QLabel()
        self.title_label.setFont(QFont("", 10, QFont.Weight.Bold))
        header.addWidget(self.title_label)
        header.addStretch()
        self.filter_cb = QCheckBox("Vis kun nyheder i valgt datointerval")
        self.filter_cb.setChecked(False)
        self.filter_cb.stateChanged.connect(self._apply_filter)
        header.addWidget(self.filter_cb)
        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Dato", "Overskrift", "Kilde"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._open_article)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        footer = QHBoxLayout()
        self.status_label = QLabel("Dobbeltklik på en artikel for at åbne i browser")
        self.status_label.setStyleSheet("color: gray;")
        footer.addWidget(self.status_label)
        footer.addStretch()
        open_btn = QPushButton("Åbn valgt artikel")
        open_btn.clicked.connect(self._open_article)
        footer.addWidget(open_btn)
        layout.addLayout(footer)

    def _fetch(self):
        finnhub_symbol = FINNHUB_SYMBOL_MAP.get(self.ticker.upper()) if _is_danish(self.ticker) else self.ticker
        use_finnhub = bool(FINNHUB_API_KEY and finnhub_symbol)

        cached = _load_from_db(self.ticker)

        if use_finnhub:
            fresh = _fetch_finnhub(finnhub_symbol, self.date_from, self.date_to)
            new_count = _save_to_db(self.ticker, finnhub_symbol, fresh)
            source_note = f"Finnhub ({finnhub_symbol})"
            if _is_danish(self.ticker):
                source_note += " — US ADR/OTC"
        else:
            fresh = _fetch_yfinance(self.ticker)
            new_count = _save_to_db(self.ticker, self.ticker, fresh)
            source_note = "Yahoo Finance (kun seneste nyheder)"

        # Merge: DB-cache er komplet, fresh kan have overlap — brug DB som kilde
        all_articles = _load_from_db(self.ticker)
        self._all_articles = sorted(all_articles, key=lambda a: a["date"] or datetime.datetime.min, reverse=True)
        cache_note = f"  ·  {len(cached)} gemt, {new_count} nye"

        range_str = ""
        if self.date_from and self.date_to:
            range_str = f"  ·  {self.date_from.strftime('%d %b %Y')} → {self.date_to.strftime('%d %b %Y')}"

        self.title_label.setText(
            f"{self.ticker} — {len(self._all_articles)} artikler  ·  {source_note}{cache_note}{range_str}"
        )
        self._apply_filter()

    def _apply_filter(self):
        filtered = []
        if self.filter_cb.isChecked() and self.date_from and self.date_to:
            filtered = [a for a in self._all_articles
                        if a["date"] and self.date_from <= a["date"] <= self.date_to]

        if filtered:
            articles = filtered
            note = f"Viser {len(articles)} af {len(self._all_articles)} artikler i valgt interval"
        elif self.filter_cb.isChecked() and self.date_from:
            articles = self._all_articles
            note = (f"Ingen artikler i valgt interval "
                    f"({self.date_from.strftime('%d %b %Y')} → {self.date_to.strftime('%d %b %Y')}) "
                    f"— Finnhub gratis dækker kun fra jan 2025. Viser alle {len(articles)} artikler.")
        else:
            articles = self._all_articles
            note = f"Viser alle {len(articles)} artikler  ·  Dobbeltklik for at åbne i browser"

        self.table.setRowCount(len(articles))
        for row, a in enumerate(articles):
            date_str = a["date"].strftime("%d %b %Y") if a["date"] else "—"
            in_range = (self.date_from and self.date_to and a["date"] and
                        self.date_from <= a["date"] <= self.date_to)

            date_item = QTableWidgetItem(date_str)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            title_item = QTableWidgetItem(a["title"])
            title_item.setData(Qt.ItemDataRole.UserRole, a["url"])
            source_item = QTableWidgetItem(a["source"])
            source_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            if in_range:
                for item in (date_item, title_item, source_item):
                    item.setForeground(QColor("#26a69a"))

            self.table.setItem(row, 0, date_item)
            self.table.setItem(row, 1, title_item)
            self.table.setItem(row, 2, source_item)

        self.status_label.setText(note)

    def _open_article(self):
        row = self.table.currentRow()
        if row < 0:
            return
        url = self.table.item(row, 1).data(Qt.ItemDataRole.UserRole)
        if url:
            QDesktopServices.openUrl(QUrl(url))
