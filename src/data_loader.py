"""Lectura por bloques de AWID3 (CSV) usando solo las columnas mapeadas en ``configs/data.yaml``.

R1: este módulo nunca escribe en ``data/raw``.
Los nombres de columnas no se escriben a mano: vienen de ``columns`` en la configuración.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import pandas as pd

from . import config as C


class DataLoaderError(FileNotFoundError):
    pass


def _natural_key(path: Path) -> list:
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", path.name)]


def capture_spec(data_cfg: dict, capture_id: str) -> dict:
    for cap in data_cfg["captures"]:
        if str(cap["id"]) == capture_id:
            return cap
    raise C.ConfigError(f"La captura '{capture_id}' no está en data.yaml")


def list_capture_files(data_cfg: dict, capture_id: str) -> list[Path]:
    """Archivos de una captura en orden natural (``file_idx`` = posición en esta lista)."""
    cap = capture_spec(data_cfg, capture_id)
    pattern = cap.get("pattern")
    if pattern is None or C.is_placeholder(pattern):
        raise C.ConfigError(
            f"El patrón de archivos de la captura '{capture_id}' aún no está definido. "
            "Use 'python -m src.inspect_data --discover' en la Fase 1 para encontrarlo."
        )
    raw = C.data_path(data_cfg, "raw")
    files = sorted((p for p in raw.glob(pattern) if p.is_file()), key=_natural_key)
    if not files:
        raise DataLoaderError(f"No se encontraron archivos para '{capture_id}' con el patrón {raw / pattern}")
    return files


def read_header(path: Path) -> list[str]:
    return list(pd.read_csv(path, nrows=0).columns)


def mapped_columns(data_cfg: dict) -> dict[str, str]:
    """Nombre interno -> nombre en el archivo, sin entradas pendientes ni nulas."""
    return {
        internal: str(external)
        for internal, external in data_cfg["columns"].items()
        if external is not None and not C.is_placeholder(external)
    }


def check_columns(path: Path, wanted: dict[str, str], required: set[str]) -> dict[str, str]:
    """Verifica que el archivo tenga las columnas requeridas; devuelve las disponibles."""
    header = set(read_header(path))
    missing_required = sorted(i for i in required if wanted.get(i) not in header)
    if missing_required:
        detail = ", ".join(f"{i} -> {wanted.get(i)!r}" for i in missing_required)
        raise DataLoaderError(
            f"Al archivo {path} le faltan columnas obligatorias: {detail}. "
            "Revise el mapeo 'columns' de configs/data.yaml."
        )
    return {i: e for i, e in wanted.items() if e in header}


REQUIRED_INTERNAL = {"ts", "label"}


def iter_chunks(data_cfg: dict, capture_id: str, *, max_rows: int | None = None
                ) -> Iterator[tuple[int, pd.DataFrame]]:
    """Itera ``(file_idx, bloque)``. Cada bloque tiene columnas con nombres internos, como texto.

    La conversión de tipos se hace en ``preprocessing`` para poder contar los valores no convertibles.
    """
    wanted = mapped_columns(data_cfg)
    has_subtype = "fc_subtype" in wanted or "fc_type_subtype" in wanted
    if not has_subtype:
        raise C.ConfigError("data.yaml debe mapear 'fc_subtype' o 'fc_type_subtype'.")
    chunksize = C.get(data_cfg, "read.chunksize", 200_000)
    if C.is_placeholder(chunksize):
        chunksize = 200_000
    remaining = max_rows
    for file_idx, path in enumerate(list_capture_files(data_cfg, capture_id)):
        available = check_columns(path, wanted, REQUIRED_INTERNAL)
        rename = {external: internal for internal, external in available.items()}
        reader = pd.read_csv(
            path,
            usecols=list(rename),
            dtype=str,
            chunksize=int(chunksize),
            keep_default_na=True,
            low_memory=False,
        )
        for chunk in reader:
            chunk = chunk.rename(columns=rename)
            if remaining is not None:
                chunk = chunk.iloc[:remaining]
                remaining -= len(chunk)
            yield file_idx, chunk
            if remaining is not None and remaining <= 0:
                return
