"""Chức năng: API công khai ổn định cho các chức năng xuất dữ liệu.

Sửa tại đây khi: bổ sung hàm xuất công khai; sửa logic trong writers/ tương ứng.
Liên kết: writers.excel, writers.mf4 và writers.raw_mf4.

Các tên hàm cũ được giữ nguyên để UI, CLI và script hiện có tiếp tục hoạt động.
Giới hạn Excel thuộc writers.excel_sheets; kích thước chunk thuộc từng writer.
"""
# COMPONENT: writers.public_api
from .writers.excel import export_excel
from .writers.mf4 import export_mf4
from .writers.raw_mf4 import RAW_CAN_DTYPE, export_raw_mf4

__all__ = ["export_excel", "export_mf4", "export_raw_mf4", "RAW_CAN_DTYPE"]
