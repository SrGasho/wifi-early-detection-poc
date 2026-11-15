import json

import numpy as np
import pandas as pd
import pytest

from scripts import figuras_evaluacion as F


def _make_results(root, split="test", y=None, final=True):
    res = root / "20260101-0000-demo"
    res.mkdir(parents=True)
    n = 20
    y = y if y is not None else [0] * 10 + [1] * 10
    ev = pd.DataFrame({
        "capture_id": "cap_b",
        "window_id": range(n),
        "t_end": np.arange(n, dtype=float) + 100.0,
        "score": [0.0] * 10 + [0.9] * 10,
        "y_pred": [0] * 10 + [1] * 10,
        "y": y,
    })
    ev.to_parquet(res / f"eval_windows_{split}.parquet", index=False)
    episodes = [{"episode_id": "e0", "capture_id": "cap_b", "t_start": 110.0, "t_end": 119.0}]
    (res / f"metrics_episode_{split}.json").write_text(json.dumps({"episodes": episodes}), encoding="utf-8")
    if final and split == "test":
        (res / "final").mkdir()
        (res / "final" / "evaluate.done").write_text("ok", encoding="utf-8")
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


def test_relativize_drops_episodes_of_captures_without_windows():
    ev = pd.DataFrame({"capture_id": ["a", "a"], "t_end": [1000.0, 1010.0]})
    eps = pd.DataFrame({"capture_id": ["a", "z"], "t_start": [1004.0, 9.0], "t_end": [1008.0, 10.0]})
    _, eps2 = F.relativize(ev, eps)
    assert eps2["capture_id"].tolist() == ["a"] and not eps2.isna().any().any()


def test_does_not_touch_results_dir(tmp_path):
    res = _make_results(tmp_path / "results")
    before = _snapshot(res)
    F.build_figures(res, "test", tmp_path / "figs")
    assert _snapshot(res) == before


def test_test_split_requires_registered_final_evaluation(tmp_path):
    res = _make_results(tmp_path / "results", final=False)
    with pytest.raises(FileNotFoundError, match="evaluate.done"):
        F.build_figures(res, "test", tmp_path / "figs")


def test_single_class_split_warns_that_pr_curve_is_skipped(tmp_path):
    res = _make_results(tmp_path / "results", split="val", y=[0] * 20)
    with pytest.warns(UserWarning, match="curva PR"):
        paths = F.build_figures(res, "val", tmp_path / "figs")
    assert {p.name for p in paths} == {"timeline_cap_b_val.png"}


def test_missing_inputs_raise_clear_error(tmp_path):
    res = tmp_path / "results" / "vacio"
    (res / "final").mkdir(parents=True)
    (res / "final" / "evaluate.done").write_text("ok", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="eval_windows_test.parquet"):
        F.build_figures(res, "test", tmp_path / "figs")


def _cfg(root, name="demo"):
    return {"name": name, "seed": 7, "_path": "demo.yaml", "paths": {"results": str(root)}}


def test_main_resolves_index_writes_figures_and_run_record(tmp_path, monkeypatch):
    root = tmp_path / "results"
    res = _make_results(root)
    (root / "_index").mkdir()
    (root / "_index" / "demo.json").write_text(json.dumps({"exp_id": res.name}), encoding="utf-8")
    monkeypatch.setattr(F.C, "load_experiment", lambda path: _cfg(root))
    before = _snapshot(res)
    out = tmp_path / "figs"
    F.main(["--exp", "demo.yaml", "--split", "test", "--out", str(out)])
    assert (out / "figures" / "pr_test.png").exists()
    run = json.loads((out / "run_figuras_test.json").read_text(encoding="utf-8"))
    assert run["exp_id"] == res.name and run["stage"] == "figuras" and run["split"] == "test"
    assert run["seed"] == 7 and "git_commit" in run
    assert set(run["source_sha256"]) == {"eval_windows_test.parquet", "metrics_episode_test.json"}
    assert _snapshot(res) == before  # el run_*.json va a la salida, no a results/


def test_main_exits_with_clear_message_when_experiment_has_no_index(tmp_path, monkeypatch):
    root = tmp_path / "results"
    root.mkdir()
    monkeypatch.setattr(F.C, "load_experiment", lambda path: _cfg(root))
    with pytest.raises(SystemExit) as exc:
        F.main(["--exp", "demo.yaml", "--split", "test", "--out", str(tmp_path / "figs")])
    assert "demo" in str(exc.value)
