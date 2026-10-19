"""Điều phối CLI và thông báo lỗi chung.

Chức năng: Điều phối CLI và thông báo lỗi chung.
Sửa tại đây khi: thêm handler hoặc thay exit code/thông báo tiến độ.
Liên kết: parser.py khai báo tùy chọn; các handler ở file theo chức năng.
"""
# COMPONENT: cli.app
import sys
from .parser import build_parser


def print_progress(fraction, message):
    """In tiến độ ra stderr để JSON trên stdout không bị trộn thông báo."""
    print(f"{fraction * 100:5.1f}% {message}", file=sys.stderr, flush=True)


def main(argv=None) -> int:
    """Chạy GUI hoặc command; trả mã 1 khi lỗi, 130 khi người dùng ngắt."""
    args = build_parser().parse_args(argv)
    try:
        if args.command in (None, "gui"):
            from ..gui import run_app
            return run_app()
        if args.command == "demo":
            from .demo import generate_demo
            return generate_demo(args)
        if args.command == "analyze":
            from .analyze import analyze_project
            return analyze_project(args, print_progress)
        if args.command == "inspect":
            from .inspect import inspect_log
            return inspect_log(args, print_progress)
        from .convert import convert_log
        return convert_log(args, print_progress)
    except KeyboardInterrupt:
        print("Đã ngắt tác vụ.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 1
