"""Chức năng: đổi tên giai đoạn, hiển thị cặp con trỏ và thời gian chỉ đọc.

Sửa tại đây khi: đổi form tên giai đoạn; ranh giới chỉ sửa bằng con trỏ.
Liên kết: stages.py tạo giai đoạn tự động; controllers/segments.py mở form này.
"""
# COMPONENT: ui.dialogs.segment
from dataclasses import replace

from PySide6 import QtWidgets

from ..widgets import label


class SegmentDialog(QtWidgets.QDialog):
    """Giai đoạn có sẵn; không chọn hai mốc bất kỳ hoặc nhập ranh giới thủ công."""

    def __init__(self, cursors, segment=None, parent=None):
        super().__init__(parent)
        if segment is None:
            raise ValueError("Giai đoạn được tạo tự động giữa các con trỏ liền nhau.")
        self.original = segment
        self.setWindowTitle("Đổi tên giai đoạn")
        self.resize(420, 210)
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.name_edit = QtWidgets.QLineEdit(segment.name)
        form.addRow("Tên", self.name_edit)
        names = {c.id: c.name for c in cursors}
        form.addRow("Hai con trỏ", label(f"{names.get(segment.start_cursor, '')} → {names.get(segment.end_cursor, '')}"))
        form.addRow("Khoảng thời gian", label(f"{segment.start:.6f} → {segment.end:.6f} s"))
        layout.addLayout(form)
        layout.addWidget(label("Kéo hoặc sửa thời gian con trỏ để thay đổi giai đoạn.", "muted"))
        boxes = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Save | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        boxes.button(QtWidgets.QDialogButtonBox.StandardButton.Save).setText("Lưu")
        boxes.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        boxes.accepted.connect(self.accept)
        boxes.rejected.connect(self.reject)
        layout.addWidget(boxes)

    def segment_value(self):
        """Chỉ trả tên mới; giữ nguyên ID, cặp mốc, thời gian và màu giai đoạn."""
        name = self.name_edit.text().strip()
        if not name:
            raise ValueError("Vui lòng đặt tên giai đoạn.")
        return replace(self.original, name=name)

    def accept(self):
        """Kiểm tra tên trước khi đóng form."""
        try:
            self.segment_value()
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(self, "Tên giai đoạn chưa hợp lệ", str(exc))
            return
        super().accept()
