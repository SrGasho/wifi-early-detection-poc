"""Reproducción temporal: procesa las tramas en orden como lo haría el sensor (plan, sección 8.8).

- Carga el modelo y todo ``metadata.json``; no lee ``features.yaml`` ni reconstruye decisiones (R8).
- Mantiene en memoria solo las tramas de la ventana actual.
- Cada ``S`` segundos de datos cierra una ventana y llama a ``compute_window_features``,
  la misma función del cálculo en lote.
- Mide tiempos con ``time.perf_counter()``.
- Al terminar compara sus predicciones con ``predictions_<split>.parquet``. Si alguna difiere,
  el resultado se marca como inválido.
"""

from __future__ import annotations

import argparse
import math
import time
from collections import deque

import numpy as np
import pandas as pd

from . import config as C
from . import experiment as E
from .feature_engineering import (assign_split, compute_window_features, grid_indices, load_frames,
                                  observable_arrays, take_arrays, window_bounds)
from .predict import load_detector, predictions_path, prepare_X

SCORE_TOLERANCE = 1e-9


def split_window_ids(g0: float, t_last: float, W: float, S: float, capture_id: str, units: dict,
                     split: str) -> list[int]:
    return [int(j) for j in grid_indices(g0, t_last, W, S)
            if assign_split(capture_id, *window_bounds(g0, int(j), S, W), units) == split]


def replay_capture(frames: pd.DataFrame, capture_id: str, window_ids: list[int], detector, meta: dict,
                   *, speed: float | None) -> tuple[list[dict], dict]:
    W, S = float(meta["W_seconds"]), float(meta["S_seconds"])
    g0 = float(meta["grid_origins"][capture_id])
    codes = [int(c) for c in meta.get("reason_codes", [])]
    m = int(round(W / S))
    frames = frames.sort_values("ts", kind="mergesort").reset_index(drop=True)
    arrays = observable_arrays(frames)
    ts = arrays["ts"]
    j_first, j_last = min(window_ids), max(window_ids)
    j_warm = j_first - 1 if j_first > m else j_first  # la ventana anterior alimenta delta_n_disconn
    wanted = set(window_ids)

    t0_stream, _ = window_bounds(g0, j_warm, S, W)
    head = int(np.searchsorted(ts, t0_stream, side="left"))  # posición inicial en la grabación
    buffer: deque[int] = deque()
    prev = math.nan
    records = []
    n_frames_seen = 0
    wall_start = time.perf_counter()
    for j in range(j_warm, j_last + 1):
        t_start, t_end = window_bounds(g0, j, S, W)
        if speed:
            target = wall_start + (t_end - window_bounds(g0, j_warm, S, W)[1]) / speed
            delay = target - time.perf_counter()
            if delay > 0:
                time.sleep(delay)
        t_close = time.perf_counter()
        while head < len(ts) and ts[head] < t_end:
            buffer.append(head)
            head += 1
            n_frames_seen += 1
        while buffer and ts[buffer[0]] < t_start:
            buffer.popleft()
        t_feat0 = time.perf_counter()
        feats = compute_window_features(take_arrays(arrays, list(buffer)), prev, W=W, reason_codes=codes)
        t_feat1 = time.perf_counter()
        prev = feats["n_disconn"]
        if j not in wanted:
            continue
        score = float(detector.score(prepare_X(pd.DataFrame([feats]), meta))[0])
        t_pred = time.perf_counter()
        records.append({"capture_id": capture_id, "window_id": j, "t_end": t_end, "score": score,
                        "y_pred": int(score >= float(meta["threshold"])),
                        "feature_seconds": t_feat1 - t_feat0, "predict_seconds": t_pred - t_feat1,
                        "total_seconds": t_pred - t_close, "frames_in_window": len(buffer)})
    wall = time.perf_counter() - wall_start
    data_seconds = window_bounds(g0, j_last, S, W)[1] - t0_stream
    stats = {"capture_id": capture_id, "n_windows": len(records), "frames_processed": n_frames_seen,
             "wall_seconds": wall, "data_seconds": data_seconds,
             "input_rate_frames_per_second": n_frames_seen / data_seconds if data_seconds > 0 else None,
             "processed_rate_frames_per_second": n_frames_seen / wall if wall > 0 else None}
    return records, stats


