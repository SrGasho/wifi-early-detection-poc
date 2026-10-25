"""Detectores guardados con joblib.

Viven en un módulo propio para que ``joblib`` registre una ruta importable (``src.detectors``)
aunque el entrenamiento se ejecute con ``python -m src.train`` o ``python -m src.baseline``.
"""

from __future__ import annotations

import numpy as np


class Detector:
    """Interfaz común: ``score(X)`` devuelve una puntuación por ventana; mayor = más sospechosa."""

    def score(self, X: np.ndarray) -> np.ndarray:  # pragma: no cover - interfaz
        raise NotImplementedError


class ThresholdDetector(Detector):
    """Línea base: la puntuación es el valor de una sola característica de conteo."""

    def __init__(self, feature: str):
        self.feature = feature

    def score(self, X: np.ndarray) -> np.ndarray:
        return np.asarray(X[:, 0], dtype="float64")


class RandomForestDetector(Detector):
    """Random Forest: la puntuación es la probabilidad de la clase ataque."""

    def __init__(self, model):
        self.model = model

    def score(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(X)[:, 1]
