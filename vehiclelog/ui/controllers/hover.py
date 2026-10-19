"""Chức năng: con trỏ xem nhanh đi theo chuột, đọc mẫu tín hiệu gốc.

Sửa tại đây khi: đổi màu con trỏ, định dạng thời gian/giá trị hoặc cách lấy mẫu.
Liên kết: measurements.sample_at giữ mẫu trước mốc; độc lập với mốc chia giai đoạn.
"""
# COMPONENT: ui.controllers.hover
from PySide6 import QtCore
import pyqtgraph as pg
from ...measurements import sample_at


class HoverController:
    """Một thời điểm xem nhanh chung; chỉ hiện giá trị của hàng đang trỏ chuột."""

    def _clear_hover(self):
        proxy = getattr(self, "_hover_proxy", None)
        if proxy is not None:
            proxy.disconnect()
        self._hover_proxy = None
        self._hide_hover()
        self._hover_items = {}

    def _install_hover(self):
        self._hover_items = {}
        for key, plot in self.plots.items():
            line = pg.InfiniteLine(angle=90, movable=False,
                                   pen=pg.mkPen("#ffe09b", style=QtCore.Qt.PenStyle.DashLine))
            dot = pg.ScatterPlotItem(size=8, brush="#ffe09b", pen="#ffffff")
            for item in (line, dot):
                item.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)
                item.setZValue(30)
                plot.addItem(item, ignoreBounds=True)
                item.hide()
            self._hover_items[key] = (line, dot)
        # Giới hạn đọc đĩa khi di chuột; giữ proxy để tránh bị garbage collector xóa.
        self._hover_proxy = pg.SignalProxy(self.graphics.scene().sigMouseMoved,
                                          rateLimit=30, slot=self._hover_moved)

    def _hide_hover(self, *_):
        for line, dot in getattr(self, "_hover_items", {}).values():
            line.hide()
            dot.hide()
        self.hover_label.setText("Di chuột trên đồ thị để xem thời gian và giá trị tín hiệu")

    def _hover_moved(self, event):
        """Ánh xạ scene sang thời gian, không dùng Y chuột hoặc dữ liệu đã giảm mẫu."""
        self._hide_hover()
        if self._syncing or not self.store or not self.hover_check.isChecked():
            return
        position = event[0]
        for key, plot in self.plots.items():
            view = plot.getViewBox()
            if not view.sceneBoundingRect().contains(position):
                continue
            time = float(view.mapSceneToView(position).x())
            value, age = sample_at(self.store, key, time)
            info = self.store.signals[key]
            for line, _ in self._hover_items.values():
                line.setValue(time)
                line.show()
            dot = self._hover_items[key][1]
            if value is None:
                text = f"{info.name} · t = {time:.6f} s · Y = — (không có mẫu hợp lệ)"
            else:
                dot.setData([time], [value])
                dot.show()
                text = (f"{info.name} · t = {time:.6f} s · Y = {value:.9g} {info.unit}"
                        f" · mẫu tại {time - age:.6f} s")
            self.hover_label.setText(text)
            return
