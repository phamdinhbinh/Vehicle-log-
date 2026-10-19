"""Tính công thức đã gán cho các giai đoạn của project.

Chức năng: Tính công thức đã gán cho các giai đoạn của project.
Sửa tại đây khi: đổi đầu ra JSON hoặc exit code; phép tính nằm ở calculations/.
Liên kết: project.py, importers.py và formulas.py.
"""
# COMPONENT: cli.analyze
import json
from pathlib import Path


def analyze_project(args, progress):
    """Tính công thức đã gán cho các giai đoạn của project."""
    from dataclasses import asdict
    from ..project import load_project
    from ..importers import import_log
    from ..formulas import evaluate_all
    project = load_project(args.project)
    cache_root = args.cache_root
    if cache_root is None and project.cache_path:
        cache_root = str(Path(project.cache_path).parent)
    store = import_log(project.source, dbc_map=project.dbc_map, cache_root=cache_root, progress=progress)
    results = evaluate_all(store, project.formulas, project.segments, progress=progress)
    if not results:
        raise ValueError("Project chưa có công thức được gán cho giai đoạn.")
    payload = json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2, allow_nan=False)
    if args.output:
        # Exclusive creation: analysis must not overwrite source/project files.
        with Path(args.output).open("x", encoding="utf-8") as out:
            out.write(payload + "\n")
    else:
        print(payload)
    return 0 if all(r.status in {"ok", "trace"} for r in results) else 2
