"""Fase 1: inventario e informe de AWID3. No modifica ``data/raw`` (R1).

Dos modos:

- ``--discover``: lista todos los archivos de ``data/raw`` con su tamaño y sus columnas. Sirve para
  completar ``captures`` y ``columns`` en ``configs/data.yaml`` sin suponer nombres.
- normal: recorre cada captura por bloques y cuenta nulos, etiquetas, subtipos, códigos de motivo,
  rango temporal y disponibilidad de campos. Genera ``inventory.json`` y ``report.md``.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import pandas as pd

from . import config as C
from . import data_loader
from .experiment import now_iso, write_json

QUESTIONS = (
    "¿Cuántas capturas independientes existen por ataque?",
    "¿Los eventos aparecen en tramos contiguos?",
    "¿Existen marcas temporales utilizables?",
    "¿Los clientes se reasocian después del evento?",
    "¿Existe un efecto observable que pueda utilizarse como referencia?",
    "¿Qué proporción de tramas tiene protección activada?",
    "¿Están disponibles wlan.seq, potencia de señal y códigos de motivo?",
    "¿Existen eventos legítimos de desautenticación o disociación?",
    "¿Las etiquetas separan difusión, ataques dirigidos y disociación?",
    "¿Qué campos son comunes a todas las capturas?",
    "¿Cada ataque es una ráfaga continua o contiene varias ráfagas separadas por silencios?",
    "¿Cuál es la banda y el canal de las capturas?",
    "¿Están disponibles mfpc y mfpr en asociación o reasociación?",
    "¿Qué otras características, como códigos de motivo, podrían actuar como sustitutos del subtipo?",
)


def discover(raw: Path) -> list[dict]:
    files = []
    for p in sorted(raw.rglob("*")):
        if not p.is_file() or p.name.startswith("."):
            continue
        entry = {"path": str(p.relative_to(raw)), "size_mb": round(p.stat().st_size / 2**20, 2)}
        if p.suffix.lower() == ".csv":
            try:
                cols = data_loader.read_header(p)
                entry.update({"n_columns": len(cols), "columns": cols})
            except Exception as exc:  # noqa: BLE001 - se informa, no se interrumpe el inventario
                entry["error"] = str(exc)
        files.append(entry)
    return files


def inspect_capture(data_cfg: dict, capture_id: str, max_rows: int | None) -> dict:
    files = data_loader.list_capture_files(data_cfg, capture_id)
    wanted = data_loader.mapped_columns(data_cfg)
    headers = {str(f.name): set(data_loader.read_header(f)) for f in files}
    present = {i: e for i, e in wanted.items() if all(e in h for h in headers.values())}
    rows, nulls = 0, Counter()
    labels, subtypes, reason_codes, protected = Counter(), Counter(), Counter(), Counter()
    ts_min, ts_max, inversions, last_ts = None, None, 0, None
    for _, chunk in data_loader.iter_chunks(data_cfg, capture_id, max_rows=max_rows):
        rows += len(chunk)
        nulls.update({c: int(chunk[c].isna().sum()) for c in chunk.columns})
        labels.update(chunk["label"].fillna("<nulo>").value_counts().to_dict())
        sub_col = "fc_subtype" if "fc_subtype" in chunk else "fc_type_subtype"
        if sub_col in chunk:
            subtypes.update(chunk[sub_col].fillna("<nulo>").value_counts().to_dict())
            if "reason_code" in chunk:
                disc = chunk[chunk[sub_col].isin(["10", "12", "0x0a", "0x0c", "0x000a", "0x000c"])]
                reason_codes.update(disc["reason_code"].fillna("<nulo>").value_counts().to_dict())
        if "protected" in chunk:
            protected.update(chunk["protected"].fillna("<nulo>").value_counts().to_dict())
        ts = pd.to_numeric(chunk["ts"], errors="coerce").dropna()
        if len(ts):
            ts_min = ts.min() if ts_min is None else min(ts_min, ts.min())
            ts_max = ts.max() if ts_max is None else max(ts_max, ts.max())
            inversions += int((ts.diff() < 0).sum())
            if last_ts is not None and ts.iloc[0] < last_ts:
                inversions += 1
            last_ts = ts.iloc[-1]
    return {
        "capture_id": capture_id,
        "files": [{"name": f.name, "size_mb": round(f.stat().st_size / 2**20, 2)} for f in files],
        "rows_read": rows,
        "sampled": max_rows is not None,
        "mapped_columns_present_in_all_files": present,
        "mapped_columns_missing": sorted(set(wanted) - set(present)),
        "null_fraction": {c: (n / rows if rows else None) for c, n in nulls.items()},
        "label_counts": dict(labels.most_common()),
        "subtype_counts": dict(subtypes.most_common(30)),
        "reason_codes_in_disconnection_frames": dict(reason_codes.most_common()),
        "protected_counts": dict(protected),
        "ts_min": None if ts_min is None else float(ts_min),
        "ts_max": None if ts_max is None else float(ts_max),
        "duration_seconds": None if ts_min is None else float(ts_max - ts_min),
        "ts_inversions": inversions,
    }


def write_report(inventory: dict, out: Path) -> None:
    lines = ["# Informe de inspección de AWID3", "", f"Generado: {inventory['created_at']}", ""]
    for cap in inventory["captures"]:
        lines += [f"## Captura `{cap['capture_id']}`", "",
                  f"- Archivos: {len(cap['files'])}; filas leídas: {cap['rows_read']}"
                  + (" (muestra)" if cap["sampled"] else ""),
                  f"- Rango temporal: {cap['ts_min']} – {cap['ts_max']} ({cap['duration_seconds']} s); "
                  f"inversiones de orden: {cap['ts_inversions']}",
                  f"- Columnas mapeadas ausentes: {cap['mapped_columns_missing'] or 'ninguna'}",
                  "", "| Etiqueta | Tramas |", "|---|---|"]
        lines += [f"| {k} | {v} |" for k, v in cap["label_counts"].items()]
        lines += ["", "| Columna | Fracción nula |", "|---|---|"]
        lines += [f"| {k} | {v:.4f} |" for k, v in cap["null_fraction"].items() if v is not None]
        lines += ["", f"Códigos de motivo en desconexiones: {cap['reason_codes_in_disconnection_frames']}", ""]
    lines += ["## Preguntas de exploración", "",
              "Responder cada pregunta en `docs/datos-awid3.md` citando este informe o el notebook.", ""]
    lines += [f"{i}. {q}" for i, q in enumerate(QUESTIONS, start=1)]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Inventario e informe de AWID3 (Fase 1).")
    ap.add_argument("--data", required=True)
    ap.add_argument("--discover", action="store_true", help="Listar archivos y columnas de data/raw")
    ap.add_argument("--max-rows", type=int, help="Leer solo una muestra por captura")
    ap.add_argument("--out", default="results/inspection")
    args = ap.parse_args(argv)
    data_cfg = C.load_data_config(args.data)
    out = C.resolve_path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.discover:
        files = discover(C.data_path(data_cfg, "raw"))
        write_json(out / "discover.json", {"created_at": now_iso(), "files": files})
        for f in files:
            print(f"{f['path']}  {f['size_mb']} MB  columnas={f.get('n_columns', '-')}")
        return
    inventory = {"created_at": now_iso(), "captures": [
        inspect_capture(data_cfg, cid, args.max_rows) for cid in C.capture_ids(data_cfg)]}
    write_json(out / "inventory.json", inventory)
    write_report(inventory, out / "report.md")
    print(f"[inspect_data] -> {out / 'report.md'}")


if __name__ == "__main__":
    main()
