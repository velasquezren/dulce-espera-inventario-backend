"""
Modelo de un documento de compras.

Separa QUE se imprime de COMO se ve: los endpoints arman un `Documento` y la
plantilla lo dibuja. Asi la hoja de un pedido y la lista consolidada comparten
el mismo diseno sin duplicar una sola linea de HTML.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from app.reportes import canales, formato


@dataclass
class Articulo:
    insumo_id: str
    nombre: str
    categoria: str
    presentacion: str
    cantidad: float
    #: Quien pidio y cuanto. Solo se imprime cuando hay mas de un solicitante.
    solicitantes: List[Tuple[str, float]] = field(default_factory=list)

    @property
    def cantidad_texto(self) -> str:
        return formato.cantidad(self.cantidad)

    @property
    def detalle_solicitantes(self) -> str:
        if len(self.solicitantes) < 2:
            return ""
        partes = [f"{nombre} {formato.cantidad(cant)}" for nombre, cant in self.solicitantes]
        return " · ".join(partes)


@dataclass
class Grupo:
    """Una categoria dentro de un canal: asi se recorre el mercado."""

    nombre: str
    articulos: List[Articulo]


@dataclass
class Seccion:
    """Todo lo que se compra en un canal. Se imprime en su propia hoja."""

    canal: Dict[str, str]
    grupos: List[Grupo]

    @property
    def total_articulos(self) -> int:
        return sum(len(grupo.articulos) for grupo in self.grupos)


@dataclass
class Documento:
    titulo: str
    subtitulo: str
    meta: List[Tuple[str, str]]
    secciones: List[Seccion]
    nota: Optional[str] = None
    firmas: Sequence[str] = ("Entrega / Compras", "Recibe en cocina")
    nombre_archivo: str = "documento.pdf"

    @property
    def total_articulos(self) -> int:
        return sum(seccion.total_articulos for seccion in self.secciones)


def _agrupar(articulos: Iterable[Articulo]) -> List[Grupo]:
    por_categoria: Dict[str, List[Articulo]] = {}
    for articulo in articulos:
        por_categoria.setdefault(articulo.categoria or "Sin categoria", []).append(articulo)

    return [
        Grupo(nombre=categoria, articulos=sorted(items, key=lambda a: a.nombre.lower()))
        for categoria, items in sorted(por_categoria.items(), key=lambda par: par[0].lower())
    ]


def _secciones(articulos_por_canal: Dict[str, List[Articulo]]) -> List[Seccion]:
    """Una seccion por canal con contenido, en el orden del recorrido de compra."""
    secciones = []
    for canal in canales.CANALES:
        articulos = articulos_por_canal.get(canal["id"], [])
        if articulos:
            secciones.append(Seccion(canal=canal, grupos=_agrupar(articulos)))
    return secciones


def _articulo_de_linea(linea) -> Articulo:
    insumo = getattr(linea, "insumo", None)
    nombre = (getattr(insumo, "nombre", None) or "Insumo sin nombre").strip()
    return Articulo(
        insumo_id=linea.insumo_id_publico or "-",
        nombre=nombre,
        categoria=(getattr(insumo, "categoria", None) or "Sin categoria").strip(),
        presentacion=formato.presentacion(nombre, getattr(insumo, "presentacion", None)),
        cantidad=float(linea.cantidad or 0),
    )


def de_pedido(pedido) -> Documento:
    """Hoja de compras de un pedido concreto."""
    por_canal: Dict[str, List[Articulo]] = {}
    for linea in pedido.lineas:
        por_canal.setdefault(canales.de_linea(linea), []).append(_articulo_de_linea(linea))

    numero = formato.folio(pedido.id_publico)
    return Documento(
        titulo="Lista de compras",
        subtitulo=f"Pedido {numero}",
        meta=[
            ("Pedido", numero),
            ("Solicita", (pedido.solicitante or "Sin solicitante").strip()),
            ("Fecha", formato.fecha_hora(pedido.fecha_solicitud)),
            ("Estado", (pedido.estado or "pendiente").capitalize()),
        ],
        nota=(pedido.motivo or "").strip() or None,
        secciones=_secciones(por_canal),
        firmas=("Autoriza gobernanta", "Recibe en cocina"),
        nombre_archivo=f"Pedido_{numero}.pdf",
    )


def consolidado(pedidos: Sequence, estados: Sequence[str]) -> Documento:
    """
    Una sola lista con todo lo que falta comprar.

    El mismo insumo pedido por varias personas se suma en una linea, y debajo
    queda el detalle de quien pidio cuanto para poder repartirlo al volver.
    """
    acumulado: Dict[Tuple[str, str], Articulo] = {}

    for pedido in pedidos:
        solicitante = (pedido.solicitante or "Sin solicitante").strip()
        for linea in pedido.lineas:
            articulo = _articulo_de_linea(linea)
            canal = canales.de_linea(linea)
            clave = (canal, articulo.insumo_id)

            existente = acumulado.get(clave)
            if existente is None:
                articulo.solicitantes = [(solicitante, articulo.cantidad)]
                acumulado[clave] = articulo
                continue

            existente.cantidad += articulo.cantidad
            for indice, (nombre, cantidad) in enumerate(existente.solicitantes):
                if nombre == solicitante:
                    existente.solicitantes[indice] = (nombre, cantidad + articulo.cantidad)
                    break
            else:
                existente.solicitantes.append((solicitante, articulo.cantidad))

    por_canal: Dict[str, List[Articulo]] = {}
    for (canal, _), articulo in acumulado.items():
        por_canal.setdefault(canal, []).append(articulo)

    etiquetas = ", ".join(estado.capitalize() for estado in estados)
    return Documento(
        titulo="Lista de compras",
        subtitulo="Consolidado de pedidos por comprar",
        meta=[
            ("Pedidos", str(len(pedidos))),
            ("Incluye", etiquetas or "Todos"),
            ("Generado", formato.fecha_hora(datetime.now())),
        ],
        nota=None,
        secciones=_secciones(por_canal),
        firmas=("Autoriza gobernanta", "Recibe en cocina"),
        nombre_archivo=f"Lista_compras_{formato.sello()}.pdf",
    )
