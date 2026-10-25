"""Partición congelada: Casos A, B y C, purga >= W y presencia de clases (plan, sección 8.4).

La partición es consciente de etiquetas: usa la posición de las tramas objetivo para organizar
capturas, verificar la presencia de clases, ubicar cortes y construir el leave-one-attack-out.
Nunca usa resultados de un modelo. Esto se declara como limitación.

Reglas de clases:
1. Obligatorio: cada conjunto tiene ventanas normales (y = 0) y de ataque (y = 1).
2. La presencia de cada tipo de ataque se verifica y se registra, pero no se exige.
3. Nunca se duplican, sobremuestrean ni sintetizan ataques.
"""

from __future__ import annotations

import argparse
import math
import random

import numpy as np
import pandas as pd

from . import config as C
from .episodes import _dominant, exploratory_path, target_frames
from .experiment import git_info, now_iso, write_json
from .feature_engineering import (assign_split, attack_types, grid_indices, load_frames,
                                  window_bounds)

SPLITS = ("train", "val", "test")


class SplitError(ValueError):
    pass


# --------------------------------------------------------------------------- ubicación de cortes

def quantile_time(ts: np.ndarray, q: float) -> float:
    if len(ts) == 0:
        raise SplitError("La captura no tiene tramas objetivo para ubicar el corte.")
    i = min(len(ts) - 1, max(0, int(math.floor(q * len(ts)))))
    return float(ts[i])


def snap_to_silence(cut: float, episodes: pd.DataFrame | None, purge: float) -> tuple[float, str]:
    """Mueve el corte al centro del silencio entre ráfagas más cercano en el que cabe la purga."""
    if episodes is None or len(episodes) < 2:
        return cut, "cuantil de tramas objetivo (sin silencios entre ráfagas)"
    ep = episodes.sort_values("t_start")
    ends = ep["t_end"].to_numpy()[:-1]
    starts = ep["t_start"].to_numpy()[1:]
    gaps = starts - ends
    ok = gaps >= 2 * purge
    if not ok.any():
        return cut, "cuantil de tramas objetivo (ningún silencio admite la purga)"
    mids = (ends + starts) / 2
    mids = mids[ok]
    best = float(mids[np.argmin(np.abs(mids - cut))])
    return best, "centro del silencio entre ráfagas exploratorias más cercano al cuantil"


def _units_from_cuts(capture_id: str, cuts: list[float], purge: float, names: tuple[str, ...]) -> dict:
    """``len(cuts) + 1`` unidades consecutivas con purga a cada lado de cada corte."""
    bounds = [None] + cuts + [None]
    units: dict = {}
    for i, name in enumerate(names):
        lo = None if bounds[i] is None else bounds[i] + purge
        hi = None if bounds[i + 1] is None else bounds[i + 1] - purge
        if lo is not None and hi is not None and lo >= hi:
            raise SplitError(f"Los cortes de {capture_id} dejan el conjunto '{name}' vacío tras la purga.")
        units.setdefault(name, []).append({"capture_id": capture_id, "t_from": lo, "t_to": hi})
    return units


def _merge(a: dict, b: dict) -> dict:
    out = {s: list(a.get(s, [])) for s in SPLITS}
    for s in SPLITS:
        out[s].extend(b.get(s, []))
    return out


# --------------------------------------------------------------------------- casos

def case_a(split_cfg: dict, capture_ids: list[str], seed: int) -> tuple[dict, str]:
    assignment = split_cfg.get("assignment")
    if assignment:
        units = {s: [{"capture_id": c, "t_from": None, "t_to": None} for c in assignment.get(s, [])]
                 for s in SPLITS}
        return units, "asignación explícita de capturas completas"
    if len(capture_ids) < 3:
        raise SplitError("El Caso A necesita al menos tres capturas o una asignación explícita.")
    props = split_cfg.get("proportions", [0.6, 0.2, 0.2])
    ids = sorted(capture_ids)
    random.Random(seed).shuffle(ids)
    n_val = max(1, round(props[1] * len(ids)))
    n_test = max(1, round(props[2] * len(ids)))
    groups = {"test": ids[:n_test], "val": ids[n_test:n_test + n_val], "train": ids[n_test + n_val:]}
    units = {s: [{"capture_id": c, "t_from": None, "t_to": None} for c in groups[s]] for s in SPLITS}
    return units, f"capturas completas asignadas con semilla {seed}"


def case_b(split_cfg: dict, targets: dict, exploratory: pd.DataFrame | None, purge: float) -> tuple[dict, str]:
    props = split_cfg.get("proportions", [0.6, 0.2, 0.2])
    q1, q2 = props[0], props[0] + props[1]
    units: dict = {s: [] for s in SPLITS}
    notes = []
    for cid, (ts, _) in targets.items():
        ep = exploratory[exploratory["capture_id"] == cid] if exploratory is not None else None
        cuts = []
        for q in (q1, q2):
            cut, how = snap_to_silence(quantile_time(ts, q), ep, purge) if split_cfg.get("snap_to_silence", True) \
                else (quantile_time(ts, q), "cuantil de tramas objetivo")
            cuts.append(cut)
            notes.append(f"{cid}@{q:.2f}: {how}")
        units = _merge(units, _units_from_cuts(cid, cuts, purge, SPLITS))
    return units, "; ".join(notes)


