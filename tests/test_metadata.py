import pytest

from src import experiment as E
from src import predict


def _complete():
    meta = {f: None for f in E.REQUIRED_METADATA_FIELDS}
    meta.update({"feature_columns": ["n_disconn"], "imputation": {"n_disconn": 0.0},
                 "alerts": {"max_gap_seconds": 0.5}})
    return meta


def test_complete_metadata_is_valid():
    E.validate_metadata(_complete())


@pytest.mark.parametrize("field", E.REQUIRED_METADATA_FIELDS)
def test_each_missing_field_is_reported(field):
    meta = _complete()
    meta.pop(field)
    with pytest.raises(E.MetadataError, match=field):
        E.validate_metadata(meta)


def test_missing_max_gap_is_reported():
    meta = _complete()
    meta["alerts"] = {}
    with pytest.raises(E.MetadataError, match="max_gap_seconds"):
        E.validate_metadata(meta)


def test_save_refuses_incomplete_metadata(tmp_path):
    meta = _complete()
    meta.pop("threshold")
    with pytest.raises(E.MetadataError):
        E.save_metadata(tmp_path, meta)
    assert not (tmp_path / "metadata.json").exists()


def test_predict_fails_clearly_without_metadata(tmp_path):
    with pytest.raises(E.MetadataError, match="metadata.json"):
        predict.load_detector(tmp_path)


def test_trained_model_metadata_is_complete(pipeline):
    from src import config as C
    from src import train

    cfg = C.load_experiment(pipeline["rf"])
    exp_id = train.run(cfg)
    meta = E.load_metadata(E.model_dir(cfg, exp_id))
    assert meta["k"] == 1 and meta["target"] == "binary"
    assert meta["T_seconds"] == 5.0 and meta["alerts"]["max_gap_seconds"] == 0.5
    assert set(meta["grid_origins"]) == {"cap_a", "cap_b"}
    assert all(c in meta["imputation"] for c in meta["feature_columns"])
