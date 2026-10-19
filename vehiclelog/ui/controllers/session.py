"""Chức năng: Mở BLF/MF4, gán DBC và nối store với các panel.

Sửa tại đây khi: đổi cách chọn nguồn, giải mã lại DBC hoặc nạp tín hiệu sau khi đọc.
Liên kết: backend importers.py đọc file; dialogs/dbc.py nhận ánh xạ DBC; project.py mở cấu hình.
"""
# COMPONENT: ui.controllers.session
from __future__ import annotations

from pathlib import Path
from PySide6 import QtCore, QtWidgets
from ...models import Cursor, Project
from ..dialogs.dbc import DbcDialog
from ..theme import COLORS
from ..widgets import fill_table

Qt = QtCore.Qt


class SessionController:
    """Mixin chức năng của MainWindow, không khởi tạo độc lập.

    self.project / self.store và widget được main_window.py cùng panels/ cung cấp.
    Callback có thể gọi controller khác qua cùng self; backend giữ thuật toán dữ liệu.
    """

    def open_log(self):
        """Chọn log, gán DBC nếu cần và giao việc đọc cho worker nền."""
        if self._worker or not self._confirm_discard():
            return
        source, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Mở log ô tô", "", "Vehicle logs (*.blf *.mf4 *.mdf);;Tất cả (*)")
        if not source:
            return
        mapping = {int(k): v for k, v in self.project.dbc_map.items()}
        if Path(source).suffix.lower() == ".blf":
            dialog = DbcDialog(mapping, self)
            if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                return
            mapping = dialog.mapping()
            if not mapping:
                self._notify("Cần DBC để xem tín hiệu", "BLF cần DBC để hiển thị tín hiệu đã giải mã.\n"
                             "Bạn có thể mở log không có DBC để xem cảnh báo và xuất MF4 bản tin thô.")
        self._import_source(source, mapping)


    def _import_source(self, source, mapping, project=None):
        """Gọi API import_log ở nền; giữ dự án đang mở để khôi phục cấu hình."""
        from ...importers import import_log
        self._loading_project = project
        self._run_task("Đang đọc và giải mã log…",
                       lambda progress, token: import_log(source, dbc_map=mapping, progress=progress, token=token),
                       lambda store: self._import_complete(store, source, mapping, project))


    def _import_complete(self, store, source, mapping, project=None):
        """Nhận store đã đọc xong và gắn lại cấu hình dự án trên GUI thread."""
        self.project = project or Project(source=str(source), dbc_map={str(k): str(v) for k, v in mapping.items()})
        self._loading_project = None
        self._project_path = None if project is None else self._project_path
        if project is not None:
            self.project.results.clear()
        self.set_store(store, source)
        self._dirty = project is None
        if project is not None:
            self.status_label.setText("Đã mở dự án và kiểm tra lại nguồn / DBC. Hãy tính lại kết quả.")


    @property
    def duration(self):
        """Lấy thời lượng từ metadata hoặc timestamp cuối các tín hiệu."""
        if not self.store:
            return 0.0
        value = self.store.metadata.get("duration")
        if value is None:
            value = max((s.end for s in self.store.signals.values()), default=0)
        return max(0.0, float(value))


    def set_store(self, store, source=None):
        """Gắn nguồn dữ liệu, nạp danh sách tín hiệu và làm mới các panel liên quan."""
        self.store = store
        self._preview_pending = None
        self._preview_cache.clear()
        self._preview_errors.clear()
        if source is not None:
            self.project.source = str(source)
        self.project.cache_path = str(store.path)
        self.project.selected_signals = [key for key in self.project.selected_signals if key in store.signals]
        if not self.project.selected_signals:
            self.project.selected_signals = list(store.signals)[:3]
        if not self.project.cursors:
            self.project.cursors = [Cursor("M1", 0, COLORS[2]), Cursor("M2", self.duration, COLORS[1])]
        self._sync_stages()
        source_name = Path(self.project.source).name if self.project.source else "Bộ dữ liệu"
        self.source_label.setText(f"{source_name}  ·  {self.duration:,.1f} s")
        self.source_label.setToolTip(self.project.source)
        self.signal_list.blockSignals(True)
        self.signal_list.clear()
        for index, (key, info) in enumerate(store.signals.items()):
            item = QtWidgets.QListWidgetItem(f"{info.name}\n{info.unit or '—'}  ·  CAN {info.channel or '—'}  ·  {info.count:,} mẫu")
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setData(Qt.ItemDataRole.UserRole + 1, f"{info.name} {key} {info.message} {info.channel} {info.can_id} "
                         + (f"{info.can_id:x}" if info.can_id is not None else ""))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if key in self.project.selected_signals else Qt.CheckState.Unchecked)
            item.setToolTip(f"{key}\nMessage: {info.message}\nNguồn: {info.source}\nĐơn vị: {info.unit or 'không có'}")
            self.signal_list.addItem(item)
        self.signal_list.blockSignals(False)
        self.signal_count.setText(f"{len(store.signals):,}")
        self._filter_signals()
        warnings = store.metadata.get("warnings", [])
        if isinstance(warnings, str):
            warnings = [warnings]
        self.warning_text.setPlainText("\n".join(str(w) for w in warnings) or "Không có cảnh báo từ quá trình đọc log.\n"
                                       "Vẫn cần kiểm tra DBC, quy ước dấu và chất lượng tín hiệu trước khi tính.")
        self.tabs.setTabText(3, f"Chất lượng dữ liệu ({len(warnings)})")
        frames = store.metadata.get("frame_preview", [])
        fill_table(self.frame_table, [(f"{frame.get('time', 0):.6f}", frame.get("channel", ""),
                                       f"0x{frame.get('can_id', 0):X}", "Có" if frame.get("is_fd") else "—",
                                       frame.get("dlc", ""), frame.get("data", "")) for frame in frames])
        stats = store.metadata.get("frame_stats", {})
        self.raw_label.setText(f"Xem trước {len(frames):,} bản tin đầu · Tổng số bản tin: {stats.get('frames', '—'):,}"
                               if isinstance(stats.get("frames"), int) else f"Xem trước {len(frames):,} bản tin đầu; không phải toàn bộ log")
        self._refresh_tables()
        self._rebuild_plots()
        self.reset_view()
        self._set_available()
        self.status_label.setText(f"Đã mở {source_name} · {len(store.signals):,} tín hiệu · {self.duration:,.1f} s")


    def manage_dbc(self):
        """Đổi DBC theo kênh; giải mã lại BLF và vô hiệu kết quả đã tính."""
        if self._worker:
            return
        dialog = DbcDialog(self.project.dbc_map, self)
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        mapping = dialog.mapping()
        if self.project.source and Path(self.project.source).suffix.lower() == ".blf":
            # Giữ mốc và ánh xạ; kết quả phải tính lại khi đổi DBC.
            self.project.dbc_map = {str(k): str(v) for k, v in mapping.items()}
            self._mark_changed()
            self._import_source(self.project.source, mapping, self.project)
        else:
            self.project.dbc_map = {str(k): str(v) for k, v in mapping.items()}
            self._dirty = True
            self.status_label.setText("Đã lưu cấu hình DBC. MF4 đang mở sử dụng các kênh số có sẵn.")