def case_c(split_cfg: dict, targets: dict, exploratory: pd.DataFrame | None, purge: float) -> tuple[dict, str]:
    train_attack = C.require({"split": split_cfg}, "split.train_attack")
    test_attack = C.require({"split": split_cfg}, "split.test_attack")
    if train_attack == test_attack:
        raise SplitError("En el Caso C el tipo de entrenamiento y el de prueba deben ser distintos.")
    val_fraction = float(split_cfg.get("val_fraction", 0.2))
    by_type = {}
    for cid, (ts, types) in targets.items():
        if len(ts):
            by_type.setdefault(_dominant(types), []).append(cid)
    if train_attack not in by_type or test_attack not in by_type:
        raise SplitError(f"No hay capturas para {train_attack} y {test_attack}: {by_type}")
    units: dict = {s: [] for s in SPLITS}
    notes = []
    for cid in by_type[train_attack]:
        ts = targets[cid][0]
        ep = exploratory[exploratory["capture_id"] == cid] if exploratory is not None else None
        cut, how = snap_to_silence(quantile_time(ts, 1 - val_fraction), ep, purge)
        notes.append(f"{cid}: validación = tramo final ({how})")
        units = _merge(units, _units_from_cuts(cid, [cut], purge, ("train", "val")))
    for cid in by_type[test_attack]:
        units["test"].append({"capture_id": cid, "t_from": None, "t_to": None})
        notes.append(f"{cid}: prueba = captura completa, incluido su inicio")
    return units, "; ".join(notes)


# --------------------------------------------------------------------------- presencia de clases

def class_presence(targets: dict, extents: dict, units: dict, W: float, S: float, types: list[str]) -> dict:
    """Presencia de ventanas normales, de ataque y de cada tipo, con la misma rejilla del lote."""
    out = {s: {"n_windows": 0, "normal": False, "attack": False, **{t: False for t in types}} for s in SPLITS}
    for cid, (ts, tys) in targets.items():
        g0, t_last = extents[cid]
        for j in grid_indices(g0, t_last, W, S):
            t_start, t_end = window_bounds(g0, int(j), S, W)
            s = assign_split(cid, t_start, t_end, units)
            if s not in out:
                continue
            lo = int(np.searchsorted(ts, t_start, side="left"))
            hi = int(np.searchsorted(ts, t_end, side="left"))
            p = out[s]
            p["n_windows"] += 1
            if hi > lo:
                p["attack"] = True
                for t in set(tys[lo:hi].tolist()):
                    if t in p:
                        p[t] = True
            else:
                p["normal"] = True
    return out


# --------------------------------------------------------------------------- principal

def make_split(cfg: dict) -> dict:
    W, S = C.window_params(cfg)
    split_cfg = C.require(cfg, "split")
    case = C.require(cfg, "split.case")
    purge = float(C.require(cfg, "split.purge_seconds"))
    max_W = float(split_cfg.get("max_W_seconds", W))
    if purge < max(W, max_W):
        raise SplitError(
            f"purge_seconds ({purge}) debe ser >= W y >= la mayor W de sensibilidad ({max(W, max_W)}) (R7)."
        )
    data_cfg = cfg["_data"]
    types = attack_types(data_cfg)
    targets, extents = {}, {}
    for cid in C.capture_ids(data_cfg):
        frames = load_frames(data_cfg, cid)
        tgt = target_frames(frames)
        targets[cid] = (tgt["ts"].to_numpy(), tgt["attack_type"].to_numpy(dtype=object))
        extents[cid] = (float(frames["ts"].min()), float(frames["ts"].max()))
    exp_path = exploratory_path(data_cfg)
    exploratory = pd.read_parquet(exp_path) if exp_path.exists() else None

    if case == "A":
        units, placement = case_a(split_cfg, list(targets), int(cfg.get("seed", 0)))
    elif case == "B":
        units, placement = case_b(split_cfg, targets, exploratory, purge)
    elif case == "C":
        units, placement = case_c(split_cfg, targets, exploratory, purge)
    else:
        raise C.ConfigError("split.case debe ser A, B o C.")

    presence = class_presence(targets, extents, units, W, S, types)
    problems = [s for s in SPLITS if not (presence[s]["normal"] and presence[s]["attack"])]
    if problems:
        raise SplitError(
            f"Los conjuntos {problems} no tienen ventanas normales y de ataque: {presence}. "
            "Rediseñe los cortes antes de Gate D. Nunca se sintetizan ataques."
        )
    return {
        "case": case,
        "created_at": now_iso(),
        "git_commit": git_info()["git_commit"],
        "W_seconds": W,
        "S_seconds": S,
        "purge_seconds": purge,
        "max_W_seconds": max(W, max_W),
        "cut_placement": placement,
        "label_aware": True,
        "label_aware_note": ("La partición usa la posición de las etiquetas de referencia solo para organizar "
                             "capturas, verificar clases y ubicar cortes. No usa resultados de modelos."),
        "units": units,
        "class_presence": presence,
        "latency_measurable_in_test": "se determina con los episodios definitivos (episodes_*_meta.json)",
    }


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Construye y congela la partición.")
    ap.add_argument("--exp", required=True)
    ap.add_argument("--freeze", action="store_true", help="Escribe la partición congelada")
    args = ap.parse_args(argv)
    cfg = C.load_experiment(args.exp)
    split = make_split(cfg)
    out = C.resolve_path(cfg["split_file"])
    if not args.freeze:
        print("[split_data] Vista previa (no se escribió nada):")
        print(pd.DataFrame(split["class_presence"]).T)
        return
    if out.exists():
        raise SplitError(f"La partición {out} ya está congelada. Use un nombre nuevo para otra partición.")
    write_json(out, split)
    print(f"[split_data] Partición congelada -> {out}")


if __name__ == "__main__":
    main()
