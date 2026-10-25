"""Línea base: alerta si una característica de conteo supera un umbral ``θ`` (plan, sección 8.5).

``θ`` se elige en validación con máximo F1 por ventana; en empate gana el menor ``θ``.
Guarda ``model.joblib`` y ``metadata.json`` con el mismo contrato que Random Forest.
"""

from __future__ import annotations

import argparse

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_curve

from . import config as C
from . import experiment as E
from .detectors import ThresholdDetector
from .feature_engineering import windows_path
from .predict import fit_imputation, prepare_X, select_split


def best_threshold(y: np.ndarray, score: np.ndarray) -> tuple[float, float]:
    """Umbral de máximo F1 sobre ``score >= θ``. En empate gana el menor umbral."""
    y = np.asarray(y).astype(int)
    if y.sum() == 0 or y.sum() == len(y):
        raise ValueError("La validación debe tener ventanas de ambas clases para elegir el umbral.")
    precision, recall, thresholds = precision_recall_curve(y, score)
    p, r = precision[:-1], recall[:-1]
    f1 = np.divide(2 * p * r, p + r, out=np.zeros_like(p), where=(p + r) > 0)
    best = f1.max()
    idx = int(np.flatnonzero(np.isclose(f1, best))[0])  # umbrales en orden ascendente
    return float(thresholds[idx]), float(best)


def load_train_val(cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    windows = pd.read_parquet(windows_path(cfg))
    return select_split(windows, "train"), select_split(windows, "val")


def run(cfg: dict) -> str:
    started = E.now_iso()
    model_cfg = C.require(cfg, "model")
    if model_cfg.get("type") != "threshold":
        raise C.ConfigError("El experimento de línea base debe tener model.type: threshold.")
    feature = model_cfg.get("feature", "n_disconn")
    if feature not in ("n_disconn", "rate_disconn"):
        raise C.ConfigError("La línea base usa n_disconn o rate_disconn.")
    train, val = load_train_val(cfg)
    imputation = fit_imputation(train, [feature], "constant", 0.0)
    exp_id = E.create_exp_id(cfg)
    meta = E.base_metadata(cfg, exp_id)
    meta.update({"model_type": "threshold", "model_params": {"feature": feature},
                 "feature_profile": "baseline", "feature_columns": [feature],
                 "reason_codes": [], "imputation": imputation, "threshold": None})
    detector = ThresholdDetector(feature)
    theta, f1 = best_threshold(val["y"].to_numpy(), detector.score(prepare_X(val, meta)))
    meta["threshold"] = theta
    meta["selection"] = {"criterion": "max_f1_validation", "tie_break": "menor umbral", "val_f1": f1}
    out_dir = E.model_dir(cfg, exp_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    E.save_metadata(out_dir, meta)
    joblib.dump(detector, out_dir / "model.joblib")
    E.record_run(cfg, exp_id, "baseline", started_at=started, extra={"threshold": theta, "val_f1": f1})
    return exp_id


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Línea base de umbral.")
    ap.add_argument("--exp", required=True)
    args = ap.parse_args(argv)
    exp_id = run(C.load_experiment(args.exp))
    print(f"[baseline] exp_id = {exp_id}")


if __name__ == "__main__":
    main()
