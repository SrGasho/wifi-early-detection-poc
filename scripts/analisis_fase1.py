"""Análisis de apoyo para la Fase 1 de AWID3. No forma parte del flujo de src/.

Uso desde la raíz del repositorio:
    python -m scripts.analisis_fase1 --data configs/data.yaml --modo timestamp

Modos:
    timestamp      fracción de marcas de tiempo enteras por etiqueta y subtipo
    cruce          subtipo x etiqueta, código de motivo, protección y origen de desconexiones
    linea          línea de tiempo de las tramas objetivo (bloques de 10 s)
    reasociacion   solicitudes de (re)asociación antes y después de cada episodio

Escribe results/inspection/analisis_<modo>.txt. Solo lee data/raw (R1).
Las direcciones MAC aparecen solo como hash corto de 8 caracteres.
"""

from __future__ import annotations

import argparse
import hashlib

import numpy as np
import pandas as pd

from src import config as C
from src import data_loader
from src.preprocessing import to_bool, to_float, to_int

BROADCAST_MAC = "ff:ff:ff:ff:ff:ff"
DISCONN_SUBTYPES = (10, 12)    # disas, deauth
ASSOC_REQ_SUBTYPES = (0, 2)    # solicitudes de asociación y reasociación (las envía el cliente)
ASSOC_SUBTYPES = (0, 1, 2, 3)  # solicitudes y respuestas de asociación y reasociación
WINDOW_S = 60.0                # ventana para contar reasociaciones alrededor de cada episodio
BIN_S = 10.0                   # resolución de la línea de tiempo


def short(mac) -> str:
    if not isinstance(mac, str) or not mac:
        return "nulo"
    return hashlib.sha256(mac.lower().encode("utf-8")).hexdigest()[:8]


def _col(chunk: pd.DataFrame, name: str) -> pd.Series:
    if name in chunk:
        return chunk[name]
    return pd.Series(pd.NA, index=chunk.index, dtype="object")


def load_rows(data_cfg: dict, capture_id: str):
    """Bloques con columnas tipadas: ts, label, subtype, src, bcast, reason, protected."""
    for _, chunk in data_loader.iter_chunks(data_cfg, capture_id):
        df = pd.DataFrame(index=chunk.index)
        df["ts"], _ = to_float(chunk["ts"])
        df["label"] = chunk["label"].astype("string").str.strip().fillna("<nulo>").astype("object")
        sub, _ = to_int(_col(chunk, "fc_subtype"))
        df["subtype"] = sub.fillna(-1).astype("int64")
        df["src"] = _col(chunk, "src").astype("object")
        dst = _col(chunk, "dst").astype("string").str.lower()
        df["bcast"] = dst.eq(BROADCAST_MAC).fillna(False).astype(bool)
        reason, _ = to_int(_col(chunk, "reason_code"))
        df["reason"] = reason.astype("string").fillna("<nulo>").astype("object")
        prot, _ = to_bool(_col(chunk, "protected"))
        df["protected"] = prot.astype("string").fillna("<nulo>").astype("object")
        yield df


def _acc(total, part):
    return part if total is None else total.add(part, fill_value=0)


def _targets(data_cfg: dict) -> list[str]:
    return [str(v) for v in data_cfg["labels"]["target"].values()]


# ----------------------------------------------------------------------------- modos

def mode_timestamp(data_cfg: dict, args) -> list[str]:
    lines = ["# Marcas de tiempo enteras por etiqueta y subtipo", ""]
    for cid in C.capture_ids(data_cfg):
        total = None
        for df in load_rows(data_cfg, cid):
            df = df.dropna(subset=["ts"])
            part = pd.DataFrame({
                "label": df["label"],
                "subtype": df["subtype"],
                "entero": (df["ts"] % 1 == 0).astype("int64"),
                "n": 1,
            })
            total = _acc(total, part.groupby(["label", "subtype"]).sum())
        lines += [f"## {cid}", "", "| Etiqueta | Subtipo | Tramas | Ts enteros | Fracción |",
                  "|---|---|---|---|---|"]
        for (lab, sub), row in total.iterrows():
            frac = row["entero"] / row["n"] if row["n"] else 0.0
            lines.append(f"| {lab} | {sub} | {int(row['n'])} | {int(row['entero'])} | {frac:.4f} |")
        lines.append("")
    return lines


