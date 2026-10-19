"""Chức năng: hằng số tài nguyên và kiểm tra hủy cho luồng tính toán.

Sửa tại đây khi: đổi kích thước chunk mặc định hoặc cơ chế kiểm tra hủy.
Liên kết: timeline.py, integration.py, engine.py, traces.py.
"""
from __future__ import annotations

# COMPONENT: calculations.common




CHUNK_SIZE = 4096


def check_cancelled(token):
    """Kiểm tra yêu cầu hủy; ngoại lệ hủy phải truyền về worker, không đổi thành kết quả lỗi."""
    if token is not None:
        token.check()
