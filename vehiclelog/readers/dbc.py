"""Chức năng: kiểm tra ánh xạ kênh CAN và nạp cơ sở dữ liệu DBC.

Sửa tại đây khi: đổi kiểm tra kênh, đường dẫn DBC hoặc thư viện giải mã.
Liên kết: service.py chuẩn hóa đầu vào; blf.py dùng DBC để giải mã.
"""
# COMPONENT: readers.dbc

from pathlib import Path
from typing import Mapping

from .common import check_cancelled


def normalize_dbc_mapping(dbc_map: Mapping | None) -> dict[int, str]:
    """Chuẩn hóa kênh CAN hiển thị (từ 1) và kiểm tra đường dẫn DBC."""
    result = {}
    for channel, filename in (dbc_map or {}).items():
        try:
            number = int(channel)
        except (TypeError, ValueError) as error:
            raise ValueError(f"Kênh CAN không hợp lệ: {channel!r}") from error
        if number < 1 or str(channel).strip() not in (str(number),):
            raise ValueError("Kênh CAN hiển thị phải là số nguyên bắt đầu từ 1.")
        path = Path(filename).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Không tìm thấy DBC: {path}")
        result[number] = str(path)
    return result


def load_databases(mapping, token=None):
    """Nạp DBC từng kênh; lỗi luôn ghi rõ kênh gây ra sự cố."""
    import cantools

    databases = {}
    for channel, filename in mapping.items():
        check_cancelled(token)
        try:
            databases[channel] = cantools.database.load_file(filename)
        except Exception as error:
            raise ValueError(f"Không đọc được DBC kênh {channel}: {error}") from error
    return databases
