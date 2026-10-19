"""Chức năng: Điểm khởi động ứng dụng desktop Qt.

Sửa tại đây khi: đổi tên ứng dụng hoặc cách mở cửa sổ lúc chạy.
Liên kết: CLI __main__.py gọi gui.run_app; main_window.py ghép các component.
"""
# COMPONENT: ui.app
from __future__ import annotations

import sys
from PySide6 import QtWidgets
from .main_window import MainWindow

def run_app() -> int:
    """Tạo QApplication và mở cửa sổ; lệnh CLI gọi qua gui.py."""
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Vehicle Log Studio")
    app.setOrganizationName("Vehicle Log Studio")
    window = MainWindow()
    window.show()
    return app.exec()

