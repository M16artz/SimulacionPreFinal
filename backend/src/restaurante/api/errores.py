"""Mensajes de validación comprensibles en español."""


def traducir_errores(errores):
    mensajes = {
        "missing": "Este campo es obligatorio",
        "extra_forbidden": "Este parámetro no pertenece al esquema",
        "int_type": "Se requiere un número entero", "int_parsing": "Se requiere un número entero",
        "int_from_float": "Se requiere un número entero",
        "float_type": "Se requiere un número", "float_parsing": "Se requiere un número",
        "finite_number": "El número debe ser finito",
        "string_type": "Se requiere texto", "string_too_short": "El texto está vacío o es demasiado corto",
        "string_too_long": "El texto supera la longitud permitida",
        "bool_type": "Se requiere una opción de verdadero o falso",
        "literal_error": "Seleccione una opción admitida por el esquema",
        "union_tag_invalid": "La distribución seleccionada no está admitida",
        "union_tag_not_found": "Debe indicar el tipo de distribución",
        "model_type": "Se requiere un objeto con los parámetros correspondientes",
        "list_type": "Se requiere una lista", "too_short": "La lista contiene menos elementos de los necesarios",
        "too_long": "La lista contiene más elementos de los permitidos",
        "json_invalid": "El contenido JSON no tiene un formato válido",
        "uuid_parsing": "El identificador debe ser un UUID válido",
    }
    salida = []
    for error in errores:
        tipo = error["type"]
        contexto = error.get("ctx", {})
        if tipo == "value_error":
            mensaje = error["msg"].removeprefix("Value error, ")
        elif tipo in ("greater_than", "greater_than_equal", "less_than", "less_than_equal"):
            nombre = {"greater_than": "mayor que", "greater_than_equal": "mayor o igual a", "less_than": "menor que", "less_than_equal": "menor o igual a"}[tipo]
            mensaje = f"El valor debe ser {nombre} {next(iter(contexto.values()), '')}"
        else:
            mensaje = mensajes.get(tipo, "El valor no cumple el formato requerido")
        salida.append({"campo": ".".join(map(str, error["loc"])), "mensaje": mensaje})
    return salida
