"""Rejilla completa de ventanas, características causales y etiqueta de referencia con k = 1.

Decisiones que este módulo hace cumplir:

- R3 causalidad: la ventana ``j`` cubre ``[t_end - W, t_end)`` con ``t_end = g0 + j*S``;
  solo usa esas tramas y, para ``delta_n_disconn``, la ventana ``j - 1``.
- R4: ``t_end`` es el instante de alerta.
- R5: ``y = 1`` si la ventana contiene al menos una trama objetivo (k = 1).
- R8: :func:`compute_window_features` es la única función que calcula características;
  la usan el cálculo en lote y ``replay.py``.
- R2: la función recibe solo campos observables; las columnas de referencia nunca entran.

La rejilla es completa: hay una ventana cada ``S`` segundos aunque no haya tramas.
``g0`` es la marca de tiempo de la primera trama de la captura; la primera ventana
completa termina en ``g0 + W`` y la última es la primera que termina después de la última trama.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C
from .experiment import now_iso, read_json, write_json
from .preprocessing import SUBTYPE_DEAUTH, SUBTYPE_DISAS, TYPE_DATA, TYPE_MGMT
from .preprocessing import frames_path  # noqa: F401  (reexportado)

SEQ_MODULO = 4096

# Columnas observables que puede usar el detector.
OBSERVABLE_FIELDS = ("ts", "fc_type", "fc_subtype", "src_anon", "dst_anon", "is_broadcast_dst",
                     "reason_code", "seq", "signal_dbm", "protected")

BASE_FEATURES = (
    "n_frames_total", "n_mgmt", "n_data", "ratio_data_mgmt", "n_deauth", "n_disas",
    "n_disconn", "rate_disconn", "n_unique_src_disconn", "n_unique_dst_disconn",
    "frac_broadcast_dst_disconn", "iat_disconn_mean", "iat_disconn_std", "iat_disconn_min",
    "delta_n_disconn", "frac_protected_mgmt", "seq_jump_max", "signal_std_disconn",
)

# Columnas que nunca pueden ser características (R2).
NON_FEATURE_COLUMNS = {
    "capture_id", "window_id", "t_start", "t_end", "grid_origin", "split", "y", "n_target",
    "label_raw", "is_target", "attack_type", "episode_id",
}


class SplitError(ValueError):
    pass


# --------------------------------------------------------------------------- rejilla

def window_end(g0: float, j: int, S: float) -> float:
    return g0 + j * S


def window_bounds(g0: float, j: int, S: float, W: float) -> tuple[float, float]:
    t_end = window_end(g0, j, S)
    return t_end - W, t_end


def grid_indices(t_first: float, t_last: float, W: float, S: float) -> np.ndarray:
    """Índices ``j`` de la rejilla completa: desde ``W/S`` hasta la primera ventana que termina después de ``t_last``."""
    m = int(round(W / S))
    j_last = max(m, int(math.floor((t_last - t_first) / S)) + 1)
    while window_end(t_first, j_last, S) <= t_last:
        j_last += 1
    return np.arange(m, j_last + 1, dtype=np.int64)


# --------------------------------------------------------------------------- arreglos observables

def observable_arrays(df: pd.DataFrame) -> dict[str, np.ndarray]:
    """Convierte un DataFrame de tramas en arreglos numpy con solo campos observables."""
    def ints(col: str) -> np.ndarray:
        return df[col].astype("Int64").fillna(-1).to_numpy(dtype=np.int64)

    def floats(col: str) -> np.ndarray:
        return pd.to_numeric(df[col], errors="coerce").astype("float64").to_numpy()

    return {
        "ts": df["ts"].to_numpy(dtype=np.float64),
        "fc_type": ints("fc_type"),
        "fc_subtype": ints("fc_subtype"),
        "src_anon": df["src_anon"].to_numpy(dtype=object),
        "dst_anon": df["dst_anon"].to_numpy(dtype=object),
        "is_broadcast_dst": df["is_broadcast_dst"].fillna(False).to_numpy(dtype=bool),
        "reason_code": df["reason_code"].astype("Float64").to_numpy(dtype=np.float64, na_value=np.nan),
        "seq": df["seq"].astype("Float64").to_numpy(dtype=np.float64, na_value=np.nan),
        "signal_dbm": floats("signal_dbm"),
        "protected": df["protected"].astype("Float64").to_numpy(dtype=np.float64, na_value=np.nan),
    }


def slice_arrays(arrays: dict[str, np.ndarray], lo: int, hi: int) -> dict[str, np.ndarray]:
    return {k: v[lo:hi] for k, v in arrays.items()}


def take_arrays(arrays: dict[str, np.ndarray], idx) -> dict[str, np.ndarray]:
    idx = np.asarray(idx, dtype=np.int64)
    return {k: v[idx] for k, v in arrays.items()}


# --------------------------------------------------------------------------- características

def _n_unique(values: np.ndarray) -> int:
    vals = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return len(set(vals))


def _seq_jump_max(src: np.ndarray, seq: np.ndarray, sources: set) -> float:
    """Mayor salto circular de ``seq`` (módulo 4096) entre tramas consecutivas de una misma fuente."""
    best = math.nan
    by_src: dict = {}
    for s, q in zip(src, seq):
        if s is None or s not in sources or math.isnan(q):
            continue
        prev = by_src.get(s)
        if prev is not None:
            d = int(q - prev) % SEQ_MODULO
            jump = min(d, SEQ_MODULO - d)
            best = jump if math.isnan(best) else max(best, jump)
        by_src[s] = q
    return float(best)


def compute_window_features(win: dict[str, np.ndarray], prev_n_disconn: float, *, W: float,
                            reason_codes: list[int]) -> dict[str, float]:
    """Calcula todas las características de una ventana.

    ``win`` contiene solo campos observables de las tramas de ``[t_end - W, t_end)``, en orden temporal.
    ``prev_n_disconn`` es ``n_disconn`` de la ventana anterior o ``nan`` si no existe.
    """
    fc_type = win["fc_type"]
    fc_sub = win["fc_subtype"]
    mgmt = fc_type == TYPE_MGMT
    deauth = mgmt & (fc_sub == SUBTYPE_DEAUTH)
    disas = mgmt & (fc_sub == SUBTYPE_DISAS)
    disconn = deauth | disas

    n_total = int(len(fc_type))
    n_mgmt = int(mgmt.sum())
    n_data = int((fc_type == TYPE_DATA).sum())
    n_deauth = int(deauth.sum())
    n_disas = int(disas.sum())
    n_disconn = n_deauth + n_disas

    f: dict[str, float] = {
        "n_frames_total": float(n_total),
        "n_mgmt": float(n_mgmt),
        "n_data": float(n_data),
        "ratio_data_mgmt": n_data / max(n_mgmt, 1),
        "n_deauth": float(n_deauth),
        "n_disas": float(n_disas),
        "n_disconn": float(n_disconn),
        "rate_disconn": n_disconn / W,
        "delta_n_disconn": (n_disconn - prev_n_disconn) if not math.isnan(prev_n_disconn) else math.nan,
    }

    if n_disconn:
        src_d = win["src_anon"][disconn]
        f["n_unique_src_disconn"] = float(_n_unique(src_d))
        f["n_unique_dst_disconn"] = float(_n_unique(win["dst_anon"][disconn]))
        f["frac_broadcast_dst_disconn"] = float(win["is_broadcast_dst"][disconn].mean())
        ts_d = win["ts"][disconn]
        if n_disconn >= 2:
            iat = np.diff(ts_d)
            f["iat_disconn_mean"] = float(iat.mean())
            f["iat_disconn_std"] = float(iat.std())
            f["iat_disconn_min"] = float(iat.min())
        else:
            f["iat_disconn_mean"] = f["iat_disconn_std"] = f["iat_disconn_min"] = math.nan
        sig = win["signal_dbm"][disconn]
        sig = sig[~np.isnan(sig)]
        f["signal_std_disconn"] = float(sig.std()) if len(sig) >= 2 else math.nan
        sources = {s for s in src_d if s is not None}
        f["seq_jump_max"] = _seq_jump_max(win["src_anon"][mgmt], win["seq"][mgmt], sources)
        rc = win["reason_code"][disconn]
    else:
        for name in ("n_unique_src_disconn", "n_unique_dst_disconn"):
            f[name] = 0.0
        for name in ("frac_broadcast_dst_disconn", "iat_disconn_mean", "iat_disconn_std",
                     "iat_disconn_min", "signal_std_disconn", "seq_jump_max"):
            f[name] = math.nan
        rc = np.empty(0)

    prot = win["protected"][mgmt]
    prot = prot[~np.isnan(prot)]
    f["frac_protected_mgmt"] = float(prot.mean()) if len(prot) else math.nan

    known = set()
    for code in reason_codes:
        f[f"rc_{int(code)}"] = float(np.sum(rc == code))
        known.add(float(code))
    rc_valid = rc[~np.isnan(rc)] if len(rc) else rc
    f["rc_other"] = float(sum(1 for v in rc_valid if v not in known))
    return f


# --------------------------------------------------------------------------- columnas permitidas

def parse_reason_codes(features_cfg: dict) -> list[int]:
    codes = features_cfg.get("reason_codes", [])
    if C.contains_placeholder(codes):
        return []
    return [int(c) for c in codes]


def expand_names(names: list[str], reason_codes: list[int]) -> list[str]:
    out = []
    for name in names:
        if name == "rc_counts":
            out.extend(f"rc_{c}" for c in reason_codes)
            out.append("rc_other")
        else:
            out.append(name)
    return out


def resolve_feature_columns(features_cfg: dict, profile: str) -> list[str]:
    """Lista ordenada de columnas de ``X`` según el perfil (``allowed`` o ``loao``)."""
    if profile not in ("allowed", "loao"):
        raise C.ConfigError("features_profile debe ser 'allowed' o 'loao'.")
    allowed = list(features_cfg.get("allowed") or [])
    if not allowed:
        raise C.ConfigError("features.yaml: la lista 'allowed' está vacía.")
    codes = parse_reason_codes(features_cfg)
    if "rc_counts" in allowed and not codes and C.contains_placeholder(features_cfg.get("reason_codes")):
        raise C.ConfigError("features.yaml usa rc_counts pero 'reason_codes' sigue pendiente (Gate D).")
    cols = expand_names(allowed, codes)
    if profile == "loao":
        exclude = set(expand_names(list(features_cfg.get("loao_exclude") or []), codes))
        cols = [c for c in cols if c not in exclude]
    known = set(BASE_FEATURES) | {f"rc_{c}" for c in codes} | {"rc_other"}
    unknown = [c for c in cols if c not in known]
    if unknown:
        raise C.ConfigError(f"features.yaml contiene características desconocidas: {unknown}")
    leaked = [c for c in cols if c in NON_FEATURE_COLUMNS or c.startswith("ref_")]
    if leaked:
        raise C.ConfigError(f"Columnas de referencia no pueden ser características (R2): {leaked}")
    return cols


# --------------------------------------------------------------------------- partición

def load_split(cfg: dict) -> dict:
    path = C.resolve_path(cfg["split_file"])
    if not path.exists():
        raise SplitError(f"No existe la partición congelada {path}. Ejecute split_data --freeze.")
    return read_json(path)


def assign_split(capture_id: str, t_start: float, t_end: float, units: dict) -> str:
    """Una ventana pertenece a un conjunto solo si cabe completa en una de sus unidades."""
    for split_name, items in units.items():
        for u in items:
            if u["capture_id"] != capture_id:
                continue
            lo = -math.inf if u.get("t_from") is None else float(u["t_from"])
            hi = math.inf if u.get("t_to") is None else float(u["t_to"])
            if t_start >= lo and t_end <= hi:
                return split_name
    return "purged"


# --------------------------------------------------------------------------- cálculo en lote

def load_frames(data_cfg: dict, capture_id: str) -> pd.DataFrame:
    path = frames_path(data_cfg, capture_id)
    if not path.exists():
        raise FileNotFoundError(f"No existe {path}. Ejecute preprocessing primero.")
    return pd.read_parquet(path)


def attack_types(data_cfg: dict) -> list[str]:
    return [str(k) for k in data_cfg["labels"]["target"]]


def capture_windows(frames: pd.DataFrame, capture_id: str, *, W: float, S: float,
                    reason_codes: list[int], types: list[str], units: dict | None) -> pd.DataFrame:
    frames = frames.sort_values("ts", kind="mergesort").reset_index(drop=True)
    arrays = observable_arrays(frames)
    ts = arrays["ts"]
    is_target = frames["is_target"].to_numpy(dtype=bool)
    attack = frames["attack_type"].to_numpy(dtype=object)
    g0 = float(ts[0])
    rows = []
    prev = math.nan
    for j in grid_indices(g0, float(ts[-1]), W, S):
        t_start, t_end = window_bounds(g0, int(j), S, W)
        lo = int(np.searchsorted(ts, t_start, side="left"))
        hi = int(np.searchsorted(ts, t_end, side="left"))
        feats = compute_window_features(slice_arrays(arrays, lo, hi), prev, W=W, reason_codes=reason_codes)
        prev = feats["n_disconn"]
        tgt = is_target[lo:hi]
        row = {
            "capture_id": capture_id,
            "window_id": int(j),
            "t_start": t_start,
            "t_end": t_end,
            "grid_origin": g0,
            **feats,
            "n_target": int(tgt.sum()),
        }
        row["y"] = int(row["n_target"] >= 1)  # k = 1 (R5)
        win_types = attack[lo:hi][tgt]
        for t in types:
            row[f"ref_{t}"] = bool(np.any(win_types == t))
        row["split"] = assign_split(capture_id, t_start, t_end, units) if units is not None else "unassigned"
        rows.append(row)
    return pd.DataFrame(rows)


def windows_path(cfg: dict) -> Path:
    W, S = C.window_params(cfg)
    stem = Path(cfg["split_file"]).stem
    return C.data_path(cfg["_data"], "processed") / f"windows_{stem}_W{W:g}_S{S:g}.parquet"


def read_grid_origins(path: Path) -> dict[str, float]:
    df = pd.read_parquet(path, columns=["capture_id", "grid_origin"])
    return {str(k): float(v) for k, v in df.groupby("capture_id")["grid_origin"].first().items()}


def build_windows(cfg: dict) -> pd.DataFrame:
    W, S = C.window_params(cfg)
    split = load_split(cfg)
    if float(split["purge_seconds"]) < W:
        raise SplitError(
            f"La purga de la partición ({split['purge_seconds']} s) es menor que W ({W} s). "
            "La purga debe ser >= W para todas las ventanas usadas, incluidas las de sensibilidad (R7)."
        )
    data_cfg = cfg["_data"]
    codes = parse_reason_codes(cfg["_features"])
    types = attack_types(data_cfg)
    parts = []
    for cid in C.capture_ids(data_cfg):
        frames = load_frames(data_cfg, cid)
        parts.append(capture_windows(frames, cid, W=W, S=S, reason_codes=codes, types=types,
                                     units=split["units"]))
    return pd.concat(parts, ignore_index=True)


def check_class_presence(windows: pd.DataFrame) -> dict:
    out = {}
    for split_name in ("train", "val", "test"):
        part = windows[windows["split"] == split_name]
        out[split_name] = {"n_windows": int(len(part)), "normal": bool((part["y"] == 0).any()),
                           "attack": bool((part["y"] == 1).any())}
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Construye la rejilla completa de ventanas.")
    ap.add_argument("--exp", required=True)
    args = ap.parse_args(argv)
    cfg = C.load_experiment(args.exp)
    windows = build_windows(cfg)
    presence = check_class_presence(windows)
    for name, p in presence.items():
        if p["n_windows"] and not (p["normal"] and p["attack"]):
            raise SplitError(f"El conjunto '{name}' no tiene ventanas normales y de ataque: {p}")
    out = windows_path(cfg)
    out.parent.mkdir(parents=True, exist_ok=True)
    windows.to_parquet(out, index=False)
    write_json(out.with_suffix(".json"), {"created_at": now_iso(), "windows": int(len(windows)),
                                          "class_presence": presence,
                                          "split_counts": windows["split"].value_counts().to_dict()})
    print(f"[feature_engineering] {len(windows)} ventanas -> {out}")


if __name__ == "__main__":
    main()
