"""Figuras de evaluación a partir de resultados ya generados (I3).

Solo LEE ``eval_windows_<split>.parquet`` y ``metrics_episode_<split>.json``. No ejecuta ni repite la
prueba y no escribe nada dentro de ``results/`` (R6). Para ``test`` exige que la evaluación final esté
registrada (``final/evaluate.done``). Cada ejecución deja ``run_figuras_<split>.json`` junto a las
figuras, con commit, semilla, entorno y hash de los archivos leídos (R10).

Las figuras salen en ``--out`` (por defecto ``docs/figuras/<experimento>``). El tiempo de las líneas
temporales es relativo al instante más temprano mostrado de cada captura (el primer ``t_end`` o el inicio
de un episodio, si es anterior); 0 s no es el inicio de la captura.

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
    first_window = ev.groupby("capture_id")["t_end"].min()
    episodes = episodes[episodes["capture_id"].isin(first_window.index)].copy()
    first_episode = episodes.groupby("capture_id")["t_start"].min()
    t0 = pd.concat([first_window, first_episode], axis=1).min(axis=1)
    ev = ev.copy()
    ev["t_end"] = ev["t_end"] - ev["capture_id"].map(t0)
    off = episodes["capture_id"].map(t0)
    episodes["t_start"] = episodes["t_start"] - off
    episodes["t_end"] = episodes["t_end"] - off
    return ev, episodes


def _source_files(results_dir: Path, split: str) -> list[Path]:
    if split == "test":
        _require(results_dir / "final" / "evaluate.done")
    return [_require(results_dir / f"eval_windows_{split}.parquet"),
            _require(results_dir / f"metrics_episode_{split}.json")]


def _render(sources: list[Path], split: str, out_dir: Path) -> list[Path]:
    windows_file, episodes_file = sources
    ev = pd.read_parquet(windows_file)
    metrics = json.loads(episodes_file.read_text(encoding="utf-8"))
    episodes = pd.DataFrame(metrics["episodes"], columns=["episode_id", "capture_id", "t_start", "t_end"])
    if ev["y"].nunique() < 2:
        warnings.warn(f"El conjunto {split} tiene una sola clase: no se genera la curva PR.", UserWarning)
    ev, episodes = relativize(ev, episodes)
    for old in (out_dir / "figures").glob(f"*_{split}.png"):  # no dejar figuras de ejecuciones anteriores
        old.unlink()
    save_figures(ev, episodes, out_dir, split)
    return sorted((out_dir / "figures").glob(f"*_{split}.png"))


def build_figures(results_dir: Path, split: str, out_dir: Path) -> list[Path]:
    """Escribe las figuras en ``out_dir/figures`` y devuelve sus rutas. No modifica ``results_dir``."""
    return _render(_source_files(Path(results_dir), split), split, Path(out_dir))


def _repo_relative(path: str | None) -> str | None:
    """Ruta relativa a la raíz del repo (con '/'); si está fuera de ella, solo el nombre del archivo.

    El registro se versiona: no debe llevar rutas absolutas ni el usuario del equipo.
    """
    if not path:
        return None
    p = Path(path)
    try:
        return p.resolve().relative_to(C.ROOT.resolve()).as_posix()
    except ValueError:
        return p.name


def record_figures_run(cfg: dict, exp_id: str, split: str, sources: dict[str, str], out_dir: Path,
                       started_at: str, git: dict | None = None) -> Path:
    """R10: deja ``run_figuras_<split>.json`` junto a las figuras (no dentro de ``results/``).

    ``git`` es el estado del repositorio capturado ANTES de escribir las figuras; si no se pasa, se
    consulta ahora (las figuras ya escritas pueden marcar el árbol como modificado).
    """
    payload = {
        "exp_id": exp_id, "stage": "figuras", "split": split,
        "started_at": started_at, "finished_at": E.now_iso(),
        "seed": cfg.get("seed"), "config_file": _repo_relative(cfg.get("_path")),
        "source_sha256": sources,
        **(git if git is not None else E.git_info()), **E.environment_info(),
    }
    return E.write_json(out_dir / f"run_figuras_{split}.json", payload)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Figuras de evaluación desde resultados ya guardados.")
    ap.add_argument("--exp", required=True)
    ap.add_argument("--split", choices=("val", "test"), required=True)
    ap.add_argument("--out", default=None, help="Carpeta base de salida (por defecto docs/figuras/<nombre>)")
    args = ap.parse_args(argv)
    started = E.now_iso()
    git = E.git_info()  # antes de escribir nada: describe el código que se ejecuta, no su salida
    cfg = C.load_experiment(args.exp)
    out = Path(args.out) if args.out else Path("docs/figuras") / cfg["name"]
    try:
        exp_id = E.resolve_exp_id(cfg)  # solo lee el índice; no aplica guardas de ejecución final
        results_dir = C.output_root(cfg, "results") / exp_id
        sources = _source_files(results_dir, args.split)
        hashes = {p.name: E.sha256_file(p) for p in sources}  # antes de leer: ata el registro a lo leído
        paths = _render(sources, args.split, out)
    except (FileNotFoundError, E.FinalRunError) as exc:
        raise SystemExit(f"error ({cfg['name']}): {exc}") from None
    record_figures_run(cfg, exp_id, args.split, hashes, out, started, git)
    for p in paths:
        print(p)


if __name__ == "__main__":
    main()
