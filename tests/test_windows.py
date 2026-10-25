import math

import numpy as np
import pandas as pd
import pytest

from src import feature_engineering as FE
from tests.conftest import S, W, make_capture


def _windows(frames, units=None):
    return FE.capture_windows(frames, "cap_a", W=W, S=S, reason_codes=[3, 7], types=["deauth", "disas"],
                              units=units)


def test_grid_is_complete_ordered_and_unique(frames_a):
    win = _windows(frames_a)
    g0, last = frames_a["ts"].iloc[0], frames_a["ts"].iloc[-1]
    assert win["t_end"].iloc[0] == pytest.approx(g0 + W)
    assert win["t_end"].iloc[-1] > last and win["t_end"].iloc[-1] - S <= last
    assert np.allclose(np.diff(win["t_end"]), S)
    assert win["window_id"].is_unique
    assert np.allclose(win["t_end"] - win["t_start"], W)


def test_window_uses_only_its_interval():
    """Una trama en t_end no pertenece a la ventana; una en t_end - W sí (R3)."""
    base = make_capture("cap_a", "deauth", 12, 7, bursts=[], duration=30.0)
    arrays = FE.observable_arrays(base)
    t_start, t_end = 10.0, 12.0
    lo, hi = np.searchsorted(arrays["ts"], [t_start, t_end], side="left")
    ref = FE.compute_window_features(FE.slice_arrays(arrays, lo, hi), math.nan, W=W, reason_codes=[7])
    extra = base.iloc[[0, 0]].copy()
    extra["ts"] = [t_end, t_start]
    extra["fc_subtype"] = pd.array([12, 12], dtype="Int16")
    mod = pd.concat([base, extra]).sort_values("ts", kind="mergesort").reset_index(drop=True)
    arr2 = FE.observable_arrays(mod)
    lo2, hi2 = np.searchsorted(arr2["ts"], [t_start, t_end], side="left")
    feats = FE.compute_window_features(FE.slice_arrays(arr2, lo2, hi2), math.nan, W=W, reason_codes=[7])
    assert feats["n_deauth"] == ref["n_deauth"] + 1  # solo la trama en t_start
    assert feats["n_frames_total"] == ref["n_frames_total"] + 1


def test_future_frames_do_not_change_past_windows(frames_a):
    win = _windows(frames_a)
    cut = 200.0
    truncated = frames_a[frames_a["ts"] < cut]
    win_t = _windows(truncated)
    feats = [c for c in win.columns if c in FE.BASE_FEATURES]
    past = win[win["t_end"] <= cut].set_index("window_id")[feats]
    past_t = win_t[win_t["t_end"] <= cut].set_index("window_id")[feats]
    pd.testing.assert_frame_equal(past, past_t.loc[past.index])


def test_empty_window_has_zero_counts_and_null_intervals():
    df = make_capture("cap_a", "deauth", 12, 7, bursts=[], duration=10.0)
    gap = pd.concat([df, df.iloc[[-1]].assign(ts=40.0)]).reset_index(drop=True)  # silencio de 30 s
    win = FE.capture_windows(gap, "cap_a", W=W, S=S, reason_codes=[7], types=["deauth"], units=None)
    empty = win[(win["t_start"] > 21) & (win["t_end"] < 38)]  # t = 20 tiene una desautenticación legítima
    assert len(empty) > 0
    assert (empty["n_frames_total"] == 0).all() and (empty["n_disconn"] == 0).all()
    assert (empty["rate_disconn"] == 0).all()
    assert empty["iat_disconn_mean"].isna().all() and empty["signal_std_disconn"].isna().all()
    assert (empty["y"] == 0).all()


def test_rc_counts_and_broadcast(frames_a):
    win = _windows(frames_a)
    row = win.iloc[(win["t_end"] - 60.0).abs().argmin()]  # dentro de la ráfaga [50, 70]
    assert row["n_deauth"] == row["rc_7"] > 0
    assert row["frac_broadcast_dst_disconn"] == 1.0
    assert row["rc_3"] == 0


def test_resolve_feature_columns_profiles():
    cfg = {"allowed": ["n_disconn", "n_deauth", "rc_counts"], "loao_exclude": ["n_deauth", "rc_counts"],
           "reason_codes": [7]}
    assert FE.resolve_feature_columns(cfg, "allowed") == ["n_disconn", "n_deauth", "rc_7", "rc_other"]
    assert FE.resolve_feature_columns(cfg, "loao") == ["n_disconn"]


def test_purge_shorter_than_W_is_rejected(pipeline):
    cfg = dict(pipeline["cfg"])
    cfg["window"] = {"W_seconds": 4.0, "S_seconds": 0.5, "k": 1}
    with pytest.raises(FE.SplitError):
        FE.build_windows(cfg)