def _summary(values: list[float]) -> dict:
    if not values:
        return {}
    arr = np.asarray(values)
    return {"mean": float(arr.mean()), "p50": float(np.percentile(arr, 50)),
            "p95": float(np.percentile(arr, 95)), "max": float(arr.max())}


def compare(replayed: pd.DataFrame, batch: pd.DataFrame) -> dict:
    keys = ["capture_id", "window_id"]
    merged = replayed.merge(batch, on=keys, how="outer", suffixes=("_replay", "_batch"), indicator=True)
    only = merged[merged["_merge"] != "both"]
    both = merged[merged["_merge"] == "both"]
    score_diff = float((both["score_replay"] - both["score_batch"]).abs().max()) if len(both) else 0.0
    pred_diff = int((both["y_pred_replay"] != both["y_pred_batch"]).sum())
    valid = only.empty and pred_diff == 0 and score_diff <= SCORE_TOLERANCE
    return {"valid": bool(valid), "windows_only_in_one_side": int(len(only)),
            "max_abs_score_difference": score_diff, "y_pred_differences": pred_diff}


def run(cfg: dict, split: str, final: bool, *, speed: float | None = None, check_git: bool = True) -> dict:
    started = E.now_iso()
    E.guard_split_access(cfg, split, final)
    exp_id = E.resolve_exp_id(cfg)
    marker = E.guard_final(cfg, exp_id, "replay", check_git=check_git) if final else None
    detector, meta = load_detector(E.model_dir(cfg, exp_id))
    if hasattr(detector, "model") and hasattr(detector.model, "n_jobs"):
        detector.model.n_jobs = 1  # una fila por llamada; no cambia el resultado
    units = E.read_json(meta["split_file"])["units"]
    W, S = float(meta["W_seconds"]), float(meta["S_seconds"])
    records, per_capture = [], []
    for cid in sorted({u["capture_id"] for u in units[split]}):
        frames = load_frames(cfg["_data"], cid)
        ids = split_window_ids(float(meta["grid_origins"][cid]), float(frames["ts"].max()), W, S, cid, units, split)
        if not ids:
            continue
        rec, stats = replay_capture(frames, cid, ids, detector, meta, speed=speed)
        records.extend(rec)
        per_capture.append(stats)
    replayed = pd.DataFrame(records)
    out_dir = E.results_dir(cfg, exp_id)
    replayed.to_parquet(out_dir / f"replay_predictions_{split}.parquet", index=False)
    check = compare(replayed[["capture_id", "window_id", "score", "y_pred"]],
                    pd.read_parquet(predictions_path(cfg, exp_id, split))[["capture_id", "window_id", "score", "y_pred"]])
    report = {"split": split, "speed": "max" if not speed else speed, "consistency_with_batch": check,
              "feature_seconds": _summary(replayed["feature_seconds"].tolist()),
              "predict_seconds": _summary(replayed["predict_seconds"].tolist()),
              "end_to_end_seconds": _summary(replayed["total_seconds"].tolist()),
              "captures": per_capture,
              "note": "La latencia de procesamiento mide registro -> característica -> predicción; "
                      "no es tiempo de reconexión ni eficacia de mitigación."}
    E.write_json(out_dir / f"replay_{split}.json", report)
    E.record_run(cfg, exp_id, "replay", split=split, started_at=started, extra={"valid": check["valid"]})
    if marker:
        E.mark_final_done(marker)
    return report


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Reproducción temporal del detector.")
    ap.add_argument("--exp", required=True)
    ap.add_argument("--split", choices=("train", "val", "test"), required=True)
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--speed", default="max", help="'max' o un factor (1.0 = tiempo real de los datos)")
    args = ap.parse_args(argv)
    speed = None if args.speed == "max" else float(args.speed)
    rep = run(C.load_experiment(args.exp), args.split, args.final, speed=speed)
    print(f"[replay] consistente con el lote: {rep['consistency_with_batch']['valid']}")


if __name__ == "__main__":
    main()
