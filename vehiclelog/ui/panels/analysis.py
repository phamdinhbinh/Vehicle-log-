"""Chức năng: Các tab giai đoạn, công thức và bảng kết quả.

Sửa tại đây khi: đổi cột bảng, nút và cách bố trí ba tab phân tích.
Liên kết: controllers/segments.py và formulas.py chứa thao tác; dialogs/ chứa form nhập.
"""
# COMPONENT: ui.panels.analysis
from __future__ import annotations

from PySide6 import QtCore, QtWidgets
import pyqtgraph as pg
from ..widgets import label, button, table

Qt = QtCore.Qt

class AnalysisPanels:
    """Mixin bố cục: gắn widget lên MainWindow và nối callback của controller.

    Không khởi tạo riêng; self là MainWindow với trạng thái chia sẻ từ main_window.py.
    """

    def _build_segment_tab(self):
        """Dựng tab bảng giai đoạn và nối nút tới SegmentsController."""
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        bar = QtWidgets.QHBoxLayout()
        self.segment_edit = button("Đổi tên", self.edit_segment)
        bar.addWidget(self.segment_edit)
        bar.addStretch()
        hint = label("Tự tạo từ M1–M2, M2–M3… · Thêm/xóa con trỏ để chia/gộp", "muted")
        hint.setWordWrap(True)
        bar.addWidget(hint)
        layout.addLayout(bar)
        self.segment_table = table(["Tên giai đoạn", "Bắt đầu (s)", "Kết thúc (s)", "Thời lượng (s)", "Liên kết con trỏ"])
        self.segment_table.itemSelectionChanged.connect(self._focus_segment)
        self.segment_table.itemDoubleClicked.connect(lambda _: self.edit_segment())
        layout.addWidget(self.segment_table)
        self.tabs.addTab(page, "Giai đoạn")


    def _build_formula_tab(self):
        """Dựng tab quản lý công thức; logic tính nằm trong FormulasController."""
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        bar = QtWidgets.QHBoxLayout()
        self.formula_add = button("+ Công thức", self.new_formula)
        self.formula_edit = button("Sửa", self.edit_formula)
        self.formula_duplicate = button("Nhân bản", self.duplicate_formula)
        self.formula_delete = button("Xóa", self.delete_formula)
        for widget in (self.formula_add, self.formula_edit, self.formula_duplicate, self.formula_delete):
            bar.addWidget(widget)
        bar.addStretch()
        self.formula_plot = button("Vẽ công thức", self.plot_formula)
        bar.addWidget(self.formula_plot)
        self.calculate_button = button("Tính kết quả", self.calculate, True)
        bar.addWidget(self.calculate_button)
        layout.addLayout(bar)
        self.formula_table = table(["Tên công thức", "Biểu thức", "Đơn vị", "Giai đoạn áp dụng"])
        self.formula_table.itemDoubleClicked.connect(lambda _: self.edit_formula())
        layout.addWidget(self.formula_table)
        self.tabs.addTab(page, "Công thức")


    def _build_result_tab(self):
        """Dựng bảng kết quả theo giai đoạn và nút xem tín hiệu tính toán."""
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        bar = QtWidgets.QHBoxLayout()
        self.result_label = label("Chưa có kết quả", "muted")
        bar.addWidget(self.result_label, 1)
        self.trace_button = button("Xem tín hiệu tính toán", self.show_result_trace)
        bar.addWidget(self.trace_button)
        layout.addLayout(bar)
        self.result_table = table(["Giai đoạn", "Công thức", "Kết quả", "Đơn vị", "Trạng thái", "Thông tin"])
        layout.addWidget(self.result_table)
        self.tabs.addTab(page, "Kết quả")

