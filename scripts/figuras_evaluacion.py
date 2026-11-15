"""Figuras de evaluación a partir de resultados ya generados (I3).

Solo LEE ``eval_windows_<split>.parquet`` y ``metrics_episode_<split>.json``. No ejecuta ni repite la
prueba, no llama a ``guard_final`` y no escribe nada dentro de ``results/`` (R6). Las figuras salen en
``--out`` (por defecto ``docs/figuras/<experimento>/figures``).

Uso::

    python -m scripts.figuras_evaluacion --exp configs/experiments/exp_loao_deauth_to_disas.yaml --split test
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src import config as C
from src.evaluate import save_figures


def _require(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Falta {path.name} en {path.parent}. Genere primero la evaluación de ese conjunto.")
    return path


def relativize(ev: pd.DataFrame, episodes: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Desplaza el tiempo de cada captura para que empiece en 0 s (el eje epoch no es legible en un paper)."""
    t0 = ev.groupby("capture_id")["t_end"].min()
    ev, episodes = ev.copy(), episodes.copy()
    ev["t_end"] = ev["t_end"] - ev["capture_id"].map(t0)
    off = episodes["capture_id"].map(t0)
    episodes["t_start"] = episodes["t_start"] - off
    episodes["t_end"] = episodes["t_end"] - off
    return ev, episodes


def build_figures(results_dir: Path, split: str, out_dir: Path) -> list[Path]:
    """Escribe las figuras en ``out_dir/figures`` y devuelve sus rutas. No modifica ``results_dir``.

    El tiempo de las líneas temporales es relativo al primer ``t_end`` de cada captura.
    """
    results_dir, out_dir = Path(results_dir), Path(out_dir)
    ev = pd.read_parquet(_require(results_dir / f"eval_windows_{split}.parquet"))
    metrics = json.loads(_require(results_dir / f"metrics_episode_{split}.json").read_text(encoding="utf-8"))
    episodes = pd.DataFrame(metrics["episodes"], columns=["episode_id", "capture_id", "t_start", "t_end"])
    ev, episodes = relativize(ev, episodes)
    save_figures(ev, episodes, out_dir, split)
    return sorted((out_dir / "figures").glob(f"*_{split}.png"))


def _results_dir_from_index(cfg: dict) -> Path:
    """Resuelve ``results/<exp_id>`` leyendo el índice, sin las guardas de ejecución final."""
    index = C.output_root(cfg, "results") / "_index" / f"{cfg['name']}.json"
    exp_id = json.loads(_require(index).read_text(encoding="utf-8"))["exp_id"]
    return C.output_root(cfg, "results") / exp_id


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Figuras de evaluación desde resultados ya guardados.")
    ap.add_argument("--exp", required=True)
    ap.add_argument("--split", choices=("val", "test"), required=True)
    ap.add_argument("--out", default=None, help="Carpeta base de salida (por defecto docs/figuras/<nombre>)")
    args = ap.parse_args(argv)
    cfg = C.load_experiment(args.exp)
    out = Path(args.out) if args.out else Path("docs/figuras") / cfg["name"]
    for p in build_figures(_results_dir_from_index(cfg), args.split, out):
        print(p)


if __name__ == "__main__":
    main()
