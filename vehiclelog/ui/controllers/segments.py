"""Chức năng: Quản lý giai đoạn từ các cặp mốc hoặc thời gian nhập tay.

Sửa tại đây khi: đổi kiểm tra ranh giới, tạo / sửa / xóa hoặc zoom tới giai đoạn.
Liên kết: dialogs/segment.py nhận giá trị; panels/analysis.py dựng bảng; formulas.py dùng gán giai đoạn.
"""
# COMPONENT: ui.controllers.segments
from __future__ import annotations

from PySide6 import QtWidgets
from ..dialogs.segment import SegmentDialog
from ..widgets import fill_table


class SegmentsController:
    """Mixin chức năng của MainWindow, không khởi tạo độc lập.

    self.project / self.store và widget được main_window.py cùng panels/ cung cấp.
    Callback có thể gọi controller khác qua cùng self; backend giữ thuật toán dữ liệu.
    """

    def add_segment(self, segment):
        """Kiểm tra phạm vi rồi thêm giai đoạn, làm mới bảng và vùng tô trên đồ thị."""
        segment.validate()
        if self.store and (segment.start < 0 or segment.end > self.duration + 1e-6):
            raise ValueError("Giai đoạn phải nằm trong thời gian log.")
        self.project.segments.append(segment)
        self._mark_changed()
        self._refresh_tables()
        self._rebuild_plots()


    def new_segment(self):
        """Mở hộp thoại tạo giai đoạn từ hai mốc hoặc thời gian nhập trực tiếp."""
        if not self.store or self._worker:
            return
        dialog = SegmentDialog(self.project.cursors, parent=self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            try:
                self.add_segment(dialog.segment_value())
            except ValueError as exc:
                self._notify("Giai đoạn chưa hợp lệ", str(exc))


    def edit_segment(self):
        """Sửa giai đoạn hiện chọn và kiểm tra ranh giới trong thời lượng log."""
        row = self.segment_table.currentRow()
        if row < 0 or self._worker:
            return
        dialog = SegmentDialog(self.project.cursors, self.project.segments[row], self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            segment = dialog.segment_value()
            if segment.start < 0 or segment.end > self.duration + 1e-6:
                self._notify("Giai đoạn chưa hợp lệ", "Giai đoạn phải nằm trong thời gian log.")
                return
            self.project.segments[row] = segment
            self._mark_changed()
            self._refresh_tables()
            self._rebuild_plots()


    def delete_segment(self):
        """Xóa giai đoạn và bỏ gán giai đoạn đó khỏi mọi công thức."""
        row = self.segment_table.currentRow()
        if row < 0 or self._worker:
            return
        segment = self.project.segments.pop(row)
        for formula in self.project.formulas:
            formula.segment_ids = [value for value in formula.segment_ids if value != segment.id]
        self._mark_changed()
        self._refresh_tables()
        self._rebuild_plots()


    def _refresh_segments(self):
        """Hiện thời gian và tên con trỏ liên kết của các giai đoạn."""
        names = {c.id: c.name for c in self.project.cursors}
        self.segment_table.blockSignals(True)
        fill_table(self.segment_table, [(s.name, f"{s.start:.6f}", f"{s.end:.6f}", f"{s.end-s.start:.3f}",
                                        f"{names.get(s.start_cursor, 'thời gian')} → {names.get(s.end_cursor, 'thời gian')}")
                                       for s in self.project.segments])
        self.segment_table.blockSignals(False)


    def _focus_segment(self):
        """Zoom tới giai đoạn được chọn trong bảng."""
        row = self.segment_table.currentRow()
        if row >= 0 and row < len(self.project.segments) and self.plots:
            segment = self.project.segments[row]
            if segment.end > segment.start:
                next(iter(self.plots.values())).setXRange(segment.start, segment.end, padding=0.03)

