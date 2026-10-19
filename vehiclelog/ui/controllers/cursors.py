"""Chức năng: Thêm / sửa nhiều con trỏ và đồng bộ giai đoạn liên kết.

Sửa tại đây khi: đổi bám mẫu, khóa mốc, cập nhật giai đoạn hoặc giá trị tại mốc.
Liên kết: panels/inspector.py dựng bảng; plots.py vẽ đường; segments.py quản lý vùng giai đoạn.
"""
# COMPONENT: ui.controllers.cursors
from __future__ import annotations

import math
import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets
from ...models import Cursor
from ..theme import COLORS
from ..widgets import fill_table

Qt = QtCore.Qt


class CursorsController:
    """Mixin chức năng của MainWindow, không khởi tạo độc lập.

    self.project / self.store và widget được main_window.py cùng panels/ cung cấp.
    Callback có thể gọi controller khác qua cùng self; backend giữ thuật toán dữ liệu.
    """

    def add_cursor(self, time=None):
        """Tạo mốc mới tại thời điểm chỉ định hoặc giữa vùng đang xem."""
        if not self.store or self._worker:
            return None
        if isinstance(time, bool):
            time = None
        if time is None:
            limits = next(iter(self.plots.values())).viewRange()[0] if self.plots else [0, self.duration]
            time = (limits[0] + limits[1]) / 2
        existing = {cursor.name for cursor in self.project.cursors}
        number = 1
        while f"M{number}" in existing:
            number += 1
        cursor = Cursor(f"M{number}", min(max(float(time), 0), self.duration), COLORS[len(self.project.cursors) % len(COLORS)])
        self.project.cursors.append(cursor)
        self._dirty = True
        self._refresh_cursors()
        self._rebuild_plots()
        return cursor


    def _sync_cursor(self, cursor_id, time):
        """Đồng bộ mốc với các đồ thị và giai đoạn liên kết; xóa kết quả hết hiệu lực."""
        if self._syncing:
            return
        cursor = next((c for c in self.project.cursors if c.id == cursor_id), None)
        if not cursor or cursor.locked or self._worker:
            return
        if not math.isfinite(time):
            return
        cursor.time = min(max(0.0, float(time)), self.duration)
        if self.snap_check.isChecked() and self.store and self.project.selected_signals:
            key = self.project.selected_signals[0]
            times, _ = self.store.read(key, start=cursor.time, end=cursor.time, neighbors=True)
            if len(times):
                cursor.time = float(times[np.argmin(np.abs(times - cursor.time))])
        invalid = []
        for segment in self.project.segments:
            if segment.start_cursor == cursor_id:
                segment.start = cursor.time
            if segment.end_cursor == cursor_id:
                segment.end = cursor.time
            if segment.end <= segment.start:
                invalid.append(segment.name)
        self._syncing = True
        for lines in self.cursor_lines.values():
            if cursor_id in lines:
                lines[cursor_id].setValue(cursor.time)
        for segment_id, region in self.segment_regions:
            segment = next(s for s in self.project.segments if s.id == segment_id)
            region.setRegion((segment.start, segment.end))
        self._syncing = False
        self._mark_changed()
        self._refresh_cursors()
        self._refresh_segments()
        self._refresh_values()
        if invalid:
            self.status_label.setText("Giai đoạn chưa hợp lệ (kết thúc ≤ bắt đầu): " + ", ".join(invalid))
        else:
            self.status_label.setText(f"{cursor.name}: {cursor.time:.6f} s · kết quả liên quan cần tính lại")


    def _refresh_cursors(self):
        """Nạp lại bảng mốc, khóa signal để tránh tự gọi thao tác sửa."""
        row_selected = self.cursor_table.currentRow()
        self.cursor_table.blockSignals(True)
        self.cursor_table.setRowCount(len(self.project.cursors))
        for row, cursor in enumerate(self.project.cursors):
            self.cursor_table.setItem(row, 0, QtWidgets.QTableWidgetItem(cursor.name))
            self.cursor_table.item(row, 0).setForeground(QtGui.QColor(cursor.color))
            self.cursor_table.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{cursor.time:.6f}"))
            lock = QtWidgets.QTableWidgetItem()
            lock.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable)
            lock.setCheckState(Qt.CheckState.Checked if cursor.locked else Qt.CheckState.Unchecked)
            self.cursor_table.setItem(row, 2, lock)
        self.cursor_table.resizeColumnsToContents()
        if self.project.cursors:
            self.cursor_table.selectRow(max(0, min(row_selected, len(self.project.cursors) - 1)))
        self.cursor_table.blockSignals(False)


    def _cursor_edited(self, item):
        """Kiểm tra sửa tên, thời gian hoặc khóa; từ chối timestamp ngoài log."""
        row, col = item.row(), item.column()
        if row >= len(self.project.cursors) or self._syncing:
            return
        cursor = self.project.cursors[row]
        if col == 0:
            if item.text().strip():
                cursor.name = item.text().strip()
                self._dirty = True
                self._rebuild_plots()
                self._refresh_segments()
            else:
                self._refresh_cursors()
        elif col == 1:
            try:
                value = float(item.text())
                if not math.isfinite(value) or not 0 <= value <= self.duration:
                    raise ValueError("Thời gian phải nằm trong log.")
                if cursor.locked:
                    raise ValueError("Mốc đang khóa. Hãy bỏ khóa trước khi sửa.")
                self._sync_cursor(cursor.id, value)
            except ValueError as exc:
                self._notify("Thời gian chưa hợp lệ", str(exc))
                self._refresh_cursors()
        elif col == 2:
            cursor.locked = item.checkState() == Qt.CheckState.Checked
            self._dirty = True
            for lines in self.cursor_lines.values():
                lines[cursor.id].setMovable(not cursor.locked)


    def change_cursor_color(self):
        """Chọn màu và dựng lại đường mốc tương ứng trên các đồ thị."""
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
        """Xóa mốc; giữ thời gian giai đoạn và bỏ liên kết tới mốc đã xóa."""
        row = self.cursor_table.currentRow()
        if row < 0 or row >= len(self.project.cursors) or self._worker:
            return
        cursor = self.project.cursors.pop(row)
        for segment in self.project.segments:
            if segment.start_cursor == cursor.id:
                segment.start_cursor = None
            if segment.end_cursor == cursor.id:
                segment.end_cursor = None
        self._dirty = True
        self._refresh_tables()
        self._rebuild_plots()
        self.status_label.setText("Đã xóa mốc. Giai đoạn giữ nguyên thời gian và bỏ liên kết tới mốc đã xóa.")


    def _refresh_values(self):
        """Hiện mẫu trước con trỏ cùng tuổi mẫu; không nội suy giá trị hiển thị."""
        if not self.store:
            return
        row = self.cursor_table.currentRow()
        cursor = self.project.cursors[row] if 0 <= row < len(self.project.cursors) else (self.project.cursors[0] if self.project.cursors else None)
        if not cursor:
            fill_table(self.value_table, [])
            return
        self.values_title.setText(f"GIÁ TRỊ TẠI {cursor.name} · {cursor.time:.3f} s")
        rows = []
        for key in self.project.selected_signals:
            if key not in self.store.signals:
                continue
            info = self.store.signals[key]
            times, values = self.store.read(key, start=cursor.time, end=cursor.time, neighbors=True)
            index = np.searchsorted(times, cursor.time, side="right") - 1
            value = values[index] if 0 <= index < len(values) else float("nan")
            age = cursor.time - times[index] if index >= 0 and len(times) else float("nan")
            text = f"{value:.6g}" if np.isfinite(value) else "—"
            if math.isfinite(age) and age > 0:
                text += f" ({age:.3g}s)"
            rows.append((info.name, text, info.unit))
        fill_table(self.value_table, rows)
        if len(self.project.cursors) >= 2:
            a, b = self.project.cursors[:2]
            self.delta_label.setText(f"Δt ({a.name} → {b.name}): {b.time-a.time:.6f} s\n"
                                     "Giá trị: mẫu trước mốc; trong ngoặc là tuổi mẫu.\nCông thức có cấu hình giới hạn mất mẫu riêng.")

