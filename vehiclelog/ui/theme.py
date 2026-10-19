"""Chức năng: Bảng màu và stylesheet dùng chung cho toàn ứng dụng.

Sửa tại đây khi: đổi màu nền, font, viền, tab hoặc màu đồ thị mặc định.
Liên kết: main_window.py áp dụng STYLE; panel và controller dùng COLORS.
"""
# COMPONENT: ui.theme
from __future__ import annotations

COLORS = ["#45d5b0", "#69a9ff", "#ffbd66", "#c394ff", "#fa849c", "#67d1ec"]


STYLE = """
QMainWindow, QDialog { background: #0c1424; color: #e1e9f7; }
QWidget { font-family: 'Segoe UI', 'DejaVu Sans'; font-size: 12px; color: #dce6f4; }
QFrame#panel, QGroupBox { background: #111e32; border: 1px solid #26364d; border-radius: 8px; }
QGroupBox { margin-top: 14px; padding-top: 14px; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; color: #95acc6; }
QLabel#eyebrow { color: #42d4b0; font-size: 10px; font-weight: 700; letter-spacing: 2px; }
QLabel#title { font-size: 22px; font-weight: 700; color: #f2f6ff; }
QLabel#muted { color: #849bb7; }
QLabel#section { font-size: 11px; font-weight: 700; color: #a4b8d1; }
QPushButton, QToolButton { background: #1a2c44; border: 1px solid #304660; padding: 7px 12px; border-radius: 5px; }
QPushButton:hover, QToolButton:hover { background: #26405e; border-color: #5b82ad; }
QPushButton:disabled { color: #52657d; border-color: #243348; background: #152136; }
QPushButton#primary { background: #21b995; color: #041e1a; font-weight: 700; border-color: #21b995; }
QPushButton#primary:hover { background: #57dbbb; }
QPushButton#danger { color: #ff9ba9; }
QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox, QTextEdit { background: #0e1a2c; border: 1px solid #30435e; padding: 6px; border-radius: 4px; selection-background-color: #245b70; }
QComboBox::drop-down { border: 0; width: 22px; }
QComboBox QAbstractItemView { background: #14243a; selection-background-color: #254767; }
QListWidget, QTableWidget, QPlainTextEdit { background: #0e192b; alternate-background-color: #122037; border: 1px solid #26364d; border-radius: 4px; gridline-color: #24364c; }
QListWidget::item { padding: 5px; border-bottom: 1px solid #17273c; }
QListWidget::item:selected, QTableWidget::item:selected { background: #204866; }
QTableCornerButton::section { background: #17273d; border: 0; }
QHeaderView::section { background: #17273d; color: #91abc7; border: 0; border-bottom: 1px solid #30415a; padding: 7px; font-weight: 600; }
QTabWidget::pane { border: 1px solid #26364d; border-radius: 5px; }
QTabBar::tab { background: #111d30; padding: 9px 15px; color: #829ab6; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #4bdfbc; background: #17283e; border-bottom: 2px solid #42d4b0; }
QSplitter::handle { background: #0c1424; width: 5px; height: 5px; }
QScrollArea { border: 0; background: #0d1729; }
QScrollBar:vertical { background: #0f1b2d; width: 9px; }
QScrollBar::handle:vertical { background: #344b68; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QProgressBar { background: #142339; border: 0; border-radius: 3px; min-height: 6px; text-align: center; }
QProgressBar::chunk { background: #36c8a4; border-radius: 3px; }
QMenuBar, QMenu, QStatusBar { background: #0e192b; }
QMenu::item:selected { background: #26435f; }
QToolTip { color: #e7f1ff; background: #243b56; border: 1px solid #50718d; }
"""

