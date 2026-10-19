"""Chức năng: đọc BLF theo lô, giải mã CAN/CAN FD và thống kê bản tin.

Sửa tại đây khi: đổi giải mã DBC, ngưỡng flush RAM hoặc bản tin xem trước.
Liên kết: service.py gọi import_blf; dbc.py nạp DBC; common.py cảnh báo/hủy.
"""
# COMPONENT: readers.blf

from collections import Counter, defaultdict
import math

import numpy as np

from ..models import SignalInfo, report
from .common import check_cancelled, warn_integer_precision
from .dbc import load_databases

# Giới hạn theo cả số bản tin và số giá trị vì một frame có thể có nhiều tín hiệu.
BLF_BATCH_FRAMES = 20_000
BLF_BATCH_VALUES = 200_000
FRAME_PREVIEW_LIMIT = 500
DIAGNOSTIC_LIMIT = 500


def import_blf(source, mapping, writer, progress, token):
    """Giải mã từng frame vào StoreWriter, chỉ giữ các lô có kích thước giới hạn."""
    import can
    databases = load_databases(mapping, token)

    warnings = writer.metadata["warnings"]
    warnings.append(
        "Bộ đọc BLF hiện nhập CAN/CAN FD. Các đối tượng LIN, FlexRay, Ethernet "
        "và sự kiện BLF khác không được nhập hoặc bảo toàn trong cache tín hiệu."
    )
    stats = Counter()
    unknown = Counter()
    errors = Counter()
    channel_frames = Counter()
    batches = defaultdict(lambda: ([], []))
    known_signals = set()
    precision_warned = set()
    preview = []
    frames_since_flush = 0
    buffered_values = 0
    duration = 0.0

    def count_diagnostic(counter, identity):
        # Giới hạn số mục chẩn đoán để file hỏng không làm tăng RAM vô hạn.
        key = identity if identity in counter or len(counter) < DIAGNOSTIC_LIMIT else "other (diagnostic limit)"
        counter[key] += 1

    def flush():
        for key, (times, values) in batches.items():
            if times:
                writer.append(key, np.asarray(times, dtype=np.float64),
                              np.asarray(values, dtype=np.float64))
        batches.clear()

    with can.BLFReader(source) as reader:
        origin = float(reader.start_timestamp)
        writer.metadata["start_time"] = origin
        file_size = max(source.stat().st_size, 1)
        for frame in reader:
            if frames_since_flush % 1024 == 0:
                check_cancelled(token)
            stats["frames"] += 1
            frames_since_flush += 1
            if frames_since_flush >= BLF_BATCH_FRAMES or buffered_values >= BLF_BATCH_VALUES:
                flush()
                frames_since_flush = 0
                buffered_values = 0
                report(progress, min(reader.file.tell() / file_size, 0.98),
                       f"Đang đọc BLF: {stats['frames']:,} bản tin, {len(known_signals)} tín hiệu")
            # python-can dùng kênh từ 0; cache/giao diện dùng từ 1. Chỉ đổi tại đây.
            channel = int(frame.channel if frame.channel is not None else 0) + 1
            channel_frames[channel] += 1
            # Cache lưu giây tương đối; mốc UTC được giữ riêng trong metadata.
            timestamp = float(frame.timestamp) - origin
            if not math.isfinite(timestamp):
                stats["invalid_timestamps"] += 1
                continue
            duration = max(duration, timestamp)
            if len(preview) < FRAME_PREVIEW_LIMIT:
                preview.append({
                    "time": timestamp, "channel": channel,
                    "can_id": int(frame.arbitration_id),
                    "is_extended_id": bool(frame.is_extended_id),
                    "is_fd": bool(frame.is_fd), "dlc": int(frame.dlc),
                    "data": bytes(frame.data).hex(" ").upper(),
                })
            if frame.is_error_frame:
                stats["error_frames"] += 1
                continue
            if frame.is_remote_frame:
                stats["remote_frames"] += 1
                continue
            database = databases.get(channel)
            if database is None:
                stats["unmapped_channel_frames"] += 1
                continue
            identity = f"CAN{channel}/0x{frame.arbitration_id:X}"
            try:
                message = database.get_message_by_frame_id(frame.arbitration_id)
            except KeyError:
                count_diagnostic(unknown, identity)
                stats["unknown_frames"] += 1
                continue
            if bool(message.is_extended_frame) != bool(frame.is_extended_id):
                count_diagnostic(errors, identity + ": standard/extended ID mismatch")
                stats["decode_errors"] += 1
                continue
            try:
                decoded = message.decode(
                    frame.data, decode_choices=False, scaling=True,
                    allow_truncated=False, allow_excess=True,
                )
            except Exception as error:
                count_diagnostic(errors, identity + ": " + str(error)[:200])
                stats["decode_errors"] += 1
                continue
            stats["decoded_frames"] += 1
            for signal in message.signals:
                if signal.name not in decoded:  # Không tạo mẫu cho nhánh multiplex chưa hoạt động.
                    continue
                value = decoded[signal.name]
                if not isinstance(value, (int, float, np.number, bool)):
                    stats["nonnumeric_values"] += 1
                    continue
                key = f"CAN{channel}:{frame.arbitration_id:X}:{'X' if frame.is_extended_id else 'S'}:{signal.name}"
                if isinstance(value, (int, np.integer)) and abs(int(value)) > 2**53:
                    warn_integer_precision(writer, key, signal.name, precision_warned)
                if key not in known_signals:
                    writer.add_signal(SignalInfo(
                        key=key, name=signal.name, unit=signal.unit or "",
                        channel=str(channel), message=message.name,
                        can_id=int(frame.arbitration_id), source=str(source),
                        choices={str(k): str(v) for k, v in (signal.choices or {}).items()},
                    ))
                    known_signals.add(key)
                times, values = batches[key]
                times.append(timestamp)
                values.append(float(value))
                buffered_values += 1
        flush()
    for channel, count in sorted(channel_frames.items()):
        if channel not in databases:
            warnings.append(f"CAN {channel}: {count:,} bản tin chưa giải mã vì chưa gán DBC.")
    if unknown:
        warnings.append(f"Có {stats['unknown_frames']:,} bản tin không tìm thấy CAN ID trong DBC.")
    if errors:
        warnings.append(f"Có {stats['decode_errors']:,} bản tin giải mã thất bại; xem decode_errors.")
    if not known_signals:
        warnings.append("Không có tín hiệu được giải mã; chỉ có thống kê và bản tin xem trước.")
    writer.metadata.update({
        "duration": duration, "frames": stats["frames"],
        "frame_stats": dict(stats), "frame_preview": preview,
        "frame_preview_limit": FRAME_PREVIEW_LIMIT,
        "channels": {str(k): v for k, v in sorted(channel_frames.items())},
        "unknown_messages": dict(unknown), "decode_errors": dict(errors),
    })
