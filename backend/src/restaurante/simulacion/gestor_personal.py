"""Personal identificado: selección FIFO de la primera persona disponible."""
import simpy


class GestorPersonal:
    def __init__(self, entorno, cantidad: int, prefijo: str):
        self.disponibles = simpy.Store(entorno, capacity=cantidad)
        self.disponibles.items.extend([f"{prefijo}-{i + 1}" for i in range(cantidad)])

    def solicitar(self):
        return self.disponibles.get()

    def liberar(self, identificador):
        return self.disponibles.put(identificador)
