"""Mitigación simulada (plan, sección 8.9). Solo escribe registros; nunca ejecuta acciones de red (R9).

- ``alerts_<split>.jsonl`` conserva todas las alertas. El enfriamiento solo agrupa notificaciones:
  cada notificación lista en ``source_alert_ids`` todas las alertas que absorbió.
- Nunca se aísla una fuente por su MAC: puede estar suplantada.
- ``mfpc = 0`` -> no compatible con PMF; ``mfpc = 1`` -> compatible; nulo -> compatibilidad desconocida.
- ``tipo_de_evento`` siempre es ``ataque_de_desconexion`` (R11).
- ``latencia_de_respuesta`` es un dato del flujo, no una medida de eficacia.
"""

from __future__ import annotations

import argparse
import time

import numpy as np
import pandas as pd

from . import config as C
from . import experiment as E
from .alerts import alerts_path
from .feature_engineering import load_frames
from .preprocessing import TYPE_MGMT

EVENT_TYPE = "ataque_de_desconexion"
ASSOC_SUBTYPES = (0, 2)  # solicitud de asociación y de reasociación
DESIGN_ONLY = ("cambio_de_canal", "localizacion_aproximada_rssi")
FORBIDDEN_ACTIONS = ("aislar", "bloquear", "desautenticar", "expulsar")


def client_pmf_observations(frames: pd.DataFrame) -> pd.DataFrame:
    """Clientes vistos en (re)asociación con su ``mfpc`` y la marca de tiempo de cada observación."""
    mask = (frames["fc_type"] == TYPE_MGMT) & frames["fc_subtype"].isin(ASSOC_SUBTYPES) & frames["src_anon"].notna()
    obs = frames.loc[mask, ["ts", "src_anon", "mfpc"]].sort_values("ts", kind="mergesort")
    return obs.reset_index(drop=True)


def pmf_status_at(obs: pd.DataFrame, t: float) -> dict[str, list[str]]:
    """Estado de compatibilidad de cada cliente usando solo observaciones anteriores a ``t`` (causal)."""
    past = obs[obs["ts"] < t]
    status: dict[str, bool | None] = {}
    for client, mfpc in zip(past["src_anon"], past["mfpc"]):
        if mfpc is pd.NA or mfpc is None or (isinstance(mfpc, float) and np.isnan(mfpc)):
            status.setdefault(client, None)
        else:
            status[client] = bool(mfpc)
    return {
        "compatibles": sorted(c for c, s in status.items() if s is True),
        "no_compatibles": sorted(c for c, s in status.items() if s is False),
        "compatibilidad_desconocida": sorted(c for c, s in status.items() if s is None),
    }


def simulate(alerts: list[dict], observations: dict[str, pd.DataFrame], *, tau_high: float,
             cooldown: float) -> list[dict]:
    notifications: list[dict] = []
    last: dict[str, dict] = {}
    for a in sorted(alerts, key=lambda x: (x["t_alert"], x["alert_id"])):
        t0 = time.perf_counter()
        cid = a["capture_id"]
        prev = last.get(cid)
        if prev is not None and a["t_alert"] - prev["hora_de_alerta"] < cooldown:
            prev["source_alert_ids"].append(a["alert_id"])
            prev["confianza"] = max(prev["confianza"], float(a["max_score"]))
            continue
        high = float(a["max_score"]) >= tau_high
        clients = pmf_status_at(observations.get(cid, pd.DataFrame(columns=["ts", "src_anon", "mfpc"])),
                                a["t_alert"])
        acciones = [{"accion": "registrar_evento", "estado": "simulada"},
                    {"accion": "notificar_administrador", "estado": "simulada"}]
        if high:
            acciones.append({"accion": "recomendar_pmf_clientes_compatibles", "estado": "simulada"})
        if clients["no_compatibles"]:
            acciones.append({"accion": "listar_clientes_no_compatibles_pmf", "estado": "simulada"})
        acciones.extend({"accion": name, "estado": "solo_diseno"} for name in DESIGN_ONLY)
        note = {
            "notification_id": f"notif_{len(notifications):05d}",
            "alert_id": a["alert_id"],
            "source_alert_ids": [a["alert_id"]],
            "capture_id": cid,
            "hora_de_alerta": float(a["t_alert"]),
            "tipo_de_evento": EVENT_TYPE,
            "confianza": float(a["max_score"]),
            "prioridad": "alta" if high else "normal",
            "accion_simulada": acciones,
            "clientes": clients,
            "resultado": "registrado",
        }
        note["latencia_de_respuesta"] = time.perf_counter() - t0
        notifications.append(note)
        last[cid] = note
    return notifications


def run(cfg: dict, split: str, final: bool, *, check_git: bool = True) -> dict:
    started = E.now_iso()
    E.guard_split_access(cfg, split, final)
    exp_id = E.resolve_exp_id(cfg)
    marker = E.guard_final(cfg, exp_id, "mitigation", check_git=check_git) if final else None
    tau_high = float(C.require(cfg, "mitigation.tau_high"))
    cooldown = float(C.require(cfg, "mitigation.cooldown_seconds"))
    alerts = E.read_jsonl(alerts_path(cfg, exp_id, split))
    observations = {cid: client_pmf_observations(load_frames(cfg["_data"], cid))
                    for cid in sorted({a["capture_id"] for a in alerts})}
    notes = simulate(alerts, observations, tau_high=tau_high, cooldown=cooldown)
    E.write_jsonl(E.results_dir(cfg, exp_id) / f"mitigation_log_{split}.jsonl", notes)
    summary = {"n_alerts": len(alerts), "n_notifications": len(notes),
               "n_alerts_absorbed_by_cooldown": len(alerts) - len(notes)}
    E.record_run(cfg, exp_id, "mitigation", split=split, started_at=started, extra=summary)
    if marker:
        E.mark_final_done(marker)
    return summary


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Mitigación simulada (solo registros).")
    ap.add_argument("--exp", required=True)
    ap.add_argument("--split", choices=("train", "val", "test"), required=True)
    ap.add_argument("--final", action="store_true")
    args = ap.parse_args(argv)
    print(f"[mitigation] {run(C.load_experiment(args.exp), args.split, args.final)}")


if __name__ == "__main__":
    main()
