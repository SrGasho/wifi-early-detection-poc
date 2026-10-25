import numpy as np
import pandas as pd
import pytest

from src import evaluate as EV


def _episodes(rows):
    cols = ["episode_id", "capture_id", "attack_type", "t_start", "t_end", "n_frames", "start_complete"]
    return pd.DataFrame(rows, columns=cols)


def _preds(t_ends, y_pred, capture="cap_a"):
    return pd.DataFrame({"capture_id": capture, "window_id": range(len(t_ends)), "t_end": t_ends,
                         "score": y_pred, "y_pred": y_pred})


W = 2.0


def test_latency_and_frames_before_alert_by_hand():
    ep = _episodes([["e0", "cap_a", "deauth", 10.0, 20.0, 11, True]])
    preds = _preds([10.5, 11.0, 11.5, 12.0], [0, 0, 1, 1])
    ts = {"cap_a": np.arange(10.0, 21.0, 1.0)}  # 11 tramas objetivo
    res = EV.episode_results(ep, preds, ts, W)[0]
    assert res["detected"] and res["t_first_alert"] == 11.5
    assert res["latency_seconds"] == pytest.approx(1.5)
    assert res["target_frames_before_alert"] == 2  # tramas en 10 y 11


def test_latency_not_available_without_complete_start():
    ep = _episodes([["e0", "cap_a", "deauth", 10.0, 20.0, 11, False]])
    preds = _preds([12.0], [1])
    res = EV.episode_results(ep, preds, {"cap_a": np.arange(10.0, 21.0)}, W)
    assert res[0]["latency_seconds"] is None
    assert EV.latency_summary(res) == EV.NOT_AVAILABLE


def test_single_episode_reports_individual_value():
    res = [{"start_complete": True, "latency_seconds": 0.5, "detected": True}]
    summary = EV.latency_summary(res)
    assert summary["value_seconds"] == 0.5 and "mean_seconds" not in summary


def test_several_episodes_report_mean_and_median():
    res = [{"start_complete": True, "latency_seconds": v, "detected": True} for v in (0.5, 1.0, 3.0)]
    summary = EV.latency_summary(res)
    assert summary["mean_seconds"] == pytest.approx(1.5) and summary["median_seconds"] == 1.0


def test_false_alerts_and_rate_by_hand():
    ep = _episodes([["e0", "cap_a", "deauth", 1000.0, 1100.0, 10, True]])
    alerts = [{"alert_id": "a0", "capture_id": "cap_a", "t_alert": 1001.0, "t_last": 1050.0},
              {"alert_id": "a1", "capture_id": "cap_a", "t_alert": 2000.0, "t_last": 2000.0}]
    matched = EV.match_alerts(alerts, ep, W)
    assert [m["is_false_alert"] for m in matched] == [False, True]
    assert matched[0]["matched_episode_id"] == "e0" and matched[0]["attack_type_ref"] == "deauth"
    ev = pd.DataFrame({"capture_id": "cap_a", "t_end": [W, 3600.0 + 100.0]})
    hours = EV.normal_hours(ev, ep, W)
    assert hours == pytest.approx(1.0)  # 3700 s de span menos 100 s de episodio
    metrics = EV.episode_metrics([], matched, hours, ["deauth"])
    assert metrics["false_alerts_per_hour"] == pytest.approx(1.0)


def test_alert_touching_episode_through_window_is_not_false():
    ep = _episodes([["e0", "cap_a", "deauth", 10.0, 20.0, 10, True]])
    alerts = [{"alert_id": "a0", "capture_id": "cap_a", "t_alert": 21.5, "t_last": 21.5}]
    assert not EV.match_alerts(alerts, ep, W)[0]["is_false_alert"]  # ventana [19.5, 21.5)


def test_window_metrics_by_hand():
    m = EV.window_metrics(np.array([1, 1, 0, 0, 0]), np.array([1, 0, 1, 0, 0]))
    assert (m["tp"], m["fp"], m["tn"], m["fn"]) == (1, 1, 2, 1)
    assert m["precision"] == 0.5 and m["recall"] == 0.5 and m["f1"] == 0.5
    assert m["fpr"] == pytest.approx(1 / 3)


def test_type_metrics_not_available_when_type_absent():
    ev = pd.DataFrame({"y": [0, 1], "y_pred": [0, 1], "ref_deauth": [False, True], "ref_disas": [False, False]})
    out = EV.window_metrics_by_type(ev, ["deauth", "disas"])
    assert out["disas"] == EV.NOT_AVAILABLE and out["deauth"]["recall"] == 1.0
