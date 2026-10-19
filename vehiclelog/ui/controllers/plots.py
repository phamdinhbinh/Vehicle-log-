"""Chức năng: Dựng đồ thị và đồng bộ vùng thời gian với timeline.

Sửa tại đây khi: đổi cách xếp đồ thị, đường con trỏ, vùng giai đoạn hoặc zoom.
Liên kết: panels/workspace.py dựng khung; previews.py tải dữ liệu; cursors.py xử lý mốc.
"""
# COMPONENT: ui.controllers.plots
from __future__ import annotations

from PySide6 import QtGui
import pyqtgraph as pg
from ..theme import COLORS


class PlotsController:
    """Mixin chức năng của MainWindow, không khởi tạo độc lập.

    self.project / self.store và widget được main_window.py cùng panels/ cung cấp.
    Callback có thể gọi controller khác qua cùng self; backend giữ thuật toán dữ liệu.
    """

    def _rebuild_plots(self):
        """Dựng lại các hàng đồ thị, vùng giai đoạn và đường con trỏ từ dự án."""
        self._plot_timer.stop()
        old_range = next(iter(self.plots.values())).viewRange()[0] if self.plots else [0, max(1, self.duration)]
        self._syncing = True
        self._clear_hover()
        self.graphics.clear()
        self.plots, self.curves, self.cursor_lines = {}, {}, {}
        self.segment_regions = []
        if not self.store:
            self._syncing = False
            return
        first_plot = None
        for index, key in enumerate(self.project.selected_signals):
            if key not in self.store.signals:
                continue
            info = self.store.signals[key]
            plot = self.graphics.addPlot(row=index, col=0)
            plot.setMinimumSize(0, 0)
            self.graphics.ci.layout.setRowStretchFactor(index, 1)
            color = COLORS[index % len(COLORS)]
            plot.setTitle(f"{info.name} <span style='color:#829bb7;font-size:10px'> · {info.unit or '—'}</span>", color=color, size="10pt")
            plot.showGrid(x=True, y=True, alpha=0.18)
            plot.setMenuEnabled(False)
            plot.setLabel("left", units=info.unit or None)
            plot.getAxis("left").setWidth(64)
            if index == len(self.project.selected_signals) - 1:
                plot.setLabel("bottom", "Thời gian", units="s")
            else:
                plot.hideAxis("bottom")
            plot.setAutoVisible(y=True)
            plot.setDownsampling(auto=False)
            if first_plot is not None:
                plot.setXLink(first_plot)
            else:
                first_plot = plot
                plot.sigXRangeChanged.connect(self._range_changed)
            self.plots[key] = plot
            self.curves[key] = plot.plot(pen=pg.mkPen(color, width=1.2), connect="finite")
            self.cursor_lines[key] = {}
            for segment in self.project.segments:
                color_obj = QtGui.QColor(segment.color)
                color_obj.setAlpha(20)
                region = pg.LinearRegionItem([segment.start, segment.end], movable=False,
                                              brush=pg.mkBrush(color_obj), pen=pg.mkPen(segment.color, width=0.5))
                region.setZValue(-5)
                plot.addItem(region)
                self.segment_regions.append((segment.id, region))
            for cursor in self.project.cursors:
                line = pg.InfiniteLine(pos=cursor.time, angle=90, movable=self._worker is None,
                                       bounds=self._cursor_limits(cursor.id),
                                       pen=pg.mkPen(cursor.color, width=1.2), hoverPen=pg.mkPen(cursor.color, width=2),
                                       label=cursor.name if index == 0 else None,
                                       labelOpts={"position": 0.94, "color": cursor.color})
                line.setZValue(20)
                line.sigPositionChangeFinished.connect(lambda obj, cid=cursor.id: self._sync_cursor(cid, float(obj.value())))
                plot.addItem(line)
                self.cursor_lines[key][cursor.id] = line
        count = len(self.plots)
        self.empty_label.setVisible(count == 0)
        if first_plot is not None:
            first_plot.setXRange(*old_range, padding=0)
            self._overview_key = next(iter(self.plots))
        else:
            self._overview_key = None
            self.overview_curve.setData([], [])
        self.overview.setXRange(0, max(1, self.duration), padding=0)
        self.view_region.setBounds([0, max(1, self.duration)])
        self.view_region.setRegion(old_range)
        self._syncing = False
        self._update_curves()
        self._refresh_values()
        self.graphics.fit_rows()
        self._install_hover()


    def _range_changed(self, *_):
        """Đồng bộ khoảng zoom chính sang timeline và trì hoãn tải để tránh đọc dồn."""
        if self._syncing or not self.plots:
            return
        limits = next(iter(self.plots.values())).viewRange()[0]
        self._syncing = True
        self.view_region.setRegion(limits)
        self._syncing = False
        self._plot_timer.start()


    def _overview_changed(self, *_):
        """Đồng bộ vùng timeline về đồ thị chính, chặn vòng lặp tín hiệu Qt."""
        if self._syncing or not self.plots:
            return
        self._syncing = True
        next(iter(self.plots.values())).setXRange(*self.view_region.getRegion(), padding=0)
        self._syncing = False
        self._plot_timer.start()


    def fit_horizontal(self):
        """Căn ngang: dùng chung khoảng thời gian toàn log, giữ lựa chọn tín hiệu."""
        if self.plots:
            next(iter(self.plots.values())).setXRange(0, max(1, self.duration), padding=0)
            self._update_curves()

    def fit_vertical(self):
        """Căn dọc: trục Y riêng của mỗi tín hiệu tự bao dữ liệu đang xem."""
        for plot in self.plots.values():
            plot.setAutoVisible(y=True)
            plot.enableAutoRange(axis=pg.ViewBox.YAxis, enable=True)
            plot.getViewBox().updateAutoRange()

    def reset_view(self):
        """Căn X/Y và co mọi hàng đồ thị vừa viewport hiện tại."""
        self.fit_horizontal()
        self.fit_vertical()
        self.graphics.fit_rows()

