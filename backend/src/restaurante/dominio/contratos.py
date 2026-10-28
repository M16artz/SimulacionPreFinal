"""Única definición tipada de los parámetros, eventos y resultados."""
from typing import Annotated, Literal
from math import isclose
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contrato(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Fija(Contrato):
    tipo: Literal["fija"] = "fija"
    valor: float = Field(ge=0, le=1440, description="Minutos")


class Uniforme(Contrato):
    tipo: Literal["uniforme"] = "uniforme"
    minimo: float = Field(ge=0, le=1440)
    maximo: float = Field(gt=0, le=1440)

    @model_validator(mode="after")
    def comprobar(self):
        if self.minimo >= self.maximo:
            raise ValueError("El mínimo debe ser menor que el máximo")
        return self


class Triangular(Contrato):
    tipo: Literal["triangular"] = "triangular"
    minimo: float = Field(ge=0, le=1440)
    moda: float = Field(ge=0, le=1440)
    maximo: float = Field(gt=0, le=1440)

    @model_validator(mode="after")
    def comprobar(self):
        if not self.minimo <= self.moda <= self.maximo or self.minimo == self.maximo:
            raise ValueError("Se requiere mínimo ≤ moda ≤ máximo y mínimo < máximo")
        return self


class Exponencial(Contrato):
    tipo: Literal["exponencial"] = "exponencial"
    media: float = Field(gt=0, le=1440)


Distribucion = Annotated[Fija | Uniforme | Triangular | Exponencial, Field(discriminator="tipo")]


class FranjaLlegadas(Contrato):
    inicio: int = Field(ge=0, lt=1440, description="Minutos desde medianoche")
    fin: int = Field(gt=0, le=1440)
    tasa: float = Field(ge=0, le=200, description="Grupos/hora")

    @model_validator(mode="after")
    def comprobar(self):
        if self.fin <= self.inicio:
            raise ValueError("La franja debe finalizar después de comenzar")
        return self


class Tiempos(Contrato):
    pedido: Distribucion | None
    preparacion: Distribucion | None
    entrega: Distribucion | None
    consumo: Distribucion | None
    cobro: Distribucion | None
    paciencia: Distribucion | None


class ConfiguracionRestaurante(Contrato):
    version_esquema: Literal["1.0"] = "1.0"
    nombre: str = Field(min_length=1, max_length=100)
    sintetica: bool
    notas: str = Field(default="", max_length=2000)
    mesas: int = Field(ge=1, le=100)
    capacidad_mesa: int = Field(ge=1, le=8)
    meseros: int = Field(ge=1, le=30)
    cocineras: int = Field(ge=1, le=30)
    apertura: int = Field(ge=0, lt=1440)
    cierre: int = Field(gt=0, le=1440)
    llegadas: list[FranjaLlegadas] = Field(min_length=1, max_length=48)
    probabilidades_grupo: list[Annotated[float, Field(ge=0, le=1)]] = Field(min_length=8, max_length=8)
    tiempos: Tiempos

    @model_validator(mode="after")
    def comprobar(self):
        if self.apertura >= self.cierre:
            raise ValueError("La apertura debe ser anterior al cierre")
        if any(not 0 <= p <= 1 for p in self.probabilidades_grupo) or not isclose(sum(self.probabilidades_grupo), 1, abs_tol=1e-8):
            raise ValueError("Las probabilidades de grupos de 1 a 8 deben sumar 100 %")
        limite = self.apertura
        for franja in self.llegadas:
            if franja.inicio != limite:
                raise ValueError("Las franjas deben estar ordenadas, sin huecos ni solapamientos")
            limite = franja.fin
        if limite != self.cierre:
            raise ValueError("Las franjas deben cubrir exactamente la jornada")
        paciencia = self.tiempos.paciencia
        if paciencia is not None:
            if isinstance(paciencia, Exponencial) or getattr(paciencia, "maximo", getattr(paciencia, "valor", 0)) > 40:
                raise ValueError("La paciencia debe tener un límite máximo de 40 minutos")
        return self

    def comprobar_ejecutable(self):
        pendientes = [clave for clave, valor in self.tiempos if valor is None]
        if pendientes:
            raise ValueError("Faltan tiempos por aprobar: " + ", ".join(pendientes))


class GrupoCliente(Contrato):
    id: int = Field(ge=1)
    personas: int = Field(ge=1, le=8)
    llegada: float = Field(ge=0)
    paciencia: float = Field(ge=0, le=40)


class EventoSimulacion(Contrato):
    secuencia: int
    tiempo: float
    entidad: int | None
    accion: str
    recursos: list[str]
    estado: dict


class IndicadorCola(Contrato):
    estacion: str
    area_grupo_minutos: float = Field(ge=0)
    longitud_media: float = Field(ge=0)
    numero_entidades: int = Field(ge=0)
    espera_media: float | None


class ContrasteLittle(Contrato):
    ambito: str
    poblacion: str
    unidad_entidades: Literal["grupos"] = "grupos"
    unidad_tiempo: Literal["minutos"] = "minutos"
    numero_entidades: int = Field(ge=0)
    inicio: float
    fin: float
    longitud_media: float = Field(ge=0)
    tasa_efectiva: float = Field(ge=0)
    tiempo_medio: float | None
    producto_lambda_w: float | None
    error_absoluto: float | None
    aplicable: bool
    coincide: bool | None
    observacion: str


class AnalisisMatematico(Contrato):
    inicio: float
    fin: float
    duracion: float = Field(gt=0)
    colas: list[IndicadorCola]
    little: list[ContrasteLittle]


class ResultadoSimulacion(Contrato):
    version_modelo: str
    version_entorno: dict[str, str]
    semilla: int
    configuracion: ConfiguracionRestaurante
    metricas: dict[str, float | int]
    recursos: list[dict]
    grupos: list[dict]
    eventos: list[EventoSimulacion]
    formulacion_matematica: AnalisisMatematico | None = None


class Rango(Contrato):
    minimo: int = Field(ge=1, le=100)
    maximo: int = Field(ge=1, le=100)
    paso: int = Field(ge=1, le=100)

    @model_validator(mode="after")
    def comprobar(self):
        if self.maximo < self.minimo:
            raise ValueError("El máximo debe ser mayor o igual al mínimo")
        return self

    def valores(self):
        return range(self.minimo, self.maximo + 1, self.paso)


class SolicitudExperimento(Contrato):
    configuraciones: list[ConfiguracionRestaurante] = Field(min_length=1, max_length=20)
    replicas: int = Field(default=5, ge=1, le=100)
    semilla: int = Field(default=42, ge=0, le=2**32 - 1)
    rangos: dict[Literal["mesas", "meseros", "cocineras"], Rango] | None = None

    @model_validator(mode="after")
    def comprobar(self):
        for configuracion in self.configuraciones:
            configuracion.comprobar_ejecutable()
        base = self.configuraciones[0]
        for configuracion in self.configuraciones[1:]:
            for clave in ("apertura", "cierre", "llegadas", "probabilidades_grupo"):
                if getattr(configuracion, clave) != getattr(base, clave):
                    raise ValueError("Las comparaciones requieren la misma demanda y jornada")
        combinaciones = len(self.configuraciones)
        for clave, rango in (self.rangos or {}).items():
            if clave != "mesas" and rango.maximo > 30:
                raise ValueError("Meseros y cocineras admiten como máximo 30 recursos")
            combinaciones *= len(rango.valores())
        if combinaciones > 200 or combinaciones * self.replicas > 1000:
            raise ValueError("Máximo 200 escenarios y 1000 ejecuciones por experimento")
        return self


class ResultadoExperimento(Contrato):
    version_modelo: str
    version_entorno: dict[str, str]
    semilla: int
    replicas: int
    semillas_replicas: list[int]
    escenarios: list[dict]
    diferencias_pareadas: list[dict]
    sensibilidad: list[dict] = Field(default_factory=list)
