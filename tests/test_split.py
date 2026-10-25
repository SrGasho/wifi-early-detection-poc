import math

import pytest

from src import config as C
from src import feature_engineering as FE
from src import split_data
from tests.conftest import PURGE, W, make_capture


def _intervals(units):
    for split, items in units.items():
        for u in items:
            lo = -math.inf if u["t_from"] is None else u["t_from"]
            hi = math.inf if u["t_to"] is None else u["t_to"]
            yield split, u["capture_id"], lo, hi


def test_units_do_not_overlap_and_respect_purge(pipeline):
    units = pipeline["split"]["units"]
    by_cap = {}
    for split, cid, lo, hi in _intervals(units):
        by_cap.setdefault(cid, []).append((lo, hi, split))
    for spans in by_cap.values():
        spans.sort()
        for (lo1, hi1, _), (lo2, hi2, _) in zip(spans, spans[1:]):
            assert hi1 <= lo2
            assert lo2 - hi1 >= 2 * PURGE - 1e-9  # purga a cada lado del corte


def test_each_window_belongs_to_one_set(pipeline):
    win = pipeline["windows"]
    units = pipeline["split"]["units"]
    for row in win.sample(300, random_state=0).itertuples():
        hits = [s for s, cid, lo, hi in _intervals(units)
                if cid == row.capture_id and row.t_start >= lo and row.t_end <= hi]
        assert len(hits) <= 1
        assert (hits[0] if hits else "purged") == row.split


def test_every_set_has_both_classes(pipeline):
    presence = FE.check_class_presence(pipeline["windows"])
    for p in presence.values():
        assert p["normal"] and p["attack"]


def test_cuts_snap_to_silence(pipeline):
    assert "silencio" in pipeline["split"]["cut_placement"]


def test_purge_shorter_than_W_is_rejected(project):
    cfg = C.load_experiment(project["rf"])
    cfg["split"] = {**cfg["split"], "purge_seconds": W / 2}
    with pytest.raises(split_data.SplitError):
        split_data.make_split(cfg)


def test_purge_must_cover_sensitivity_W(project):
    cfg = C.load_experiment(project["rf"])
    cfg["split"] = {**cfg["split"], "max_W_seconds": PURGE * 2}
    with pytest.raises(split_data.SplitError):
        split_data.make_split(cfg)


def test_set_without_attack_is_rejected(project):
    from tests.conftest import _write_yaml  # noqa: PLC0415

    root = project["root"]
    make_capture("cap_c", "deauth", 12, 7, bursts=[]).assign(capture_id="cap_c").to_parquet(
        root / "data/interim/frames_cap_c.parquet", index=False)
    data = C.load_yaml(root / "configs/data.yaml")
    data.pop("_path")
    data["captures"].append({"id": "cap_c", "pattern": "c/*.csv"})
    _write_yaml(root / "configs/data.yaml", data)
    cfg = C.load_experiment(project["rf"])
    cfg["split"] = {"case": "A", "purge_seconds": PURGE,
                    "assignment": {"train": ["cap_a"], "val": ["cap_c"], "test": ["cap_b"]}}
    with pytest.raises(split_data.SplitError):
        split_data.make_split(cfg)


def test_case_c_accepts_single_type_in_test(project):
    cfg = C.load_experiment(project["rf"])
    cfg["split"] = {"case": "C", "purge_seconds": PURGE, "train_attack": "deauth", "test_attack": "disas",
                    "val_fraction": 0.2}
    split = split_data.make_split(cfg)
    test = split["class_presence"]["test"]
    assert test["disas"] and not test["deauth"]
    assert split["units"]["test"] == [{"capture_id": "cap_b", "t_from": None, "t_to": None}]
    assert split["label_aware"] is True
