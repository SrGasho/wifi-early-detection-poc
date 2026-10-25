"""Trazabilidad de experimentos (R10), contrato de metadatos (R8) y bloqueo de la prueba (R6)."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

from . import config as C

LIBRARIES = (
    "pandas",
    "numpy",
    "scikit-learn",
    "matplotlib",
    "pyarrow",
    "PyYAML",
    "pytest",
    "joblib",
)

# Contrato de models/<exp_id>/metadata.json (plan, sección 5.5).
REQUIRED_METADATA_FIELDS = (
    "exp_id",
    "role",
    "git_commit",
    "seed",
    "target",
    "model_type",
    "model_params",
    "feature_profile",
    "feature_columns",
    "reason_codes",
    "imputation",
    "categorical_encoding",
    "W_seconds",
    "S_seconds",
    "k",
    "T_seconds",
    "alerts",
    "threshold",
    "grid_origins",
    "split_file",
    "split_sha256",
    "windows_file",
    "data_files_sha256",
    "library_versions",
    "created_at",
)


class MetadataError(ValueError):
    pass


class FinalRunError(RuntimeError):
    pass


# --------------------------------------------------------------------------- utilidades

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: str | Path, data: Any) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, default=_json_default)
        fh.write("\n")
    return p


def read_json(path: str | Path) -> Any:
    with Path(path).open(encoding="utf-8") as fh:
        return json.load(fh)


def write_jsonl(path: str | Path, rows: list[dict]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, default=_json_default) + "\n")
    return p


def read_jsonl(path: str | Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _json_default(obj: Any) -> Any:
    try:
        import numpy as np

        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return None if np.isnan(obj) else float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
    except ImportError:  # pragma: no cover
        pass
    if isinstance(obj, Path):
        return str(obj)
    raise TypeError(f"Tipo no serializable: {type(obj)!r}")


# --------------------------------------------------------------------------- entorno y git

def git_info(cwd: Path = C.ROOT) -> dict:
    """Commit actual y estado del árbol. ``None`` si no es un repositorio git."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True, check=True
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=cwd, capture_output=True, text=True, check=True
        ).stdout
        return {"git_commit": commit, "git_dirty": bool(status.strip())}
    except (OSError, subprocess.CalledProcessError):
        return {"git_commit": None, "git_dirty": None}


def library_versions() -> dict:
    versions = {}
    for lib in LIBRARIES:
        try:
            versions[lib] = importlib_metadata.version(lib)
        except importlib_metadata.PackageNotFoundError:
            versions[lib] = None
    return versions


def environment_info() -> dict:
    req = C.ROOT / "requirements.txt"
    return {
        "python_version": platform.python_version(),
        "platform": f"{platform.system()} {platform.release()} {platform.machine()}",
        "library_versions": library_versions(),
        "requirements_sha256": sha256_file(req) if req.exists() else None,
    }


# --------------------------------------------------------------------------- identificadores

def make_exp_id(name: str, when: datetime | None = None) -> str:
    when = when or datetime.now()
    return f"{when:%Y%m%d-%H%M}-{name}"


def _index_file(cfg: dict) -> Path:
    return C.output_root(cfg, "results") / "_index" / f"{cfg['name']}.json"


def create_exp_id(cfg: dict) -> str:
    """Crea el ``exp_id`` de un experimento. Solo lo hacen ``train`` y ``baseline``."""
    index = _index_file(cfg)
    if index.exists():
        raise FinalRunError(
            f"El experimento '{cfg['name']}' ya tiene un exp_id ({read_json(index)['exp_id']}). "
            "Para repetirlo cree un experimento nuevo con otro nombre (R6, R10)."
        )
    exp_id = make_exp_id(cfg["name"])
    write_json(index, {"exp_id": exp_id, "created_at": now_iso(), "config": cfg["_path"]})
    return exp_id


def resolve_exp_id(cfg: dict) -> str:
    index = _index_file(cfg)
    if not index.exists():
        raise FinalRunError(
            f"El experimento '{cfg['name']}' no tiene modelo entrenado. Ejecute train o baseline primero."
        )
    return read_json(index)["exp_id"]


def model_dir(cfg: dict, exp_id: str) -> Path:
    return C.output_root(cfg, "models") / exp_id


def results_dir(cfg: dict, exp_id: str) -> Path:
    d = C.output_root(cfg, "results") / exp_id
    d.mkdir(parents=True, exist_ok=True)
    return d


# --------------------------------------------------------------------------- registro de ejecuciones

def record_run(cfg: dict, exp_id: str, stage: str, *, split: str | None = None,
               started_at: str, extra: dict | None = None) -> Path:
    """Guarda ``run_<stage>[_<split>].json`` con configuración, commit, semilla y entorno."""
    split_file = C.resolve_path(cfg["split_file"])
    clean_cfg = {k: v for k, v in cfg.items() if not k.startswith("_")}
    payload = {
        "exp_id": exp_id,
        "stage": stage,
        "split": split,
        "role": cfg.get("role", "main"),
        "started_at": started_at,
        "finished_at": now_iso(),
        "seed": cfg.get("seed"),
        "config": clean_cfg,
        "config_file": cfg["_path"],
        "split_file": str(split_file),
        "split_sha256": sha256_file(split_file) if split_file.exists() else None,
        **git_info(),
        **environment_info(),
    }
    if extra:
        payload.update(extra)
    name = f"run_{stage}" + (f"_{split}" if split else "") + ".json"
    return write_json(results_dir(cfg, exp_id) / name, payload)


