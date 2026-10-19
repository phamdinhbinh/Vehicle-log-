"""Hộp thoại tạo/sửa giai đoạn từ thời gian hoặc các con trỏ.

Chức năng: nhập tên, ranh giới, màu và liên kết giai đoạn với con trỏ.
Sửa tại đây khi: đổi các trường nhập hoặc cách người dùng chọn mốc giai đoạn.
Liên kết: models.Segment kiểm tra dữ liệu; MainWindow cập nhật liên kết con trỏ.
"""
# COMPONENT: ui.dialogs.segment
from __future__ import annotations

from PySide6 import QtGui, QtWidgets

from ...models import Segment
from ..theme import COLORS
from ..widgets import button, label, time_spin


class SegmentDialog(QtWidgets.QDialog):
    """Biên tập một giai đoạn, giữ nguyên id khi sửa và tùy chọn liên kết con trỏ."""

    def __init__(self, cursors, segment=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sửa giai đoạn" if segment else "Tạo giai đoạn")
        self.resize(500, 310)
        self.original = segment
        self.cursors = {c.id: c for c in cursors}
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.name_edit = QtWidgets.QLineEdit(segment.name if segment else "Giai đoạn mới")
        self.start_edit = time_spin(segment.start if segment else (cursors[0].time if cursors else 0))
        self.end_edit = time_spin(segment.end if segment else (cursors[1].time if len(cursors) > 1 else 1))
        self.start_combo = QtWidgets.QComboBox()
        self.end_combo = QtWidgets.QComboBox()
        for combo in (self.start_combo, self.end_combo):
            combo.addItem("Nhập thời gian trực tiếp", None)
            for cursor in cursors:
                combo.addItem(f"{cursor.name} · {cursor.time:.6f} s", cursor.id)
        self.start_combo.currentIndexChanged.connect(lambda _: self._link(self.start_combo, self.start_edit))
        self.end_combo.currentIndexChanged.connect(lambda _: self._link(self.end_combo, self.end_edit))
        if segment:
            self.start_combo.setCurrentIndex(max(0, self.start_combo.findData(segment.start_cursor)))
            self.end_combo.setCurrentIndex(max(0, self.end_combo.findData(segment.end_cursor)))
        elif len(cursors) >= 2:
            self.start_combo.setCurrentIndex(1)
            self.end_combo.setCurrentIndex(2)
        form.addRow("Tên giai đoạn", self.name_edit)
        form.addRow("Mốc bắt đầu", self.start_combo)
        form.addRow("Thời gian bắt đầu", self.start_edit)
        form.addRow("Mốc kết thúc", self.end_combo)
        form.addRow("Thời gian kết thúc", self.end_edit)
        self.color = segment.color if segment else COLORS[0]
        self.color_button = button("Chọn màu vùng", self.choose_color)
        form.addRow("Màu", self.color_button)
        layout.addLayout(form)
        hint = label("Chọn con trỏ để liên kết: khi kéo mốc, ranh giới giai đoạn sẽ cập nhật.", "muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        boxes = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Save | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        boxes.accepted.connect(self.accept)
        boxes.rejected.connect(self.reject)
        layout.addWidget(boxes)

    def _link(self, combo, spin):
        """Khóa thời gian khi chọn con trỏ và lấy timestamp hiện tại của con trỏ đó."""
        cursor_id = combo.currentData()
        spin.setEnabled(cursor_id is None)
        if cursor_id in self.cursors:
            spin.setValue(self.cursors[cursor_id].time)

    def choose_color(self):
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor(self.color), self)
        if color.isValid():
            self.color = color.name()

    def segment_value(self):
        """Tạo và kiểm tra Segment; không thay đổi đối tượng gốc trong hộp thoại."""
        name = self.name_edit.text().strip()
        if not name:
            raise ValueError("Vui lòng đặt tên giai đoạn.")
        kwargs = {"id": self.original.id} if self.original else {}
        result = Segment(name, self.start_edit.value(), self.end_edit.value(), color=self.color,
                         start_cursor=self.start_combo.currentData(), end_cursor=self.end_combo.currentData(), **kwargs)
        result.validate()
        return result

    def accept(self):
        try:
            self.segment_value()
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(self, "Giai đoạn chưa hợp lệ", str(exc))
            return
        super().accept()
