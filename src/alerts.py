"""Fusiona ventanas positivas en eventos de alerta (plan, sección 8.7).

Regla: dos ventanas positivas ``i`` y ``j`` (``j`` posterior, misma captura) pertenecen al mismo
evento si ``t_end(j) - t_end(i) <= max_gap_seconds``. ``max_gap_seconds >= S``.

``alerts_<split>.jsonl`` guarda todos los eventos del detector y no declara el tipo de ataque (R11).
El enfriamiento no pertenece a este módulo y no afecta las métricas.
"""

from __future__ import annotations

import argparse

import pandas as pd

from . import config as C
from . import experiment as E
from .predict import predictions_path

ALERT_FIELDS = ("alert_id", "capture_id", "t_alert", "t_last", "n_windows", "max_score")


def merge_alerts(preds: pd.DataFrame, max_gap: float) -> list[dict]:
    alerts: list[dict] = []
    positives = preds[preds["y_pred"] == 1].sort_values(["capture_id", "t_end"])
    for cid, group in positives.groupby("capture_id", sort=True):
        current = None
        for t_end, score in zip(group["t_end"].to_numpy(), group["score"].to_numpy()):
            if current is not None and t_end - current["t_last"] <= max_gap + 1e-9:
                current["t_last"] = float(t_end)
                current["n_windows"] += 1
                current["max_score"] = max(current["max_score"], float(score))
                continue
            current = {"alert_id": None, "capture_id": str(cid), "t_alert": float(t_end),
                       "t_last": float(t_end), "n_windows": 1, "max_score": float(score)}
            alerts.append(current)
    for n, a in enumerate(sorted(alerts, key=lambda a: (a["t_alert"], a["capture_id"]))):
        a["alert_id"] = f"alert_{n:05d}"
    return sorted(alerts, key=lambda a: a["alert_id"])


def alerts_path(cfg: dict, exp_id: str, split: str):
    return E.results_dir(cfg, exp_id) / f"alerts_{split}.jsonl"


def run(cfg: dict, split: str, final: bool, *, check_git: bool = True):
    started = E.now_iso()
    E.guard_split_access(cfg, split, final)
    exp_id = E.resolve_exp_id(cfg)
    marker = E.guard_final(cfg, exp_id, "alerts", check_git=check_git) if final else None
    meta = E.load_metadata(E.model_dir(cfg, exp_id))
    preds = pd.read_parquet(predictions_path(cfg, exp_id, split))
    alerts = merge_alerts(preds, float(meta["alerts"]["max_gap_seconds"]))
    out = E.write_jsonl(alerts_path(cfg, exp_id, split), alerts)
    E.record_run(cfg, exp_id, "alerts", split=split, started_at=started, extra={"n_alerts": len(alerts)})
    if marker:
        E.mark_final_done(marker)
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Fusiona ventanas positivas en alertas.")
    ap.add_argument("--exp", required=True)
    ap.add_argument("--split", choices=("train", "val", "test"), required=True)
    ap.add_argument("--final", action="store_true")
    args = ap.parse_args(argv)
    print(f"[alerts] -> {run(C.load_experiment(args.exp), args.split, args.final)}")


if __name__ == "__main__":
    main()
