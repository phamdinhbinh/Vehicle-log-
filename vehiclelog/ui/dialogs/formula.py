"""Hộp thoại tạo/sửa công thức và chọn các giai đoạn áp dụng.

Chức năng: đặt tên, gán tín hiệu cho bí danh, chọn cách tính và giai đoạn.
Sửa tại đây khi: đổi bố cục trình soạn công thức, phép tính mẫu hoặc bộ chọn tín hiệu.
Liên kết: models.Formula lưu cấu hình; formulas.py kiểm tra và tính biểu thức.
"""
# COMPONENT: ui.dialogs.formula
from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from ...models import Formula
from ..widgets import button, label, table

Qt = QtCore.Qt


class FormulaDialog(QtWidgets.QDialog):
    """Biên tập công thức độc lập với phép tính; chỉ trả cấu hình Formula hợp lệ."""

    def __init__(self, store, segments, formula=None, parent=None):
        super().__init__(parent)
        self.store = store
        self.original = formula
        self.setWindowTitle("Sửa công thức" if formula else "Tạo công thức")
        self.resize(780, 720)
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.name_edit = QtWidgets.QLineEdit(formula.name if formula else "")
        self.name_edit.setPlaceholderText("Ví dụ: Năng lượng pin")
        self.unit_edit = QtWidgets.QLineEdit(formula.unit if formula else "")
        form.addRow("Tên công thức", self.name_edit)
        form.addRow("Đơn vị kết quả", self.unit_edit)
        layout.addLayout(form)
        layout.addWidget(label("TÍN HIỆU ĐẦU VÀO · đặt bí danh dùng trong biểu thức", "section"))
        self.binding_table = table(["Bí danh", "Tín hiệu"])
        self.binding_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.binding_table.setMaximumHeight(170)
        layout.addWidget(self.binding_table)
        if formula:
            for alias, key in formula.bindings.items():
                self.add_binding(alias, key)
        else:
            self.add_binding("x")
        bar = QtWidgets.QHBoxLayout()
        bar.addWidget(button("+ Tín hiệu", lambda: self.add_binding()))
        bar.addWidget(button("Xóa dòng", self.remove_binding))
        bar.addStretch()
        layout.addLayout(bar)
        expression_form = QtWidgets.QFormLayout()
        # Sửa danh sách bên dưới để bổ sung công thức mẫu cho người dùng.
        self.template_combo = QtWidgets.QComboBox()
        for name, expression in [
            ("Chọn phép tính mẫu…", ""), ("Tín hiệu tính toán", "x * 2"),
            ("Năng lượng (P bằng kW)", "integral(P) / 3600"),
            ("Năng lượng (U bằng V, I bằng A)", "integral(U * I) / 3600000"),
            ("Giá trị lớn nhất", "max(x)"), ("Trung bình theo thời gian", "mean(x)"),
            ("Chênh lệch đầu–cuối", "delta(x)"),
            ("Tiêu thụ (V/A/km/h; ngưỡng 1 m)", "100 * safe_div(integral(U * I) / 3600000, integral(v) / 3600, 0.001)"),
        ]:
            self.template_combo.addItem(name, expression)
        self.template_combo.currentIndexChanged.connect(self._template)
        self.expression_edit = QtWidgets.QLineEdit(formula.expression if formula else "")
        self.expression_edit.setPlaceholderText("integral(U * I) / 3600000")
        expression_form.addRow("Cách tính mẫu", self.template_combo)
        expression_form.addRow("Biểu thức", self.expression_edit)
        self.interpolation_combo = QtWidgets.QComboBox()
        self.interpolation_combo.addItem("Giữ giá trị trước (hold)", "hold")
        self.interpolation_combo.addItem("Nội suy tuyến tính (linear)", "linear")
        if formula:
            self.interpolation_combo.setCurrentIndex(max(0, self.interpolation_combo.findData(formula.interpolation)))
        self.max_gap_edit = QtWidgets.QDoubleSpinBox()
        self.max_gap_edit.setRange(0.000001, 1e9)
        self.max_gap_edit.setDecimals(6)
        self.max_gap_edit.setSuffix(" s")
        self.max_gap_edit.setValue(formula.max_gap if formula else 1.0)
        expression_form.addRow("Đồng bộ tín hiệu", self.interpolation_combo)
        expression_form.addRow("Khoảng mất mẫu tối đa", self.max_gap_edit)
        layout.addLayout(expression_form)
        hints = label("Hàm: integral, mean, sample_mean, min, max, first, last, delta, abs, clip, positive, negative, sqrt, safe_div.\n"
                      "integral tính theo giây. safe_div(a, b, ngưỡng) chặn mẫu số gần 0; ngưỡng do bạn chọn, cùng đơn vị với b.\n"
                      "Kiểm tra đơn vị đầu vào và quy ước dấu trước khi tính.", "muted")
        hints.setWordWrap(True)
        layout.addWidget(hints)
        layout.addWidget(label("GIAI ĐOẠN ÁP DỤNG · tick chọn cụ thể", "section"))
        # Mỗi công thức lưu danh sách id giai đoạn; không tự áp dụng cho giai đoạn khác.
        self.segment_list = QtWidgets.QListWidget()
        self.segment_list.setMinimumHeight(95)
        for segment in segments:
            item = QtWidgets.QListWidgetItem(f"{segment.name}    {segment.start:g} → {segment.end:g} s")
            item.setData(Qt.ItemDataRole.UserRole, segment.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if formula and segment.id in formula.segment_ids else Qt.CheckState.Unchecked)
            self.segment_list.addItem(item)
        layout.addWidget(self.segment_list)
        choices = QtWidgets.QHBoxLayout()
        choices.addWidget(button("Chọn tất cả", lambda: self._check_segments(True)))
        choices.addWidget(button("Bỏ chọn", lambda: self._check_segments(False)))
        choices.addStretch()
        layout.addLayout(choices)
        boxes = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Save | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        boxes.accepted.connect(self.accept)
        boxes.rejected.connect(self.reject)
        layout.addWidget(boxes)

    def add_binding(self, alias="", key=None):
        """Thêm bí danh và bộ chọn tín hiệu có tìm kiếm, giữ thông tin tín hiệu bị thiếu."""
        row = self.binding_table.rowCount()
        self.binding_table.insertRow(row)
        self.binding_table.setItem(row, 0, QtWidgets.QTableWidgetItem(alias or f"x{row + 1}"))
        combo = QtWidgets.QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
        combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        for signal_key, info in self.store.signals.items():
            combo.addItem(f"{info.name} [{info.unit or '—'}] · {signal_key}", signal_key)
        if key is not None:
            index = combo.findData(key)
            if index >= 0:
                combo.setCurrentIndex(index)
            else:
                combo.addItem(f"Thiếu tín hiệu: {key}", key)
                combo.setCurrentIndex(combo.count() - 1)
        self.binding_table.setCellWidget(row, 1, combo)

    def remove_binding(self):
        row = self.binding_table.currentRow()
        if row >= 0:
            self.binding_table.removeRow(row)

    def _template(self, index):
        expression = self.template_combo.itemData(index)
        if expression:
            self.expression_edit.setText(expression)

    def _check_segments(self, checked):
        for index in range(self.segment_list.count()):
            self.segment_list.item(index).setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)

    def formula_value(self):
        """Kiểm tra bí danh, tín hiệu, cú pháp và thu thập đúng các giai đoạn đã tick."""
        from ...formulas import validate_expression
        name = self.name_edit.text().strip()
        if not name:
            raise ValueError("Vui lòng đặt tên công thức.")
        bindings = {}
        for row in range(self.binding_table.rowCount()):
            item = self.binding_table.item(row, 0)
            alias = item.text().strip() if item else ""
            combo = self.binding_table.cellWidget(row, 1)
            key = combo.currentData()
            if not alias or not alias.isidentifier() or alias.startswith("_"):
                raise ValueError("Bí danh phải là tên hợp lệ, ví dụ U, I hoặc speed.")
            if alias in bindings:
                raise ValueError(f"Bí danh bị trùng: {alias}")
            if key not in self.store.signals or combo.currentText() != combo.itemText(combo.currentIndex()):
                raise ValueError(f"Chọn một tín hiệu hợp lệ cho {alias}.")
            bindings[alias] = key
        expression = self.expression_edit.text().strip()
        validate_expression(expression, bindings)
        segment_ids = [self.segment_list.item(i).data(Qt.ItemDataRole.UserRole)
                       for i in range(self.segment_list.count())
                       if self.segment_list.item(i).checkState() == Qt.CheckState.Checked]
        kwargs = {"id": self.original.id} if self.original else {}
        return Formula(name, expression, bindings, self.unit_edit.text().strip(), segment_ids,
                       self.interpolation_combo.currentData(), self.max_gap_edit.value(), **kwargs)

    def accept(self):
        try:
            self.formula_value()
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(self, "Công thức chưa hợp lệ", str(exc))
            return
        super().accept()
