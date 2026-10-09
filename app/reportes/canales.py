"""Canales de compra: el orden en que la gobernanta recorre el abastecimiento."""

from typing import Any, Dict, List

CANALES: List[Dict[str, str]] = [
    {
        "id": "Mercado",
        "nombre": "Plaza de mercado",
        "detalle": "Verduras, frutas, carnes y tubérculos frescos",
        "color": "#B45309",
    },
    {
        "id": "Super Mercado",
        "nombre": "Supermercado y abarrotes",
        "detalle": "Secos, enlatados, lácteos industriales y limpieza",
        "color": "#006156",
    },
    {
        "id": "Proveedor",
        "nombre": "Proveedores directos",
        "detalle": "Distribuidoras, fórmulas clínicas y contratos",
        "color": "#4338CA",
    },
    {
        "id": "Otros",
        "nombre": "Otros insumos",
        "detalle": "Panadería diaria, descartables y misceláneos",
        "color": "#475569",
    },
]

ORDEN = {canal["id"]: posicion for posicion, canal in enumerate(CANALES)}
POR_ID = {canal["id"]: canal for canal in CANALES}

_ALIAS = {
    "mercado": "Mercado",
    "super mercado": "Super Mercado",
    "supermercado": "Super Mercado",
    "super": "Super Mercado",
    "proveedor": "Proveedor",
    "proveedores": "Proveedor",
    "otros": "Otros",
}


def normalizar(valor: Any) -> str:
    """Lleva cualquier variante escrita en base de datos al canal canonico."""
    return _ALIAS.get(str(valor or "").strip().lower(), "Otros")


def de_linea(linea) -> str:
    """
    Canal de una linea de pedido.

    La fuente de verdad es el campo `grupo` del insumo, que se administra desde
    FileMaker. Si viniera vacio, el insumo cae en Otros en vez de adivinarse por
    el nombre: un insumo sin canal es un dato que hay que corregir en el
    catalogo, no una suposicion que deba hacer el reporte.
    """
    insumo = getattr(linea, "insumo", None)
    return normalizar(getattr(insumo, "grupo", None) if insumo else None)


def definicion(canal_id: str) -> Dict[str, str]:
    return POR_ID.get(canal_id, POR_ID["Otros"])
