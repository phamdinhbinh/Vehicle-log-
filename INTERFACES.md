# Internal contracts

Source layout: UI in `vehiclelog/ui`, import in `readers`, calculation in
`calculations`, disk cache in `storage`, export in `writers`, commands in `cli`.
The historical `gui.py`, `importers.py`, `formulas.py`, `store.py`, `exports.py`
modules are thin public facades. See `CODE_MAP.md` for Vietnamese edit guidance.
Chunk limits belong to their implementation modules; tests patch those owners.

Package `vehiclelog`; Python 3.11+. Shared dataclasses in `models.py`.

## Disk store (root implements)

`SignalStore(path)` opens completed store, `.signals` is dict[str, SignalInfo],
`.metadata` is dict (source, start_time, duration, warnings, frames…), `.path` Path.
`read(key, start=None, end=None, neighbors=False) -> (np.ndarray times, values)`;
neighbors includes one point either side for interpolation. Data is memmapped,
sorted by time, duplicate timestamp keeps last value. Times relative to log origin.
`iter_chunks(key, start=None, end=None, chunk_size=100000)` yields times,values.
`plot_data(key, start=None, end=None, max_points=4000)` min/max overview.
`StoreWriter(path, metadata=None)` context manager: `add_signal(SignalInfo)`,
`append(key, times, values)` (bounded buffering internal), `.metadata` mutable dict,
`finish() -> SignalStore`. Temporary directory renamed on successful finish.
No implicit finish in __exit__; partial discarded. Existing path not overwritten.
Cache helpers: `cache_key(source, dbc_map)`, `default_cache_root()`.

## Import (io agent)

`vehiclelog.importers.import_log(source, dbc_map=None, cache_root=None,
 progress=None, token=None, force=False) -> SignalStore`
DBC map uses **one-based displayed CAN channel**: `{1: '/file.dbc'}`;
BLF python-can channel is zero-based; normalize +1 exactly once.
MF4 numeric channels only initially, warnings for skipped types; preserve invalid
samples as NaN; avoid eager full-file loading where possible.
`vehiclelog.demo.create_demo(directory) -> dict` with keys `blf`, `dbc`, `mf4`;
create deterministic synthetic voltage/current/speed, includes regenerative phase.

## Calculations (formulas agent)

`vehiclelog.formulas.validate_expression(expression, aliases)` raises ValueError.
`evaluate_formula(store, formula, segment, token=None) -> FormulaResult`
`evaluate_all(store, formulas, segments, progress=None, token=None) -> list[FormulaResult]`
`evaluate_trace(store, formula, segment, token=None) -> (times, values)` for pointwise formulas.
Whitelist AST, never eval arbitrary Python. Functions integral, mean (time weighted),
sample_mean, min, max, first, last, delta, abs, clip, positive, negative (magnitude),
sqrt. `integral` in seconds. Hold default; linear optional. Validate max_gap >0.
Gaps/missing coverage => incomplete/invalid with value None, no silently partial total.
segment_ids empty means no assignment, NOT all; GUI explicitly fills selected IDs.
Compute boundaries correctly and bound memory by evaluation chunks when possible.

## Export (exports agent)

`vehiclelog.exports.export_excel(store, destination, keys=None, segments=None,
 formulas=None, results=None, raster=None, interpolation='hold', max_gap=1.0,
 progress=None, token=None) -> Path`
Native: tall layout per signal or data sheets with explicit timestamps, chunked.
Raster optional, preserve gaps. Sheet split at Excel limit. Include provenance.
`export_mf4(store, destination, keys=None, segments=None, zero_time=False,
 progress=None, token=None) -> Path` decoded numeric signals, native timestamps;
segment labels/provenance recorded; no unintended concatenation of disjoint cuts.
`export_raw_mf4(source, destination, dbc_map=None, segments=None, zero_time=False,
 progress=None, token=None) -> Path` streamed CAN_DataFrame structure compatible
asammdf bus logging; retain bus IDs / flags; supported flags documented/tested.
If cannot implement raw reliably report explicit limitation, do not fake raw export.
All writes temporary/atomic, reject overwriting input source, cancellation cleanup.

## GUI (gui agent)

`vehiclelog.gui.run_app() -> int`; `MainWindow` available for smoke test.
Calls above APIs in cancellable QThread background workers. Demo action import
demo via import_log. Parent provides __main__, persistence, store.
`vehiclelog.project.save_project(project, path)` and `load_project(path) -> Project`.
GUI signal plot selection, fit X/Y buttons and a fitted canvas with no scroll.
Ordered cursors automatically generate adjacent stages via stages.synchronize_stages;
the GUI edits stage names only. Cursor pairs expose native Y values, delta-Y and
delta-t via measurements.py; no lock/snap/manual-range UI. Formula CRUD retains
explicit segment checkboxes, calculate, result table,
Excel/decoded MF4/raw MF4 export, project save/load. Never UI-blocking import,
calculation, export. Cache store windowed reads for plot (small overview minmax).

Work ownership: root models/store/project/CLI/docs/integration;
agents importers+demo; formulas; exports; GUI. Each adds own focused tests.
