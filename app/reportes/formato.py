"""Formato de numeros y fechas para documentos impresos en espanol."""

import re
import unicodedata
from datetime import datetime
from typing import Optional

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def cantidad(valor) -> str:
    """2.00 se imprime 2; 1.50 se imprime 1,5. Nadie compra "2.00 kilos"."""
    try:
        numero = float(valor or 0)
    except (TypeError, ValueError):
        return "0"
    if numero == int(numero):
        return str(int(numero))
    return f"{numero:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def fecha_hora(valor: Optional[datetime]) -> str:
    return valor.strftime("%d/%m/%Y a las %H:%M") if valor else "Sin fecha"


def fecha(valor: Optional[datetime]) -> str:
    return valor.strftime("%d/%m/%Y") if valor else "Sin fecha"


def fecha_larga(valor: Optional[datetime]) -> str:
    if not valor:
        return "Sin fecha"
    return f"{valor.day} de {MESES[valor.month - 1]} de {valor.year}"


def folio(id_publico: Optional[str]) -> str:
    return (id_publico or "")[:8].upper() or "SIN-ID"


def sello(valor: Optional[datetime] = None) -> str:
    return (valor or datetime.now()).strftime("%Y%m%d_%H%M")


def _sin_acentos(texto: str) -> str:
    plano = unicodedata.normalize("NFD", (texto or "").lower())
    plano = "".join(c for c in plano if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", plano).strip()


def presentacion(nombre: Optional[str], unidad: Optional[str]) -> str:
    """
    Unidad legible para imprimir.

    En el catalogo hay 447 insumos cuya unidad es una copia del nombre, y asi el
    renglon queda como "2 aceite fino de 4,800ml" en vez de "2 Unidad". Cuando
    la unidad no aporta informacion se reemplaza por Unidad, y en el resto se
    corrige solo el uso de mayusculas (kilos, KILOS y Kilos eran tres unidades
    distintas en la misma hoja).
    """
    texto = (unidad or "").strip()
    if not texto or _sin_acentos(texto) == _sin_acentos(nombre):
        return "Unidad"
    if texto.isupper():
        return texto.capitalize()
    return texto[0].upper() + texto[1:]
