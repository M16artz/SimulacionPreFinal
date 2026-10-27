"""Asignación compatible: examina la cola completa y adquiere mesas atómicamente."""
from itertools import combinations
import simpy


class GestorMesas:
    def __init__(self, entorno: simpy.Environment, capacidades: list[int]):
        self.entorno = entorno
        self.capacidades = capacidades
        self.libres = set(range(len(capacidades)))
        self.pendientes = []

    def solicitar(self, personas: int):
        solicitud = self.entorno.event()
        self.pendientes.append((personas, solicitud))
        self.asignar()
        return solicitud

    def asignar(self):
        for personas, solicitud in list(self.pendientes):
            # La regla del modelo exige dos mesas para 5–8 personas.
            cantidad = 2 if personas >= 5 else 1
            opciones = [mesas for mesas in combinations(sorted(self.libres), cantidad) if sum(self.capacidades[i] for i in mesas) >= personas]
            if opciones:
                mesas = min(opciones, key=lambda opcion: (sum(self.capacidades[i] for i in opcion), opcion))
                self.libres.difference_update(mesas)
                self.pendientes.remove((personas, solicitud))
                solicitud.succeed(list(mesas))

    def cancelar(self, solicitud):
        self.pendientes = [(personas, evento) for personas, evento in self.pendientes if evento is not solicitud]

    def liberar(self, mesas: list[int]):
        if any(mesa in self.libres for mesa in mesas):
            raise RuntimeError("Se intentó liberar una mesa que ya estaba disponible")
        self.libres.update(mesas)
        self.asignar()
