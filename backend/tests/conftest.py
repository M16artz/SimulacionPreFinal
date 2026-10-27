from pathlib import Path
import pytest
import yaml
from restaurante.dominio.contratos import ConfiguracionRestaurante


@pytest.fixture
def configuracion():
    raiz = Path(__file__).resolve().parents[2]
    return ConfiguracionRestaurante.model_validate(yaml.safe_load((raiz / "configuraciones/ejemplos/sintetica.yaml").read_text(encoding="utf-8")))


@pytest.fixture
def breve(configuracion):
    datos = configuracion.model_dump()
    datos.update(apertura=540, cierre=570, llegadas=[{"inicio": 540, "fin": 570, "tasa": 60}])
    return ConfiguracionRestaurante.model_validate(datos)
