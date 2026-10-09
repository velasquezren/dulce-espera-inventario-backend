"""
Planillas de compras en Excel.

Comparten el mismo Documento que el PDF, asi que la hoja impresa y la planilla
no pueden contradecirse: mismo orden de canales, mismas categorias y la misma
regla de unidades.

Una pestana por canal, igual que las hojas del PDF: cada una se imprime y se
entrega por separado a quien va a comprar en ese lugar.
"""

import io
from typing import List, Sequence

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.reportes.modelo import Documento, Seccion

VERDE = "006156"
VERDE_SUAVE = "E8F1F0"
GRIS_LINEA = "CBD5E1"
GRIS_TEXTO = "475569"
TINTA = "0F172A"

FUENTE = "Calibri"

#: Ancho, titulo y alineacion de cada columna.
COLUMNAS = [
    (5, "N°", "center"),
    (42, "Insumo", "left"),
    (22, "Categoría", "left"),
    (11, "Cantidad", "right"),
    (14, "Unidad", "left"),
    (11, "Recibido", "center"),
    (13, "Cant. real", "center"),
    (30, "Observaciones", "left"),
]

TOTAL_COLUMNAS = len(COLUMNAS)
ULTIMA = get_column_letter(TOTAL_COLUMNAS)

_lado = Side(border_style="thin", color=GRIS_LINEA)
BORDE = Border(left=_lado, right=_lado, top=_lado, bottom=_lado)


def _texto(ws: Worksheet, celda: str, valor, *, tam=10, negrita=False, color=TINTA,
           fondo=None, alineacion="left", ajustar=False):
    c = ws[celda]
    c.value = valor
    c.font = Font(name=FUENTE, size=tam, bold=negrita, color=color)
    c.alignment = Alignment(horizontal=alineacion, vertical="center", wrap_text=ajustar)
    if fondo:
        c.fill = PatternFill("solid", start_color=fondo, end_color=fondo)
    return c


def _encabezado(ws: Worksheet, documento: Documento, seccion: Seccion) -> int:
    """Identidad del documento y datos del pedido. Devuelve la fila siguiente."""
    ws.merge_cells(f"A1:{ULTIMA}1")
    _texto(ws, "A1", "CLÍNICA MONTALVO · DULCE ESPERA", tam=14, negrita=True,
           color="FFFFFF", fondo=VERDE, alineacion="left")
    ws.row_dimensions[1].height = 26

    ws.merge_cells(f"A2:{ULTIMA}2")
    _texto(ws, "A2", f"{documento.titulo} · {seccion.canal['nombre']}",
           tam=11, negrita=True, color=VERDE)
    ws.row_dimensions[2].height = 18

    ws.merge_cells(f"A3:{ULTIMA}3")
    _texto(ws, "A3", seccion.canal["detalle"], tam=9, color=GRIS_TEXTO)

    # Los datos del pedido en dos columnas de etiqueta/valor.
    fila = 5
    for indice, (etiqueta, valor) in enumerate(documento.meta):
        columna = 1 if indice % 2 == 0 else 4
        f = fila + indice // 2
        _texto(ws, f"{get_column_letter(columna)}{f}", f"{etiqueta}:", tam=9,
               negrita=True, color=GRIS_TEXTO)
        ws.merge_cells(start_row=f, start_column=columna + 1, end_row=f,
                       end_column=columna + 2 if columna == 1 else TOTAL_COLUMNAS)
        _texto(ws, f"{get_column_letter(columna + 1)}{f}", valor, tam=10)

    fila += (len(documento.meta) + 1) // 2

    if documento.nota:
        fila += 1
        ws.merge_cells(f"A{fila}:{ULTIMA}{fila}")
        _texto(ws, f"A{fila}", f"Nota de cocina: {documento.nota}", tam=9,
               color=GRIS_TEXTO, fondo=VERDE_SUAVE, ajustar=True)
        ws.row_dimensions[fila].height = 24

    return fila + 2


