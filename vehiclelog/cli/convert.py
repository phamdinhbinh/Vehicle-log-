"""Chuyển log thành Excel hoặc MF4.

Chức năng: Chuyển log thành Excel hoặc MF4.
Sửa tại đây khi: đổi luồng CLI; định dạng file nằm trong writers/.
Liên kết: importers và exports giữ API tương thích.
"""
# COMPONENT: cli.convert
from pathlib import Path
from .options import parse_dbc_map, parse_segments


def convert_log(args, progress):
    """Kiểm tra đích trước khi giải mã log lớn; xuất qua component writers."""
    dbcs = parse_dbc_map(args.dbc)
    if args.command == "convert":
        destination = Path(args.destination).expanduser().resolve()
        if destination == Path(args.source).expanduser().resolve() or destination in [Path(p).resolve() for p in dbcs.values()]:
            raise ValueError("Không được ghi đè file nguồn hoặc DBC.")
        if destination.exists():
            raise FileExistsError(f"File đích đã tồn tại: {destination}")
        if not destination.parent.is_dir():
            raise FileNotFoundError(f"Thư mục đích không tồn tại: {destination.parent}")
        if args.format == "excel" and destination.suffix.lower() != ".xlsx":
            raise ValueError("File Excel phải có phần mở rộng .xlsx.")
        if args.format != "excel" and destination.suffix.lower() != ".mf4":
            raise ValueError("File MDF4 phải có phần mở rộng .mf4.")
    if args.command == "convert" and args.format == "raw-mf4":
        from ..exports import export_raw_mf4
        output = export_raw_mf4(args.source, args.destination, dbc_map=dbcs, segments=parse_segments(args.segment), zero_time=args.zero_time, progress=progress)
        print(output)
        return 0
    from ..importers import import_log
    store = import_log(args.source, dbc_map=dbcs, cache_root=args.cache_root, force=args.force, progress=progress)
    from ..exports import export_excel, export_mf4
    keys = []
    for name in args.signal:
        if name in store.signals:
            keys.append(name)
        else:
            matches = [key for key, info in store.signals.items() if info.name == name]
            if len(matches) != 1:
                raise ValueError(f"Tín hiệu không tồn tại hoặc trùng tên: {name}; dùng key từ inspect.")
            keys.extend(matches)
    options = dict(keys=keys or None, segments=parse_segments(args.segment), progress=progress)
    if args.format == "excel":
        output = export_excel(store, args.destination, **options)
    else:
        output = export_mf4(store, args.destination, zero_time=args.zero_time, **options)
    print(output)
    return 0
