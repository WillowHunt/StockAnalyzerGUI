from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


class NumericItem(QTableWidgetItem):
    def __lt__(self, other):
        try:
            return float(self.data(Qt.ItemDataRole.UserRole)) < float(other.data(Qt.ItemDataRole.UserRole))
        except (TypeError, ValueError):
            return super().__lt__(other)


class BacktestPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.title = QLabel("Backtest resultater")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self.summary_table = QTableWidget()
        self.summary_table.setColumnCount(6)
        self.summary_table.setHorizontalHeaderLabels(["Signal", "Indikator", "Total", "Success", "Fejl", "Success %"])
        self.summary_table.horizontalHeader().setStretchLastSection(True)
        self.summary_table.setSortingEnabled(True)
        self.summary_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.summary_table.itemSelectionChanged.connect(self._on_summary_selection)
        splitter.addWidget(self.summary_table)

        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(7)
        self.detail_table.setHorizontalHeaderLabels(
            ["Dato", "Signal", "Indikator", "Kurs", "Outcome dato", "% ændring", "Resultat"]
        )
        self.detail_table.horizontalHeader().setStretchLastSection(True)
        self.detail_table.setSortingEnabled(True)
        splitter.addWidget(self.detail_table)

        splitter.setSizes([200, 400])
        layout.addWidget(splitter)
        self._details: list = []

    def _on_summary_selection(self):
        selected = self.summary_table.selectedItems()
        if not selected:
            self._populate_detail(self._details)
            return
        row = self.summary_table.currentRow()
        signal_type = self.summary_table.item(row, 0).text()
        indicator = self.summary_table.item(row, 1).text()
        filtered = [d for d in self._details if d["signal_type"] == signal_type and d["indicator"] == indicator]
        self._populate_detail(filtered)

    def show_results(self, ticker: str, results: dict, details: list = None):
        self.title.setText(f"Backtest: {ticker} — {len(results)} signaltyper analyseret")
        self.summary_table.setRowCount(len(results))
        for row, (key, data) in enumerate(results.items()):
            signal_type, indicator = key.split("_", 1)
            items = [
                signal_type,
                indicator,
                str(data["total"]),
                str(data["success"]),
                str(data["fail"]),
                f"{data['success_rate']}%",
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.summary_table.setItem(row, col, item)

        if details:
            self._details = details
            self._populate_detail(details)

    def _populate_detail(self, details: list):
        self.detail_table.setSortingEnabled(False)
        self.detail_table.setRowCount(len(details))
        for row, sig in enumerate(details):
            pct = sig["outcome_pct"]
            success = sig["is_success"]
            pct_str = f"{pct:+.2f}%" if pct is not None else "—"
            outcome_str = str(sig["outcome_date"]) if sig["outcome_date"] else "—"
            result_str = "OK" if success else "Fejl" if success is not None else "—"
            price_str = f"{sig['price']:.2f}" if sig["price"] else "—"

            numeric_cols = {3: sig["price"], 5: pct}
            cells = [sig["date"], sig["signal_type"], sig["indicator"], price_str,
                     outcome_str, pct_str, result_str]
            for col, text in enumerate(cells):
                if col in numeric_cols and numeric_cols[col] is not None:
                    item = NumericItem(text)
                    item.setData(Qt.ItemDataRole.UserRole, numeric_cols[col])
                else:
                    item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if success is True:
                    item.setForeground(QColor("#00cc66"))
                elif success is False:
                    item.setForeground(QColor("#ff4444"))
                self.detail_table.setItem(row, col, item)
        self.detail_table.setSortingEnabled(True)
