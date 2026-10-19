"""Tạo BLF/DBC/MF4 mẫu và tùy chọn mở GUI.

Chức năng: Tạo BLF/DBC/MF4 mẫu và tùy chọn mở GUI.
Sửa tại đây khi: đổi đầu ra của lệnh demo; dữ liệu mẫu nằm ở vehiclelog/demo.py.
Liên kết: demo.create_demo và gui.run_app.
"""
# COMPONENT: cli.demo
import json
from pathlib import Path


def generate_demo(args):
    """Tạo BLF/DBC/MF4 mẫu và tùy chọn mở GUI."""
    from ..demo import create_demo
    files = create_demo(args.directory)
    print(json.dumps({k: str(v) for k, v in files.items()}, ensure_ascii=False, indent=2))
    if args.gui:
        from ..gui import run_app
        return run_app()
    return 0
