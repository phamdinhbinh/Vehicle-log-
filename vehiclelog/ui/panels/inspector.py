"""Chức năng: Panel con trỏ và giá trị tín hiệu tại mốc bên phải.

Sửa tại đây khi: đổi bảng mốc, chọn cặp đo, nút màu hoặc bảng Y đầu/cuối/ΔY.
Liên kết: controllers/cursors.py xử lý tạo / kéo / sửa mốc và giá trị tại mốc.
"""
# COMPONENT: ui.panels.inspector
from __future__ import annotations

from PySide6 import QtCore, QtWidgets
import pyqtgraph as pg
from ..widgets import label, button, table

Qt = QtCore.Qt

class InspectorPanel:
    """Mixin bố cục: gắn widget lên MainWindow và nối callback của controller.

    Không khởi tạo riêng; self là MainWindow với trạng thái chia sẻ từ main_window.py.
    """

    def _build_inspector(self):
        """Dựng bảng con trỏ đơn giản và phép đo giữa hai mốc liền kề."""
        panel = QtWidgets.QFrame()
        panel.setObjectName("panel")
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.addWidget(label("CON TRỎ ĐO", "section"))
        self.cursor_table = table(["Con trỏ", "Thời gian (s)"])
        self.cursor_table.setMaximumHeight(190)
        self.cursor_table.itemChanged.connect(self._cursor_edited)
        self.cursor_table.itemSelectionChanged.connect(self._cursor_selected)
        self.cursor_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.cursor_table)
        controls = QtWidgets.QHBoxLayout()
        controls.addWidget(button("+ Mốc", lambda: self.add_cursor()))
        self.delete_cursor_button = button("Xóa", self.delete_cursor)
        controls.addWidget(self.delete_cursor_button)
        self.cursor_color_button = button("Màu", self.change_cursor_color)
        controls.addWidget(self.cursor_color_button)
        layout.addLayout(controls)
        hint = label("M1 → M2 là giai đoạn 1; M2 → M3 là giai đoạn 2.\nKéo mốc hoặc nhấp đúp thời gian để sửa.", "muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addSpacing(12)
        self.values_title = label("ĐO GIỮA HAI CON TRỎ", "section")
        layout.addWidget(self.values_title)
        self.pair_combo = QtWidgets.QComboBox()
        self.pair_combo.setToolTip("Chọn hai con trỏ liền nhau để đọc Y đầu, Y cuối và ΔY.")
        self.pair_combo.currentIndexChanged.connect(self._refresh_values)
        layout.addWidget(self.pair_combo)
        self.value_table = table(["Tín hiệu", "Y đầu", "Y cuối", "ΔY", "Đơn vị"])
        self.value_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.value_table.horizontalHeader().setStretchLastSection(False)
        self.value_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.value_table, 1)
        self.delta_label = label("Thêm hai con trỏ để đo Δt và ΔY.\nGiá trị tại mốc: giữ mẫu gần nhất trước mốc.", "muted")
        self.delta_label.setWordWrap(True)
        layout.addWidget(self.delta_label)
        self.main_splitter.addWidget(panel)

