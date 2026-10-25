import math

import numpy as np
import pandas as pd
import pytest

from src import feature_engineering as FE
from src.experiment import MetadataError
from src.predict import prepare_X
from tests.conftest import S, W

REFERENCE = {"y", "is_target", "attack_type", "label_raw", "episode_id", "split", "n_target"}


def test_feature_columns_never_include_reference(pipeline):
    cols = FE.resolve_feature_columns(pipeline["cfg"]["_features"], "allowed")
    assert not (set(cols) & REFERENCE)
    assert not any(c.startswith("ref_") for c in cols)


def test_reference_columns_are_rejected_in_features_yaml():
    with pytest.raises(Exception):
        FE.resolve_feature_columns({"allowed": ["n_disconn", "y"], "reason_codes": []}, "allowed")


def test_prepare_X_rejects_reference_columns():
    df = pd.DataFrame({"n_disconn": [1.0], "y": [1]})
    with pytest.raises(MetadataError):
        prepare_X(df, {"feature_columns": ["n_disconn", "y"], "imputation": {"n_disconn": 0, "y": 0}})


def test_features_do_not_depend_on_labels(frames_a):
    """Alterar las etiquetas no cambia ninguna característica."""
    shuffled = frames_a.copy()
    shuffled["is_target"] = ~shuffled["is_target"]
    shuffled["attack_type"] = "normal"
    shuffled["label_raw"] = "x"
    a = FE.capture_windows(frames_a, "cap_a", W=W, S=S, reason_codes=[7], types=["deauth"], units=None)
    b = FE.capture_windows(shuffled, "cap_a", W=W, S=S, reason_codes=[7], types=["deauth"], units=None)
    feats = [c for c in a.columns if c in FE.BASE_FEATURES or c.startswith("rc_")]
    pd.testing.assert_frame_equal(a[feats], b[feats])
    assert not a["y"].equals(b["y"])


def test_observable_arrays_exclude_reference(frames_a):
    arrays = FE.observable_arrays(frames_a)
    assert not (set(arrays) & REFERENCE)
    feats = FE.compute_window_features(FE.slice_arrays(arrays, 0, 10), math.nan, W=W, reason_codes=[])
    assert all(isinstance(v, float) for v in feats.values())
    _ = np
