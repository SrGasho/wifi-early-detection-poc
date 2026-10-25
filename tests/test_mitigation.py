import pandas as pd

from src import mitigation_simulator as M
from tests.conftest import make_capture


def _alert(i, t, score=0.95):
    return {"alert_id": f"alert_{i:05d}", "capture_id": "cap_a", "t_alert": t, "t_last": t,
            "n_windows": 1, "max_score": score}


def _obs():
    return {"cap_a": M.client_pmf_observations(make_capture("cap_a", "deauth", 12, 7, bursts=[], duration=30))}


def test_cooldown_keeps_alerts_and_only_groups_notifications():
    alerts = [_alert(0, 100.0), _alert(1, 110.0), _alert(2, 200.0)]
    notes = M.simulate(alerts, _obs(), tau_high=0.9, cooldown=30.0)
    assert len(notes) == 2 and len(alerts) == 3
    covered = [a for n in notes for a in n["source_alert_ids"]]
    assert sorted(covered) == sorted(a["alert_id"] for a in alerts)
    assert notes[0]["source_alert_ids"] == ["alert_00000", "alert_00001"]


def test_mfpc_null_is_unknown_never_vulnerable():
    note = M.simulate([_alert(0, 100.0)], _obs(), tau_high=0.9, cooldown=0.0)[0]
    clients = note["clientes"]
    assert clients["no_compatibles"] == ["cli_nopmf"]
    assert clients["compatibles"] == ["cli_pmf"]
    assert clients["compatibilidad_desconocida"] == ["cli_unknown"]
    assert "cli_unknown" not in clients["no_compatibles"]


def test_observations_are_causal():
    note = M.simulate([_alert(0, 1.0)], _obs(), tau_high=0.9, cooldown=0.0)[0]
    assert all(not v for v in note["clientes"].values())  # nadie se había asociado en t = 1


def test_no_isolation_by_mac_and_fixed_event_type():
    notes = M.simulate([_alert(0, 100.0), _alert(1, 500.0, score=0.1)], _obs(), tau_high=0.9, cooldown=0.0)
    for n in notes:
        assert n["tipo_de_evento"] == "ataque_de_desconexion"
        for action in n["accion_simulada"]:
            assert not any(word in action["accion"] for word in M.FORBIDDEN_ACTIONS)
        assert {a["accion"] for a in n["accion_simulada"] if a["estado"] == "solo_diseno"} == set(M.DESIGN_ONLY)
    assert notes[0]["prioridad"] == "alta" and notes[1]["prioridad"] == "normal"
    _ = pd
