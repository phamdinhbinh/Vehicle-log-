"""Điểm khởi động ngắn cho python -m vehiclelog và gói Windows.

Chức năng: chuyển điều khiển đến CLI; mặc định CLI mở GUI.
Sửa tại đây khi: đổi entry point; giao diện ở ui/, lệnh ở cli/.
Liên kết: launch.py và pyproject.toml sử dụng main.
"""
# COMPONENT: app.entrypoint
from .cli.app import main

if __name__ == "__main__":
    raise SystemExit(main())
