"""Tạo bộ dữ liệu demo tái lập được, có đáp án năng lượng biết trước.

Chức năng: sinh DBC, BLF và MF4 điện áp/dòng điện/tốc độ để thử ứng dụng.
Sửa tại đây khi: thay dạng sóng hoặc DBC mẫu; cập nhật hằng số đáp án tương ứng.
Liên kết: cli/demo.py và ui/controllers/demo.py gọi create_demo.
"""
# COMPONENT: demo.data
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np


DEMO_START_TIME = 1_735_689_600.0  # 2025-01-01 00:00:00 UTC
DEMO_DURATION = 120.0
DEMO_EXPECTED_NET_KWH = 0.26666666666666666
DEMO_EXPECTED_DISCHARGE_KWH = 0.35555555555555557
DEMO_EXPECTED_REGEN_KWH = 0.08888888888888889
DEMO_EXPECTED_DISTANCE_KM = 1.2

DEMO_DBC = '''VERSION "Vehicle Log Studio synthetic demo"

NS_ :
BS_:
BU_: BMS VCU

BO_ 256 Battery: 8 BMS
 SG_ PackVoltage : 0|16@1+ (0.1,0) [0|6553.5] "V" VCU
 SG_ PackCurrent : 16|16@1- (0.1,0) [-3276.8|3276.7] "A" VCU

BO_ 257 Vehicle: 8 VCU
 SG_ VehicleSpeed : 0|16@1+ (0.01,0) [0|655.35] "km/h" BMS
'''


def create_demo(directory) -> dict:
    """Tạo BLF/DBC/MF4 dài 120 s, 10 Hz, có pha thu hồi năng lượng.

    Công suất lần lượt 20, -8, 12 kW, mỗi pha 40 s; dòng dương là xả.
    Hold cho năng lượng ròng 0.2666667 kWh. MF4 thêm kênh chuỗi để kiểm tra
    báo cáo bỏ qua kiểu dữ liệu không hỗ trợ.
    """
    import can
    import cantools
    from asammdf import MDF, Signal

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    dbc = directory / "demo_vehicle.dbc"
    blf = directory / "demo_drive.blf"
    mf4 = directory / "demo_drive.mf4"
    dbc.write_text(DEMO_DBC, encoding="utf-8")
    database = cantools.database.load_file(dbc)
    times = np.arange(1201, dtype=np.float64) / 10
    voltage = np.full(times.size, 400.0)
    current = np.where(times < 40, 50.0, np.where(times < 80, -20.0, 30.0))
    speed = np.full(times.size, 36.0)
    battery_message = database.get_message_by_name("Battery")
    speed_message = database.get_message_by_name("Vehicle")
    with can.BLFWriter(blf) as writer:
        for timestamp, volts, amps, kph in zip(times, voltage, current, speed):
            writer.on_message_received(can.Message(
                timestamp=DEMO_START_TIME + float(timestamp), channel=0,
                arbitration_id=256, is_extended_id=False,
                data=battery_message.encode({"PackVoltage": volts, "PackCurrent": amps}),
            ))
            writer.on_message_received(can.Message(
                timestamp=DEMO_START_TIME + float(timestamp), channel=0,
                arbitration_id=257, is_extended_id=False,
                data=speed_message.encode({"VehicleSpeed": kph}),
            ))
    with MDF(version="4.10") as mdf:
        mdf.header.start_time = datetime.fromtimestamp(DEMO_START_TIME, timezone.utc)
        mdf.append([
            Signal(voltage, times, name="PackVoltage", unit="V"),
            Signal(current, times, name="PackCurrent", unit="A"),
            Signal(speed, times, name="VehicleSpeed", unit="km/h"),
        ], common_timebase=True, comment="Synthetic demo; positive current means discharge.")
        mdf.append(Signal(np.array([b"demo", b"end"]), np.array([0.0, 120.0]), name="Notes", encoding="utf-8"))
        mdf.save(mf4, overwrite=True)
    return {"blf": blf, "dbc": dbc, "mf4": mf4}
