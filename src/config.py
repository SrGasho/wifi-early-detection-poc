"""Carga y validación de los archivos de configuración YAML.

Todo valor ajustable del proyecto vive en ``configs/``. Este módulo no conoce
nombres de columnas de AWID3: solo lee lo que dicen los archivos.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]

_MISSING = object()


class ConfigError(ValueError):
    """Error de configuración con un mensaje comprensible."""


def resolve_path(path: str | Path, base: Path = ROOT) -> Path:
    """Devuelve una ruta absoluta; las relativas se resuelven desde la raíz."""
    p = Path(path)
    return p if p.is_absolute() else (Path(base) / p)


def load_yaml(path: str | Path) -> dict:
    p = resolve_path(path)
    if not p.exists():
        raise ConfigError(f"No existe el archivo de configuración: {p}")
    with p.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"El archivo {p} debe contener un diccionario YAML.")
    data["_path"] = str(p)
    return data


def is_placeholder(value: Any) -> bool:
    """Un valor ``<...>`` indica una decisión pendiente (Fase 1 o Gate D)."""
    if not isinstance(value, str):
        return False
    v = value.strip()
    return v.startswith("<") and v.endswith(">")


def contains_placeholder(value: Any) -> bool:
    if is_placeholder(value):
        return True
    if isinstance(value, dict):
        return any(contains_placeholder(v) for k, v in value.items() if not str(k).startswith("_"))
    if isinstance(value, (list, tuple)):
        return any(contains_placeholder(v) for v in value)
    return False


def get(cfg: dict, dotted: str, default: Any = _MISSING) -> Any:
    node: Any = cfg
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            if default is _MISSING:
                return _MISSING
            return default
        node = node[part]
    return node


def require(cfg: dict, dotted: str, *, allow_placeholder: bool = False) -> Any:
    """Devuelve ``cfg[dotted]`` o lanza un error explicando qué falta."""
    value = get(cfg, dotted)
    origin = cfg.get("_path", "configuración")
    if value is _MISSING:
        raise ConfigError(f"Falta la clave obligatoria '{dotted}' en {origin}.")
    if not allow_placeholder and contains_placeholder(value):
        raise ConfigError(
            f"La clave '{dotted}' en {origin} aún tiene un valor pendiente ({value!r}). "
            "Debe fijarse en la Fase 1 o en Gate D y registrarse en docs/decisiones.md."
        )
    return value


DATA_REQUIRED_KEYS = (
    "paths.raw",
    "paths.interim",
    "paths.processed",
    "captures",
    "columns",
    "labels.target",
    "labels.normal",
    "anonymization.salt_env_var",
)


def load_data_config(path: str | Path) -> dict:
    cfg = load_yaml(path)
    for key in DATA_REQUIRED_KEYS:
        require(cfg, key, allow_placeholder=True)
    if not isinstance(cfg["captures"], list) or not cfg["captures"]:
        raise ConfigError("'captures' debe ser una lista no vacía.")
    if not isinstance(cfg["labels"]["target"], dict):
        raise ConfigError(
            "'labels.target' debe ser un diccionario tipo_de_ataque -> etiqueta "
            "(por ejemplo deauth: <etiqueta>)."
        )
    return cfg


def capture_ids(data_cfg: dict) -> list[str]:
    return [str(c["id"]) for c in data_cfg["captures"]]


EXPERIMENT_REQUIRED_KEYS = (
    "name",
    "data_config",
    "features_config",
    "split_file",
    "target",
    "window.W_seconds",
    "window.S_seconds",
    "window.k",
)


def load_experiment(path: str | Path) -> dict:
    cfg = load_yaml(path)
    for key in EXPERIMENT_REQUIRED_KEYS:
        require(cfg, key, allow_placeholder=True)
    if cfg["target"] != "binary":
        raise ConfigError("El objetivo del modelo principal es binario (target: binary). Ver R11.")
    if cfg["window"]["k"] != 1:
        raise ConfigError("k está fijado en 1 y no se optimiza (R5).")
    role = cfg.get("role", "main")
    if role not in ("main", "sensitivity"):
        raise ConfigError("'role' debe ser 'main' o 'sensitivity'.")
    cfg["role"] = role
    cfg["_data"] = load_data_config(cfg["data_config"])
    cfg["_features"] = load_yaml(cfg["features_config"])
    return cfg


def window_params(cfg: dict) -> tuple[float, float]:
    """Devuelve ``(W, S)`` validados (``S < W`` y ``W`` múltiplo de ``S``)."""
    W = float(require(cfg, "window.W_seconds"))
    S = float(require(cfg, "window.S_seconds"))
    if not (0 < S < W):
        raise ConfigError(f"Se requiere 0 < S < W (S={S}, W={W}).")
    ratio = W / S
    if abs(ratio - round(ratio)) > 1e-9:
        raise ConfigError(f"W debe ser múltiplo de S (W={W}, S={S}).")
    return W, S


def data_path(data_cfg: dict, key: str) -> Path:
    return resolve_path(require(data_cfg, f"paths.{key}"))


def output_root(cfg: dict, key: str) -> Path:
    """Raíz de ``models`` o ``results`` (configurable para pruebas)."""
    return resolve_path(get(cfg, f"paths.{key}", key))
