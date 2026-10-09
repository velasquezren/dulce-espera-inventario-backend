"""
Flujo de estados de un pedido.

Hay tres clientes que cambian estados: la aplicacion de cocina, la de compras y
FileMaker. Si cada uno decide por su cuenta que transiciones valen, tarde o
temprano aparece un pedido entregado que vuelve a pendiente. La regla vive aca,
del lado del servidor, que es el unico punto por el que pasan los tres.
"""

from typing import Dict, FrozenSet, Optional

PENDIENTE = "pendiente"
EN_REVISION = "en revision"
ACEPTADO = "aceptado"
COMPRADO = "comprado"
ENTREGADO = "entregado"
RECHAZADO = "rechazado"
CANCELADO = "cancelado"

ESTADOS = (PENDIENTE, EN_REVISION, ACEPTADO, COMPRADO, ENTREGADO, RECHAZADO, CANCELADO)

#: Un pedido que llego a uno de estos ya no se mueve.
FINALES: FrozenSet[str] = frozenset({ENTREGADO, RECHAZADO, CANCELADO})

#: A donde puede ir cada estado.
TRANSICIONES: Dict[str, FrozenSet[str]] = {
    PENDIENTE: frozenset({EN_REVISION, ACEPTADO, RECHAZADO, CANCELADO}),
    EN_REVISION: frozenset({ACEPTADO, RECHAZADO, CANCELADO}),
    # Todavia no se compro nada, asi que cocina puede arrepentirse.
    ACEPTADO: frozenset({COMPRADO, RECHAZADO, CANCELADO}),
    # Ya se gasto el dinero: lo unico que queda es que llegue a cocina.
    COMPRADO: frozenset({ENTREGADO}),
    ENTREGADO: frozenset(),
    RECHAZADO: frozenset(),
    CANCELADO: frozenset(),
}

ETIQUETAS = {
    PENDIENTE: "Pendiente",
    EN_REVISION: "En revision",
    ACEPTADO: "Aceptado",
    COMPRADO: "Comprado",
    ENTREGADO: "Entregado",
    RECHAZADO: "Rechazado",
    CANCELADO: "Cancelado",
}

_ALIAS = {
    "en revisión": EN_REVISION,
    "aprobado": ACEPTADO,
}


def normalizar(valor: Optional[str]) -> Optional[str]:
    """Estado canonico, o None si no es un estado conocido."""
    limpio = (valor or "").strip().lower()
    limpio = _ALIAS.get(limpio, limpio)
    return limpio if limpio in ESTADOS else None


def se_puede_cancelar(estado: Optional[str]) -> bool:
    return CANCELADO in TRANSICIONES.get(normalizar(estado) or "", frozenset())


def motivo_de_rechazo(actual: Optional[str], siguiente: str) -> Optional[str]:
    """
    Explica por que no se admite el cambio, o None si es valido.

    El texto va tal cual al usuario y a FileMaker, asi que se escribe para que
    lo entienda quien aprieta el boton, no para quien lee el codigo.
    """
    origen = normalizar(actual)
    if origen is None:
        return f"El pedido tiene un estado desconocido ('{actual}') y no se puede cambiar."

    if origen == siguiente:
        return None  # repetir el mismo estado no es un error, no hace nada

    if origen in FINALES:
        return (
            f"El pedido ya esta {ETIQUETAS[origen].lower()} y no admite mas cambios."
        )

    permitidos = TRANSICIONES[origen]
    if siguiente not in permitidos:
        opciones = ", ".join(ETIQUETAS[e].lower() for e in sorted(permitidos))
        return (
            f"Un pedido {ETIQUETAS[origen].lower()} no puede pasar a "
            f"{ETIQUETAS[siguiente].lower()}. Solo puede pasar a: {opciones}."
        )

    return None
