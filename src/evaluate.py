"""Métricas por ventana y por episodio (plan, sección 8.7; ``docs/protocolo-evaluacion.md``).

Este módulo es el único que cruza las salidas del detector con la referencia. El tipo de ataque
que aparece en ``eval_*`` sale de la etiqueta de referencia, nunca del detector (R11).
Solo acepta episodios definitivos.
"""

from __future__ import annotations

import argparse
import statistics

import numpy as np
import pandas as pd

from . import config as C
from . import experiment as E
from .alerts import alerts_path
from .episodes import load_definitive, target_frames
from .feature_engineering import attack_types, load_frames
from .predict import predictions_path

NOT_AVAILABLE = "no disponible para esta partición"


# --------------------------------------------------------------------------- por ventana

def _ratio(a: float, b: float):
    return None if b == 0 else a / b


def window_metrics(y: np.ndarray, y_pred: np.ndarray) -> dict:
    y = np.asarray(y).astype(int)
    p = np.asarray(y_pred).astype(int)
    tp = int(((y == 1) & (p == 1)).sum())
    fp = int(((y == 0) & (p == 1)).sum())
    tn = int(((y == 0) & (p == 0)).sum())
    fn = int(((y == 1) & (p == 0)).sum())
    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    f1 = None if not precision or not recall else 2 * precision * recall / (precision + recall)
    if precision is not None and recall is not None and f1 is None:
        f1 = 0.0
    return {"n_windows": int(len(y)), "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "precision": precision, "recall": recall, "f1": f1,
            "fpr": _ratio(fp, fp + tn), "fnr": _ratio(fn, fn + tp)}


def window_metrics_by_type(ev: pd.DataFrame, types: list[str]) -> dict:
    """Por tipo: ventanas normales más las que contienen ese tipo. "No disponible" si el tipo no está."""
    out = {}
    for t in types:
        col = f"ref_{t}"
        if col not in ev or not ev[col].any():
            out[t] = NOT_AVAILABLE
            continue
        sub = ev[(ev["y"] == 0) | ev[col]]
        out[t] = window_metrics(sub["y"].to_numpy(), sub["y_pred"].to_numpy())
    return out


# --------------------------------------------------------------------------- por episodio

def episode_results(episodes: pd.DataFrame, preds: pd.DataFrame, target_ts: dict[str, np.ndarray],
                    W: float) -> list[dict]:
    rows = []
    pos = preds[preds["y_pred"] == 1]
    for ep in episodes.itertuples(index=False):
        p = pos[(pos["capture_id"] == ep.capture_id) & (pos["t_end"] - W <= ep.t_end) & (pos["t_end"] > ep.t_start)]
        detected = not p.empty
        t_alert = float(p["t_end"].min()) if detected else None
        latency = None
        if detected and bool(ep.start_complete):
            latency = t_alert - float(ep.t_start)
        frames_before = None
        if detected:
            ts = target_ts[ep.capture_id]
            frames_before = int(((ts >= ep.t_start) & (ts <= ep.t_end) & (ts < t_alert)).sum())
        rows.append({"episode_id": ep.episode_id, "capture_id": ep.capture_id,
                     "attack_type_ref": ep.attack_type, "t_start": float(ep.t_start),
                     "t_end": float(ep.t_end), "n_frames": int(ep.n_frames),
                     "start_complete": bool(ep.start_complete), "detected": detected,
                     "t_first_alert": t_alert, "latency_seconds": latency,
                     "target_frames_before_alert": frames_before})
    return rows


def latency_summary(results: list[dict]) -> dict | str:
    complete = [r for r in results if r["start_complete"]]
    if not complete:
        return NOT_AVAILABLE
    values = [r["latency_seconds"] for r in complete if r["latency_seconds"] is not None]
    base = {"n_start_complete": len(complete), "n_measured": len(values),
            "n_start_complete_not_detected": len(complete) - len(values)}
    if not values:
        return {**base, "note": "ningún episodio con inicio completo fue detectado"}
    if len(values) == 1:
        return {**base, "value_seconds": values[0],
                "note": "un solo episodio: se reporta el valor individual, sin media ni mediana"}
    return {**base, "values_seconds": values, "mean_seconds": statistics.fmean(values),
            "median_seconds": statistics.median(values), "min_seconds": min(values),
            "max_seconds": max(values)}


def match_alerts(alerts: list[dict], episodes: pd.DataFrame, W: float) -> list[dict]:
    """Cada alerta cubre ``[t_alert - W, t_last)``. Es falsa si no se solapa con ningún episodio definitivo."""
    out = []
    for a in alerts:
        ep = episodes[(episodes["capture_id"] == a["capture_id"]) & (episodes["t_start"] < a["t_last"])
                      & (episodes["t_end"] >= a["t_alert"] - W)].sort_values("t_start")
        matched = None if ep.empty else ep.iloc[0]
        out.append({**a, "matched_episode_id": None if matched is None else matched["episode_id"],
                    "attack_type_ref": None if matched is None else matched["attack_type"],
                    "is_false_alert": matched is None})
    return out


def normal_hours(ev: pd.DataFrame, episodes: pd.DataFrame, W: float) -> float | None:
    """Horas de tiempo normal evaluado: duración del conjunto sin purgas menos la duración de los episodios."""
    total = 0.0
    for cid, part in ev.groupby("capture_id"):
        span = float(part["t_end"].max() - part["t_end"].min()) + W
        ep = episodes[episodes["capture_id"] == cid]
        total += span - float((ep["t_end"] - ep["t_start"]).sum())
    return None if total <= 0 else total / 3600.0


