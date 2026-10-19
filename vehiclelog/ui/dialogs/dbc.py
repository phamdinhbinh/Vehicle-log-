"""Hộp thoại gán DBC theo kênh CAN.

Chức năng: thêm/xóa dòng kênh, chọn file DBC và kiểm tra ánh xạ đầu vào.
Sửa tại đây khi: đổi giao diện quản lý DBC hoặc quy tắc kiểm tra kênh/file.
Liên kết: ui/main_window.py mở hộp thoại; importers.py sử dụng mapping trả về.
"""
# COMPONENT: ui.dialogs.dbc
from __future__ import annotations

from pathlib import Path

from PySide6 import QtWidgets

from ..widgets import button, label, table


class DbcDialog(QtWidgets.QDialog):
    """Biên tập ánh xạ kênh CAN → DBC; số kênh hiển thị và lưu bắt đầu từ 1."""
    def __init__(self, mapping=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DBC theo kênh CAN")
        self.resize(720, 350)
        layout = QtWidgets.QVBoxLayout(self)
        info = label("Gán DBC cho từng kênh CAN. Số kênh bắt đầu từ 1.\nCó thể thêm nhiều DBC cho các kênh khác nhau.", "muted")
        layout.addWidget(info)
        self.rows = table(["Kênh CAN", "File DBC", ""])
        self.rows.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.rows)
        for channel, path in (mapping or {}).items():
            self.add_row(int(channel), str(path))
        if not self.rows.rowCount():
            self.add_row()
        controls = QtWidgets.QHBoxLayout()
        controls.addWidget(button("+ Thêm kênh", self.add_row))
        controls.addWidget(button("Xóa dòng", self.delete_row))
        controls.addStretch()
        layout.addLayout(controls)
        boxes = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        boxes.accepted.connect(self.accept)
        boxes.rejected.connect(self.reject)
        layout.addWidget(boxes)

    def add_row(self, channel=None, path=""):
        """Thêm bộ nhập kênh/file; bỏ qua giá trị bool từ tín hiệu clicked của Qt."""
        # clicked(bool) must not accidentally become channel 0.
        if isinstance(channel, bool) or channel is None:
            channel = self.rows.rowCount() + 1
        r = self.rows.rowCount()
        self.rows.insertRow(r)
        spin = QtWidgets.QSpinBox()
        spin.setRange(1, 256)
        spin.setValue(channel)
        self.rows.setCellWidget(r, 0, spin)
        edit = QtWidgets.QLineEdit(path)
        self.rows.setCellWidget(r, 1, edit)
        browse = button("Chọn…")
        browse.clicked.connect(lambda checked=False, e=edit: self.browse(e))
        self.rows.setCellWidget(r, 2, browse)

    def browse(self, edit):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Chọn DBC", "", "CAN database (*.dbc)")
        if filename:
            edit.setText(filename)

    def delete_row(self):
        row = self.rows.currentRow()
        if row >= 0:
            self.rows.removeRow(row)

    def mapping(self):
        """Trả về ánh xạ đã kiểm tra, bỏ qua dòng trống và từ chối kênh trùng."""
        result = {}
        for row in range(self.rows.rowCount()):
            path = self.rows.cellWidget(row, 1).text().strip()
            if not path:
                continue
            channel = self.rows.cellWidget(row, 0).value()
            if channel in result:
                raise ValueError(f"Kênh {channel} được gán nhiều lần.")
            if not Path(path).is_file():
                raise ValueError(f"Không tìm thấy DBC: {path}")
            result[channel] = path
        return result

    def accept(self):
        """Chỉ đóng hộp thoại khi mọi dòng DBC đã nhập đều hợp lệ."""
        try:
            self.mapping()
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(self, "DBC chưa hợp lệ", str(exc))
            return
        super().accept()
