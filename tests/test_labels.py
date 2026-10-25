import pandas as pd

from src import feature_engineering as FE
from tests.conftest import S, W, make_capture


def test_single_target_frame_makes_window_positive():
    df = make_capture("cap_a", "deauth", 12, 7, bursts=[], duration=20.0)
    idx = df.index[(df["ts"] > 10.0) & (df["fc_subtype"] == 8)][0]
    df.loc[idx, "is_target"] = True
    df.loc[idx, "attack_type"] = "deauth"
    t = df.loc[idx, "ts"]
    win = FE.capture_windows(df, "cap_a", W=W, S=S, reason_codes=[], types=["deauth"], units=None)
    contains = (win["t_start"] <= t) & (win["t_end"] > t)
    assert (win.loc[contains, "y"] == 1).all()
    assert (win.loc[contains, "n_target"] == 1).all()
    assert (win.loc[~contains, "y"] == 0).all()
    assert contains.sum() == int(W / S)  # la trama aparece en W/S ventanas
    assert win.loc[contains, "ref_deauth"].all()


def test_k_must_be_one(project):
    import pytest
    import yaml

    from src import config as C

    data = yaml.safe_load(project["rf"].read_text(encoding="utf-8"))
    data["window"]["k"] = 3
    project["rf"].write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(C.ConfigError):
        C.load_experiment(project["rf"])


def test_target_must_be_binary(project):
    import pytest
    import yaml

    from src import config as C

    data = yaml.safe_load(project["rf"].read_text(encoding="utf-8"))
    data["target"] = "multiclass"
    project["rf"].write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(C.ConfigError):
        C.load_experiment(project["rf"])
    _ = pd  # noqa
