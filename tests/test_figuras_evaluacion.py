import json

import numpy as np
import pandas as pd
import pytest

from scripts import figuras_evaluacion as F


def _make_results(root, split="test"):
    res = root / "20260101-0000-demo"
    res.mkdir(parents=True)
    n = 20
    ev = pd.DataFrame({
        "capture_id": "cap_b",
        "window_id": range(n),
        "t_end": np.arange(n, dtype=float) + 100.0,
        "score": [0.0] * 10 + [0.9] * 10,
        "y_pred": [0] * 10 + [1] * 10,
        "y": [0] * 10 + [1] * 10,
    })
    ev.to_parquet(res / f"eval_windows_{split}.parquet", index=False)
    episodes = [{"episode_id": "e0", "capture_id": "cap_b", "t_start": 110.0, "t_end": 119.0}]
    (res / f"metrics_episode_{split}.json").write_text(json.dumps({"episodes": episodes}), encoding="utf-8")
    return res


def _snapshot(path):
    return {str(p.relative_to(path)): p.stat().st_size for p in sorted(path.rglob("*")) if p.is_file()}


def test_builds_pr_and_timeline_pngs(tmp_path):
    res = _make_results(tmp_path / "results")
    out = tmp_path / "figs"
    paths = F.build_figures(res, "test", out)
    names = {p.name for p in paths}
    assert names == {"pr_test.png", "timeline_cap_b_test.png"}
    assert all(p.exists() and p.stat().st_size > 0 for p in paths)


def test_relativize_shifts_each_capture_to_start_at_zero():
    ev = pd.DataFrame({"capture_id": ["a", "a", "b"], "t_end": [1000.0, 1010.0, 5000.0]})
    eps = pd.DataFrame({"capture_id": ["a", "b"], "t_start": [1004.0, 5002.0], "t_end": [1008.0, 5003.0]})
    ev2, eps2 = F.relativize(ev, eps)
    assert ev2["t_end"].tolist() == [0.0, 10.0, 0.0]
    assert eps2["t_start"].tolist() == [4.0, 2.0] and eps2["t_end"].tolist() == [8.0, 3.0]
    assert ev["t_end"].tolist() == [1000.0, 1010.0, 5000.0]  # la entrada no se modifica


def test_does_not_touch_results_dir(tmp_path):
    res = _make_results(tmp_path / "results")
    before = _snapshot(res)
    F.build_figures(res, "test", tmp_path / "figs")
    assert _snapshot(res) == before
    assert not (res / "final").exists()


def test_missing_inputs_raise_clear_error(tmp_path):
    res = tmp_path / "results" / "vacio"
    res.mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match="eval_windows_test.parquet"):
        F.build_figures(res, "test", tmp_path / "figs")
