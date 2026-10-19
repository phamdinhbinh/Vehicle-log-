"""Chức năng: bảng Y đầu, Y cuối, ΔY và Δt của cặp con trỏ đã chọn.

Sửa tại đây khi: đổi cách hiển thị phép đo; lấy mẫu ở vehiclelog/measurements.py.
Liên kết: inspector.py tạo bảng/combobox; stages.py bảo đảm hai mốc liền nhau.
"""
# COMPONENT: ui.controllers.measurements
from PySide6 import QtWidgets

from ...measurements import measure_between
from ..widgets import fill_table


def _number(value):
    return "—" if value is None else f"{value:.8g}"


class MeasurementsController:
    """Mixin của MainWindow, chỉ đọc mẫu gốc và không thay kết quả công thức."""

    def _cursor_selected(self):
        """Chọn mốc cũng chọn cặp bắt đầu từ mốc đó; mốc cuối dùng cặp trước."""
        row = self.cursor_table.currentRow()
        if self.project.segments and row >= 0:
            self.pair_combo.setCurrentIndex(min(row, len(self.project.segments) - 1))
        self._refresh_values()

    def _refresh_values(self, *_):
        """Đọc Y ở hai mốc; ΔY=Y cuối−Y đầu, Δt=t cuối−t đầu."""
        if not self.store:
            return
        stage = next((s for s in self.project.segments if s.id == self.pair_combo.currentData()), None)
        cursors = {c.id: c for c in self.project.cursors}
        if stage:
            a, b = cursors[stage.start_cursor], cursors[stage.end_cursor]
            start, end = a.time, b.time
            headers = ["Tín hiệu", f"Y({a.name})", f"Y({b.name})", "ΔY", "Đơn vị"]
            self.delta_label.setText(f"{a.name}: {start:.6f} s → {b.name}: {end:.6f} s\n"
                                     f"Δt = {end-start:.6f} s\nΔY = Y({b.name}) − Y({a.name})\n"
                                     "Giữ mẫu trước mốc; ngoài dữ liệu/invalid hiển thị —.")
        elif self.project.cursors:
            a = self.project.cursors[0]
            start = end = a.time
            headers = ["Tín hiệu", f"Y({a.name})", "—", "ΔY", "Đơn vị"]
            self.delta_label.setText("Thêm một con trỏ nữa để tạo giai đoạn và đo Δt/ΔY.")
        else:
            fill_table(self.value_table, [])
            self.delta_label.setText("Thêm hai con trỏ để tạo giai đoạn và đo Δt/ΔY.")
            self.last_measurements = []
            return
        keys = [key for key in self.project.selected_signals if key in self.store.signals]
        self.last_measurements = measure_between(self.store, keys, start, end)
        self.value_table.setHorizontalHeaderLabels(headers)
        fill_table(self.value_table, [(r.name, _number(r.start_value), _number(r.end_value) if stage else "—",
                                       _number(r.delta) if stage else "—", r.unit) for r in self.last_measurements])
        self.value_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        for row, r in enumerate(self.last_measurements):
            self.value_table.item(row, 0).setToolTip(r.key)
            for col, age in ((1, r.start_age), (2, r.end_age)):
                if age is not None:
                    self.value_table.item(row, col).setToolTip(f"Tuổi mẫu tại con trỏ: {age:.9g} s")
