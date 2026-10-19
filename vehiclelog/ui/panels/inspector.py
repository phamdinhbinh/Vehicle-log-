"""Chức năng: Panel con trỏ và giá trị tín hiệu tại mốc bên phải.

Sửa tại đây khi: đổi bảng mốc, nút màu, tùy chọn bám mẫu hoặc bảng giá trị.
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
        """Dựng bảng con trỏ, điều khiển bám mẫu và giá trị tại mốc bên phải."""
        panel = QtWidgets.QFrame()
        panel.setObjectName("panel")
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.addWidget(label("CON TRỎ ĐO", "section"))
        self.cursor_table = table(["Tên", "Thời gian (s)", "Khóa"])
        self.cursor_table.setMaximumHeight(270)
        self.cursor_table.itemChanged.connect(self._cursor_edited)
        self.cursor_table.itemSelectionChanged.connect(self._refresh_values)
        self.cursor_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.cursor_table)
        controls = QtWidgets.QHBoxLayout()
        controls.addWidget(button("+ Mốc", lambda: self.add_cursor()))
        self.delete_cursor_button = button("Xóa", self.delete_cursor)
        controls.addWidget(self.delete_cursor_button)
        self.cursor_color_button = button("Màu", self.change_cursor_color)
        controls.addWidget(self.cursor_color_button)
        layout.addLayout(controls)
        self.snap_check = QtWidgets.QCheckBox("Bám mẫu của tín hiệu đầu tiên")
        self.snap_check.setToolTip("Khi kéo hoặc sửa thời gian, chọn timestamp gần nhất của tín hiệu đầu tiên đang vẽ.")
        layout.addWidget(self.snap_check)
        layout.addWidget(label("Sửa tên / thời gian bằng cách nhấp đúp.\nKéo mốc trên đồ thị để đổi vị trí.", "muted"))
        layout.addSpacing(12)
        self.values_title = label("GIÁ TRỊ TẠI MỐC", "section")
        layout.addWidget(self.values_title)
        self.value_table = table(["Tín hiệu", "Giá trị", "Đơn vị"])
        layout.addWidget(self.value_table, 1)
        self.delta_label = label("Chọn hai mốc để xác định giai đoạn.\nGiá trị hiển thị: mẫu gần nhất trước mốc.", "muted")
        self.delta_label.setWordWrap(True)
        layout.addWidget(self.delta_label)
        self.main_splitter.addWidget(panel)

