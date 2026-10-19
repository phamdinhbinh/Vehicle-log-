from datetime import datetime, timezone

import can
import cantools
import numpy as np
import pytest
from asammdf import MDF, Signal

from vehiclelog.demo import (
    create_demo, DEMO_START_TIME, DEMO_EXPECTED_NET_KWH,
    DEMO_EXPECTED_DISTANCE_KM, DEMO_DBC,
)
from vehiclelog.importers import import_log
from vehiclelog.models import CancellationToken, CancelledError


def named(store, name, channel=None):
    return next(key for key, info in store.signals.items()
                if info.name == name and (channel is None or info.channel == str(channel)))


def test_real_demo_blf_decoding_regeneration_energy_and_cache(tmp_path):
    files = create_demo(tmp_path / "samples")
    store = import_log(files["blf"], {1: files["dbc"]}, tmp_path / "cache")
    t, voltage = store.read(named(store, "PackVoltage"))
    _, current = store.read(named(store, "PackCurrent"))
    _, speed = store.read(named(store, "VehicleSpeed"))
    assert len(t) == 1201
    assert t[0] == 0
    assert t[-1] == pytest.approx(120)
    assert voltage.tolist() == [400.0] * 1201
    assert current[400] == -20
    assert current[800] == 30
    # Independent zero-order-hold reference; regenerative energy has negative sign.
    assert np.sum(voltage[:-1] * current[:-1] * np.diff(t)) / 3_600_000 == pytest.approx(DEMO_EXPECTED_NET_KWH)
    assert np.sum(speed[:-1] * np.diff(t)) / 3600 == pytest.approx(DEMO_EXPECTED_DISTANCE_KM)
    assert store.metadata["start_time"] == DEMO_START_TIME
    assert store.metadata["frame_stats"]["decoded_frames"] == 2402
    assert len(store.metadata["frame_preview"]) == 500
    assert store.metadata["frame_preview"][0]["channel"] == 1
    reopened = import_log(files["blf"], {"1": str(files["dbc"])}, tmp_path / "cache")
    assert reopened.path == store.path
    refreshed = import_log(files["blf"], {1: files["dbc"]}, tmp_path / "cache", force=True)
    assert refreshed.path != store.path
    assert store.path.exists()


def test_channel_mapping_is_one_based_and_decode_failures_are_visible(tmp_path):
    dbc = tmp_path / "vehicle.dbc"
    dbc.write_text(DEMO_DBC)
    db = cantools.database.load_file(dbc)
    frame_data = db.get_message_by_name("Battery").encode({"PackVoltage": 420, "PackCurrent": -15})
    blf = tmp_path / "channels.blf"
    with can.BLFWriter(blf) as writer:
        for channel in (0, 1):
            writer.on_message_received(can.Message(timestamp=DEMO_START_TIME, channel=channel,
                arbitration_id=256, is_extended_id=False, data=frame_data))
        writer.on_message_received(can.Message(timestamp=DEMO_START_TIME + 1, channel=1,
            arbitration_id=999, is_extended_id=False, data=b"\0" * 8))
        writer.on_message_received(can.Message(timestamp=DEMO_START_TIME + 2, channel=1,
            arbitration_id=256, is_extended_id=False, data=b"\0"))
    store = import_log(blf, {2: dbc}, tmp_path / "cache")
    assert {info.channel for info in store.signals.values()} == {"2"}
    _, values = store.read(named(store, "PackCurrent", 2))
    assert values.tolist() == [-15]
    stats = store.metadata["frame_stats"]
    assert stats["frames"] == 4
    assert stats["decoded_frames"] == 1
    assert stats["unmapped_channel_frames"] == 1
    assert stats["unknown_frames"] == 1
    assert stats["decode_errors"] == 1
    assert store.metadata["unknown_messages"] == {"CAN2/0x3E7": 1}
    assert any("CAN 1" in warning for warning in store.metadata["warnings"])
    with pytest.raises(ValueError, match="bắt đầu từ 1"):
        import_log(blf, {0: dbc}, tmp_path / "invalid")


