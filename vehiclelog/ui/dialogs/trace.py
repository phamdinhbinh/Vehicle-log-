"""Chức năng: Cửa sổ đồ thị xem trước của một công thức dạng chuỗi trong một giai đoạn.

Sửa tại đây khi: đổi tiêu đề, trục, màu hoặc lời giải thích đồ thị công thức.
Liên kết: controllers/formulas.py tính preview ở nền rồi truyền times / values vào cửa sổ.
"""
# COMPONENT: ui.dialogs.trace
from __future__ import annotations

from PySide6 import QtWidgets
import pyqtgraph as pg
from ..theme import COLORS
from ..widgets import label


class TraceDialog(QtWidgets.QDialog):
    """Chỉ dựng giao diện xem chuỗi; dữ liệu đầu vào đã được rút gọn để vẽ."""

    def __init__(self, formula, segment, times, values, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{formula.name} · {segment.name}")
        self.resize(1000, 560)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(label(f"{formula.expression} · {formula.unit}", "section"))
        chart = pg.PlotWidget()
        chart.showGrid(x=True, y=True, alpha=.2)
        chart.setLabel("bottom", "Thời gian", units="s")
        chart.setLabel("left", formula.name, units=formula.unit or None)
        chart.plot(times, values, pen=pg.mkPen(COLORS[0], width=1.3), connect="finite")
        layout.addWidget(chart)
        layout.addWidget(label("Đồ thị tổng quan tối đa 4.000 điểm min/max; khoảng không hợp lệ được ngắt bằng NaN.\n"
                               "Tính toán và xuất file sử dụng dữ liệu đầy đủ.", "muted"))
