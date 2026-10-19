"""Create a portable demo workspace with assigned energy formulas."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vehiclelog.demo import create_demo
from vehiclelog.importers import import_log
from vehiclelog.models import Project, Cursor, Segment, Formula
from vehiclelog.formulas import evaluate_all
from vehiclelog.project import save_project


def make_demo_project(directory):
    directory = Path(directory).resolve()
    files = create_demo(directory)
    store = import_log(files["blf"], {1: files["dbc"]}, cache_root=directory / ".cache")
    keys = {info.name: key for key, info in store.signals.items()}
    cursors = [Cursor(f"M{i+1}", t, color) for i, (t, color) in enumerate(zip([0,40,80,120],["#f8b952", "#56c8ef", "#a18bff", "#40d4a4"]))]
    segments = [Segment(name, cursors[i].time, cursors[i+1].time, color,
                        start_cursor=cursors[i].id, end_cursor=cursors[i+1].id)
                for i, (name,color) in enumerate(zip(["Tăng tốc", "Thu hồi năng lượng", "Chạy ổn định"], ["#247eae", "#248a6b", "#8854b7"]))]
    segments.append(Segment("Toàn hành trình", 0, 120, "#d39240"))
    assigned = [s.id for s in segments]
    bindings = {"U": keys["PackVoltage"], "I": keys["PackCurrent"]}
    formulas = [
        Formula("Năng lượng ròng", "integral(U * I) / 3600000", bindings, "kWh", assigned),
        Formula("Năng lượng xả", "integral(positive(U * I)) / 3600000", bindings, "kWh", assigned),
        Formula("Năng lượng thu hồi", "integral(negative(U * I)) / 3600000", bindings, "kWh", assigned),
        Formula("Quãng đường", "integral(v) / 3600", {"v": keys["VehicleSpeed"]}, "km", assigned),
        Formula("Công suất pin", "U * I / 1000", bindings, "kW", assigned),
        Formula("Mức tiêu thụ", "100 * safe_div(integral(U * I) / 3600000, integral(v) / 3600, 0.001)",
                {**bindings, "v": keys["VehicleSpeed"]}, "kWh/100km", assigned),
    ]
    # Scalar results only; pointwise power is available through the plot action.
    results = evaluate_all(store, [f for f in formulas if f.name != "Công suất pin"], segments)
    project = Project(source=str(files["blf"]), dbc_map={"1": str(files["dbc"])},
                      selected_signals=list(store.signals), cursors=cursors,
                      segments=segments, formulas=formulas, results=results,
                      cache_path=str(store.path))
    target = save_project(project, directory / "demo.vls.json")
    # Relative paths make the source folder portable to Windows/Linux machines.
    import json
    payload = project.to_dict()
    payload["source"] = files["blf"].name
    payload["dbc_map"] = {"1": files["dbc"].name}
    payload["cache_path"] = ""
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return project, store, target


if __name__ == "__main__":
    project, store, target = make_demo_project(sys.argv[1] if len(sys.argv) > 1 else "examples/demo")
    for result in project.results:
        if result.segment_name == "Toàn hành trình":
            print(f"{result.formula_name}: {result.value} {result.unit} [{result.status}]")
    print(target)
