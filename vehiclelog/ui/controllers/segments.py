"""Chức năng: các giai đoạn tự tạo giữa hai con trỏ liền nhau.

Sửa tại đây khi: đổi bảng giai đoạn hoặc cách chọn vùng đo; quy tắc ở stages.py.
Liên kết: không tạo giai đoạn thủ công; kéo/thêm/xóa con trỏ để đổi khoảng.
"""
# COMPONENT: ui.controllers.segments
from PySide6 import QtWidgets

from ...stages import synchronize_stages
from ..dialogs.segment import SegmentDialog
from ..widgets import fill_table


class SegmentsController:
    """Mixin của MainWindow: tự đồng bộ giai đoạn, chỉ cho phép đổi tên."""

    def _sync_stages(self):
        """M1–M2 là giai đoạn 1, M2–M3 là giai đoạn 2; giữ gán công thức phù hợp."""
        return synchronize_stages(self.project)

    def edit_segment(self):
        """Đổi tên giai đoạn; ranh giới luôn lấy trực tiếp từ cặp con trỏ."""
        row = self.segment_table.currentRow()
        if row < 0 or self._worker:
            return
        segment = self.project.segments[row]
        dialog = SegmentDialog(self.project.cursors, segment, self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            segment.name = dialog.segment_value().name
            self._dirty = True
            # Tên kết quả được cập nhật, không thay giá trị đã tính.
            for result in self.project.results:
                if result.segment_id == segment.id:
                    result.segment_name = segment.name
            self._refresh_tables()

    def _refresh_segments(self):
        """Hiện các cặp liền kề và đồng bộ danh sách chọn cặp đo ΔY."""
        names = {c.id: c.name for c in self.project.cursors}
        selected_id = self.pair_combo.currentData()
        self.segment_table.blockSignals(True)
        fill_table(self.segment_table, [(s.name, f"{s.start:.6f}", f"{s.end:.6f}", f"{s.end-s.start:.6f}",
                                        f"{names.get(s.start_cursor, '')} → {names.get(s.end_cursor, '')}")
                                       for s in self.project.segments])
        self.segment_table.blockSignals(False)
        self.pair_combo.blockSignals(True)
        self.pair_combo.clear()
        for s in self.project.segments:
            self.pair_combo.addItem(f"{names[s.start_cursor]} → {names[s.end_cursor]} · {s.name}", s.id)
        index = self.pair_combo.findData(selected_id)
        self.pair_combo.setCurrentIndex(max(0, index))
        self.pair_combo.blockSignals(False)

    def _focus_segment(self):
        """Chọn cặp đo tương ứng và zoom tới giai đoạn được chọn trong bảng."""
        row = self.segment_table.currentRow()
        if 0 <= row < len(self.project.segments):
            segment = self.project.segments[row]
            self.pair_combo.setCurrentIndex(self.pair_combo.findData(segment.id))
            if self.plots:
                next(iter(self.plots.values())).setXRange(segment.start, segment.end, padding=0)
