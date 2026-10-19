"""Chức năng: Cửa sổ chính: khởi tạo trạng thái và ghép các component giao diện.

Sửa tại đây khi: thêm component hoặc trạng thái dùng chung; sửa bố cục trong panels/, hành vi trong controllers/.
Liên kết: gui.py giữ API cũ; app.py khởi động; theme.py quản lý giao diện chung.
"""
# COMPONENT: ui.main_window
from __future__ import annotations

from collections import OrderedDict
from PySide6 import QtCore, QtWidgets
import pyqtgraph as pg
from ..models import Project
from .theme import STYLE
from .panels.shell import ShellLayout
from .panels.signals import SignalsPanel
from .panels.workspace import WorkspacePanel
from .panels.analysis import AnalysisPanels
from .panels.inspector import InspectorPanel
from .controllers.background import BackgroundController
from .controllers.session import SessionController
from .controllers.demo import DemoController
from .controllers.project import ProjectController
from .controllers.window import WindowController
from .controllers.signals import SignalsController
from .controllers.hover import HoverController
from .controllers.plots import PlotsController
from .controllers.previews import PreviewsController
from .controllers.cursors import CursorsController
from .controllers.segments import SegmentsController
from .controllers.formulas import FormulasController
from .controllers.exports import ExportsController
from .controllers.measurements import MeasurementsController


class MainWindow(
    ShellLayout,
    SignalsPanel,
    WorkspacePanel,
    AnalysisPanels,
    InspectorPanel,
    BackgroundController,
    SessionController,
    DemoController,
    ProjectController,
    WindowController,
    SignalsController,
    PlotsController,
    HoverController,
    PreviewsController,
    CursorsController,
    MeasurementsController,
    SegmentsController,
    FormulasController,
    ExportsController,
    QtWidgets.QMainWindow,
):
    """Ghép panel (bố cục) và controller (thao tác) trên cùng một cửa sổ.

    Trạng thái chia sẻ:
    - project: cấu hình, tín hiệu chọn, con trỏ, giai đoạn, công thức, kết quả.
    - store: dữ liệu đầy đủ trên ổ đĩa; plots / curves chỉ là phần hiển thị.
    - _worker / _thread / _token: tác vụ đọc, tính hoặc xuất đang chạy.
    - _preview_*: worker riêng và cache giới hạn cho đồ thị.
    - _dirty / _project_path: trạng thái lưu cấu hình dự án.

    Các mixin không giữ bản sao trạng thái: self luôn là MainWindow này.
    Giữ tên phương thức cũ để menu, script và kiểm thử tiếp tục sử dụng.
    """

    def __init__(self):
        """Khởi tạo trạng thái dùng chung trước khi panel nối các signal."""
        super().__init__()
        self.setWindowTitle("Vehicle Log Studio · Phân tích tín hiệu ô tô")
        self.resize(1500, 980)
        self.setMinimumSize(1100, 750)
        self.setStyleSheet(STYLE)
        # Dữ liệu dự án và đối tượng hiển thị; logic ở controllers/.
        self.project = Project()
        self.store = None
        self.plots = {}
        self.curves = {}
        self.cursor_lines = {}
        self.segment_regions = []
        self._syncing = False
        # Worker tác vụ chính: đọc log, tính công thức hoặc xuất file.
        self._worker = None
        self._thread = None
        self._token = None
        self._job_callback = None
        self._pending_result = None
        self._job_failed = False
        self._task_relay = None
        self._dirty = False
        self._project_path = None
        self._demo_dir = None
        # Preview có worker và cache riêng; không cung cấp dữ liệu tính toán.
        self._preview_cache = OrderedDict()
        self._preview_thread = None
        self._preview_worker = None
        self._preview_relay = None
        self._preview_token = None
        self._preview_result = None
        self._preview_pending = None
        self._preview_errors = set()
        self._preview_failed_requests = []
        self._closing_after_preview = False
        self._overview_key = None
        self._loading_project = None
        # Gộp thao tác zoom liên tiếp trước khi đọc thêm dữ liệu đồ thị.
        self._plot_timer = QtCore.QTimer(self)
        self._plot_timer.setSingleShot(True)
        self._plot_timer.setInterval(100)
        self._plot_timer.timeout.connect(self._update_curves)
        pg.setConfigOptions(antialias=False, background="#0e192b", foreground="#829bb7")
        self._build_ui()
        self._build_menus()
        self._set_available()
        self._refresh_tables()