def _tabla(ws: Worksheet, seccion: Seccion, fila: int) -> int:
    cabecera = fila
    for indice, (_, titulo, alineacion) in enumerate(COLUMNAS, start=1):
        _texto(ws, f"{get_column_letter(indice)}{cabecera}", titulo, tam=9,
               negrita=True, color="FFFFFF", fondo=VERDE, alineacion=alineacion)
        ws[f"{get_column_letter(indice)}{cabecera}"].border = BORDE
    ws.row_dimensions[cabecera].height = 20

    fila = cabecera + 1
    numero = 0

    for grupo in seccion.grupos:
        for articulo in grupo.articulos:
            numero += 1
            valores = [
                numero,
                articulo.nombre,
                grupo.nombre,
                articulo.cantidad,
                articulo.presentacion,
                None,  # casilla para marcar al recibir
                None,  # cantidad que llego de verdad
                None,  # observaciones
            ]
            for indice, valor in enumerate(valores, start=1):
                letra = get_column_letter(indice)
                celda = _texto(ws, f"{letra}{fila}", valor, tam=10,
                               negrita=(indice in (2, 4)),
                               alineacion=COLUMNAS[indice - 1][2])
                celda.border = BORDE
                if indice == 4:
                    # Entero cuando es entero: 2, no 2,00.
                    celda.number_format = "#,##0.##"
            fila += 1

    ultima_dato = fila - 1

    # Total honesto: insumos contados, no cantidades sumadas. Sumar kilos con
    # litros y unidades daba un numero que no significaba nada.
    ws.merge_cells(f"A{fila}:C{fila}")
    _texto(ws, f"A{fila}", f"TOTAL EN {seccion.canal['nombre'].upper()}", tam=10,
           negrita=True, color=VERDE, fondo=VERDE_SUAVE, alineacion="right")
    total = _texto(ws, f"D{fila}", numero, tam=11, negrita=True, color=VERDE,
                   fondo=VERDE_SUAVE, alineacion="right")
    total.number_format = "#,##0"
    _texto(ws, f"E{fila}", "insumos", tam=9, color=GRIS_TEXTO, fondo=VERDE_SUAVE)
    for indice in range(6, TOTAL_COLUMNAS + 1):
        _texto(ws, f"{get_column_letter(indice)}{fila}", None, fondo=VERDE_SUAVE)
    ws.row_dimensions[fila].height = 20

    return cabecera, ultima_dato, fila + 2


def _firmas(ws: Worksheet, documento: Documento, fila: int) -> None:
    fila += 1
    for indice, firma in enumerate(documento.firmas):
        columna = 1 if indice == 0 else 5
        ws.merge_cells(start_row=fila, start_column=columna, end_row=fila,
                       end_column=columna + 2)
        _texto(ws, f"{get_column_letter(columna)}{fila}", "_" * 34, tam=10,
               color=GRIS_TEXTO, alineacion="center")
        ws.merge_cells(start_row=fila + 1, start_column=columna, end_row=fila + 1,
                       end_column=columna + 2)
        _texto(ws, f"{get_column_letter(columna)}{fila + 1}", firma, tam=9,
               negrita=True, color=GRIS_TEXTO, alineacion="center")


def _impresion(ws: Worksheet, cabecera: int, ultima_dato: int, ultima_fila: int) -> None:
    """Una hoja A4 de ancho, con los titulos repetidos en cada pagina."""
    ws.page_setup.orientation = "portrait"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_title_rows = f"{cabecera}:{cabecera}"
    ws.print_area = f"A1:{ULTIMA}{ultima_fila}"
    ws.freeze_panes = f"A{cabecera + 1}"
    ws.sheet_view.showGridLines = False
    if ultima_dato > cabecera:
        ws.auto_filter.ref = f"A{cabecera}:{ULTIMA}{ultima_dato}"


def _hoja_de_canal(wb: Workbook, documento: Documento, seccion: Seccion) -> None:
    ws = wb.create_sheet(title=seccion.canal["id"][:31])

    for indice, (ancho, _, _) in enumerate(COLUMNAS, start=1):
        ws.column_dimensions[get_column_letter(indice)].width = ancho

    fila = _encabezado(ws, documento, seccion)
    cabecera, ultima_dato, fila = _tabla(ws, seccion, fila)
    _firmas(ws, documento, fila)
    _impresion(ws, cabecera, ultima_dato, fila + 2)


def _libro(documento: Documento) -> io.BytesIO:
    wb = Workbook()
    wb.remove(wb.active)

    for seccion in documento.secciones:
        _hoja_de_canal(wb, documento, seccion)

    if not wb.sheetnames:
        ws = wb.create_sheet(title="Sin insumos")
        _texto(ws, "A1", "Este documento no tiene insumos que comprar.", tam=11)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def generar_excel_pedido(pedido) -> io.BytesIO:
    from app.reportes import modelo

    return _libro(modelo.de_pedido(pedido))


def generar_excel_pendientes(pedidos: Sequence, estados: Sequence[str] = ("pendiente",)) -> io.BytesIO:
    from app.reportes import modelo

    return _libro(modelo.consolidado(list(pedidos), list(estados)))
