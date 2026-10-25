import pandas as pd

from src.alerts import ALERT_FIELDS, merge_alerts


def _preds(rows):
    return pd.DataFrame(rows, columns=["capture_id", "window_id", "t_end", "score", "y_pred"])


def test_merge_with_max_gap():
    preds = _preds([
        ("cap_a", 1, 1.0, 0.9, 1), ("cap_a", 2, 1.5, 0.8, 1), ("cap_a", 3, 2.0, 0.1, 0),
        ("cap_a", 4, 2.5, 0.7, 1), ("cap_a", 5, 10.0, 0.95, 1), ("cap_b", 1, 1.0, 0.6, 1),
    ])
    alerts = merge_alerts(preds, max_gap=0.5)
    a = [x for x in alerts if x["capture_id"] == "cap_a"]
    assert [(x["t_alert"], x["t_last"], x["n_windows"]) for x in a] == [(1.0, 1.5, 2), (2.5, 2.5, 1), (10.0, 10.0, 1)]
    merged = merge_alerts(preds, max_gap=1.0)
    a = [x for x in merged if x["capture_id"] == "cap_a"]
    assert [(x["t_alert"], x["t_last"], x["n_windows"]) for x in a] == [(1.0, 2.5, 3), (10.0, 10.0, 1)]
    assert a[0]["max_score"] == 0.9


def test_alerts_do_not_declare_attack_type():
    preds = _preds([("cap_a", 1, 1.0, 0.9, 1)])
    alert = merge_alerts(preds, 0.5)[0]
    assert set(alert) == set(ALERT_FIELDS)
    assert not any("attack" in k or "type" in k for k in alert)


def test_no_positive_windows_no_alerts():
    assert merge_alerts(_preds([("cap_a", 1, 1.0, 0.1, 0)]), 0.5) == []
