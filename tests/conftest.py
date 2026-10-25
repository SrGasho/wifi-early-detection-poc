"""Datos sintéticos en el formato interno (plan, sección 5.1). Ninguna prueba requiere AWID3.

Cada captura dura 600 s y tiene:
- balizas del AP cada 0,1 s y tramas de datos a ~20 por segundo;
- solicitudes de asociación de tres clientes con mfpc = True, False y nulo;
- una desautenticación legítima aislada (no objetivo) en t = 20 s;
- cinco ráfagas de ataque de 20 s a 50 tramas/s: [50,70], [150,170], [250,270], [350,370], [450,470].

``cap_a`` contiene desautenticación (subtipo 12) y ``cap_b`` disociación (subtipo 10).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from src import config as C
from src.preprocessing import INTERNAL_COLUMNS, finalize_types

BURSTS = [(50, 70), (150, 170), (250, 270), (350, 370), (450, 470)]
DURATION = 600.0
AP = "ap000000000a"
CLIENTS = {"cli_pmf": True, "cli_nopmf": False, "cli_unknown": None}


def _frame(ts, *, fc_type, fc_subtype, src, dst, reason=None, seq=None, signal=-40.0,
           protected=False, mfpc=None, target=False, attack="normal", capture="cap_a"):
    return {"ts": float(ts), "capture_id": capture, "file_idx": 0, "frame_number": 0,
            "fc_type": fc_type, "fc_subtype": fc_subtype, "src_anon": src, "dst_anon": dst,
            "bssid_anon": AP, "is_broadcast_dst": dst == "BROADCAST", "reason_code": reason,
            "seq": seq, "signal_dbm": signal, "protected": protected, "mfpc": mfpc,
            "label_raw": attack if target else "Normal", "is_target": target, "attack_type": attack}


def make_capture(capture_id: str, attack: str, subtype: int, reason: int, *, bursts=BURSTS,
                 duration: float = DURATION, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    seq = 0
    for t in np.arange(0.0, duration, 0.1):  # balizas
        rows.append(_frame(t, fc_type=0, fc_subtype=8, src=AP, dst="BROADCAST", seq=seq % 4096,
                           capture=capture_id))
        seq += 1
    for t in np.sort(rng.uniform(0, duration, int(20 * duration))):  # datos
        rows.append(_frame(t, fc_type=2, fc_subtype=0, src=rng.choice(list(CLIENTS)), dst=AP,
                           protected=True, capture=capture_id))
    for i, (client, mfpc) in enumerate(CLIENTS.items()):  # asociaciones
        rows.append(_frame(5 + i, fc_type=0, fc_subtype=0, src=client, dst=AP, mfpc=mfpc, capture=capture_id))
    rows.append(_frame(20.0, fc_type=0, fc_subtype=12, src="cli_pmf", dst=AP, reason=3, capture=capture_id))
    for a, b in bursts:  # ataque: suplanta al AP, destino de difusión
        for t in np.arange(a, b, 0.02):
            rows.append(_frame(t, fc_type=0, fc_subtype=subtype, src=AP, dst="BROADCAST", reason=reason,
                               seq=int(rng.integers(0, 4096)), signal=-70.0, target=True, attack=attack,
                               capture=capture_id))
    df = pd.DataFrame(rows, columns=INTERNAL_COLUMNS)
    df["frame_number"] = np.arange(len(df))
    df = finalize_types(df).sort_values("ts", kind="mergesort").reset_index(drop=True)
    return df


@pytest.fixture(scope="session")
def frames_a() -> pd.DataFrame:
    return make_capture("cap_a", "deauth", 12, 7, seed=1)


@pytest.fixture(scope="session")
def frames_b() -> pd.DataFrame:
    return make_capture("cap_b", "disas", 10, 8, seed=2)


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


W, S, PURGE, T = 2.0, 0.5, 2.0, 5.0


def experiment_dict(root: Path, name: str, **overrides) -> dict:
    d = {
        "name": name,
        "role": "main",
        "seed": 7,
        "data_config": str(root / "configs/data.yaml"),
        "features_config": str(root / "configs/features.yaml"),
        "split_file": str(root / "configs/splits/caso_B.json"),
        "paths": {"models": str(root / "models"), "results": str(root / "results")},
        "target": "binary",
        "window": {"W_seconds": W, "S_seconds": S, "k": 1},
        "split": {"case": "B", "purge_seconds": PURGE, "max_W_seconds": W,
                  "proportions": [0.6, 0.2, 0.2], "snap_to_silence": True},
        "episodes": {"T_method": "fixed", "T_seconds": T},
        "alerts": {"max_gap_seconds": S},
        "model": {"type": "random_forest", "grid": {"n_estimators": [20], "max_depth": [None, 5]},
                  "class_weight": "balanced"},
        "imputation": {"strategy": "constant", "value": -1},
        "features_profile": "allowed",
        "mitigation": {"tau_high": 0.9, "cooldown_seconds": 30.0},
    }
    d.update(overrides)
    return d


@pytest.fixture
def project(tmp_path, frames_a, frames_b):
    """Proyecto temporal con configuraciones completas y tramas ya normalizadas."""
    root = tmp_path
    data = {
        "paths": {k: str(root / "data" / k) for k in ("raw", "interim", "processed")},
        "captures": [{"id": "cap_a", "pattern": "a/*.csv"}, {"id": "cap_b", "pattern": "b/*.csv"}],
        "columns": {"ts": "frame.time_epoch", "label": "Label", "fc_type": "wlan.fc.type",
                    "fc_subtype": "wlan.fc.subtype"},
        "labels": {"target": {"deauth": "deauth", "disas": "disas"}, "normal": ["Normal"]},
        "anonymization": {"salt_env_var": "WIFI_ML_SALT_TEST"},
    }
    _write_yaml(root / "configs/data.yaml", data)
    feats = yaml.safe_load((C.ROOT / "configs/features.yaml").read_text(encoding="utf-8"))
    feats["reason_codes"] = [3, 7, 8]
    _write_yaml(root / "configs/features.yaml", feats)
    interim = root / "data/interim"
    interim.mkdir(parents=True, exist_ok=True)
    (root / "data/processed").mkdir(parents=True, exist_ok=True)
    frames_a.to_parquet(interim / "frames_cap_a.parquet", index=False)
    frames_b.to_parquet(interim / "frames_cap_b.parquet", index=False)
    rf = _write_yaml(root / "configs/experiments/exp_rf.yaml", experiment_dict(root, "rf_test"))
    base = experiment_dict(root, "baseline_test", model={"type": "threshold", "feature": "n_disconn"})
    base.pop("split")
    bl = _write_yaml(root / "configs/experiments/exp_baseline.yaml", base)
    sens = experiment_dict(root, "rf_sens_test", role="sensitivity")
    sn = _write_yaml(root / "configs/experiments/exp_sens.yaml", sens)
    return {"root": root, "rf": rf, "baseline": bl, "sens": sn}


@pytest.fixture
def pipeline(project):
    """Ejecuta exploración, partición, episodios definitivos y ventanas sobre el proyecto temporal."""
    from src import episodes, feature_engineering as FE, split_data
    from src.experiment import write_json

    cfg = C.load_experiment(project["rf"])
    episodes.run_exploratory(cfg["_data"], T)
    split = split_data.make_split(cfg)
    write_json(C.resolve_path(cfg["split_file"]), split)
    episodes.run_definitive(cfg)
    windows = FE.build_windows(cfg)
    windows.to_parquet(FE.windows_path(cfg), index=False)
    return {**project, "cfg": cfg, "split": split, "windows": windows}
