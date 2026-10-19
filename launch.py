"""Entry point cho PyInstaller; sửa hành vi khởi động tại vehiclelog/cli/app.py."""
from vehiclelog.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
