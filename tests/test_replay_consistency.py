import math

import numpy as np

from src import baseline, predict, replay, train
from src import config as C
from src import experiment as E
from src import feature_engineering as FE
from tests.conftest import S, W


def test_streamed_features_equal_batch_features(frames_a):
    """La misma función, alimentada por un búfer que se desliza, da lo mismo que el lote (R8)."""
    batch = FE.capture_windows(frames_a, "cap_a", W=W, S=S, reason_codes=[3, 7], types=["deauth"], units=None)
    arrays = FE.observable_arrays(frames_a)
    ts = arrays["ts"]
    g0 = float(ts[0])
    from collections import deque

    buf, head, prev = deque(), 0, math.nan
    for row in batch.itertuples():
        t_start, t_end = FE.window_bounds(g0, row.window_id, S, W)
        while head < len(ts) and ts[head] < t_end:
            buf.append(head)
            head += 1
        while buf and ts[buf[0]] < t_start:
            buf.popleft()
        f = FE.compute_window_features(FE.take_arrays(arrays, list(buf)), prev, W=W, reason_codes=[3, 7])
        prev = f["n_disconn"]
        for name in ("n_frames_total", "n_disconn", "iat_disconn_mean", "delta_n_disconn", "seq_jump_max"):
            a, b = f[name], getattr(row, name)
            assert (math.isnan(a) and math.isnan(b)) or a == b, (name, row.window_id)


def test_replay_matches_batch_predictions(pipeline):
    cfg = C.load_experiment(pipeline["rf"])
    train.run(cfg)
    predict.run(cfg, "val", final=False)
    report = replay.run(cfg, "val", final=False)
    assert report["consistency_with_batch"]["valid"], report["consistency_with_batch"]
    assert report["end_to_end_seconds"]["mean"] > 0


def test_replay_matches_for_baseline(pipeline):
    cfg = C.load_experiment(pipeline["baseline"])
    baseline.run(cfg)
    predict.run(cfg, "val", final=False)
    report = replay.run(cfg, "val", final=False)
    assert report["consistency_with_batch"]["valid"]


def test_replay_detects_inconsistency(pipeline):
    cfg = C.load_experiment(pipeline["baseline"])
    exp_id = baseline.run(cfg)
    out = predict.run(cfg, "val", final=False)
    import pandas as pd

    preds = pd.read_parquet(out)
    preds.loc[preds.index[0], "score"] += 1.0
    preds.to_parquet(out, index=False)
    report = replay.run(cfg, "val", final=False)
    assert not report["consistency_with_batch"]["valid"]
    assert E.results_dir(cfg, exp_id).exists()
    _ = np
