import yfinance as yf
import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QCheckBox, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QColor, QFont


class NewsWindow(QDialog):
    def __init__(self, ticker: str, date_from=None, date_to=None, parent=None):
        super().__init__(parent)
        self.ticker = ticker
        self.date_from = date_from
        self.date_to = date_to
        self._all_articles = []
        self.setWindowTitle(f"Nyheder — {ticker}")
        self.setMinimumSize(900, 500)
        self._build_ui()
        self._fetch()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Header
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

        # Table
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

        # Footer
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
        try:
            news = yf.Ticker(self.ticker).news or []
        except Exception:
            news = []

        for item in news:
            content = item.get("content", {})
            title = content.get("title", "")
            pub_date_str = content.get("pubDate", "")
            source = content.get("provider", {}).get("displayName", "")
            url = content.get("clickThroughUrl", {}).get("url") or \
                  content.get("canonicalUrl", {}).get("url", "")
            try:
                pub_date = datetime.datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                pub_date = pub_date.replace(tzinfo=None)
            except Exception:
                pub_date = None

            if title and url:
                self._all_articles.append({
                    "date": pub_date,
                    "title": title,
                    "source": source,
                    "url": url,
                })

        range_str = ""
        if self.date_from and self.date_to:
            range_str = f"  ·  Valgt interval: {self.date_from.strftime('%d %b %Y')} → {self.date_to.strftime('%d %b %Y')}"
        self.title_label.setText(f"{self.ticker} — {len(self._all_articles)} artikler fundet{range_str}")

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
            note = (f"Ingen artikler fundet i valgt interval "
                    f"({self.date_from.strftime('%d %b %Y')} → {self.date_to.strftime('%d %b %Y')}) "
                    f"— Yahoo Finance har kun de seneste nyheder. Viser alle {len(articles)} artikler.")
        else:
            articles = self._all_articles
            note = f"Viser alle {len(articles)} artikler"

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

        self.status_label.setText(f"{note}  ·  Dobbeltklik for at åbne i browser")

    def _open_article(self):
        row = self.table.currentRow()
        if row < 0:
            return
        url = self.table.item(row, 1).data(Qt.ItemDataRole.UserRole)
        if url:
            QDesktopServices.openUrl(QUrl(url))
