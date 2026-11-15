"""Figuras de evaluación a partir de resultados ya generados (I3).

Solo LEE ``eval_windows_<split>.parquet`` y ``metrics_episode_<split>.json``. No ejecuta ni repite la
prueba y no escribe nada dentro de ``results/`` (R6). Para ``test`` exige que la evaluación final esté
registrada (``final/evaluate.done``). Cada ejecución deja ``run_figuras_<split>.json`` junto a las
figuras, con commit, semilla, entorno y hash de los archivos leídos (R10).

Las figuras salen en ``--out`` (por defecto ``docs/figuras/<experimento>``). El tiempo de las líneas
temporales es relativo al primer ``t_end`` de cada captura, es decir, 0 s es el cierre de la primera
ventana y no el inicio de la captura.

Uso::

    python -m scripts.figuras_evaluacion --exp configs/experiments/exp_loao_deauth_to_disas.yaml --split test
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import pandas as pd

from src import config as C
from src import experiment as E
from src.evaluate import save_figures


def _require(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Falta {path.name} en {path.parent}. Genere primero la evaluación de ese conjunto.")
    return path


def relativize(ev: pd.DataFrame, episodes: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Desplaza el tiempo de cada captura para que empiece en 0 s (el eje epoch no es legible en un paper).

    Los episodios de capturas sin ventanas evaluadas se descartan: no hay nada que dibujar y no tienen origen.
    """
    t0 = ev.groupby("capture_id")["t_end"].min()
    ev, episodes = ev.copy(), episodes.copy()
    ev["t_end"] = ev["t_end"] - ev["capture_id"].map(t0)
    episodes = episodes[episodes["capture_id"].isin(t0.index)].copy()
    off = episodes["capture_id"].map(t0)
    episodes["t_start"] = episodes["t_start"] - off
    episodes["t_end"] = episodes["t_end"] - off
    return ev, episodes


def _source_files(results_dir: Path, split: str) -> list[Path]:
    if split == "test":
        _require(results_dir / "final" / "evaluate.done")
    return [_require(results_dir / f"eval_windows_{split}.parquet"),
            _require(results_dir / f"metrics_episode_{split}.json")]


def build_figures(results_dir: Path, split: str, out_dir: Path) -> list[Path]:
    """Escribe las figuras en ``out_dir/figures`` y devuelve sus rutas. No modifica ``results_dir``."""
    results_dir, out_dir = Path(results_dir), Path(out_dir)
    windows_file, episodes_file = _source_files(results_dir, split)
    ev = pd.read_parquet(windows_file)
    metrics = json.loads(episodes_file.read_text(encoding="utf-8"))
    episodes = pd.DataFrame(metrics["episodes"], columns=["episode_id", "capture_id", "t_start", "t_end"])
    if ev["y"].nunique() < 2:
        warnings.warn(f"El conjunto {split} tiene una sola clase: no se genera la curva PR.", UserWarning)
    ev, episodes = relativize(ev, episodes)
    save_figures(ev, episodes, out_dir, split)
    return sorted((out_dir / "figures").glob(f"*_{split}.png"))


def record_figures_run(cfg: dict, exp_id: str, split: str, sources: list[Path], out_dir: Path,
                       started_at: str) -> Path:
    """R10: deja ``run_figuras_<split>.json`` junto a las figuras (no dentro de ``results/``)."""
    payload = {
        "exp_id": exp_id, "stage": "figuras", "split": split,
        "started_at": started_at, "finished_at": E.now_iso(),
        "seed": cfg.get("seed"), "config_file": cfg.get("_path"),
        "source_sha256": {p.name: E.sha256_file(p) for p in sources},
        **E.git_info(), **E.environment_info(),
    }
    return E.write_json(out_dir / f"run_figuras_{split}.json", payload)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Figuras de evaluación desde resultados ya guardados.")
    ap.add_argument("--exp", required=True)
    ap.add_argument("--split", choices=("val", "test"), required=True)
    ap.add_argument("--out", default=None, help="Carpeta base de salida (por defecto docs/figuras/<nombre>)")
    args = ap.parse_args(argv)
    started = E.now_iso()
    cfg = C.load_experiment(args.exp)
    out = Path(args.out) if args.out else Path("docs/figuras") / cfg["name"]
    try:
        exp_id = E.resolve_exp_id(cfg)  # solo lee el índice; no aplica guardas de ejecución final
        results_dir = C.output_root(cfg, "results") / exp_id
        paths = build_figures(results_dir, args.split, out)
    except (FileNotFoundError, E.FinalRunError) as exc:
        raise SystemExit(f"error ({cfg['name']}): {exc}") from None
    record_figures_run(cfg, exp_id, args.split, _source_files(results_dir, args.split), out, started)
    for p in paths:
        print(p)


if __name__ == "__main__":
    main()
