"""Chức năng: Khung cửa sổ, thanh công cụ, menu và tiến độ.

Sửa tại đây khi: đổi bố cục tổng thể, nút trên cùng hoặc phím tắt.
Liên kết: main_window.py gọi; các panel còn lại dựng ba vùng chính.
"""
# COMPONENT: ui.panels.shell
from __future__ import annotations

from PySide6 import QtCore, QtWidgets
import pyqtgraph as pg
from ..widgets import label, button, table

Qt = QtCore.Qt

class ShellLayout:
    """Mixin bố cục: gắn widget lên MainWindow và nối callback của controller.

    Không khởi tạo riêng; self là MainWindow với trạng thái chia sẻ từ main_window.py.
    """

    def _build_ui(self):
        """Dựng khung cửa sổ, thanh công cụ và thanh tiến độ; ghép các panel chức năng."""
        root = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(root)
        outer.setContentsMargins(18, 16, 18, 8)
        outer.setSpacing(12)
        top = QtWidgets.QHBoxLayout()
        brand = QtWidgets.QVBoxLayout()
        brand.setSpacing(2)
        brand.addWidget(label("MEASUREMENT WORKSPACE", "eyebrow"))
        brand.addWidget(label("Vehicle Log Studio", "title"))
        top.addLayout(brand)
        top.addStretch()
        self.source_label = label("Chưa mở log  ·  BLF / MF4", "muted")
        self.source_label.setMaximumWidth(460)
        top.addWidget(self.source_label)
        outer.addLayout(top)
        tools = QtWidgets.QHBoxLayout()
        self.open_button = button("Mở log…", self.open_log, True)
        self.demo_button = button("Dữ liệu demo", self.open_demo)
        self.dbc_button = button("DBC / Kênh CAN", self.manage_dbc)
        self.save_button = button("Lưu dự án", self.save_project)
        self.cursor_button = button("+ Con trỏ", lambda: self.add_cursor())
        self.export_button = button("Xuất dữ liệu…", self.export_data)
        for widget in (self.open_button, self.demo_button, self.dbc_button, self.save_button):
            tools.addWidget(widget)
        tools.addStretch()
        tools.addWidget(self.cursor_button)
        tools.addWidget(self.export_button)
        outer.addLayout(tools)
        self.main_splitter = QtWidgets.QSplitter(Qt.Orientation.Horizontal)
        outer.addWidget(self.main_splitter, 1)
        self._build_signals()
        self._build_workspace()
        self._build_inspector()
        self.main_splitter.setSizes([260, 950, 270])
        self.main_splitter.setStretchFactor(1, 1)
        footer = QtWidgets.QHBoxLayout()
        self.status_label = label("Sẵn sàng · mở log hoặc dùng dữ liệu demo để bắt đầu", "muted")
        footer.addWidget(self.status_label, 1)
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedWidth(180)
        self.progress_bar.hide()
        footer.addWidget(self.progress_bar)
        self.cancel_button = button("Hủy tác vụ", self.cancel_task)
        self.cancel_button.hide()
        footer.addWidget(self.cancel_button)
        outer.addLayout(footer)
        self.setCentralWidget(root)
        self.setAcceptDrops(True)


    def _build_menus(self):
        """Dựng menu và phím tắt, dùng lại callback của thanh công cụ."""
        file_menu = self.menuBar().addMenu("Tệp")
        for title, shortcut, callback in [
            ("Mở log…", "Ctrl+O", self.open_log), ("Mở dự án…", "Ctrl+Shift+O", self.load_project),
            ("Lưu dự án…", "Ctrl+S", self.save_project), ("Xuất dữ liệu…", "Ctrl+E", self.export_data),
        ]:
            action = file_menu.addAction(title)
            action.setShortcut(shortcut)
            action.triggered.connect(callback)
        file_menu.addSeparator()
        file_menu.addAction("Thoát", self.close)
        help_menu = self.menuBar().addMenu("Trợ giúp")
        help_menu.addAction("Hướng dẫn nhanh", self.show_help)
        help_menu.addAction("Thông tin", lambda: QtWidgets.QMessageBox.information(
            self, "Vehicle Log Studio", "Vehicle Log Studio\nBLF / MF4 · DBC · Giai đoạn · Công thức\n"
            "Ứng dụng phân tích dữ liệu đo. Kết quả cần được đối chiếu với dữ liệu tham chiếu."))

