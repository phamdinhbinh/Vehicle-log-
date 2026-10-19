"""Chức năng: Vùng đồ thị, timeline và tab dữ liệu thô / cảnh báo.

Sửa tại đây khi: đổi kích thước đồ thị, timeline hoặc bố cục các tab.
Liên kết: controllers/plots.py và previews.py xử lý dữ liệu vẽ; analysis.py dựng tab phân tích.
"""
# COMPONENT: ui.panels.workspace
from __future__ import annotations

from PySide6 import QtCore, QtWidgets
import pyqtgraph as pg
from ..widgets import label, button, table
from ..plot_canvas import FittedPlotCanvas

Qt = QtCore.Qt

class WorkspacePanel:
    """Mixin bố cục: gắn widget lên MainWindow và nối callback của controller.

    Không khởi tạo riêng; self là MainWindow với trạng thái chia sẻ từ main_window.py.
    """

    def _build_workspace(self):
        """Dựng vùng đồ thị, timeline và các tab phân tích; không đọc dữ liệu log."""
        splitter = QtWidgets.QSplitter(Qt.Orientation.Vertical)
        charts = QtWidgets.QFrame()
        charts.setObjectName("panel")
        layout = QtWidgets.QVBoxLayout(charts)
        layout.setContentsMargins(10, 10, 10, 8)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(label("ĐỒ THỊ TÍN HIỆU", "section"))
        self.range_label = label("—", "muted")
        row.addWidget(self.range_label)
        row.addStretch()
        layout.addLayout(row)
        fit_bar = QtWidgets.QHBoxLayout()
        self.fit_x_button = button("Căn ngang", self.fit_horizontal)
        self.fit_x_button.setToolTip("Đưa trục thời gian của mọi tín hiệu về toàn bộ log.")
        self.fit_y_button = button("Căn dọc", self.fit_vertical)
        self.fit_y_button.setToolTip("Tự căn trục giá trị Y riêng cho mỗi tín hiệu trong vùng đang xem.")
        self.fit_all_button = button("Vừa màn hình", self.reset_view)
        self.fit_all_button.setToolTip("Căn cả X/Y và chia các khung để mọi tín hiệu đã chọn đều hiện trên màn hình.")
        for control in (self.fit_x_button, self.fit_y_button, self.fit_all_button):
            fit_bar.addWidget(control)
        fit_bar.addStretch()
        layout.addLayout(fit_bar)
        # Canvas co cả scene khi cần, thay vì tăng minimumHeight và buộc cuộn.
        self.graphics = FittedPlotCanvas()
        layout.addWidget(self.graphics, 1)
        self.empty_label = label("Mở log và chọn tín hiệu ở bảng bên trái\nđể bắt đầu phân tích.", "muted")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty_label)
        self.overview = pg.PlotWidget()
        self.overview.setFixedHeight(55)
        self.overview.setMouseEnabled(x=True, y=False)
        self.overview.hideAxis("left")
        self.overview.getAxis("bottom").setLabel("Thời gian", units="s")
        self.overview_curve = self.overview.plot(pen=pg.mkPen("#3d8f94", width=1))
        self.view_region = pg.LinearRegionItem([0, 1], brush=pg.mkBrush(67, 192, 166, 35), pen=pg.mkPen("#40bfab"))
        self.view_region.setZValue(10)
        self.overview.addItem(self.view_region)
        self.view_region.sigRegionChanged.connect(self._overview_changed)
        layout.addWidget(self.overview)
        splitter.addWidget(charts)
        self.tabs = QtWidgets.QTabWidget()
        self._build_segment_tab()
        self._build_formula_tab()
        self._build_result_tab()
        warning_page = QtWidgets.QWidget()
        warning_layout = QtWidgets.QVBoxLayout(warning_page)
        self.warning_text = QtWidgets.QPlainTextEdit()
        self.warning_text.setReadOnly(True)
        warning_layout.addWidget(self.warning_text)
        self.tabs.addTab(warning_page, "Chất lượng dữ liệu")
        raw_page = QtWidgets.QWidget()
        raw_layout = QtWidgets.QVBoxLayout(raw_page)
        self.raw_label = label("Bản xem trước bản tin CAN · tối đa 500 bản tin đầu log", "muted")
        raw_layout.addWidget(self.raw_label)
        self.frame_table = table(["Thời gian (s)", "CAN", "CAN ID", "FD", "DLC", "Payload (hex)"])
        raw_layout.addWidget(self.frame_table)
        self.tabs.addTab(raw_page, "CAN thô · xem trước")
        splitter.addWidget(self.tabs)
        splitter.setSizes([570, 235])
        splitter.setStretchFactor(0, 1)
        self.main_splitter.addWidget(splitter)

