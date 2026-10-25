import numpy as np
import pandas as pd
import pytest

from src import config as C
from src import episodes
from tests.conftest import BURSTS, T


def test_group_bursts_with_known_T():
    ts = np.array([0.0, 0.1, 0.2, 10.0, 10.1, 30.0])
    assert episodes.group_bursts(ts, 5.0) == [(0, 2), (3, 4), (5, 5)]
    assert episodes.group_bursts(np.array([]), 5.0) == []


def test_exploratory_finds_all_bursts(frames_a):
    ep = episodes.exploratory_episodes(frames_a, "cap_a", T)
    assert len(ep) == len(BURSTS)
    assert set(ep["mode"]) == {"exploratory"}
    for (a, b), row in zip(BURSTS, ep.itertuples()):
        assert row.t_start == pytest.approx(a)
        assert row.t_end == pytest.approx(b - 0.02, abs=1e-6)
        assert row.attack_type == "deauth"


def test_start_complete_false_when_cut_truncates_episode():
    ts = np.arange(100.0, 120.0, 0.02)
    types = np.array(["deauth"] * len(ts), dtype=object)
    # La unidad empieza a mitad de la ráfaga: el episodio queda recortado.
    cut = episodes.definitive_episodes(ts, types, "cap_a", "test", 110.0, np.inf, T)
    assert len(cut) == 1 and not cut.iloc[0]["start_complete"]
    whole = episodes.definitive_episodes(ts, types, "cap_a", "test", 50.0, np.inf, T)
    assert len(whole) == 1 and whole.iloc[0]["start_complete"]


def test_definitive_episodes_per_split(pipeline):
    cfg = pipeline["cfg"]
    meta = episodes.load_definitive_meta(cfg)
    assert meta["T_seconds"] == T
    for split in ("train", "val", "test"):
        df = episodes.load_definitive(cfg, split, T)
        assert set(df["mode"]) == {"definitive"} and set(df["split"]) == {split}
    test = episodes.load_definitive(cfg, "test", T)
    assert test["start_complete"].all()
    assert meta["latency_measurable_in_test"] is True


def test_T_is_computed_only_from_training():
    train = [np.arange(0, 10, 0.02)]
    T_val, info = episodes.compute_T(train, {"T_method": "percentile_multiple", "T_percentile": 99,
                                             "T_multiplier": 50})
    assert T_val == pytest.approx(1.0, rel=1e-6)
    assert info["base_seconds"] == pytest.approx(0.02, rel=1e-6)


def test_load_definitive_rejects_mismatched_T(pipeline):
    with pytest.raises(episodes.EpisodeError):
        episodes.load_definitive(pipeline["cfg"], "test", T + 1)


def test_exploratory_file_is_never_definitive(pipeline):
    exp = pd.read_parquet(episodes.exploratory_path(pipeline["cfg"]["_data"]))
    assert set(exp["mode"]) == {"exploratory"}
    assert exp["split"].isna().all()


def test_placeholder_T_is_rejected():
    with pytest.raises(C.ConfigError):
        episodes.compute_T([np.arange(5.0)], {"T_method": "fixed", "T_seconds": "<Gate D>"})
