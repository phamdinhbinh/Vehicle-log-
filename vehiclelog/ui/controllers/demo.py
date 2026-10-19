"""Chức năng: Tạo và mở dữ liệu mô phỏng minh họa.

Sửa tại đây khi: đổi giai đoạn hoặc công thức mẫu của nút Dữ liệu demo.
Liên kết: backend demo.py tạo log; session.py gắn store; không ảnh hưởng dữ liệu xe thật.
"""
# COMPONENT: ui.controllers.demo
from __future__ import annotations

import tempfile
from pathlib import Path
from ...models import Cursor, Formula, Project, Segment
from ..theme import COLORS


class DemoController:
    """Mixin chức năng của MainWindow, không khởi tạo độc lập.

    self.project / self.store và widget được main_window.py cùng panels/ cung cấp.
    Callback có thể gọi controller khác qua cùng self; backend giữ thuật toán dữ liệu.
    """

    def open_demo(self):
        """Tạo log mô phỏng rồi đọc bằng cùng luồng xử lý như dữ liệu thật."""
        if self._worker or not self._confirm_discard():
            return
        from ...demo import create_demo
        from ...importers import import_log
        self._demo_dir = Path(tempfile.mkdtemp(prefix="vehiclelog-demo-"))
        directory = self._demo_dir
        def work(progress, token):
            progress(0.0, "Đang tạo log mô phỏng…")
            files = create_demo(directory)
            token.check()
            store = import_log(files["blf"], {1: str(files["dbc"])}, progress=progress, token=token)
            return store, files
        def complete(result):
            store, files = result
            self.project = Project(source=str(files["blf"]), dbc_map={"1": str(files["dbc"])})
            self._project_path = None
            self.set_store(store, files["blf"])
            self._setup_demo_analysis()
            self.status_label.setText("Dữ liệu mô phỏng · không phải dữ liệu xe thực tế. Đã tạo 3 giai đoạn và công thức mẫu.")
        self._run_task("Đang chuẩn bị dữ liệu demo…", work, complete)


    def _setup_demo_analysis(self):
        """Thêm con trỏ, giai đoạn và công thức minh họa cho dữ liệu demo."""
        duration = self.duration
        if duration <= 0:
            return
        self.project.cursors = [Cursor(f"M{i+1}", duration*i/3, COLORS[i % len(COLORS)]) for i in range(4)]
        self.project.segments = []
        self._sync_stages()
        for stage, name in zip(self.project.segments, ["Tăng tốc / chạy", "Thu hồi năng lượng", "Chạy ổn định"]):
            stage.name = name
        voltage = next((k for k, v in self.store.signals.items() if "volt" in v.name.lower()), None)
        current = next((k for k, v in self.store.signals.items() if "current" in v.name.lower()), None)
        if voltage and current:
            self.project.formulas = [Formula("Năng lượng pin ròng", "integral(U * I) / 3600000",
                                            {"U": voltage, "I": current}, "kWh", [s.id for s in self.project.segments], max_gap=1.0),
                                     Formula("Công suất pin", "U * I / 1000", {"U": voltage, "I": current},
                                             "kW", [s.id for s in self.project.segments], max_gap=1.0)]
        self._dirty = True
        self._refresh_tables()
        self._rebuild_plots()

