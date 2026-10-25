"""Aplica un detector guardado a un conjunto, usando solo ``metadata.json`` (R8).

La salida ``predictions_<split>.parquet`` no contiene información de referencia (R11):
``capture_id, window_id, t_end, score, y_pred``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from . import config as C
from . import experiment as E
from .detectors import Detector
from .feature_engineering import NON_FEATURE_COLUMNS

PREDICTION_COLUMNS = ["capture_id", "window_id", "t_end", "score", "y_pred"]


def fit_imputation(train: pd.DataFrame, columns: list[str], strategy: str = "constant",
                   value: float = -1.0) -> dict[str, float]:
    """Valor de imputación por columna, ajustado solo con entrenamiento."""
    if strategy == "constant":
        return {c: float(value) for c in columns}
    if strategy == "train_median":
        out = {}
        for c in columns:
            med = train[c].median()
            out[c] = float(value) if pd.isna(med) else float(med)
        return out
    raise C.ConfigError("imputation.strategy debe ser 'constant' o 'train_median'.")


def prepare_X(df: pd.DataFrame, meta: dict) -> np.ndarray:
    """``X`` con el orden de columnas y la imputación de ``metadata.json``. Nunca incluye referencia (R2)."""
    cols = meta["feature_columns"]
    leaked = [c for c in cols if c in NON_FEATURE_COLUMNS or c.startswith("ref_")]
    if leaked:
        raise E.MetadataError(f"feature_columns contiene columnas de referencia: {leaked}")
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise E.MetadataError(f"Faltan columnas de características en las ventanas: {missing}")
    X = df[cols].astype("float64").copy()
    for c in cols:
        X[c] = X[c].fillna(meta["imputation"][c])
    return X.to_numpy()


def load_detector(directory: Path) -> tuple[Detector, dict]:
    meta = E.load_metadata(directory)
    model_path = Path(directory) / "model.joblib"
    if not model_path.exists():
        raise E.MetadataError(f"No existe {model_path}")
    return joblib.load(model_path), meta


def select_split(windows: pd.DataFrame, split: str) -> pd.DataFrame:
    part = windows[windows["split"] == split]
    if part.empty:
        raise ValueError(f"No hay ventanas del conjunto '{split}'.")
    return part.sort_values(["capture_id", "t_end"]).reset_index(drop=True)


def predict_frame(detector: Detector, meta: dict, windows: pd.DataFrame) -> pd.DataFrame:
    scores = detector.score(prepare_X(windows, meta))
    out = windows[["capture_id", "window_id", "t_end"]].copy()
    out["score"] = scores.astype("float64")
    out["y_pred"] = (out["score"] >= float(meta["threshold"])).astype(int)
    return out[PREDICTION_COLUMNS]


def check_windows_integrity(meta: dict) -> Path:
    path = Path(meta["windows_file"])
    expected = meta["data_files_sha256"].get(path.name)
    if expected is None or E.sha256_file(path) != expected:
        raise E.MetadataError(f"Las ventanas {path} no coinciden con las usadas al entrenar (hash distinto).")
    return path


def predictions_path(cfg: dict, exp_id: str, split: str) -> Path:
    return E.results_dir(cfg, exp_id) / f"predictions_{split}.parquet"


def run(cfg: dict, split: str, final: bool, *, check_git: bool = True) -> Path:
    started = E.now_iso()
    E.guard_split_access(cfg, split, final)
    exp_id = E.resolve_exp_id(cfg)
    marker = E.guard_final(cfg, exp_id, "predict", check_git=check_git) if final else None
    detector, meta = load_detector(E.model_dir(cfg, exp_id))
    windows = pd.read_parquet(check_windows_integrity(meta))
    preds = predict_frame(detector, meta, select_split(windows, split))
    out = predictions_path(cfg, exp_id, split)
    preds.to_parquet(out, index=False)
    E.record_run(cfg, exp_id, "predict", split=split, started_at=started,
                 extra={"n_windows": int(len(preds)), "n_positive": int(preds["y_pred"].sum())})
    if marker:
        E.mark_final_done(marker)
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Aplica un detector guardado.")
    ap.add_argument("--exp", required=True)
    ap.add_argument("--split", choices=("train", "val", "test"), required=True)
    ap.add_argument("--final", action="store_true")
    args = ap.parse_args(argv)
    out = run(C.load_experiment(args.exp), args.split, args.final)
    print(f"[predict] -> {out}")


if __name__ == "__main__":
    main()
