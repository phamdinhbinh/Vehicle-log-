"""Chuẩn hóa tham số DBC và giai đoạn.

Chức năng: Chuẩn hóa tham số DBC và giai đoạn.
Sửa tại đây khi: đổi cú pháp CHANNEL=PATH, NAME:START:END hoặc quy tắc kiểm tra.
Liên kết: inspect.py và convert.py.
"""
# COMPONENT: cli.options
from pathlib import Path


def parse_dbc_map(items):
    """Chuyển CHANNEL=PATH thành ánh xạ DBC; kênh bắt đầu từ 1."""
    mapping = {}
    for item in items or []:
        channel, sep, path = item.partition("=")
        if not sep or not channel.isdigit() or int(channel) < 1:
            raise ValueError("DBC dùng dạng CHANNEL=PATH, ví dụ --dbc 1=vehicle.dbc")
        mapping[int(channel)] = str(Path(path).resolve())
    return mapping


def parse_segments(items):
    """Chuyển NAME:START:END thành các giai đoạn theo giây."""
    from ..models import Segment
    result = []
    for item in items or []:
        try:
            name, start, end = item.rsplit(":", 2)
            segment = Segment(name, float(start), float(end))
            segment.validate()
            result.append(segment)
        except (ValueError, TypeError) as exc:
            raise ValueError("Giai đoạn dùng dạng NAME:START:END, đơn vị giây.") from exc
    return result or None