def mode_cruce(data_cfg: dict, args) -> list[str]:
    normal = {str(v) for v in data_cfg["labels"]["normal"]}
    lines = ["# Cruce de tramas por etiqueta, subtipo, motivo, protección y destino", ""]
    for cid in C.capture_ids(data_cfg):
        total, srcs = None, None
        for df in load_rows(data_cfg, cid):
            g = df.assign(n=1).groupby(["label", "subtype", "reason", "protected", "bcast"])["n"].sum()
            total = _acc(total, g)
            d = df[df["subtype"].isin(DISCONN_SUBTYPES) & df["label"].isin(list(normal))]
            srcs = _acc(srcs, d["src"].map(short).value_counts())
        t = total.reset_index()
        lines += [f"## {cid}", "", "### Subtipo por etiqueta", "",
                  "| Etiqueta | Subtipo | Tramas |", "|---|---|---|"]
        for (lab, sub), n in t.groupby(["label", "subtype"])["n"].sum().items():
            lines.append(f"| {lab} | {sub} | {int(n)} |")
        dis = t[t["subtype"].isin(DISCONN_SUBTYPES)].sort_values("n", ascending=False).head(60)
        lines += ["", "### Desconexiones: motivo, protección y broadcast (60 filas principales)", "",
                  "| Etiqueta | Subtipo | Motivo | Protegida | Broadcast | Tramas |",
                  "|---|---|---|---|---|---|"]
        for _, r in dis.iterrows():
            lines.append(f"| {r['label']} | {r['subtype']} | {r['reason']} | {r['protected']} | "
                         f"{r['bcast']} | {int(r['n'])} |")
        lines += ["", "### Origen de las desconexiones etiquetadas como normales", ""]
        if srcs is None or srcs.empty:
            lines.append("Sin desconexiones etiquetadas como normales.")
        else:
            top = srcs.sort_values(ascending=False)
            lines += [f"- Fuentes distintas (hash): {len(srcs)}",
                      f"- Tramas: {int(srcs.sum())}",
                      f"- Parte de las tramas que aportan las 10 fuentes principales: "
                      f"{top.head(10).sum() / srcs.sum():.4f}",
                      "- 10 fuentes principales (hash: tramas): "
                      + ", ".join(f"{k}: {int(v)}" for k, v in top.head(10).items())]
        lines.append("")
    return lines


def mode_linea(data_cfg: dict, args) -> list[str]:
    lines = ["# Línea de tiempo de tramas objetivo", "", f"Bloques de {BIN_S:.0f} s.", ""]
    targets = _targets(data_cfg)
    for cid in C.capture_ids(data_cfg):
        parts = []
        for df in load_rows(data_cfg, cid):
            m = df["label"].isin(targets).to_numpy()
            parts.append(df.loc[m, "ts"].dropna().to_numpy())
        ts = np.sort(np.concatenate(parts)) if parts else np.array([])
        lines.append(f"## {cid}")
        lines.append("")
        if ts.size < 2:
            lines += ["Menos de dos tramas objetivo.", ""]
            continue
        gaps = np.diff(ts)
        bins = np.floor((ts - ts[0]) / BIN_S).astype(int)
        counts = np.bincount(bins)
        occupied = counts[counts > 0]
        max_run = run = 0
        for empty in counts == 0:
            run = run + 1 if empty else 0
            max_run = max(max_run, run)
        lines += [
            f"- Tramas objetivo: {ts.size}",
            f"- Duración entre la primera y la última: {ts[-1] - ts[0]:.1f} s",
            f"- Brecha entre tramas objetivo: máxima {gaps.max():.1f} s; mediana {np.median(gaps):.1f} s; "
            f"percentil 99 {np.percentile(gaps, 99):.1f} s",
            f"- Bloques de {BIN_S:.0f} s con tramas objetivo: {occupied.size} de {counts.size} "
            f"({occupied.size / counts.size:.4f})",
            f"- Racha máxima de bloques vacíos: {max_run}",
            f"- Tramas por bloque ocupado: mínimo {occupied.min()}, mediana {np.median(occupied):.0f}, "
            f"máximo {occupied.max()}",
            "",
        ]
    return lines


