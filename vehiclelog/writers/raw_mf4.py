"""Chức năng: chuyển CAN/CAN FD data frame từ BLF sang MF4 bus logging.

Sửa tại đây khi: đổi layout CAN_DataFrame, cờ CAN FD, kiểm tra payload hoặc chia giai đoạn.
Liên kết: common.py ghi MF4/tiến độ; atomic.py bảo vệ đầu ra; DBC chỉ lưu nguồn gốc.
"""
# COMPONENT: writers.raw_mf4
from __future__ import annotations

from dataclasses import asdict
import math
from pathlib import Path

import numpy as np

from ..models import report
from .atomic import _output
from .common import _check, _json, _save_mf4, _set_start_time

CHUNK_SIZE = 50_000

RAW_CAN_DTYPE = np.dtype([
    ("CAN_DataFrame.BusChannel", "u1"),
    ("CAN_DataFrame.ID", "<u4"),
    ("CAN_DataFrame.IDE", "u1"),
    ("CAN_DataFrame.DLC", "u1"),
    ("CAN_DataFrame.DataLength", "u1"),
    ("CAN_DataFrame.DataBytes", "u1", (64,)),
    ("CAN_DataFrame.Dir", "u1"),
    ("CAN_DataFrame.EDL", "u1"),
    ("CAN_DataFrame.BRS", "u1"),
    ("CAN_DataFrame.ESI", "u1"),
])


