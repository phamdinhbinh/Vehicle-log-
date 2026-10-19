"""Headless checks for the desktop's data and analysis interactions."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PySide6 import QtCore, QtWidgets

from vehiclelog.gui import FormulaDialog, MainWindow
from vehiclelog.models import Formula, FormulaResult, Segment, SignalInfo
from vehiclelog.store import StoreWriter


@pytest.fixture(scope="session")
def app():
    instance = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield instance


@pytest.fixture
def store(tmp_path):
    with StoreWriter(tmp_path / "store", {"source": "synthetic.blf", "duration": 5.0}) as writer:
        for key, name, unit, values in (
            ("voltage", "BatteryVoltage", "V", [400, 400, 400, 400, 400, 400]),
            ("current", "BatteryCurrent", "A", [10, 20, 10, -5, 0, 10]),
            ("speed", "VehicleSpeed", "km/h", [0, 10, 20, 30, 20, 0]),
        ):
            writer.add_signal(SignalInfo(key=key, name=name, unit=unit, channel="1"))
            writer.append(key, np.arange(6, dtype=float), np.asarray(values, dtype=float))
        return writer.finish()


@pytest.fixture
def window(app, store):
    instance = MainWindow()
    instance.set_store(store)
    yield instance
    instance._dirty = False
    instance.close()
    instance.deleteLater()
    app.processEvents()


def _item_with_key(widget, key):
    return next(
        widget.item(index)
        for index in range(widget.count())
        if widget.item(index).data(QtCore.Qt.ItemDataRole.UserRole) == key
    )


def test_store_signals_can_be_selected_and_removed_from_plot(window, app):
    assert window.signal_list.count() == 3
    item = _item_with_key(window.signal_list, "voltage")
    item.setCheckState(QtCore.Qt.CheckState.Checked)
    app.processEvents()

    assert "voltage" in window.project.selected_signals
    assert "voltage" in window.plots
    curves = window.plots["voltage"].listDataItems()
    assert curves
    times, values = curves[0].getData()
    np.testing.assert_array_equal(times, np.arange(6, dtype=float))
    np.testing.assert_array_equal(values, np.full(6, 400.0))

    item.setCheckState(QtCore.Qt.CheckState.Unchecked)
    app.processEvents()
    assert "voltage" not in window.project.selected_signals
    assert "voltage" not in window.plots


def test_middle_cursor_updates_both_adjacent_stages_and_invalidates_results(window):
    cursor = window.add_cursor(time=1.0)
    left, right = window.project.segments
    window.project.results = [
        FormulaResult("energy", "Battery energy", right.id, right.name, 0.01, "kWh")
    ]

    window._sync_cursor(cursor.id, 1.5)

    assert cursor.time == pytest.approx(1.5)
    assert [(s.start, s.end) for s in window.project.segments] == [(0, 1.5), (1.5, 5)]
    assert [s.id for s in window.project.segments] == [left.id, right.id]
    assert not window.project.results


def test_formula_dialog_preserves_explicit_stage_assignments(app, store):
    urban = Segment("Urban", 0.0, 2.0)
    hill = Segment("Hill", 2.0, 5.0)
    original = Formula(
        "Battery energy",
        "integral(U * I) / 3600000",
        {"U": "voltage", "I": "current"},
        unit="kWh",
        segment_ids=[hill.id],
    )
    dialog = FormulaDialog(store, [urban, hill], original)
    try:
        result = dialog.formula_value()
        assert result.name == original.name
        assert result.expression == original.expression
        assert result.bindings == original.bindings
        assert result.unit == "kWh"
        assert result.segment_ids == [hill.id]

        _item_with_key(dialog.segment_list, urban.id).setCheckState(QtCore.Qt.CheckState.Checked)
        result = dialog.formula_value()
        assert set(result.segment_ids) == {urban.id, hill.id}

        for index in range(dialog.segment_list.count()):
            dialog.segment_list.item(index).setCheckState(QtCore.Qt.CheckState.Unchecked)
        # No checkboxes means no assignment; it must never mean "all stages".
        assert dialog.formula_value().segment_ids == []
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()


@pytest.mark.parametrize("expression", ["__import__('os').system('echo unsafe')", "U.__class__", "unknown + 1"])
def test_formula_dialog_rejects_unsafe_or_unbound_expressions(app, store, expression):
    segment = Segment("Urban", 0.0, 5.0)
    formula = Formula("Energy", "integral(U)", {"U": "voltage"}, segment_ids=[segment.id])
    dialog = FormulaDialog(store, [segment], formula)
    try:
        dialog.expression_edit.setText(expression)
        with pytest.raises(ValueError):
            dialog.formula_value()
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()


def _wait_until(app, condition, timeout=5.0):
    import time
    deadline = time.monotonic() + timeout
    while not condition() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    app.processEvents()
    assert condition(), "Qt worker did not finish before the timeout"


def test_large_plot_preview_uses_background_and_cursor_reuses_cache(window, app, monkeypatch):
    import threading
    gui_thread = threading.get_ident()
    calls = []
    original = window.store.plot_data

    def observed(key, *args, **kwargs):
        if key == "voltage":
            calls.append(threading.get_ident())
        return original(key, *args, **kwargs)

    # Trigger the large-channel path without manufacturing a large on-disk log.
    window.store.signals["voltage"].count = 100_001
    monkeypatch.setattr(window.store, "plot_data", observed)
    window._preview_cache.clear()
    window._update_curves()
    _wait_until(app, lambda: window._preview_thread is None)
    assert calls
    assert all(thread_id != gui_thread for thread_id in calls)
    previous_calls = len(calls)
    cursor = window.project.cursors[0]
    window._sync_cursor(cursor.id, 1.25)
    app.processEvents()
    assert len(calls) == previous_calls


def test_background_job_result_is_delivered_on_gui_thread(window, app):
    import threading
    gui_thread = threading.get_ident()
    observations = []

    def work(progress, token):
        assert threading.get_ident() != gui_thread
        progress(0.5, "Working")
        token.check()
        return 42

    def finished(result):
        observations.append((result, threading.get_ident()))

    window._run_task("Test", work, finished)
    _wait_until(app, lambda: window._worker is None)
    assert observations == [(42, gui_thread)]
    assert not window.progress_bar.isVisible()


def test_export_subrange_requires_explicit_segment_choice(app, store, monkeypatch):
    from vehiclelog.gui import ExportDialog
    from vehiclelog.models import Project
    segment = Segment("Urban", 0, 5)
    dialog = ExportDialog(store, Project(selected_signals=["voltage"], segments=[segment]))
    notifications = []
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", lambda *args: notifications.append(args[1]))
    try:
        dialog.whole_check.setChecked(False)
        dialog.accept()
        assert dialog.result() != QtWidgets.QDialog.DialogCode.Accepted
        assert "Chưa chọn giai đoạn" in notifications
        dialog.segment_list.item(0).setCheckState(QtCore.Qt.CheckState.Checked)
        dialog.accept()
        assert dialog.result() == QtWidgets.QDialog.DialogCode.Accepted
        assert dialog.selected_segments() == [segment]
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()


def test_formula_preview_bounds_memory_preserves_peaks_and_gap(monkeypatch):
    from vehiclelog import formulas
    from vehiclelog.gui import trace_preview
    segment = Segment("Long stage", 0, 100)
    formula = Formula("Power", "x", {"x": "voltage"}, segment_ids=[segment.id])
    times = np.linspace(0, 100, 100_001)
    values = np.ones(len(times))
    values[100] = 1000
    values[90_000] = -500
    values[50_000:51_000] = np.nan

    def chunks(*args, **kwargs):
        for start in range(0, len(times), 10_000):
            yield times[start:start+10_000], values[start:start+10_000]

    monkeypatch.setattr(formulas, "iter_evaluate_trace", chunks)
    display_times, display_values = trace_preview(None, formula, segment)
    assert len(display_times) <= 4000
    assert np.all(display_times[1:] >= display_times[:-1])
    assert np.nanmax(display_values) == 1000
    assert np.nanmin(display_values) == -500
    assert np.any(np.isnan(display_values))


def test_pair_selector_shows_both_values_delta_and_elapsed_time(window):
    window.add_cursor(1)
    window.add_cursor(3)
    window.pair_combo.setCurrentIndex(1)  # M2=1 s → M3=3 s.
    assert window.value_table.horizontalHeaderItem(1).text() == 'Y(M2)'
    assert window.value_table.horizontalHeaderItem(2).text() == 'Y(M3)'
    rows = {r.key: r for r in window.last_measurements}
    assert (rows['current'].start_value, rows['current'].end_value, rows['current'].delta) == (20, -5, -25)
    assert 'Δt = 2.000000 s' in window.delta_label.text()
    window.cursor_table.selectRow(3)  # M4 uses previous pair M3→M4.
    assert window.pair_combo.currentIndex() == 2


def test_marker_cannot_cross_neighbor_and_duplicate_not_added(window):
    middle = window.add_cursor(2)
    assert window.add_cursor(2) is None
    assert len(window.project.cursors) == 3
    window._sync_cursor(middle.id, 9)
    assert 0 < middle.time < 5
    assert all(s.end > s.start for s in window.project.segments)
    window.cursor_table.selectRow(1)
    window.delete_cursor()
    assert len(window.project.cursors) == 2
    assert [(s.start, s.end) for s in window.project.segments] == [(0, 5)]


def test_adjacent_stage_energy_uses_updated_bounds_and_explicit_assignment(window):
    from vehiclelog.formulas import evaluate_all
    middle = window.add_cursor(2)
    second = window.project.segments[1]
    formula = Formula('Energy', 'integral(U * I) / 3600000',
                      {'U': 'voltage', 'I': 'current'}, 'kWh', [second.id], max_gap=1)
    window.project.formulas = [formula]
    result = evaluate_all(window.store, [formula], window.project.segments)
    assert len(result) == 1 and result[0].segment_id == second.id
    assert result[0].value == pytest.approx(2000 / 3600000)
    window._sync_cursor(middle.id, 3)
    result = evaluate_all(window.store, [formula], window.project.segments)
    assert len(result) == 1 and result[0].value == pytest.approx(-2000 / 3600000)


def test_axis_fit_buttons_restore_full_time_and_visible_y(window, app):
    plot = window.plots['voltage']
    plot.setXRange(1, 2, padding=0)
    plot.setYRange(-1, 1, padding=0)
    window.fit_x_button.click()
    app.processEvents()
    assert plot.viewRange()[0] == pytest.approx([0, 5])
    window.fit_y_button.click()
    app.processEvents()
    low, high = plot.viewRange()[1]
    assert low < 400 < high
    window.fit_all_button.click()
    app.processEvents()
    assert plot.viewRange()[0] == pytest.approx([0, 5])


def test_all_selected_plots_fit_without_scrolling_after_resize(window, app, tmp_path):
    with StoreWriter(tmp_path / 'many-signals', {'duration': 5}) as writer:
        for i in range(15):
            writer.add_signal(SignalInfo(str(i), f'Signal {i}', 'V'))
            writer.append(str(i), np.arange(6), np.arange(6) * (i + 1))
        large_selection = writer.finish()
    window.set_store(large_selection)
    window.project.selected_signals = list(large_selection.signals)
    window._rebuild_plots()
    window.show()
    for size in ((1500, 980), (1100, 750), (1700, 1000)):
        window.resize(*size)
        for _ in range(6):
            app.processEvents()
        window.graphics.fit_rows()
        app.processEvents()
        viewport = window.graphics.viewport().rect().adjusted(-2, -2, 2, 2)
        assert len(window.plots) == 15
        assert not window.graphics.verticalScrollBar().isVisible()
        assert not window.graphics.horizontalScrollBar().isVisible()
        for key, plot in window.plots.items():
            bounds = window.graphics.mapFromScene(plot.sceneBoundingRect()).boundingRect()
            assert bounds.height() > 0 and viewport.contains(bounds), (size, key, bounds, viewport)
            times, values = window.curves[key].getData()
            assert len(times) == 6


def test_repeated_jobs_deliver_widget_progress_on_gui_thread(window, app, monkeypatch):
    import threading
    gui_thread = threading.get_ident()
    deliveries = []
    set_text = window.status_label.setText
    set_value = window.progress_bar.setValue

    def observed_text(text):
        deliveries.append(threading.get_ident())
        if threading.get_ident() == gui_thread:
            set_text(text)

    def observed_value(value):
        deliveries.append(threading.get_ident())
        if threading.get_ident() == gui_thread:
            set_value(value)

    monkeypatch.setattr(window.status_label, 'setText', observed_text)
    monkeypatch.setattr(window.progress_bar, 'setValue', observed_value)
    results = []
    for job in range(3):
        def work(progress, token, value=job):
            for i in range(20):
                progress(i / 20, f'Job {value} progress {i}')
                token.check()
            return value
        window._run_task('Repeated jobs', work, results.append)
        _wait_until(app, lambda: window._worker is None)
    assert results == [0, 1, 2]
    assert len(deliveries) >= 120
    assert all(thread_id == gui_thread for thread_id in deliveries)


def test_hover_reads_native_sample_and_keeps_stages_unchanged(window, app):
    import copy
    window.show()
    for key in ("current", "voltage"):
        _item_with_key(window.signal_list, key).setCheckState(QtCore.Qt.CheckState.Checked)
    app.processEvents()
    window.reset_view()
    app.processEvents()
    before = copy.deepcopy(window.project)
    dirty = window._dirty
    # Deliberately remove preview data: hover must still use original samples.
    window.curves["current"].setData([], [])
    view = window.plots["current"].getViewBox()
    y = sum(view.viewRange()[1]) / 2
    window._hover_moved((view.mapViewToScene(QtCore.QPointF(1.5, y)),))
    assert "BatteryCurrent" in window.hover_label.text()
    assert "Y = 20 A" in window.hover_label.text()
    assert "mẫu tại 1.000000 s" in window.hover_label.text()
    assert window._hover_items["current"][1].isVisible()
    assert not window._hover_items["voltage"][1].isVisible()
    assert all(line.isVisible() for line, dot in window._hover_items.values())
    assert window.project == before
    assert window._dirty == dirty
    view = window.plots["voltage"].getViewBox()
    window._hover_moved((view.mapViewToScene(QtCore.QPointF(2, 400)),))
    assert "Y = 400 V" in window.hover_label.text()
    assert not window._hover_items["current"][1].isVisible()


def test_hover_disable_leave_and_rebuild_clear_readout(window, app):
    window.show()
    _item_with_key(window.signal_list, "current").setCheckState(QtCore.Qt.CheckState.Checked)
    app.processEvents()
    view = window.plots["current"].getViewBox()
    position = view.mapViewToScene(QtCore.QPointF(2, 10))
    window._hover_moved((position,))
    assert window._hover_items["current"][1].isVisible()
    app.sendEvent(window.graphics.viewport(), QtCore.QEvent(QtCore.QEvent.Type.Leave))
    assert not window._hover_items["current"][1].isVisible()
    window.hover_check.setChecked(False)
    window._hover_moved((position,))
    assert not window._hover_items["current"][0].isVisible()
    window.hover_check.setChecked(True)
    window._rebuild_plots()
    assert len(window._hover_items) == len(window.plots)
    assert all(not dot.isVisible() for line, dot in window._hover_items.values())
    window._hover_moved((QtCore.QPointF(-100, -100),))
    assert "Di chuột" in window.hover_label.text()


def test_hover_outside_signal_bounds_has_no_stale_value(window, app):
    window.show()
    _item_with_key(window.signal_list, "current").setCheckState(QtCore.Qt.CheckState.Checked)
    app.processEvents()
    plot = window.plots["current"]
    plot.setXRange(-2, 7, padding=0)
    app.processEvents()
    view = plot.getViewBox()
    window._hover_moved((view.mapViewToScene(QtCore.QPointF(-1, 10)),))
    assert "không có mẫu hợp lệ" in window.hover_label.text()
    assert not window._hover_items["current"][1].isVisible()