def test_dbc_contents_invalidate_cache(tmp_path):
    files = create_demo(tmp_path / "samples")
    cache = tmp_path / "cache"
    old = import_log(files["blf"], {1: files["dbc"]}, cache)
    files["dbc"].write_text(files["dbc"].read_text().replace("(0.1,0) [0|6553.5]", "(0.2,0) [0|6553.5]"))
    new = import_log(files["blf"], {1: files["dbc"]}, cache)
    assert new.path != old.path
    _, values = new.read(named(new, "PackVoltage"))
    assert values[0] == 800


def test_multiplexed_motorola_signal_and_numeric_choices(tmp_path, monkeypatch):
    from vehiclelog.readers import blf as importer_module
    monkeypatch.setattr(importer_module, "BLF_BATCH_FRAMES", 2)
    dbc = tmp_path / "multiplex.dbc"
    dbc.write_text('''VERSION ""
NS_ :
BS_:
BU_: ECU
BO_ 512 Multiplexed: 8 ECU
 SG_ Mode M : 0|8@1+ (1,0) [0|255] "" ECU
 SG_ BigEndian m1 : 15|16@0- (0.5,-10) [-16000|16000] "V" ECU
 SG_ Alternate m2 : 8|16@1+ (1,0) [0|65535] "A" ECU
VAL_ 512 Mode 1 "active" 2 "alternate";
''')
    message = cantools.database.load_file(dbc).get_message_by_name("Multiplexed")
    blf = tmp_path / "multiplex.blf"
    values = [{"Mode": 1, "BigEndian": -12.5}, {"Mode": 2, "Alternate": 321},
              {"Mode": 1, "BigEndian": 14.0}]
    with can.BLFWriter(blf) as writer:
        for index, signals in enumerate(values):
            writer.on_message_received(can.Message(timestamp=DEMO_START_TIME + index,
                channel=0, arbitration_id=512, is_extended_id=False,
                data=message.encode(signals)))
    store = import_log(blf, {1: dbc}, tmp_path / "cache")
    times, physical = store.read(named(store, "BigEndian"))
    np.testing.assert_array_equal(times, [0, 2])
    np.testing.assert_array_equal(physical, [-12.5, 14])
    times, physical = store.read(named(store, "Alternate"))
    np.testing.assert_array_equal(times, [1])
    np.testing.assert_array_equal(physical, [321])
    _, numeric_modes = store.read(named(store, "Mode"))
    np.testing.assert_array_equal(numeric_modes, [1, 2, 1])
    assert store.signals[named(store, "Mode")].choices["1"] == "active"


def test_mf4_preserves_physical_scaling_timestamps_and_invalidation(tmp_path, monkeypatch):
    from vehiclelog.readers import mf4 as importer_module
    monkeypatch.setattr(importer_module, "MF4_BATCH_SAMPLES", 2)
    source = tmp_path / "invalid.mf4"
    times = np.array([0.0, 0.1, 0.3, 0.8, 1.0])
    with MDF(version="4.10") as mdf:
        mdf.header.start_time = datetime.fromtimestamp(DEMO_START_TIME, timezone.utc)
        mdf.append(Signal(np.array([1, 2, 3, 4, 5], dtype=np.int16), times,
            name="Voltage", unit="V",
            conversion={"a": 2.0, "b": 1.0},
            invalidation_bits=np.array([False, True, False, False, True])))
        mdf.append(Signal(np.array([b"text"]), np.array([0.0]), name="Text", encoding="utf-8"))
        mdf.save(source, overwrite=True)
    store = import_log(source, cache_root=tmp_path / "cache")
    actual_times, actual_values = store.read(named(store, "Voltage"))
    np.testing.assert_array_equal(actual_times, times)
    np.testing.assert_allclose(actual_values, [3, np.nan, 7, 9, np.nan], equal_nan=True)
    assert store.metadata["start_time"] == DEMO_START_TIME
    assert any("Text" in item for item in store.metadata["skipped_channels"])
    assert len(store.signals) == 1


