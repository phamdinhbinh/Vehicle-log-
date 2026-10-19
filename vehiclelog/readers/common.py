"""Chức năng: kiểm tra hủy và cảnh báo độ chính xác dùng chung khi nhập log.

Sửa tại đây khi: đổi quy tắc hủy hoặc cách báo mất chính xác số nguyên.
Liên kết: blf.py và mf4.py gọi các hàm này; service.py quản lý cache.
"""
# COMPONENT: readers.common

def check_cancelled(token):
    """Dừng ngay nếu tác vụ đã được yêu cầu hủy."""
    if token is not None:
        token.check()


def warn_integer_precision(writer, key, name, warned):
    """Ghi một cảnh báo mỗi tín hiệu nếu float64 không giữ nguyên số nguyên lớn."""
    if key in warned:
        return
    warned.add(key)
    writer.metadata.setdefault("precision_loss_signals", []).append(key)
    writer.metadata["warnings"].append(
        f"Tín hiệu {name} ({key}) có số nguyên với |giá trị| > 2**53. "
        "Cache dùng float64 nên có thể mất độ chính xác số nguyên; "
        "không dùng kết quả này để đối chiếu chính xác bộ đếm hoặc bitfield 64-bit."
    )
