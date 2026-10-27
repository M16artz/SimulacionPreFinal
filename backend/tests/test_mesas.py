import simpy
from restaurante.simulacion.gestor_mesas import GestorMesas


def test_dos_mesas_atomicas_y_compatibilidad_no_fifo():
    entorno = simpy.Environment()
    gestor = GestorMesas(entorno, [4, 4])
    primera = gestor.solicitar(4)
    grande = gestor.solicitar(8)
    pequeno = gestor.solicitar(2)
    assert primera.triggered and pequeno.triggered
    assert not grande.triggered and len(gestor.libres) == 0
    gestor.liberar(primera.value)
    assert not grande.triggered and len(gestor.libres) == 1
    gestor.liberar(pequeno.value)
    assert grande.triggered and len(grande.value) == 2
    assert len(set(grande.value)) == 2 and not gestor.libres
    assert not gestor.pendientes


def test_cancelar_no_pierde_ni_duplica_solicitudes():
    gestor = GestorMesas(simpy.Environment(), [4, 4])
    ocupante = gestor.solicitar(8)
    abandono = gestor.solicitar(5)
    siguiente = gestor.solicitar(8)
    gestor.cancelar(abandono)
    gestor.liberar(ocupante.value)
    assert siguiente.triggered and not abandono.triggered
    assert not gestor.pendientes
    gestor.liberar(siguiente.value)
    assert gestor.libres == {0, 1}


def test_mesas_incompatibles_no_se_asignan():
    gestor = GestorMesas(simpy.Environment(), [2, 2])
    solicitud = gestor.solicitar(5)
    assert not solicitud.triggered and gestor.libres == {0, 1}
