import pytest

from src import config as C
from src import evaluate, experiment as E, predict, train


def test_test_split_requires_final(pipeline):
    cfg = C.load_experiment(pipeline["rf"])
    with pytest.raises(E.FinalRunError):
        E.guard_split_access(cfg, "test", final=False)
    with pytest.raises(E.FinalRunError):
        E.guard_split_access(cfg, "val", final=True)


def test_sensitivity_never_reaches_test(pipeline):
    cfg = C.load_experiment(pipeline["sens"])
    with pytest.raises(E.FinalRunError):
        E.guard_split_access(cfg, "test", final=True)


def test_final_run_cannot_be_repeated(pipeline):
    cfg = C.load_experiment(pipeline["rf"])
    train.run(cfg)
    predict.run(cfg, "test", final=True, check_git=False)
    with pytest.raises(E.FinalRunError):
        predict.run(cfg, "test", final=True, check_git=False)


def test_experiment_id_cannot_be_reused(pipeline):
    cfg = C.load_experiment(pipeline["rf"])
    train.run(cfg)
    with pytest.raises(E.FinalRunError):
        train.run(cfg)


def test_full_validation_flow_and_run_records(pipeline):
    from src import alerts

    cfg = C.load_experiment(pipeline["rf"])
    exp_id = train.run(cfg)
    predict.run(cfg, "val", final=False)
    alerts.run(cfg, "val", final=False)
    res = evaluate.run(cfg, "val", final=False, figures=True)
    assert res["window"]["global"]["f1"] is not None
    run = E.read_json(E.results_dir(cfg, exp_id) / "run_evaluate_val.json")
    for key in ("python_version", "platform", "library_versions", "requirements_sha256", "split_sha256", "seed"):
        assert key in run
    assert (E.results_dir(cfg, exp_id) / "figures").exists()


def test_placeholders_are_rejected():
    with pytest.raises(C.ConfigError):
        C.require({"window": {"W_seconds": "<Gate D>"}}, "window.W_seconds")
