"""Pruebas del script de apoyo scripts/analisis_fase1.py (Fase 1).

El script lee CSV crudo con data_loader.iter_chunks, así que el proyecto temporal
escribe dos CSV mínimos con la estructura de AWID3 (solo las columnas mapeadas) en
lugar de parquet. No requiere AWID3 ni la sal de anonimización.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from scripts import analisis_fase1 as A
from src import config as C


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def _raw_capture(attack: str, subtype: int) -> pd.DataFrame:
    """CSV crudo mínimo: balizas normales (ts con decimales) + ataque (ts entero)."""
    rows = []
    # Normales: balizas (subtipo 8) con ts fraccionario.
    for i, t in enumerate(np.arange(0.0, 30.0, 0.1)):
        rows.append({"frame.time_epoch": f"{1000.0 + t:.4f}", "wlan.fc.type": "0",
                     "wlan.fc.subtype": "8", "wlan.sa": "ap:00", "wlan.da": "ff:ff:ff:ff:ff:ff",
                     "wlan.bssid": "ap:00", "wlan.fixed.reason_code": "", "wlan.seq": str(i % 4096),
                     "radiotap.dbm_antsignal": "-40", "wlan.fc.protected": "0", "Label": "Normal"})
    # Una desconexión legítima aislada (Normal, sin src).
    rows.append({"frame.time_epoch": "1005.0", "wlan.fc.type": "0", "wlan.fc.subtype": "12",
                 "wlan.sa": "", "wlan.da": "", "wlan.bssid": "", "wlan.fixed.reason_code": "",
                 "radiotap.dbm_antsignal": "-50", "wlan.fc.protected": "0", "wlan.seq": "1", "Label": "Normal"})
    # Ataque: ráfaga densa de subtipo de desconexión, ts ENTERO, reason_code 7.
    for t in range(1050, 1070):
        for _ in range(10):
            rows.append({"frame.time_epoch": f"{t}", "wlan.fc.type": "0",
                         "wlan.fc.subtype": str(subtype), "wlan.sa": "ap:00",
                         "wlan.da": "ff:ff:ff:ff:ff:ff", "wlan.bssid": "ap:00",
                         "wlan.fixed.reason_code": "7", "wlan.seq": "2",
                         "radiotap.dbm_antsignal": "-70", "wlan.fc.protected": "0", "Label": attack})
    return pd.DataFrame(rows)


@pytest.fixture
def proyecto_csv(tmp_path):
    """Proyecto temporal con dos capturas en CSV crudo y data.yaml apuntando a ellas."""
    root = tmp_path
    raw = root / "data/raw"
    (raw / "a").mkdir(parents=True)
    (raw / "b").mkdir(parents=True)
    _raw_capture("Deauth", 12).to_csv(raw / "a" / "cap0.csv", index=False)
    _raw_capture("Disas", 10).to_csv(raw / "b" / "cap0.csv", index=False)
    data = {
        "paths": {"raw": str(raw), "interim": str(root / "data/interim"),
                  "processed": str(root / "data/processed")},
        "captures": [{"id": "cap_a", "pattern": "a/*.csv"}, {"id": "cap_b", "pattern": "b/*.csv"}],
        "columns": {"ts": "frame.time_epoch", "fc_type": "wlan.fc.type",
                    "fc_subtype": "wlan.fc.subtype", "src": "wlan.sa", "dst": "wlan.da",
                    "bssid": "wlan.bssid", "reason_code": "wlan.fixed.reason_code",
                    "seq": "wlan.seq", "signal_dbm": "radiotap.dbm_antsignal",
                    "protected": "wlan.fc.protected", "label": "Label"},
        "labels": {"target": {"deauth": "Deauth", "disas": "Disas"}, "normal": ["Normal"]},
        "anonymization": {"salt_env_var": "WIFI_ML_SALT_TEST"},
    }
    cfg_path = _write_yaml(root / "configs/data.yaml", data)
    return {"root": root, "data_cfg": C.load_data_config(cfg_path)}


def _args(out: Path, T: float = 2.0):
    class _A:
        pass
    a = _A()
    a.T = T
    a.out = str(out)
    return a


def test_short_anonimiza_y_maneja_nulos():
    assert A.short("AA:BB:CC:DD:EE:FF") == A.short("aa:bb:cc:dd:ee:ff")  # insensible a mayúsculas
    assert len(A.short("aa:bb:cc:dd:ee:ff")) == 8
    assert A.short(None) == "nulo"
    assert A.short("") == "nulo"


def test_targets_usa_valores_no_claves(proyecto_csv):
    # Regresión: el bug corregido leía las CLAVES de labels.target (deauth/disas)
    # en vez de sus VALORES (Deauth/Disas).
    assert A._targets(proyecto_csv["data_cfg"]) == ["Deauth", "Disas"]


def test_mode_timestamp_ataque_entero_normal_fraccionario(proyecto_csv):
    lines = A.mode_timestamp(proyecto_csv["data_cfg"], _args(proyecto_csv["root"]))
    texto = "\n".join(lines)
    assert "cap_a" in texto and "cap_b" in texto
    # El ataque (subtipo 12/10) debe tener fracción de ts entero = 1.0000.
    assert "| Deauth | 12 |" in texto
    for ln in lines:
        if "| Deauth | 12 |" in ln:
            assert ln.strip().endswith("1.0000 |")
    # Las balizas Normal (subtipo 8) tienen ts mayormente fraccionario: fracción baja (< 0.5),
    # claramente distinta del 1.0000 del ataque. (1 de cada 10 balizas cae en entero por el paso 0.1.)
    for ln in lines:
        if "| Normal | 8 |" in ln:
            frac = float(ln.strip().rstrip("|").strip().split("|")[-1])
            assert frac < 0.5


def test_mode_cruce_reason7_solo_en_ataque(proyecto_csv):
    lines = A.mode_cruce(proyecto_csv["data_cfg"], _args(proyecto_csv["root"]))
    texto = "\n".join(lines)
    assert "Subtipo por etiqueta" in texto
    assert "Origen de las desconexiones etiquetadas como normales" in texto
    # El motivo 7 aparece en el ataque (deauth/disas), no en Normal.
    assert "| Deauth | 12 | 7 |" in texto or "| Disas | 10 | 7 |" in texto


def test_mode_linea_una_rafaga_contigua(proyecto_csv):
    lines = A.mode_linea(proyecto_csv["data_cfg"], _args(proyecto_csv["root"]))
    texto = "\n".join(lines)
    assert "Tramas objetivo: 200" in texto  # 20 s * 10 tramas/s
    assert "Racha máxima de bloques vacíos: 0" in texto  # ráfaga sin huecos


def test_mode_reasociacion_corre_sin_error(proyecto_csv):
    lines = A.mode_reasociacion(proyecto_csv["data_cfg"], _args(proyecto_csv["root"]))
    texto = "\n".join(lines)
    assert "Reasociaciones alrededor de cada episodio" in texto
    assert "cap_a" in texto


def test_main_escribe_archivo(proyecto_csv, tmp_path):
    out = tmp_path / "salida"
    A.main(["--data", proyecto_csv["data_cfg"]["_path"], "--modo", "timestamp", "--out", str(out)])
    assert (out / "analisis_timestamp.txt").exists()
