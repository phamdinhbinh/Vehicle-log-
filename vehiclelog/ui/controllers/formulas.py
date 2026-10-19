"""Chức năng: Quản lý công thức, giai đoạn áp dụng, tính kết quả và xem chuỗi.

Sửa tại đây khi: đổi thao tác tạo / sửa công thức, chọn giai đoạn hoặc cách hiển thị kết quả.
Liên kết: dialogs/formula.py nhận biểu thức; backend formulas.py tính; dialogs/trace.py dựng đồ thị chuỗi.
"""
# COMPONENT: ui.controllers.formulas
from __future__ import annotations

from PySide6 import QtGui, QtWidgets
from ..dialogs.formula import FormulaDialog
from ..dialogs.trace import TraceDialog
from ..widgets import fill_table
from ..trace_preview import trace_preview


class FormulasController:
    """Mixin chức năng của MainWindow, không khởi tạo độc lập.

    self.project / self.store và widget được main_window.py cùng panels/ cung cấp.
    Callback có thể gọi controller khác qua cùng self; backend giữ thuật toán dữ liệu.
    """

    def new_formula(self):
        """Tạo công thức có tên, ánh xạ tín hiệu và giai đoạn áp dụng."""
        if not self.store or self._worker:
            return
        dialog = FormulaDialog(self.store, self.project.segments, parent=self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.project.formulas.append(dialog.formula_value())
            self._mark_changed()
            self._refresh_formulas()


    def edit_formula(self):
        """Sửa công thức đang chọn; kết quả cũ được đánh dấu cần tính lại."""
        row = self.formula_table.currentRow()
        if row < 0 or self._worker:
            return
        dialog = FormulaDialog(self.store, self.project.segments, self.project.formulas[row], self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.project.formulas[row] = dialog.formula_value()
            self._mark_changed()
            self._refresh_formulas()


    def duplicate_formula(self):
        """Sao chép độc lập công thức và cấp ID mới, giữ gán giai đoạn."""
        row = self.formula_table.currentRow()
        if row < 0 or self._worker:
            return
        from dataclasses import replace
        from ...models import new_id
        formula = self.project.formulas[row]
        self.project.formulas.append(replace(formula, id=new_id(), name=formula.name + " (bản sao)",
                                             bindings=dict(formula.bindings), segment_ids=list(formula.segment_ids)))
        self._mark_changed()
        self._refresh_formulas()


    def delete_formula(self):
        """Xóa công thức hiện chọn và vô hiệu kết quả cũ."""
        row = self.formula_table.currentRow()
        if row < 0 or self._worker:
            return
        self.project.formulas.pop(row)
        self._mark_changed()
        self._refresh_formulas()


    def _refresh_formulas(self):
        """Hiện biểu thức, đơn vị và đúng danh sách giai đoạn đã được gán."""
        names = {s.id: s.name for s in self.project.segments}
        fill_table(self.formula_table, [(f.name, f.expression, f.unit,
                                        ", ".join(names.get(sid, "giai đoạn thiếu") for sid in f.segment_ids) or "Chưa gán")
                                       for f in self.project.formulas])


    def calculate(self):
        """Kiểm tra giai đoạn rồi tính các cặp công thức / giai đoạn trên worker."""
        if not self.store or self._worker:
            return
        if not self.project.formulas:
            self._notify("Chưa có công thức", "Tạo công thức và chọn giai đoạn áp dụng trước khi tính.")
            return
        try:
            for segment in self.project.segments:
                segment.validate()
        except ValueError as exc:
            self._notify("Giai đoạn chưa hợp lệ", str(exc))
            return
        from ...formulas import evaluate_all
        def complete(results):
            self.project.results = results
            self._dirty = True
            self._refresh_results()
            self.tabs.setCurrentIndex(2)
            self.status_label.setText(f"Đã tính {len(results)} kết quả. Kiểm tra trạng thái và độ phủ dữ liệu.")
        self._run_task("Đang tính công thức theo giai đoạn…",
                       lambda progress, token: evaluate_all(self.store, self.project.formulas, self.project.segments,
                                                            progress=progress, token=token), complete)


    def _refresh_results(self):
        """Hiện kết quả, trạng thái và cảnh báo thiếu dữ liệu theo từng giai đoạn."""
        results = self.project.results
        self.result_label.setText(f"{len(results)} kết quả" if results else "Chưa có kết quả hoặc cần tính lại sau thay đổi")
        statuses = {"ok": "Hợp lệ", "incomplete": "Thiếu dữ liệu", "invalid": "Không hợp lệ", "trace": "Chuỗi tín hiệu", "error": "Lỗi"}
        fill_table(self.result_table, [(r.segment_name, r.formula_name, f"{r.value:.8g}" if r.value is not None else "—",
                                       r.unit, statuses.get(r.status, r.status), r.message) for r in results])
        for row, result in enumerate(results):
            if result.status not in ("ok", "trace"):
                for col in range(self.result_table.columnCount()):
                    self.result_table.item(row, col).setForeground(QtGui.QColor("#ffbd66"))


    def plot_formula(self):
        """Chọn một giai đoạn đã gán để xem công thức dạng chuỗi."""
        row = self.formula_table.currentRow()
        if row < 0 or self._worker:
            return
        formula = self.project.formulas[row]
        segments = [segment for segment in self.project.segments if segment.id in formula.segment_ids]
        if not segments:
            self._notify("Chưa gán giai đoạn", "Sửa công thức và tick giai đoạn áp dụng trước khi vẽ.")
            return
        if len(segments) == 1:
            segment = segments[0]
        else:
            names = [f"{segment.name} ({segment.start:g} → {segment.end:g} s)" for segment in segments]
            chosen, ok = QtWidgets.QInputDialog.getItem(self, "Chọn giai đoạn", "Giai đoạn áp dụng", names, 0, False)
            if not ok:
                return
            segment = segments[names.index(chosen)]
        self._plot_formula_trace(formula, segment)


    def show_result_trace(self):
        """Tìm công thức và giai đoạn tương ứng với hàng kết quả đang chọn."""
        row = self.result_table.currentRow()
        if row < 0 or self._worker:
            return
        result = self.project.results[row]
        formula = next((f for f in self.project.formulas if f.id == result.formula_id), None)
        segment = next((s for s in self.project.segments if s.id == result.segment_id), None)
        if not formula or not segment:
            return
        self._plot_formula_trace(formula, segment)


    def _plot_formula_trace(self, formula, segment):
        """Tính preview chuỗi ở nền rồi mở TraceDialog; không dùng preview cho tổng năng lượng."""
        from ...formulas import formula_kind
        if formula_kind(formula) != "trace":
            self._notify("Công thức tổng hợp", "Công thức này tạo một kết quả cho mỗi giai đoạn. Dùng Tính kết quả để xem giá trị.")
            return
        def complete(data):
            times, values = data
            dialog = TraceDialog(formula, segment, times, values, self)
            dialog.show()
            self._trace_dialog = dialog
        store = self.store
        self._run_task("Đang tính chuỗi tín hiệu…", lambda progress, token: trace_preview(store, formula, segment, progress=progress, token=token), complete)

