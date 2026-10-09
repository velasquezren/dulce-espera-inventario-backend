"""
Documentos de compras: HTML para ver en pantalla, PDF para imprimir y Excel
para trabajar la planilla.

Todas las direcciones que ya usaban FileMaker y la PWA siguen funcionando.
"""

from typing import List, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app import models
from app.database import get_db
from app.reportes import excel, modelo, pdf, plantilla

router = APIRouter(tags=["Reportes"])

EXCEL_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

#: Lo que todavia no se compro ni se rechazo.
ESTADOS_POR_COMPRAR = ("pendiente", "en revision", "aceptado")


def _pedido(db: Session, id_publico: str) -> models.Pedido:
    pedido = (
        db.query(models.Pedido)
        .options(joinedload(models.Pedido.lineas).joinedload(models.DetallePedido.insumo))
        .filter(models.Pedido.id_publico == id_publico)
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")
    return pedido


def _pedidos_por_estado(db: Session, estados: Sequence[str]) -> List[models.Pedido]:
    return (
        db.query(models.Pedido)
        .options(joinedload(models.Pedido.lineas).joinedload(models.DetallePedido.insumo))
        .filter(models.Pedido.estado.in_(list(estados)))
        .order_by(models.Pedido.fecha_solicitud.asc())
        .all()
    )


def _descarga(buffer, nombre: str, mime: str) -> StreamingResponse:
    return StreamingResponse(
        buffer,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


# --- Hoja de compras de un pedido -------------------------------------------

@router.get("/pedidos/{id_publico}/reporte", response_class=HTMLResponse)
@router.get("/pedidos/{id_publico}/reporte-admin", response_class=HTMLResponse, include_in_schema=False)
@router.get("/pedidos/{id_publico}/reporte-abastecimiento", response_class=HTMLResponse, include_in_schema=False)
@router.get("/pedidos/{id_publico}/reporte-categorias", response_class=HTMLResponse, include_in_schema=False)
def ver_reporte_pedido(id_publico: str, db: Session = Depends(get_db)):
    """
    Hoja de compras del pedido en HTML.

    Las cuatro direcciones eran cuatro plantillas casi iguales mantenidas por
    separado. Ahora comparten el mismo documento; las rutas se conservan para no
    romper nada que ya las estuviera abriendo.
    """
    documento = modelo.de_pedido(_pedido(db, id_publico))
    return HTMLResponse(content=plantilla.render(documento))


@router.get("/pedidos/{id_publico}/reporte/pdf")
def descargar_reporte_pedido_pdf(id_publico: str, db: Session = Depends(get_db)):
    """PDF del pedido, con una hoja por canal de compra."""
    documento = modelo.de_pedido(_pedido(db, id_publico))
    return _descarga(pdf.a_pdf(plantilla.render(documento)), documento.nombre_archivo, "application/pdf")


@router.get("/pedidos/{id_publico}/reporte/excel")
@router.get("/pedidos/{id_publico}/reporte-excel", include_in_schema=False)
def descargar_reporte_pedido_excel(id_publico: str, db: Session = Depends(get_db)):
    """Planilla del pedido con subtotales por canal y columnas de recepcion."""
    pedido = _pedido(db, id_publico)
    fecha_slug = pedido.fecha_solicitud.strftime("%Y%m%d_%H%M") if pedido.fecha_solicitud else "pedido"
    nombre = f"Orden_Compra_{pedido.id_publico[:8].upper()}_{fecha_slug}.xlsx"
    return _descarga(excel.generar_excel_pedido(pedido), nombre, EXCEL_MIME)


# --- Consolidado de varios pedidos ------------------------------------------

@router.get("/api/compras/pendientes/pdf")
def descargar_lista_compras_pdf(
    db: Session = Depends(get_db),
    estados: str = Query(
        ",".join(ESTADOS_POR_COMPRAR),
        description="Estados a incluir, separados por coma.",
    ),
):
    """
    Lista unica con todo lo que falta comprar.

    Junta los pedidos abiertos y suma el mismo insumo pedido por varias
    personas, para hacer una sola compra en vez de una por pedido.
    """
    seleccion = [estado.strip().lower() for estado in estados.split(",") if estado.strip()]
    pedidos = _pedidos_por_estado(db, seleccion or ESTADOS_POR_COMPRAR)
    documento = modelo.consolidado(pedidos, seleccion or ESTADOS_POR_COMPRAR)
    return _descarga(pdf.a_pdf(plantilla.render(documento)), documento.nombre_archivo, "application/pdf")


@router.get("/api/pedidos/pendientes/excel")
def descargar_consolidado_pendientes_excel(db: Session = Depends(get_db)):
    """Consolidado maestro de los pedidos pendientes en planilla."""
    from app.reportes.formato import sello

    pedidos = _pedidos_por_estado(db, ("pendiente",))
    return _descarga(
        excel.generar_excel_pendientes(pedidos),
        f"Consolidado_Pendientes_{sello()}.xlsx",
        EXCEL_MIME,
    )
