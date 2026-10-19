"""Chức năng: co giãn các hàng đồ thị vừa viewport, không dùng thanh cuộn.

Sửa tại đây khi: đổi cách chia chiều cao khi chọn nhiều tín hiệu hoặc đổi cỡ cửa sổ.
Liên kết: panels/workspace.py tạo canvas; controllers/plots.py cung cấp số hàng.
"""
# COMPONENT: ui.plot_canvas
from PySide6 import QtCore
import pyqtgraph as pg


class FittedPlotCanvas(pg.GraphicsLayoutWidget):
    """Chia đều các hàng và thu cả scene khi số hàng vượt chiều cao tối thiểu.

    Chỉ thay phép biến đổi hiển thị, giữ nguyên tọa độ/thời gian của tín hiệu.
    Nhiều tín hiệu sẽ có khung nhỏ hơn; tất cả vẫn nằm trong viewport.
    """

    pointerLeft = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.viewport().installEventFilter(self)
        self.setMinimumSize(0, 0)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.ci.layout.setContentsMargins(2, 2, 2, 2)
        self.ci.layout.setSpacing(3)
        self._fit_timer = QtCore.QTimer(self)
        self._fit_timer.setSingleShot(True)
        self._fit_timer.timeout.connect(self.fit_rows)

    def eventFilter(self, watched, event):
        """Xóa readout khi chuột rời viewport, kể cả không có mouseMoved tiếp theo."""
        if watched is self.viewport() and event.type() == QtCore.QEvent.Type.Leave:
            self.pointerLeft.emit()
        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        """Co giãn lại scene sau khi Qt tính xong kích thước viewport mới."""
        super().resizeEvent(event)
        if hasattr(self, "_fit_timer"):
            self._fit_timer.start(0)

    def fit_rows(self):
        """Lấy kích thước thực của layout và ánh xạ toàn bộ vào vùng đang có."""
        width, height = max(1, self.viewport().width()), max(1, self.viewport().height())
        self.ci.setGeometry(QtCore.QRectF(0, 0, width, height))
        self.ci.layout.activate()
        rect = self.ci.boundingRect()
        if rect.width() > 0 and rect.height() > 0:
            self.setRange(rect, padding=0, lockAspect=False)