def export_raw_mf4(source, destination, dbc_map=None, segments=None, zero_time=False,
                   progress=None, token=None):
    """Chuyển tuần tự CAN/CAN FD data frame từ BLF sang MF4 bus logging.

    BusChannel = kênh BLF zero-based + 1; giữ IDE, Rx/Tx, EDL, BRS, ESI,
    DLC chuẩn và độ dài payload. Từ chối remote/error frame và payload hỏng.
    Không sao chép các đối tượng logger riêng mà BLFReader không cung cấp.
    DBC chỉ lưu nguồn gốc; việc giải mã thuộc phần mềm đọc MF4 sau này.
    """
    import can
    from asammdf import MDF, Signal
    from asammdf.blocks.source_utils import Source
    from asammdf.blocks import v4_constants as v4c

    source = Path(source).expanduser().resolve()
    if source.suffix.lower() != ".blf":
        raise ValueError("Xuất MF4 bản tin thô yêu cầu file BLF.")
    if Path(destination).suffix.lower() != ".mf4":
        raise ValueError("File MDF4 phải có phần mở rộng .mf4.")
    scopes = list(segments or [])
    for scope in scopes:
        scope.validate()
    # None là toàn log để không bỏ mất mẫu cuối do stop_timestamp làm tròn ms.
    scope_specs = scopes if scopes else [None]
    with _output(destination, source=source, dbc_map=dbc_map, token=token) as temporary:
        with can.BLFReader(source) as reader, MDF(version="4.10") as mdf:
            origin = reader.start_timestamp
            _set_start_time(mdf, {"start_time": origin})
            bus_source = Source("CAN", "CAN", "BLF CAN/CAN FD data frames", v4c.SOURCE_BUS, v4c.BUS_TYPE_CAN)
            groups, buffers, time_buffers = {}, {}, {}
            buffered = 0
            exported = 0
            last_timestamp = -math.inf
            source_size = max(source.stat().st_size, 1)

            def flush():
                """Đẩy buffer các giai đoạn vào group, giữ tổng RAM theo CHUNK_SIZE."""
                nonlocal buffered
                _check(token)
                for index, records in buffers.items():
                    if not records:
                        continue
                    scope = scope_specs[index]
                    samples = np.array(records, dtype=RAW_CAN_DTYPE)
                    timestamps = np.array(time_buffers[index], dtype=np.float64)
                    if scope is not None and zero_time:
                        # Mốc 0 là đầu giai đoạn; không dịch theo mẫu đầu của buffer.
                        timestamps -= scope.start
                    if index not in groups:
                        provenance = _json({"source": str(source), "dbc_map": dbc_map or {},
                                            "segment": asdict(scope) if scope else None,
                                            "source_start_utc": origin,
                                            "output_time_offset_s": scope.start if scope and zero_time else 0.0,
                                            "raw_format": "ASAM CAN_DataFrame; CAN/CAN FD data frames only",
                                            "limitations": "BLF non-frame logger objects are not retained; remote/error frames rejected"})
                        groups[index] = mdf.append(
                            [Signal(samples, timestamps, name="CAN_DataFrame", source=bus_source,
                                    comment="CAN/CAN FD data frames; BusChannel is one-based")],
                            common_timebase=True, comment=provenance,
                        )
                    else:
                        mdf.extend(groups[index], [(timestamps, None), (samples, None)])
                    records.clear()
                    time_buffers[index].clear()
                buffered = 0

            for frame_number, message in enumerate(reader, start=1):
                if frame_number % 2_000 == 1:
                    _check(token)
                # Ranh giới giai đoạn dùng mốc header BLF, không dùng frame đầu.
                timestamp = float(message.timestamp-origin)
                matched = [i for i, scope in enumerate(scope_specs)
                           if scope is None or scope.start <= timestamp <= scope.end]
                if not matched:
                    if frame_number % 5_000 == 0:
                        report(progress, min(reader.file.tell()/source_size, 1)*0.85,
                               f"Đã đọc {frame_number:,} bản tin BLF")
                    continue
                if not math.isfinite(timestamp) or timestamp < last_timestamp:
                    raise ValueError("Timestamp BLF không hợp lệ hoặc đi lùi trong vùng chọn; cần kiểm tra log trước khi xuất MF4.")
                last_timestamp = timestamp
                if message.is_remote_frame or message.is_error_frame:
                    raise ValueError("Chế độ MF4 bản tin thô hiện chỉ hỗ trợ CAN/CAN FD data frame; log có remote/error frame trong vùng chọn.")
                length = len(message.data)
                if length != message.dlc or length > (64 if message.is_fd else 8):
                    raise ValueError("Payload CAN không khớp DLC hoặc vượt kích thước hỗ trợ.")
                if message.is_fd and length not in {0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 16, 20, 24, 32, 48, 64}:
                    raise ValueError("Độ dài payload CAN FD không có DLC chuẩn tương ứng.")
                if not 0 <= message.arbitration_id <= (0x1FFFFFFF if message.is_extended_id else 0x7FF):
                    raise ValueError("CAN ID không hợp lệ cho kiểu standard/extended của bản tin.")
                try:
                    # DBC/UI/ASAM dùng kênh 1-based; python-can trả kênh 0-based.
                    channel = int(message.channel)+1
                except (TypeError, ValueError) as exc:
                    raise ValueError("Không xác định được kênh CAN của bản tin BLF.") from exc
                if not 1 <= channel <= 255:
                    raise ValueError("MF4 CAN_DataFrame hiện hỗ trợ kênh CAN từ 1 đến 255.")
                payload = np.frombuffer(bytes(message.data).ljust(64, b"\0"), dtype=np.uint8)
                record = (channel, message.arbitration_id, int(message.is_extended_id),
                          can.util.len2dlc(length), length, payload, int(not message.is_rx),
                          int(message.is_fd), int(message.bitrate_switch), int(message.error_state_indicator))
                for index in matched:
                    buffers.setdefault(index, []).append(record)
                    time_buffers.setdefault(index, []).append(timestamp)
                    buffered += 1
                    exported += 1
                    if buffered >= CHUNK_SIZE:
                        flush()
                if frame_number % 5_000 == 0:
                    report(progress, min(reader.file.tell()/source_size, 1)*0.85,
                           f"Đã đọc {frame_number:,} bản tin BLF")
            flush()
            if not exported:
                raise ValueError("Không có bản tin CAN trong phạm vi đã chọn.")
            _check(token)
            report(progress, 0.9, f"Đang ghi {exported:,} bản tin vào MF4")
            _save_mf4(mdf, temporary, progress, token)
    report(progress, 1.0, "Đã xuất MF4 bản tin CAN/CAN FD")
    return Path(destination).expanduser().resolve()
