"""Intervalos t de Student; una réplica no permite estimar incertidumbre."""
import numpy as np
from scipy.stats import t


def resumir(valores):
    muestras = np.asarray(valores, dtype=float)
    if muestras.ndim != 1 or not len(muestras) or not np.isfinite(muestras).all():
        raise ValueError("Se necesita una lista no vacía de valores finitos")
    media = float(np.mean(muestras))
    if len(muestras) < 2:
        return {"media": media, "ic95": None, "replicas": len(muestras)}
    margen = float(t.ppf(0.975, len(muestras) - 1) * np.std(muestras, ddof=1) / np.sqrt(len(muestras)))
    return {"media": media, "ic95": [media - margen, media + margen], "replicas": len(muestras)}
