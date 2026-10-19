"""Hộp thoại cấu hình xuất Excel, MF4 tín hiệu hoặc MF4 bản tin thô.

Chức năng: chọn định dạng, tín hiệu, giai đoạn và các tùy chọn đồng bộ thời gian.
Sửa tại đây khi: đổi giao diện xuất hoặc điều kiện bật/tắt, xác thực các lựa chọn.
Liên kết: MainWindow chạy tác vụ xuất; exports.py chịu trách nhiệm ghi file.
"""
# COMPONENT: ui.dialogs.export
from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtWidgets

from ..widgets import button, label, time_spin

Qt = QtCore.Qt


class ExportDialog(QtWidgets.QDialog):
    """Thu thập và kiểm tra lựa chọn xuất; thao tác ghi file chạy ở lớp tác vụ nền."""

    def __init__(self, store, project, parent=None):
        super().__init__(parent)
        self.store, self.project = store, project
        self.setWindowTitle("Xuất dữ liệu & kết quả")
        self.resize(710, 650)
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.format_combo = QtWidgets.QComboBox()
        self.format_combo.addItem("Excel (.xlsx)", "excel")
        self.format_combo.addItem("MF4 — tín hiệu đã giải mã", "mf4")
        self.format_combo.addItem("BLF → MF4 — bản tin CAN thô", "raw")
        form.addRow("Định dạng", self.format_combo)
        self.raster_check = QtWidgets.QCheckBox("Đồng bộ thời gian khi xuất Excel")
        self.raster_spin = time_spin(0.1)
        self.raster_spin.setMinimum(0.000001)
        self.raster_spin.setEnabled(False)
        self.raster_check.toggled.connect(self.raster_spin.setEnabled)
        form.addRow(self.raster_check, self.raster_spin)
        self.interpolation = QtWidgets.QComboBox()
        self.interpolation.addItem("Giữ giá trị trước", "hold")
        self.interpolation.addItem("Nội suy tuyến tính", "linear")
        self.max_gap = time_spin(1)
        self.max_gap.setMinimum(0.000001)
        form.addRow("Đồng bộ Excel", self.interpolation)
        form.addRow("Khoảng mất mẫu tối đa", self.max_gap)
        self.zero_check = QtWidgets.QCheckBox("Đưa đầu khoảng xuất về 0 s (MF4)")
        form.addRow("Mốc thời gian", self.zero_check)
        self.derived_check = QtWidgets.QCheckBox("Kèm tín hiệu công thức đã gán cho các giai đoạn chọn")
        self.derived_check.setToolTip("Chỉ công thức tạo chuỗi tín hiệu; kết quả vô hướng xuất trong Excel.")
        form.addRow("MF4 đã giải mã", self.derived_check)
        layout.addLayout(form)
        lists = QtWidgets.QHBoxLayout()
        left = QtWidgets.QVBoxLayout()
        left.addWidget(label("TÍN HIỆU XUẤT", "section"))
        self.signal_list = QtWidgets.QListWidget()
        for key, info in store.signals.items():
            item = QtWidgets.QListWidgetItem(f"{info.name} [{info.unit or '—'}]")
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if key in project.selected_signals else Qt.CheckState.Unchecked)
            self.signal_list.addItem(item)
        left.addWidget(self.signal_list)
        left.addWidget(button("Chọn tất cả tín hiệu", lambda: self.check_all(self.signal_list)))
        right = QtWidgets.QVBoxLayout()
        self.whole_check = QtWidgets.QCheckBox("Toàn bộ log")
        self.whole_check.setChecked(True)
        right.addWidget(self.whole_check)
        self.segment_list = QtWidgets.QListWidget()
        for segment in project.segments:
            item = QtWidgets.QListWidgetItem(f"{segment.name} · {segment.end-segment.start:g} s")
            item.setData(Qt.ItemDataRole.UserRole, segment.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.segment_list.addItem(item)
        self.segment_list.setEnabled(False)
        self.whole_check.toggled.connect(lambda checked: self.segment_list.setEnabled(not checked))
        right.addWidget(self.segment_list)
        right.addWidget(button("Chọn tất cả giai đoạn", self.select_segments))
        lists.addLayout(left, 1)
        lists.addLayout(right, 1)
        layout.addLayout(lists)
        self.estimate = label("", "muted")
        self.estimate.setWordWrap(True)
        layout.addWidget(self.estimate)
        self.signal_list.itemChanged.connect(self.update_estimate)
        self.segment_list.itemChanged.connect(self.update_estimate)
        self.whole_check.toggled.connect(self.update_estimate)
        self.raster_check.toggled.connect(self.update_estimate)
        self.raster_spin.valueChanged.connect(self.update_estimate)
        self.format_combo.currentIndexChanged.connect(self.update_format)
        notes = label("Excel tự chia sheet khi vượt giới hạn. MF4 giữ các khoảng thời gian đã chọn.\n"
                      "File đích phải là file mới. Chi tiết, DBC và công thức được ghi kèm khi định dạng hỗ trợ.", "muted")
        notes.setWordWrap(True)
        layout.addWidget(notes)
        boxes = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Save | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        boxes.button(QtWidgets.QDialogButtonBox.StandardButton.Save).setText("Chọn nơi lưu & Xuất")
        boxes.accepted.connect(self.accept)
        boxes.rejected.connect(self.reject)
        layout.addWidget(boxes)
        self.update_format()

    @staticmethod
    def checked(widget):
        return [widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(widget.count())
                if widget.item(i).checkState() == Qt.CheckState.Checked]

    @staticmethod
    def check_all(widget):
        for i in range(widget.count()):
            widget.item(i).setCheckState(Qt.CheckState.Checked)

    def select_segments(self):
        self.whole_check.setChecked(False)
        self.check_all(self.segment_list)

    def selected_segments(self):
        """None biểu thị toàn log; danh sách rỗng biểu thị chưa chọn giai đoạn nào."""
        ids = self.checked(self.segment_list)
        return None if self.whole_check.isChecked() else [s for s in self.project.segments if s.id in ids]

    def update_format(self, *_):
        """Bật đúng trường tùy chọn theo định dạng, không thay đổi logic ghi file."""
        kind = self.format_combo.currentData()
        excel = kind == "excel"
        self.signal_list.setEnabled(kind != "raw")
        self.raster_check.setEnabled(excel)
        self.raster_spin.setEnabled(excel and self.raster_check.isChecked())
        self.interpolation.setEnabled(excel and self.raster_check.isChecked())
        self.max_gap.setEnabled(excel and self.raster_check.isChecked())
        self.zero_check.setEnabled(not excel)
        self.derived_check.setEnabled(kind == "mf4")
        self.update_estimate()

    def update_estimate(self, *_):
        """Ước tính kích thước bảng đồng bộ hoặc số mẫu gốc để người dùng cân nhắc."""
        keys = self.checked(self.signal_list)
        segments = self.selected_segments()
        if self.raster_check.isChecked() and self.format_combo.currentData() == "excel":
            duration = sum(s.end - s.start for s in segments) if segments is not None else float(self.store.metadata.get("duration", 0))
            rows = int(duration / self.raster_spin.value()) + (len(segments) if segments else 1)
            cells = rows * (len(keys) + 1)
            text = f"Ước tính đồng bộ: {rows:,} hàng · {cells:,} ô."
        else:
            count = sum(self.store.signals[k].count for k in keys)
            text = f"Tín hiệu đã chọn: {len(keys)} · {count:,} mẫu trong toàn log (chưa lọc giai đoạn)."
        self.estimate.setText(text)

    def accept(self):
        """Chặn cấu hình xuất thiếu tín hiệu/giai đoạn hoặc không phù hợp nguồn."""
        kind = self.format_combo.currentData()
        if kind != "raw" and not self.checked(self.signal_list):
            QtWidgets.QMessageBox.warning(self, "Chưa chọn tín hiệu", "Chọn ít nhất một tín hiệu để xuất.")
            return
        if not self.whole_check.isChecked() and not self.checked(self.segment_list):
            QtWidgets.QMessageBox.warning(self, "Chưa chọn giai đoạn", "Chọn ít nhất một giai đoạn hoặc chọn toàn bộ log.")
            return
        if kind == "mf4" and self.derived_check.isChecked() and self.whole_check.isChecked():
            QtWidgets.QMessageBox.warning(self, "Chọn giai đoạn", "Để kèm tín hiệu công thức, bỏ chọn toàn log và tick các giai đoạn cần xuất.")
            return
        if kind == "raw" and Path(self.project.source).suffix.lower() != ".blf":
            QtWidgets.QMessageBox.warning(self, "Nguồn chưa phù hợp", "Xuất MF4 bản tin thô cần file BLF nguồn.")
            return
        super().accept()