# --------------------------------------------------------------------------- bloqueo de la prueba (R6)

def guard_split_access(cfg: dict, split: str, final: bool) -> None:
    """El conjunto de prueba solo se toca con ``--final`` y solo con la configuración principal."""
    if split not in ("train", "val", "test"):
        raise FinalRunError(f"Conjunto desconocido: {split}")
    if split == "test" and not final:
        raise FinalRunError("El conjunto de prueba solo se usa con --final (R6).")
    if final and split != "test":
        raise FinalRunError("--final solo aplica al conjunto de prueba.")
    if final and cfg.get("role", "main") != "main":
        raise FinalRunError(
            "Los experimentos de sensibilidad nunca se ejecutan sobre la prueba (plan, sección 8.2.1)."
        )


def guard_final(cfg: dict, exp_id: str, stage: str, *, check_git: bool = True) -> Path:
    """Impide repetir una ejecución final y exige un árbol git limpio.

    Devuelve la ruta del marcador que debe crearse con :func:`mark_final_done`.
    """
    marker = results_dir(cfg, exp_id) / "final" / f"{stage}.done"
    if marker.exists():
        raise FinalRunError(
            f"Ya existe una ejecución final de '{stage}' para {exp_id}. "
            "Repetirla exige un experimento nuevo (R6)."
        )
    if check_git:
        info = git_info()
        if info["git_commit"] is None:
            raise FinalRunError("La ejecución final requiere un repositorio git para registrar el commit.")
        if info["git_dirty"]:
            raise FinalRunError(
                "El árbol de git tiene cambios sin guardar. Haga commit antes de la ejecución final (R10)."
            )
    return marker


def mark_final_done(marker: Path) -> None:
    marker.parent.mkdir(parents=True, exist_ok=True)
    write_json(marker, {"done_at": now_iso(), **git_info()})


# --------------------------------------------------------------------------- metadatos (R8)

def validate_metadata(meta: dict) -> None:
    missing = [f for f in REQUIRED_METADATA_FIELDS if f not in meta]
    if missing:
        raise MetadataError(f"metadata.json incompleto; faltan los campos: {', '.join(missing)}")
    if "max_gap_seconds" not in (meta.get("alerts") or {}):
        raise MetadataError("metadata.json incompleto; falta alerts.max_gap_seconds")
    if not meta["feature_columns"]:
        raise MetadataError("metadata.json: feature_columns está vacío")
    absent = [c for c in meta["feature_columns"] if c not in meta["imputation"]]
    if absent:
        raise MetadataError(f"metadata.json: falta la imputación de {absent}")


def save_metadata(directory: Path, meta: dict) -> Path:
    validate_metadata(meta)
    return write_json(Path(directory) / "metadata.json", meta)


def load_metadata(directory: Path) -> dict:
    path = Path(directory) / "metadata.json"
    if not path.exists():
        raise MetadataError(f"No existe {path}")
    meta = read_json(path)
    validate_metadata(meta)
    return meta


def base_metadata(cfg: dict, exp_id: str) -> dict:
    """Campos comunes que comparten la línea base y Random Forest."""
    from . import episodes, feature_engineering as FE

    W, S = C.window_params(cfg)
    ep_meta = episodes.load_definitive_meta(cfg)
    windows_file = FE.windows_path(cfg)
    split_file = C.resolve_path(cfg["split_file"])
    frames = {cid: FE.frames_path(cfg["_data"], cid) for cid in C.capture_ids(cfg["_data"])}
    data_hashes = {str(p.name): sha256_file(p) for p in frames.values() if p.exists()}
    data_hashes[windows_file.name] = sha256_file(windows_file)
    max_gap = float(C.require(cfg, "alerts.max_gap_seconds"))
    if max_gap < S:
        raise C.ConfigError(f"alerts.max_gap_seconds ({max_gap}) debe ser >= S ({S}).")
    return {
        "exp_id": exp_id,
        "role": cfg.get("role", "main"),
        "git_commit": git_info()["git_commit"],
        "seed": int(cfg.get("seed", 0)),
        "target": cfg["target"],
        "categorical_encoding": {},
        "W_seconds": W,
        "S_seconds": S,
        "k": 1,
        "T_seconds": ep_meta["T_seconds"],
        "alerts": {"max_gap_seconds": max_gap},
        "grid_origins": FE.read_grid_origins(windows_file),
        "split_file": str(split_file),
        "split_sha256": sha256_file(split_file),
        "windows_file": str(windows_file),
        "data_files_sha256": data_hashes,
        "library_versions": library_versions(),
        "python_version": sys.version.split()[0],
        "created_at": now_iso(),
    }
