"""Random Forest con búsqueda de hiperparámetros y umbral solo en validación (plan, sección 8.6).

- No se usa validación cruzada aleatoria: mezclaría ventanas vecinas.
- Hiperparámetros: máximo F1 en validación (con su mejor umbral); en empate gana el primero de la rejilla.
- No se guarda el modelo si ``metadata.json`` está incompleto.
"""

from __future__ import annotations

import argparse
import itertools
import warnings

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance

from . import config as C
from . import experiment as E
from .baseline import best_threshold, load_train_val
from .detectors import RandomForestDetector
from .feature_engineering import parse_reason_codes, resolve_feature_columns
from .predict import fit_imputation, prepare_X


def param_grid(grid: dict) -> list[dict]:
    keys = list(grid)
    return [dict(zip(keys, values)) for values in itertools.product(*(grid[k] for k in keys))]


def run(cfg: dict, *, importance: bool = False) -> str:
    started = E.now_iso()
    model_cfg = C.require(cfg, "model")
    if model_cfg.get("type") != "random_forest":
        raise C.ConfigError("train.py entrena model.type: random_forest.")
    profile = cfg.get("features_profile", "allowed")
    columns = resolve_feature_columns(cfg["_features"], profile)
    train, val = load_train_val(cfg)
    imp_cfg = cfg.get("imputation") or {}
    imputation = fit_imputation(train, columns, imp_cfg.get("strategy", "constant"), imp_cfg.get("value", -1.0))
    all_nan = [c for c in columns if train[c].isna().all()]
    if all_nan:
        warnings.warn(f"Características sin datos en entrenamiento (revise Gate D): {all_nan}", stacklevel=2)

    exp_id = E.create_exp_id(cfg)
    meta = E.base_metadata(cfg, exp_id)
    meta.update({"model_type": "random_forest", "feature_profile": profile, "feature_columns": columns,
                 "reason_codes": parse_reason_codes(cfg["_features"]), "imputation": imputation})
    X_train, y_train = prepare_X(train, meta), train["y"].to_numpy()
    X_val, y_val = prepare_X(val, meta), val["y"].to_numpy()

    seed = int(cfg.get("seed", 0))
    search = []
    best = None
    for params in param_grid(model_cfg.get("grid") or {"n_estimators": [100]}):
        rf = RandomForestClassifier(random_state=seed, n_jobs=-1,
                                    class_weight=model_cfg.get("class_weight", "balanced"), **params)
        rf.fit(X_train, y_train)
        theta, f1 = best_threshold(y_val, rf.predict_proba(X_val)[:, 1])
        search.append({"params": params, "val_f1": f1, "threshold": theta})
        if best is None or f1 > best[2] + 1e-12:
            best = (rf, params, f1, theta)
    rf, params, f1, theta = best
    meta.update({"model_params": params, "threshold": theta,
                 "selection": {"criterion": "max_f1_validation", "tie_break": "primero de la rejilla",
                               "val_f1": f1, "search": search}})

    out_dir = E.model_dir(cfg, exp_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    E.save_metadata(out_dir, meta)  # valida el contrato antes de guardar el modelo
    joblib.dump(RandomForestDetector(rf), out_dir / "model.joblib")

    if importance:
        res = permutation_importance(rf, X_val, y_val, scoring="average_precision",
                                     n_repeats=5, random_state=seed, n_jobs=-1)
        order = np.argsort(-res.importances_mean)
        E.write_json(E.results_dir(cfg, exp_id) / "permutation_importance_val.json",
                     [{"feature": columns[i], "mean": float(res.importances_mean[i]),
                       "std": float(res.importances_std[i])} for i in order])
    E.record_run(cfg, exp_id, "train", started_at=started, extra={"best_params": params, "val_f1": f1})
    return exp_id


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Entrena Random Forest.")
    ap.add_argument("--exp", required=True)
    ap.add_argument("--importance", action="store_true", help="Importancia por permutación en validación")
    args = ap.parse_args(argv)
    exp_id = run(C.load_experiment(args.exp), importance=args.importance)
    print(f"[train] exp_id = {exp_id}")


if __name__ == "__main__":
    main()