def mode_reasociacion(data_cfg: dict, args) -> list[str]:
    lines = [
        "# Reasociaciones alrededor de cada episodio", "",
        f"Episodio: tramas objetivo separadas por más de T = {args.T} s. Ventana de {WINDOW_S:.0f} s "
        "antes y después. Se cuentan solicitudes de (re)asociación (subtipos 0 y 2) y clientes "
        "distintos (hash).",
        "Referencia: ventanas de la misma captura sin tramas objetivo. Con una sola captura por ataque, "
        "la referencia no es tráfico independiente.", "",
    ]
    targets = _targets(data_cfg)
    for cid in C.capture_ids(data_cfg):
        att_parts, mg = [], []
        for df in load_rows(data_cfg, cid):
            m = df["label"].isin(targets).to_numpy()
            att_parts.append(df.loc[m, "ts"].dropna().to_numpy())
            mm = df["subtype"].isin(ASSOC_SUBTYPES).to_numpy()
            mg.append(df.loc[mm, ["ts", "subtype", "src"]].dropna(subset=["ts"]))
        att = np.sort(np.concatenate(att_parts)) if att_parts else np.array([])
        lines.append(f"## {cid}")
        lines.append("")
        if att.size == 0:
            lines += ["Sin tramas objetivo.", ""]
            continue
        mgmt = pd.concat(mg, ignore_index=True).sort_values("ts", kind="mergesort").reset_index(drop=True)
        mgmt["client"] = mgmt["src"].map(short)
        mts = mgmt["ts"].to_numpy()
        is_req = mgmt["subtype"].isin(ASSOC_REQ_SUBTYPES).to_numpy()
        clients = mgmt["client"].to_numpy()

        def window(a: float, b: float) -> tuple[int, int]:
            i = np.searchsorted(mts, a, side="right")
            j = np.searchsorted(mts, b, side="right")
            sel = is_req[i:j]
            return int(sel.sum()), len(set(clients[i:j][sel]))

        def has_attack(a: float, b: float) -> bool:
            i = np.searchsorted(att, a, side="left")
            j = np.searchsorted(att, b, side="right")
            return j > i

        cuts = np.where(np.diff(att) > args.T)[0]
        starts = np.r_[att[0], att[cuts + 1]]
        ends = np.r_[att[cuts], att[-1]]
        lines += ["| Episodio | Inicio (s desde la primera) | Duración (s) | Solicitudes antes | "
                  "Clientes antes | Solicitudes después | Clientes después |",
                  "|---|---|---|---|---|---|---|"]
        for k, (a, b) in enumerate(zip(starts, ends), start=1):
            nb, cb = window(a - WINDOW_S, a)
            na, ca = window(b, b + WINDOW_S)
            lines.append(f"| {k} | {a - att[0]:.1f} | {b - a:.1f} | {nb} | {cb} | {na} | {ca} |")
        base = []
        if not mgmt.empty:
            for b0 in np.arange(mts[0], mts[-1], WINDOW_S):
                if not has_attack(b0, b0 + WINDOW_S):
                    base.append(window(b0, b0 + WINDOW_S))
        if base:
            rq = [x[0] for x in base]
            rc = [x[1] for x in base]
            lines += ["", f"Referencia: {len(base)} ventanas de {WINDOW_S:.0f} s sin tramas objetivo. "
                      f"Solicitudes: mediana {np.median(rq):.0f}, máximo {max(rq)}. "
                      f"Clientes: mediana {np.median(rc):.0f}, máximo {max(rc)}."]
        lines.append("")
    return lines


MODOS = {
    "timestamp": mode_timestamp,
    "cruce": mode_cruce,
    "linea": mode_linea,
    "reasociacion": mode_reasociacion,
}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Análisis de apoyo de la Fase 1 de AWID3.")
    ap.add_argument("--data", required=True)
    ap.add_argument("--modo", required=True, choices=sorted(MODOS))
    ap.add_argument("--T", type=float, default=2.0, help="Separación entre episodios, en segundos")
    ap.add_argument("--out", default="results/inspection")
    args = ap.parse_args(argv)
    data_cfg = C.load_data_config(args.data)
    lines = MODOS[args.modo](data_cfg, args)
    out_dir = C.resolve_path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"analisis_{args.modo}.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[analisis_fase1] -> {path}")


if __name__ == "__main__":
    main()
