import sys
from PyQt6.QtWidgets import QApplication
from database.connection import init_db
from gui.main_window import MainWindow


def main():
    init_db()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