def episode_metrics(results: list[dict], matched: list[dict], hours: float | None, types: list[str]) -> dict:
    n_false = sum(1 for a in matched if a["is_false_alert"])

    def block(rs: list[dict]) -> dict:
        n = len(rs)
        det = sum(1 for r in rs if r["detected"])
        return {"n_episodes": n, "n_detected": det, "detection_rate": _ratio(det, n),
                "latency": latency_summary(rs)}

    by_type = {}
    for t in types:
        rs = [r for r in results if r["attack_type_ref"] == t]
        by_type[t] = block(rs) if rs else NOT_AVAILABLE
    return {"global": block(results), "by_type": by_type, "n_alerts": len(matched),
            "n_false_alerts": n_false, "normal_hours_evaluated": hours,
            "false_alerts_per_hour": None if hours is None else n_false / hours,
            "episodes": results}


# --------------------------------------------------------------------------- figuras

def save_figures(ev: pd.DataFrame, episodes: pd.DataFrame, out_dir, split: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.metrics import precision_recall_curve

    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    if ev["y"].nunique() == 2:
        p, r, _ = precision_recall_curve(ev["y"], ev["score"])
        fig, ax = plt.subplots(figsize=(4, 3.2))
        ax.plot(r, p)
        ax.set_xlabel("Exhaustividad (recall)")
        ax.set_ylabel("Precisión (precision)")
        ax.set_title(f"Curva PR ({split})")
        fig.tight_layout()
        fig.savefig(fig_dir / f"pr_{split}.png", dpi=150)
        plt.close(fig)
    for cid, part in ev.groupby("capture_id"):
        fig, ax = plt.subplots(figsize=(7, 2.6))
        ax.plot(part["t_end"], part["score"], lw=0.8)
        for e in episodes[episodes["capture_id"] == cid].itertuples():
            ax.axvspan(e.t_start, e.t_end, alpha=0.2, color="tab:red")
        ax.set_xlabel("t_end (s)")
        ax.set_ylabel("puntuación")
        ax.set_title(f"Línea temporal {cid} ({split})")
        fig.tight_layout()
        fig.savefig(fig_dir / f"timeline_{cid}_{split}.png", dpi=150)
        plt.close(fig)


# --------------------------------------------------------------------------- ejecución

def run(cfg: dict, split: str, final: bool, *, figures: bool = False, check_git: bool = True) -> dict:
    started = E.now_iso()
    E.guard_split_access(cfg, split, final)
    exp_id = E.resolve_exp_id(cfg)
    marker = E.guard_final(cfg, exp_id, "evaluate", check_git=check_git) if final else None
    meta = E.load_metadata(E.model_dir(cfg, exp_id))
    W = float(meta["W_seconds"])
    types = attack_types(cfg["_data"])
    out_dir = E.results_dir(cfg, exp_id)

    windows = pd.read_parquet(meta["windows_file"])
    ref_cols = ["capture_id", "window_id", "y"] + [f"ref_{t}" for t in types]
    preds = pd.read_parquet(predictions_path(cfg, exp_id, split))
    ev = preds.merge(windows.loc[windows["split"] == split, ref_cols], on=["capture_id", "window_id"],
                     how="left", validate="one_to_one")
    if ev["y"].isna().any():
        raise ValueError("Hay predicciones sin ventana de referencia correspondiente.")
    ev.to_parquet(out_dir / f"eval_windows_{split}.parquet", index=False)

    m_window = {"global": window_metrics(ev["y"].to_numpy(), ev["y_pred"].to_numpy()),
                "by_type": window_metrics_by_type(ev, types)}
    E.write_json(out_dir / f"metrics_window_{split}.json", m_window)

    episodes = load_definitive(cfg, split, float(meta["T_seconds"]))
    target_ts = {cid: target_frames(load_frames(cfg["_data"], cid))["ts"].to_numpy()
                 for cid in ev["capture_id"].unique()}
    results = episode_results(episodes, preds, target_ts, W)
    matched = match_alerts(E.read_jsonl(alerts_path(cfg, exp_id, split)), episodes, W)
    E.write_jsonl(out_dir / f"eval_alerts_{split}.jsonl", matched)
    m_episode = episode_metrics(results, matched, normal_hours(ev, episodes, W), types)
    E.write_json(out_dir / f"metrics_episode_{split}.json", m_episode)
    if figures:
        save_figures(ev, episodes, out_dir, split)
    E.record_run(cfg, exp_id, "evaluate", split=split, started_at=started,
                 extra={"f1_window": m_window["global"]["f1"]})
    if marker:
        E.mark_final_done(marker)
    return {"window": m_window, "episode": {k: v for k, v in m_episode.items() if k != "episodes"}}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Evalúa predicciones y alertas.")
    ap.add_argument("--exp", required=True)
    ap.add_argument("--split", choices=("train", "val", "test"), required=True)
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--figures", action="store_true")
    args = ap.parse_args(argv)
    res = run(C.load_experiment(args.exp), args.split, args.final, figures=args.figures)
    g = res["window"]["global"]
    print(f"[evaluate] F1 por ventana = {g['f1']}; falsas alertas/h = {res['episode']['false_alerts_per_hour']}")


if __name__ == "__main__":
    main()
