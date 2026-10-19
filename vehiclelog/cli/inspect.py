"""Tra cứu metadata và signal key.

Chức năng: Tra cứu metadata và signal key.
Sửa tại đây khi: đổi nội dung JSON của lệnh inspect.
Liên kết: readers qua importers.import_log.
"""
# COMPONENT: cli.inspect
from ..importers import import_log
from .options import parse_dbc_map
import json


def inspect_log(args, progress):
    """Đọc log và in metadata/tín hiệu dạng JSON, giới hạn preview theo --preview."""
    store = import_log(args.source, dbc_map=parse_dbc_map(args.dbc), cache_root=args.cache_root,
                       force=args.force, progress=progress)
    from dataclasses import asdict
    metadata = dict(store.metadata)
    metadata["frame_preview"] = metadata.get("frame_preview", [])[:max(0, args.preview)]
    print(json.dumps({"cache": str(store.path), "metadata": metadata, "signals": [asdict(s) for s in store.signals.values()]}, ensure_ascii=False, indent=2))
    return 0