def test_mf4_demo_matches_blf_numeric_signals(tmp_path):
    files = create_demo(tmp_path / "samples")
    cache = tmp_path / "cache"
    blf = import_log(files["blf"], {1: files["dbc"]}, cache)
    mf4 = import_log(files["mf4"], cache_root=cache)
    for name in ("PackVoltage", "PackCurrent", "VehicleSpeed"):
        bt, bv = blf.read(named(blf, name))
        mt, mv = mf4.read(named(mf4, name))
        np.testing.assert_allclose(bt, mt, atol=2e-7)
        np.testing.assert_array_equal(bv, mv)


def test_cancellation_removes_partial_cache(tmp_path, monkeypatch):
    from vehiclelog.readers import blf as importer_module
    monkeypatch.setattr(importer_module, "BLF_BATCH_FRAMES", 25)
    files = create_demo(tmp_path / "samples")
    token = CancellationToken()
    def progress(fraction, message):
        if fraction > 0:
            token.cancel()
    cache = tmp_path / "cache"
    with pytest.raises(CancelledError):
        import_log(files["blf"], {1: files["dbc"]}, cache, progress, token)
    assert not list(cache.iterdir())


@pytest.mark.parametrize("changed_file", ["blf", "dbc"])
def test_changing_input_during_import_does_not_publish_cache(tmp_path, monkeypatch, changed_file):
    import os
    from vehiclelog.readers import blf as importer_module
    monkeypatch.setattr(importer_module, "BLF_BATCH_FRAMES", 25)
    files = create_demo(tmp_path / "samples")
    changed = False
    def progress(fraction, message):
        nonlocal changed
        if fraction > 0 and not changed:
            changed = True
            path = files[changed_file]
            if changed_file == "dbc":
                path.write_text(path.read_text() + "\n")
            else:
                stat = path.stat()
                os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
    cache = tmp_path / "cache"
    with pytest.raises(ValueError, match="đã thay đổi"):
        import_log(files["blf"], {1: files["dbc"]}, cache, progress=progress)
    assert changed
    assert not list(cache.iterdir())


def test_mf4_large_unsigned_integer_warns_once_across_chunks(tmp_path, monkeypatch):
    from vehiclelog.readers import mf4 as importer_module
    monkeypatch.setattr(importer_module, "MF4_BATCH_SAMPLES", 1)
    source = tmp_path / "counter.mf4"
    original = np.array([2**63 + 1, 2**63 + 3, 2**63 + 5], dtype=np.uint64)
    with MDF(version="4.10") as mdf:
        mdf.append(Signal(original, np.array([0.0, 1.0, 2.0]), name="Counter64"))
        mdf.save(source, overwrite=True)
    store = import_log(source, cache_root=tmp_path / "cache")
    key = named(store, "Counter64")
    _, converted = store.read(key)
    assert int(converted[0]) != int(original[0])  # Real precision loss is observable.
    assert store.metadata["precision_loss_signals"] == [key]
    assert len([w for w in store.metadata["warnings"] if "2**53" in w]) == 1
    assert store.metadata["numeric_storage"] == "float64"


def test_blf_large_dbc_integer_warns_once(tmp_path, monkeypatch):
    from vehiclelog.readers import blf as importer_module
    monkeypatch.setattr(importer_module, "BLF_BATCH_FRAMES", 1)
    dbc = tmp_path / "counter.dbc"
    dbc.write_text('''VERSION ""
NS_ :
BS_:
BU_: ECU
BO_ 512 Counters: 8 ECU
 SG_ Counter64 : 0|64@1+ (1,0) [0|18446744073709551615] "" ECU
''')
    message = cantools.database.load_file(dbc).get_message_by_name("Counters")
    blf = tmp_path / "counter.blf"
    with can.BLFWriter(blf) as writer:
        for index in range(3):
            writer.on_message_received(can.Message(timestamp=DEMO_START_TIME + index,
                channel=0, arbitration_id=512, is_extended_id=False,
                data=message.encode({"Counter64": 2**63 + 1 + index})))
    store = import_log(blf, {1: dbc}, tmp_path / "cache")
    key = named(store, "Counter64")
    _, converted = store.read(key)
    assert int(converted[0]) != 2**63 + 1
    assert store.metadata["precision_loss_signals"] == [key]
    assert len([w for w in store.metadata["warnings"] if "2**53" in w]) == 1
