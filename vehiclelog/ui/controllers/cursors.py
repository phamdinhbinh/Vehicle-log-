"""Chức năng: con trỏ M1…Mn theo thứ tự thời gian, không đi xuyên qua nhau.

Sửa tại đây khi: đổi cách thêm/xóa/kéo mốc; giai đoạn được tự đồng bộ theo mốc.
Liên kết: stages.py tạo cặp liên tiếp; measurements.py đọc Y từ dữ liệu gốc.
"""
# COMPONENT: ui.controllers.cursors
import math

from PySide6 import QtCore, QtGui, QtWidgets

from ...models import Cursor
from ..theme import COLORS

Qt = QtCore.Qt


class CursorsController:
    """Mixin của MainWindow; UI chỉ quản lý mốc và thời gian, không khóa/liên kết tay."""

    def add_cursor(self, time=None):
        """Chèn mốc theo thời gian; mặc định chia đôi giai đoạn rộng nhất đang xem."""
        if not self.store or self._worker:
            return None
        if time is None or isinstance(time, bool):
            lo, hi = next(iter(self.plots.values())).viewRange()[0] if self.plots else (0, self.duration)
            points = sorted({max(0, lo), min(self.duration, hi),
                             *(c.time for c in self.project.cursors if lo < c.time < hi)})
            gaps = [(b - a, a, b) for a, b in zip(points, points[1:]) if b > a]
            if not gaps:
                return None
            _, a, b = max(gaps)
            time = (a + b) / 2
        if not math.isfinite(float(time)):
            return None
        time = min(max(float(time), 0), self.duration)
        if any(abs(c.time - time) < 1e-6 for c in self.project.cursors):
            self.status_label.setText("Vị trí đã có con trỏ. Hãy chọn thời điểm khác.")
            return None
        cursor = Cursor("", time, COLORS[len(self.project.cursors) % len(COLORS)])
        self.project.cursors.append(cursor)
        self._sync_stages()
        self._mark_changed()
        self._refresh_tables()
        self._rebuild_plots()
        self.cursor_table.selectRow(self.project.cursors.index(cursor))
        return cursor

    def _cursor_limits(self, cursor_id):
        """Giới hạn mốc trong hai hàng xóm để M1 < M2 < … luôn đúng."""
        index = next(i for i, c in enumerate(self.project.cursors) if c.id == cursor_id)
        cursors = self.project.cursors
        lower = cursors[index - 1].time + 1e-6 if index else 0.0
        upper = cursors[index + 1].time - 1e-6 if index + 1 < len(cursors) else self.duration
        return lower, upper

    def _sync_cursor(self, cursor_id, time):
        """Cập nhật hai giai đoạn kề mốc và phép đo, giữ thứ tự các con trỏ."""
        if self._syncing or self._worker or not math.isfinite(time):
            return
        cursor = next((c for c in self.project.cursors if c.id == cursor_id), None)
        if cursor is None:
            return
        lower, upper = self._cursor_limits(cursor_id)
        if lower > upper:
            return
        cursor.time = min(max(float(time), lower), upper)
        self._sync_stages()
        self._syncing = True
        try:
            for lines in self.cursor_lines.values():
                for c in self.project.cursors:
                    if c.id in lines:
                        lines[c.id].setBounds(self._cursor_limits(c.id))
                        lines[c.id].setValue(c.time)
            by_id = {s.id: s for s in self.project.segments}
            for segment_id, region in self.segment_regions:
                if segment_id in by_id:
                    s = by_id[segment_id]
                    region.setRegion((s.start, s.end))
        finally:
            self._syncing = False
        self._mark_changed()
        self._refresh_cursors()
        self._refresh_segments()
        self._refresh_values()
        self.status_label.setText(f"{cursor.name}: {cursor.time:.6f} s · đã cập nhật các giai đoạn kề mốc")

    def _refresh_cursors(self):
        """Tên M1… tự đánh số; chỉ thời gian được sửa trong bảng."""
        current = self.cursor_table.currentRow()
        selected = self.cursor_table.item(current, 0)
        selected_id = selected.data(Qt.ItemDataRole.UserRole) if selected else None
        self.cursor_table.blockSignals(True)
        self.cursor_table.setRowCount(len(self.project.cursors))
        for row, cursor in enumerate(self.project.cursors):
            name = QtWidgets.QTableWidgetItem(cursor.name)
            name.setData(Qt.ItemDataRole.UserRole, cursor.id)
            name.setFlags(name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name.setForeground(QtGui.QColor(cursor.color))
            self.cursor_table.setItem(row, 0, name)
            self.cursor_table.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{cursor.time:.6f}"))
        if self.project.cursors:
            row = next((i for i, c in enumerate(self.project.cursors) if c.id == selected_id), 0)
            self.cursor_table.selectRow(row)
        self.cursor_table.blockSignals(False)

    def _cursor_edited(self, item):
        """Sửa thời gian mốc rồi đồng bộ đồ thị, giai đoạn và bảng ΔY."""
        if self._syncing or item.column() != 1 or item.row() >= len(self.project.cursors):
            return
        try:
            value = float(item.text())
            if not math.isfinite(value) or not 0 <= value <= self.duration:
                raise ValueError("Thời gian phải nằm trong log.")
            self._sync_cursor(self.project.cursors[item.row()].id, value)
        except ValueError as exc:
            self._notify("Thời gian chưa hợp lệ", str(exc))
            self._refresh_cursors()

    def change_cursor_color(self):
        """Chọn màu đường mốc mà không thay ranh giới giai đoạn."""
        row = self.cursor_table.currentRow()
        if row < 0 or self._worker:
            return
        cursor = self.project.cursors[row]
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor(cursor.color), self, "Màu con trỏ")
        if color.isValid():
            cursor.color = color.name()
            self._dirty = True
            self._refresh_cursors()
            self._rebuild_plots()

    def delete_cursor(self):
        """Xóa mốc và tự gộp hai khoảng kề nhau; không giữ giai đoạn rời."""
        row = self.cursor_table.currentRow()
        if row < 0 or self._worker:
            return
        self.project.cursors.pop(row)
        self._sync_stages()
        self._mark_changed()
        self._refresh_tables()
        self._rebuild_plots()
        self.status_label.setText("Đã xóa mốc và cập nhật các giai đoạn liên tiếp.")
