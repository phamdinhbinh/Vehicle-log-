"""Khai báo command và tham số argparse.

Chức năng: Khai báo command và tham số argparse.
Sửa tại đây khi: đổi --help, thêm tùy chọn hoặc giá trị mặc định.
Liên kết: app.py chọn handler sau khi parse.
"""
# COMPONENT: cli.parser
import argparse


def build_parser():
    """Tạo parser dùng chung cho console script và python -m vehiclelog."""
    parser = argparse.ArgumentParser(description="Vehicle Log Studio — CAN signals, segments & energy")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("gui", help="Mở ứng dụng desktop")
    demo = sub.add_parser("demo", help="Tạo BLF/DBC/MF4 mẫu có năng lượng biết trước")
    demo.add_argument("--directory", default="examples/demo")
    demo.add_argument("--gui", action="store_true")
    for command in ("inspect", "convert"):
        p = sub.add_parser(command)
        p.add_argument("source")
        p.add_argument("--dbc", action="append", default=[], metavar="CHANNEL=PATH")
        p.add_argument("--cache-root", default=None)
        p.add_argument("--force", action="store_true")
        if command == "inspect":
            p.add_argument("--preview", type=int, default=0, help="Số bản tin xem trước trong JSON")
        if command == "convert":
            p.add_argument("destination")
            p.add_argument("--format", choices=["excel", "mf4", "raw-mf4"], required=True)
            p.add_argument("--signal", action="append", default=[], help="Signal key or unique signal name")
            p.add_argument("--segment", action="append", default=[], metavar="NAME:START:END")
            p.add_argument("--zero-time", action="store_true")
    analyze = sub.add_parser("analyze", help="Tính công thức đã gán trong project JSON")
    analyze.add_argument("project")
    analyze.add_argument("--output", help="Ghi kết quả JSON (từ chối ghi đè file có sẵn)")
    analyze.add_argument("--cache-root", help="Thư mục cache; mặc định ưu tiên cache project đã lưu")
    return parser
