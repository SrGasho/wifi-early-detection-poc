"""Episodios: ráfagas de tramas objetivo separadas por un silencio mayor que ``T``.

Dos productos distintos que nunca se mezclan (plan, sección 5.2):

- ``exploratory``: toda la captura, ``T`` provisional. Solo describe el dataset y ayuda a ubicar
  cortes. Nunca se usa para métricas, entrenamiento ni etiquetado.
- ``definitive``: por conjunto, con ``T`` calculado solo con el entrenamiento y aplicado igual a
  los tres conjuntos. Incluye ``start_complete``.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C
from .experiment import now_iso, read_json, sha256_file, write_json
from .feature_engineering import load_frames, load_split

EPISODE_COLUMNS = ["episode_id", "mode", "split", "capture_id", "attack_type", "t_start", "t_end",
                   "n_frames", "start_complete", "T_seconds"]


class EpisodeError(ValueError):
    pass


def group_bursts(ts: np.ndarray, T: float) -> list[tuple[int, int]]:
    """Agrupa marcas de tiempo ordenadas. Devuelve pares ``(inicio, fin)`` de índices inclusivos."""
    if len(ts) == 0:
        return []
    breaks = np.flatnonzero(np.diff(ts) > T)
    starts = np.concatenate(([0], breaks + 1))
    ends = np.concatenate((breaks, [len(ts) - 1]))
    return list(zip(starts.tolist(), ends.tolist()))


def _dominant(values: np.ndarray) -> str:
    vals, counts = np.unique(values.astype(str), return_counts=True)
    return str(vals[np.argmax(counts)])


def target_frames(frames: pd.DataFrame) -> pd.DataFrame:
    t = frames.loc[frames["is_target"], ["ts", "attack_type"]]
    return t.sort_values("ts", kind="mergesort").reset_index(drop=True)


# --------------------------------------------------------------------------- exploratorio

def interarrival_summary(ts: np.ndarray) -> dict:
    """Describe los intervalos entre tramas objetivo para elegir un ``T`` provisional."""
    if len(ts) < 2:
        return {"n_target_frames": int(len(ts))}
    iat = np.diff(ts)
    qs = [50, 90, 99, 99.9, 99.99, 100]
    return {"n_target_frames": int(len(ts)),
            "iat_percentiles": {str(q): float(np.percentile(iat, q)) for q in qs},
            "largest_gaps": [float(g) for g in np.sort(iat)[-10:][::-1]]}


def exploratory_episodes(frames: pd.DataFrame, capture_id: str, T: float) -> pd.DataFrame:
    tgt = target_frames(frames)
    ts = tgt["ts"].to_numpy()
    rows = []
    for n, (a, b) in enumerate(group_bursts(ts, T)):
        rows.append({"episode_id": f"{capture_id}_exp_{n}", "mode": "exploratory", "split": None,
                     "capture_id": capture_id,
                     "attack_type": _dominant(tgt["attack_type"].to_numpy()[a:b + 1]),
                     "t_start": float(ts[a]), "t_end": float(ts[b]), "n_frames": int(b - a + 1),
                     "start_complete": None, "T_seconds": float(T)})
    return pd.DataFrame(rows, columns=EPISODE_COLUMNS)


def exploratory_path(data_cfg: dict) -> Path:
    return C.data_path(data_cfg, "interim") / "episodes_exploratory.parquet"


def run_exploratory(data_cfg: dict, T: float) -> pd.DataFrame:
    parts, summary = [], {"created_at": now_iso(), "T_provisional": T, "captures": {}}
    for cid in C.capture_ids(data_cfg):
        frames = load_frames(data_cfg, cid)
        ts = target_frames(frames)["ts"].to_numpy()
        ep = exploratory_episodes(frames, cid, T)
        parts.append(ep)
        summary["captures"][cid] = {**interarrival_summary(ts), "n_episodes": int(len(ep))}
    out = pd.concat(parts, ignore_index=True)
    path = exploratory_path(data_cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(path, index=False)
    write_json(path.with_suffix(".json"), summary)
    return out


# --------------------------------------------------------------------------- definitivo

def compute_T(train_target_ts: list[np.ndarray], episodes_cfg: dict) -> tuple[float, dict]:
    """``T`` definitivo, calculado solo con tramas objetivo del entrenamiento."""
    method = C.require({"episodes": episodes_cfg}, "episodes.T_method")
    if method == "fixed":
        T = float(C.require({"episodes": episodes_cfg}, "episodes.T_seconds"))
        return T, {"method": "fixed"}
    if method == "percentile_multiple":
        p = float(C.require({"episodes": episodes_cfg}, "episodes.T_percentile"))
        m = float(C.require({"episodes": episodes_cfg}, "episodes.T_multiplier"))
        iats = [np.diff(ts) for ts in train_target_ts if len(ts) >= 2]
        if not iats:
            raise EpisodeError("No hay suficientes tramas objetivo en entrenamiento para calcular T.")
        base = float(np.percentile(np.concatenate(iats), p))
        return m * base, {"method": method, "percentile": p, "multiplier": m, "base_seconds": base}
    raise C.ConfigError("episodes.T_method debe ser 'fixed' o 'percentile_multiple'.")


def _unit_bounds(u: dict) -> tuple[float, float]:
    lo = -math.inf if u.get("t_from") is None else float(u["t_from"])
    hi = math.inf if u.get("t_to") is None else float(u["t_to"])
    return lo, hi


def definitive_episodes(target_ts: np.ndarray, target_types: np.ndarray, capture_id: str,
                        split_name: str, lo: float, hi: float, T: float, start_n: int = 0) -> pd.DataFrame:
    """Episodios de una unidad ``[lo, hi)``.

    ``start_complete`` es ``True`` si la trama objetivo anterior de la captura completa (fuera de la
    unidad, en otra parte o en la purga) está a más de ``T`` segundos o no existe.
    """
    mask = (target_ts >= lo) & (target_ts < hi)
    idx = np.flatnonzero(mask)
    rows = []
    if len(idx) == 0:
        return pd.DataFrame(rows, columns=EPISODE_COLUMNS)
    local_ts = target_ts[idx]
    for n, (a, b) in enumerate(group_bursts(local_ts, T), start=start_n):
        first_global = idx[a]
        prev_gap = target_ts[first_global] - target_ts[first_global - 1] if first_global > 0 else math.inf
        rows.append({"episode_id": f"{capture_id}_{split_name}_{n}", "mode": "definitive",
                     "split": split_name, "capture_id": capture_id,
                     "attack_type": _dominant(target_types[idx[a]:idx[b] + 1]),
                     "t_start": float(local_ts[a]), "t_end": float(local_ts[b]),
                     "n_frames": int(b - a + 1), "start_complete": bool(prev_gap > T),
                     "T_seconds": float(T)})
    return pd.DataFrame(rows, columns=EPISODE_COLUMNS)


def definitive_dir(cfg: dict) -> Path:
    return C.data_path(cfg["_data"], "interim")


def definitive_meta_path(cfg: dict) -> Path:
    return definitive_dir(cfg) / f"episodes_{Path(cfg['split_file']).stem}_meta.json"


def definitive_path(cfg: dict, split_name: str) -> Path:
    return definitive_dir(cfg) / f"episodes_{Path(cfg['split_file']).stem}_{split_name}.parquet"


def load_definitive_meta(cfg: dict) -> dict:
    path = definitive_meta_path(cfg)
    if not path.exists():
        raise EpisodeError(f"No existen episodios definitivos ({path}). Ejecute episodes --mode definitive.")
    return read_json(path)


def load_definitive(cfg: dict, split_name: str, T_expected: float) -> pd.DataFrame:
    """Carga episodios definitivos y verifica que no sean exploratorios y que ``T`` coincida."""
    path = definitive_path(cfg, split_name)
    if "exploratory" in path.name:
        raise EpisodeError("Los episodios exploratorios nunca se usan para métricas.")
    df = pd.read_parquet(path)
    if len(df) and (set(df["mode"]) != {"definitive"} or set(df["split"]) != {split_name}):
        raise EpisodeError(f"{path} no contiene episodios definitivos del conjunto '{split_name}'.")
    if len(df) and not np.allclose(df["T_seconds"].to_numpy(), T_expected):
        raise EpisodeError("El T de los episodios no coincide con el de metadata.json.")
    return df


def run_definitive(cfg: dict) -> dict:
    split = load_split(cfg)
    data_cfg = cfg["_data"]
    targets = {}
    for cid in C.capture_ids(data_cfg):
        tgt = target_frames(load_frames(data_cfg, cid))
        targets[cid] = (tgt["ts"].to_numpy(), tgt["attack_type"].to_numpy(dtype=object))

    train_ts = []
    for u in split["units"]["train"]:
        lo, hi = _unit_bounds(u)
        ts = targets[u["capture_id"]][0]
        train_ts.append(ts[(ts >= lo) & (ts < hi)])
    T, method = compute_T(train_ts, cfg.get("episodes") or {})

    meta_path = definitive_meta_path(cfg)
    if meta_path.exists():
        old = read_json(meta_path)
        if not math.isclose(old["T_seconds"], T) or old["split_sha256"] != sha256_file(C.resolve_path(cfg["split_file"])):
            raise EpisodeError(
                f"Ya existen episodios definitivos con otro T o con otra partición ({meta_path}). "
                "Después de gate-d no se modifican; cree una partición nueva (R6)."
            )

    counts, measurable = {}, False
    for split_name in ("train", "val", "test"):
        parts, n = [], 0
        for u in split["units"][split_name]:
            lo, hi = _unit_bounds(u)
            ts, types = targets[u["capture_id"]]
            ep = definitive_episodes(ts, types, u["capture_id"], split_name, lo, hi, T, start_n=n)
            n += len(ep)
            parts.append(ep)
        df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=EPISODE_COLUMNS)
        df.to_parquet(definitive_path(cfg, split_name), index=False)
        counts[split_name] = {"n_episodes": int(len(df)),
                              "n_start_complete": int(df["start_complete"].sum()) if len(df) else 0,
                              "by_type": df["attack_type"].value_counts().to_dict() if len(df) else {}}
        if split_name == "test":
            measurable = counts["test"]["n_start_complete"] > 0
    meta = {"created_at": now_iso(), "T_seconds": T, "T_method": method,
            "split_file": cfg["split_file"],
            "split_sha256": sha256_file(C.resolve_path(cfg["split_file"])),
            "counts": counts, "latency_measurable_in_test": measurable}
    write_json(meta_path, meta)
    return meta


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Episodios exploratorios o definitivos.")
    ap.add_argument("--mode", choices=("exploratory", "definitive"), required=True)
    ap.add_argument("--data", help="configs/data.yaml (modo exploratorio)")
    ap.add_argument("--exp", help="experimento principal (modo definitivo)")
    ap.add_argument("--T-provisional", type=float, help="T provisional en segundos (modo exploratorio)")
    args = ap.parse_args(argv)
    if args.mode == "exploratory":
        if not args.data or args.T_provisional is None:
            ap.error("El modo exploratorio requiere --data y --T-provisional")
        out = run_exploratory(C.load_data_config(args.data), args.T_provisional)
        print(f"[episodes] {len(out)} episodios exploratorios (solo descriptivos)")
    else:
        if not args.exp:
            ap.error("El modo definitivo requiere --exp")
        meta = run_definitive(C.load_experiment(args.exp))
        print(f"[episodes] T = {meta['T_seconds']:.6g} s; {meta['counts']}")


if __name__ == "__main__":
    main()
