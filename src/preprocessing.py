"""Convierte AWID3 al formato interno del proyecto (plan, sección 5.1).

- Tipos explícitos; los valores no convertibles pasan a nulo y se cuentan.
- Duplicados exactos se eliminan y se cuentan.
- Orden por ``ts`` dentro de cada captura.
- Anonimización HMAC-SHA256 con sal en variable de entorno; ``BROADCAST`` se conserva.
- Las MAC originales no salen de ``data/raw`` (R1).
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import os

import numpy as np
import pandas as pd

from . import config as C
from . import data_loader
from .experiment import now_iso, write_json

BROADCAST = "BROADCAST"
BROADCAST_MAC = "ff:ff:ff:ff:ff:ff"
SUBTYPE_DISAS = 10
SUBTYPE_DEAUTH = 12
TYPE_MGMT = 0
TYPE_DATA = 2

INTERNAL_COLUMNS = [
    "ts", "capture_id", "file_idx", "frame_number", "fc_type", "fc_subtype",
    "src_anon", "dst_anon", "bssid_anon", "is_broadcast_dst", "reason_code", "seq",
    "signal_dbm", "protected", "mfpc", "mfpr", "label_raw", "is_target", "attack_type",
]
REFERENCE_COLUMNS = ("label_raw", "is_target", "attack_type")


# --------------------------------------------------------------------------- conversión

def to_float(series: pd.Series) -> tuple[pd.Series, int]:
    out = pd.to_numeric(series, errors="coerce")
    bad = int((out.isna() & series.notna()).sum())
    return out.astype("float64"), bad


def to_int(series: pd.Series) -> tuple[pd.Series, int]:
    """Acepta decimal, hexadecimal ``0x..`` y valores tipo ``12.0``. Devuelve Int64 con nulos."""
    s = series.astype("string").str.strip()
    is_hex = s.str.lower().str.startswith("0x", na=False)
    out = pd.Series(pd.NA, index=s.index, dtype="Float64")
    if is_hex.any():
        out[is_hex] = s[is_hex].map(lambda v: float(int(v, 16)) if _is_hex(v) else np.nan)
    rest = ~is_hex & s.notna()
    out[rest] = pd.to_numeric(s[rest], errors="coerce")
    whole = out.notna() & (out % 1 == 0)
    bad = int((s.notna() & ~whole).sum())
    result = out.where(whole).astype("Int64")
    return result, bad


def _is_hex(v: str) -> bool:
    try:
        int(v, 16)
        return True
    except (TypeError, ValueError):
        return False


_TRUE = {"1", "true", "t", "yes", "y", "1.0"}
_FALSE = {"0", "false", "f", "no", "n", "0.0"}


def to_bool(series: pd.Series) -> tuple[pd.Series, int]:
    s = series.astype("string").str.strip().str.lower()
    out = pd.Series(pd.NA, index=s.index, dtype="boolean")
    out[s.isin(_TRUE)] = True
    out[s.isin(_FALSE)] = False
    bad = int((s.notna() & out.isna()).sum())
    return out, bad


# --------------------------------------------------------------------------- anonimización

def load_salt(data_cfg: dict) -> bytes:
    var = C.require(data_cfg, "anonymization.salt_env_var")
    salt = os.environ.get(var)
    if not salt:
        raise C.ConfigError(
            f"Defina la variable de entorno {var} con la sal de anonimización. La sal no se guarda en el repositorio."
        )
    return salt.encode("utf-8")


def anonymize(series: pd.Series, salt: bytes) -> pd.Series:
    def _one(mac):
        if mac is None or (isinstance(mac, float) and np.isnan(mac)) or mac is pd.NA:
            return None
        m = str(mac).strip().lower()
        if not m:
            return None
        if m == BROADCAST_MAC:
            return BROADCAST
        return hmac.new(salt, m.encode("utf-8"), hashlib.sha256).hexdigest()[:12]

    unique = pd.unique(series.dropna())
    mapping = {u: _one(u) for u in unique}
    return series.map(mapping).astype("object")


# --------------------------------------------------------------------------- normalización

def normalize_chunk(chunk: pd.DataFrame, *, capture_id: str, file_idx: int, data_cfg: dict,
                    salt: bytes, counters: dict) -> pd.DataFrame:
    """Convierte un bloque con nombres internos (texto) al formato interno."""
    out = pd.DataFrame(index=chunk.index)

    def count(name: str, n: int) -> None:
        counters["unconvertible"][name] = counters["unconvertible"].get(name, 0) + n

    out["ts"], n = to_float(chunk["ts"])
    count("ts", n)
    out["capture_id"] = capture_id
    out["file_idx"] = np.int32(file_idx)
    if "frame_number" in chunk:
        out["frame_number"], n = to_int(chunk["frame_number"])
        count("frame_number", n)
    else:
        out["frame_number"] = pd.array([pd.NA] * len(chunk), dtype="Int64")

    if "fc_type_subtype" in chunk and "fc_subtype" not in chunk:
        # Hipótesis a confirmar en la Fase 1: type_subtype = (tipo << 4) | subtipo.
        ts_val, n = to_int(chunk["fc_type_subtype"])
        count("fc_type_subtype", n)
        out["fc_type"] = (ts_val // 16).astype("Int64")
        out["fc_subtype"] = (ts_val % 16).astype("Int64")
    else:
        out["fc_subtype"], n = to_int(chunk["fc_subtype"])
        count("fc_subtype", n)
        if "fc_type" in chunk:
            out["fc_type"], n = to_int(chunk["fc_type"])
            count("fc_type", n)
        else:
            out["fc_type"] = pd.array([pd.NA] * len(chunk), dtype="Int64")

    for internal in ("src", "dst", "bssid"):
        if internal in chunk:
            out[f"{internal}_anon"] = anonymize(chunk[internal], salt)
        else:
            out[f"{internal}_anon"] = None
    out["is_broadcast_dst"] = out["dst_anon"].eq(BROADCAST).fillna(False).astype(bool)

    for internal in ("reason_code", "seq"):
        if internal in chunk:
            out[internal], n = to_int(chunk[internal])
            count(internal, n)
        else:
            out[internal] = pd.array([pd.NA] * len(chunk), dtype="Int64")
    if "signal_dbm" in chunk:
        out["signal_dbm"], n = to_float(chunk["signal_dbm"])
        count("signal_dbm", n)
    else:
        out["signal_dbm"] = np.nan
    for internal in ("protected", "mfpc", "mfpr"):
        if internal in chunk:
            out[internal], n = to_bool(chunk[internal])
            count(internal, n)
        else:
            out[internal] = pd.array([pd.NA] * len(chunk), dtype="boolean")

    label = chunk["label"].astype("string").str.strip()
    target_map = {str(v): str(k) for k, v in data_cfg["labels"]["target"].items()}
    normal_labels = {str(v) for v in data_cfg["labels"]["normal"]}
    out["label_raw"] = label.astype("object")
    out["is_target"] = label.isin(list(target_map)).fillna(False).astype(bool)
    attack = label.map(target_map)
    attack = attack.where(attack.notna(), np.where(label.isin(list(normal_labels)), "normal", "other"))
    out["attack_type"] = attack.astype("object")
    return out[INTERNAL_COLUMNS]


def finalize_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ("fc_type", "fc_subtype", "reason_code", "seq"):
        df[col] = df[col].astype("Int16")
    df["frame_number"] = df["frame_number"].astype("Int64")
    df["signal_dbm"] = df["signal_dbm"].astype("float32")
    for col in ("protected", "mfpc", "mfpr"):
        df[col] = df[col].astype("boolean")
    for col in ("capture_id", "src_anon", "dst_anon", "bssid_anon", "label_raw", "attack_type"):
        df[col] = df[col].astype("object")
    return df


def clean_capture(df: pd.DataFrame, counters: dict) -> pd.DataFrame:
    n0 = len(df)
    df = df[df["ts"].notna()]
    counters["dropped_null_ts"] = n0 - len(df)
    n1 = len(df)
    df = df.drop_duplicates()
    counters["dropped_duplicates"] = n1 - len(df)
    ts = df["ts"].to_numpy()
    counters["ts_inversions_before_sort"] = int(np.sum(np.diff(ts) < 0)) if len(ts) > 1 else 0
    df = df.sort_values(["ts", "file_idx", "frame_number"], kind="mergesort").reset_index(drop=True)
    counters["rows_out"] = len(df)
    counters["label_counts"] = {str(k): int(v) for k, v in df["label_raw"].value_counts(dropna=False).items()}
    counters["attack_type_counts"] = {str(k): int(v) for k, v in df["attack_type"].value_counts().items()}
    return df


def frames_path(data_cfg: dict, capture_id: str):
    return C.data_path(data_cfg, "interim") / f"frames_{capture_id}.parquet"


def preprocess_capture(data_cfg: dict, capture_id: str, *, max_rows: int | None = None) -> dict:
    salt = load_salt(data_cfg)
    counters = {"capture_id": capture_id, "unconvertible": {}, "rows_in": 0}
    parts = []
    for file_idx, chunk in data_loader.iter_chunks(data_cfg, capture_id, max_rows=max_rows):
        counters["rows_in"] += len(chunk)
        parts.append(normalize_chunk(chunk, capture_id=capture_id, file_idx=file_idx,
                                     data_cfg=data_cfg, salt=salt, counters=counters))
    df = finalize_types(pd.concat(parts, ignore_index=True))
    df = clean_capture(df, counters)
    out = frames_path(data_cfg, capture_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    counters["output"] = str(out)
    return counters


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Normaliza AWID3 al formato interno.")
    ap.add_argument("--data", required=True)
    ap.add_argument("--capture", help="Solo una captura")
    ap.add_argument("--max-rows", type=int, help="Procesar solo una muestra (prueba)")
    args = ap.parse_args(argv)
    data_cfg = C.load_data_config(args.data)
    if C.contains_placeholder(data_cfg["labels"]) or C.contains_placeholder(data_cfg["columns"]):
        raise C.ConfigError("data.yaml aún tiene columnas o etiquetas pendientes (< >). Complete la Fase 1.")
    captures = [args.capture] if args.capture else C.capture_ids(data_cfg)
    summary = {"created_at": now_iso(), "captures": []}
    for cid in captures:
        info = preprocess_capture(data_cfg, cid, max_rows=args.max_rows)
        summary["captures"].append(info)
        print(f"[preprocessing] {cid}: {info['rows_out']} tramas -> {info['output']}")
    write_json(C.data_path(data_cfg, "interim") / "preprocessing_summary.json", summary)


if __name__ == "__main__":
    main()
