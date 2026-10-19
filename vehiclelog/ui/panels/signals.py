"""Chức năng: Panel danh sách và bộ lọc tín hiệu bên trái.

Sửa tại đây khi: đổi bố cục tìm kiếm, nhãn hoặc danh sách tín hiệu.
Liên kết: controllers/signals.py xử lý lọc / tick; controllers/session.py nạp danh sách.
"""
# COMPONENT: ui.panels.signals
from __future__ import annotations

from PySide6 import QtCore, QtWidgets
import pyqtgraph as pg
from ..widgets import label, button, table

Qt = QtCore.Qt

class SignalsPanel:
    """Mixin bố cục: gắn widget lên MainWindow và nối callback của controller.

    Không khởi tạo riêng; self là MainWindow với trạng thái chia sẻ từ main_window.py.
    """

    def _build_signals(self):
        """Dựng panel tìm kiếm / chọn tín hiệu bên trái; callback thuộc SignalsController."""
        panel = QtWidgets.QFrame()
        panel.setObjectName("panel")
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(label("TÍN HIỆU", "section"))
        row.addStretch()
        self.signal_count = label("0", "muted")
        row.addWidget(self.signal_count)
        layout.addLayout(row)
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Tìm tên, CAN ID, message…")
        self.search_edit.textChanged.connect(self._filter_signals)
        layout.addWidget(self.search_edit)
        self.signal_list = QtWidgets.QListWidget()
        self.signal_list.setSpacing(2)
        self.signal_list.itemChanged.connect(self._signal_changed)
        layout.addWidget(self.signal_list, 1)
        layout.addWidget(button("Bỏ chọn tín hiệu", self.clear_selection))
        help_label = label("Tick tín hiệu để thêm đồ thị.\nĐồ thị tổng quan dùng min/max; tính toán dùng dữ liệu đầy đủ.", "muted")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        self.main_splitter.addWidget(panel)

