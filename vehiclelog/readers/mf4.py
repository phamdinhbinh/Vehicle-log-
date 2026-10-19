"""Chức năng: nhập các kênh số MF4 theo lô và giữ thông tin mẫu không hợp lệ.

Sửa tại đây khi: đổi loại kênh được hỗ trợ, kích thước đọc hoặc chuyển đổi giá trị vật lý.
Liên kết: service.py điều phối; common.py cảnh báo/hủy; store.py lưu timestamp và giá trị.
"""
# COMPONENT: readers.mf4

from datetime import timezone

import numpy as np

from ..models import SignalInfo, report
from .common import check_cancelled, warn_integer_precision

MF4_READ_FRAGMENT_SIZE = 8 * 1024 * 1024
MF4_BATCH_SAMPLES = 100_000


def import_mf4(source, mapping, writer, progress, token):
    """Đọc kênh số vô hướng, bảo toàn timestamp và đánh dấu mẫu lỗi bằng NaN."""
    from asammdf import MDF

    warnings = writer.metadata["warnings"]
    skipped = []
    imported = 0
    precision_warned = set()
    duration = 0.0
    if mapping:
        warnings.append(
            "DBC không được áp dụng khi nhập MF4 ở phiên bản này; chỉ đọc các "
            "kênh số đã có. MF4 chứa bus thô cần được giải mã riêng."
        )
    with MDF(source) as mdf:
        if not str(mdf.version).startswith("4"):
            raise ValueError("Chỉ hỗ trợ MDF phiên bản 4 (MF4).")
        mdf.configure(read_fragment_size=MF4_READ_FRAGMENT_SIZE)
        start_time = mdf.header.start_time
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
            warnings.append("MF4 không có múi giờ; mốc thời gian tuyệt đối được hiểu là UTC.")
        writer.metadata["start_time"] = start_time.timestamp()
        channels = [(group_index, channel_index, channel)
                    for group_index, group in enumerate(mdf.groups)
                    for channel_index, channel in enumerate(group.channels)
                    if channel_index != mdf.masters_db.get(group_index)]
        for position, (group_index, channel_index, channel) in enumerate(channels):
            check_cancelled(token)
            key = f"MF4:{group_index}:{channel_index}:{channel.name}"
            registered = False
            cycles = int(mdf.groups[group_index].channel_group.cycles_nr)
            # iter_get của asammdf 8.x có thể loại mẫu lỗi; get theo lô giữ cả
            # timestamp lẫn invalidation_bits mà không dùng API nội bộ.
            for offset in range(0, cycles, MF4_BATCH_SAMPLES):
                check_cancelled(token)
                fragment = mdf.get(
                    group=group_index, index=channel_index, raw=True,
                    ignore_invalidation_bits=True, record_offset=offset,
                    record_count=min(MF4_BATCH_SAMPLES, cycles - offset),
                ).physical(copy=False, ignore_value2text_conversions=True)
                values = np.asarray(fragment.samples)
                if values.ndim != 1 or values.dtype.kind not in "biuf":
                    skipped.append(f"{channel.name} (nhóm {group_index}, kiểu {values.dtype})")
                    break
                if not registered:
                    writer.add_signal(SignalInfo(
                        key=key, name=fragment.name or channel.name,
                        unit=fragment.unit or "", channel=str(group_index),
                        message=f"MF4 group {group_index}", source=str(source),
                    ))
                    registered = True
                    imported += 1
                times = np.asarray(fragment.timestamps, dtype=np.float64)
                if values.dtype.kind in "iu":
                    high = bool(np.any(values > 2**53))
                    low = values.dtype.kind == "i" and bool(np.any(values < -(2**53)))
                    if high or low:
                        warn_integer_precision(writer, key, channel.name, precision_warned)
                values = values.astype(np.float64, copy=True)
                invalidation = getattr(fragment, "invalidation_bits", None)
                # Giữ vị trí mẫu lỗi trong trục thời gian; không loại bỏ hoặc nội suy.
                if invalidation is not None:
                    values[np.asarray(invalidation, dtype=bool)] = np.nan
                if len(times):
                    if not np.all(np.isfinite(times)):
                        raise ValueError(f"MF4 có timestamp không hợp lệ: {channel.name}")
                    writer.append(key, times, values)
                    duration = max(duration, float(times[-1]))
                report(progress, (position + min(1.0, (offset + MF4_BATCH_SAMPLES) / max(cycles, 1))) / max(len(channels), 1),
                       f"Đang đọc MF4: {channel.name}")
        if skipped:
            warnings.append(f"Bỏ qua {len(skipped)} kênh không phải dữ liệu số vô hướng; xem skipped_channels.")
        if not imported:
            warnings.append("MF4 không có kênh số có thể nhập.")
        warnings.append(
            "Nhập MF4 hiện chỉ hỗ trợ tín hiệu số vô hướng; bản tin bus dạng cấu "
            "trúc, chuỗi, mảng và sự kiện không được bảo toàn."
        )
    writer.metadata.update({"duration": duration, "skipped_channels": skipped,
                            "imported_channels": imported})
