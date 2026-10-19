"""Đối chiếu Y đầu/cuối và ΔY bằng dữ liệu gốc, gồm invalid và ngoài phạm vi."""
import numpy as np
import pytest

from vehiclelog.measurements import measure_between, sample_at
from vehiclelog.models import SignalInfo
from vehiclelog.store import StoreWriter


@pytest.fixture
def store(tmp_path):
    with StoreWriter(tmp_path / "store") as writer:
        writer.add_signal(SignalInfo("i", "Current", "A"))
        writer.append("i", [1, 2, 3, 4], [10, 20, np.nan, -5])
        return writer.finish()


def test_hold_samples_and_signed_difference(store):
    row = measure_between(store, ["i"], 1.5, 4)[0]
    assert (row.start_value, row.end_value, row.delta) == (10, -5, -15)
    assert row.start_age == .5 and row.end_age == 0
    assert row.name == "Current" and row.unit == "A"


def test_invalid_or_missing_endpoint_has_no_fabricated_delta(store):
    for start, end in ((0, 2), (1, 5), (1, 3.5)):
        row = measure_between(store, ["i"], start, end)[0]
        assert row.delta is None
    assert sample_at(store, "i", 3) == (None, None)
