import copy
import pytest
from pydantic import TypeAdapter, ValidationError
from restaurante.dominio.contratos import ConfiguracionRestaurante, Distribucion, ResultadoSimulacion, SolicitudExperimento, Rango, GrupoCliente, EventoSimulacion, ResultadoExperimento


@pytest.mark.parametrize("datos", [
    {"tipo": "triangular", "minimo": 10, "moda": 9, "maximo": 20},
    {"tipo": "triangular", "minimo": 10, "moda": 10, "maximo": 10},
    {"tipo": "uniforme", "minimo": 5, "maximo": 4},
    {"tipo": "exponencial", "media": 0},
    {"tipo": "fija", "valor": -1},
    {"tipo": "fija", "valor": float("nan")},
    {"tipo": "desconocida", "valor": 2},
])
def test_distribuciones_invalidas(datos):
    with pytest.raises(ValidationError):
        TypeAdapter(Distribucion).validate_python(datos)


@pytest.mark.parametrize("clave,valor", [("mesas", 0), ("meseros", 1.5), ("cocineras", 31), ("apertura", 1300), ("probabilidades_grupo", [0.2] * 8), ("version_esquema", "2.0")])
def test_parametros_invalidos(configuracion, clave, valor):
    datos = configuracion.model_dump()
    datos[clave] = valor
    with pytest.raises(ValidationError):
        ConfiguracionRestaurante.model_validate(datos)


def test_franjas_sin_huecos_y_sin_solapamientos(configuracion):
    for inicio in (719, 721):
        datos = configuracion.model_dump()
        datos["llegadas"][1]["inicio"] = inicio
        with pytest.raises(ValidationError, match="huecos"):
            ConfiguracionRestaurante.model_validate(datos)


def test_pendientes_se_guardan_pero_no_se_ejecutan(configuracion):
    datos = configuracion.model_dump()
    datos["tiempos"]["pedido"] = None
    pendiente = ConfiguracionRestaurante.model_validate(datos)
    assert pendiente.tiempos.pedido is None
    with pytest.raises(ValueError, match="pedido"):
        pendiente.comprobar_ejecutable()


@pytest.mark.parametrize("paciencia", [{"tipo": "exponencial", "media": 10}, {"tipo": "fija", "valor": 41}, {"tipo": "uniforme", "minimo": 10, "maximo": 41}])
def test_paciencia_acotada(configuracion, paciencia):
    datos = configuracion.model_dump()
    datos["tiempos"]["paciencia"] = paciencia
    with pytest.raises(ValidationError, match="40"):
        ConfiguracionRestaurante.model_validate(datos)


def test_comparacion_requiere_demanda_identica(configuracion):
    otra = copy.deepcopy(configuracion.model_dump())
    otra["llegadas"][0]["tasa"] = 9
    with pytest.raises(ValidationError, match="misma demanda"):
        SolicitudExperimento(configuraciones=[configuracion, ConfiguracionRestaurante.model_validate(otra)])


def test_rangos_y_limites_experimentales(configuracion):
    assert list(Rango(minimo=1, maximo=5, paso=2).valores()) == [1, 3, 5]
    with pytest.raises(ValidationError):
        Rango(minimo=5, maximo=1, paso=1)
    with pytest.raises(ValidationError, match="1000"):
        SolicitudExperimento(configuraciones=[configuracion], replicas=100, rangos={"mesas": Rango(minimo=1, maximo=100, paso=1)})


def test_contratos_json(configuracion):
    assert ConfiguracionRestaurante.model_validate_json(configuracion.model_dump_json()) == configuracion
    grupo = GrupoCliente(id=1, personas=5, llegada=550, paciencia=30)
    assert GrupoCliente.model_validate_json(grupo.model_dump_json()) == grupo
    evento = EventoSimulacion(secuencia=0, tiempo=540, entidad=None, accion="apertura", recursos=[], estado={})
    assert EventoSimulacion.model_validate_json(evento.model_dump_json()) == evento
    for contrato in (ResultadoSimulacion, ResultadoExperimento):
        assert contrato.model_json_schema()["additionalProperties"] is False
