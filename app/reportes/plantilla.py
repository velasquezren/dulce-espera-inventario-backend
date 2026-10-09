"""
Dibuja un Documento como HTML listo para imprimir.

Pensado para alguien que camina por el mercado con la hoja y un boligrafo:
una hoja por canal, casilla al principio de cada renglon, articulos agrupados
por categoria y una columna en blanco para anotar lo que realmente se compro.
"""

from html import escape
from typing import List

from app.reportes.modelo import Documento, Seccion

HOJA_CSS = """
@page {
    size: a4 portrait;
    margin: 1.3cm 1.3cm 1.9cm 1.3cm;
    @frame pie_pagina {
        -pdf-frame-content: pie-pagina;
        bottom: 0.9cm;
        left: 1.3cm;
        right: 1.3cm;
        height: 0.8cm;
    }
}

body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 10pt;
    color: #0F172A;
}

.marca { font-size: 13pt; font-weight: bold; color: #006156; letter-spacing: 0.5pt; }
.marca-sub { font-size: 8pt; color: #475569; }

.cabecera { width: 100%; border-bottom: 1.5pt solid #006156; padding-bottom: 6pt; margin-bottom: 10pt; }
.cabecera td { vertical-align: middle; }
.dato { font-size: 8.5pt; color: #475569; line-height: 1.5; }
.dato b { color: #0F172A; }

.titulo-canal { font-size: 15pt; font-weight: bold; }
.detalle-canal { font-size: 8.5pt; color: #475569; }
.conteo { font-size: 9pt; color: #475569; text-align: right; }
.franja { width: 100%; margin-bottom: 9pt; }
.franja td { vertical-align: bottom; }

.nota { background-color: #F1F5F9; border-left: 3pt solid #006156; padding: 6pt 9pt; font-size: 9pt; margin-bottom: 10pt; }
.nota b { color: #006156; }

table.articulos { width: 100%; border-collapse: collapse; }
table.articulos thead th {
    background-color: #006156;
    color: #FFFFFF;
    font-size: 7.5pt;
    text-transform: uppercase;
    letter-spacing: 0.4pt;
    padding: 4pt;
    text-align: left;
}
table.articulos td { padding: 3.5pt 4pt; border-bottom: 0.5pt solid #CBD5E1; }

.categoria td {
    background-color: #E8F1F0;
    font-size: 7.5pt;
    font-weight: bold;
    color: #006156;
    text-transform: uppercase;
    letter-spacing: 0.4pt;
    padding: 3pt 4pt;
    border-bottom: 0.5pt solid #BCD8D4;
}

.casilla { width: 11pt; border: 0.9pt solid #475569; font-size: 8pt; line-height: 11pt; }
.nombre { font-size: 9.5pt; font-weight: bold; }
.reparto { font-size: 7pt; color: #475569; }
.medida { font-size: 9.5pt; font-weight: bold; text-align: right; }
.medida-larga { font-size: 7.5pt; }
.anotar { font-size: 9pt; color: #94A3B8; }

.firmas { width: 100%; margin-top: 26pt; }
.firmas td { border-top: 0.5pt solid #64748B; padding-top: 4pt; font-size: 8pt; color: #475569; text-align: center; }

#pie-pagina { font-size: 7.5pt; color: #94A3B8; }
.vacio { font-size: 9pt; color: #475569; font-style: italic; padding: 10pt 0; }
"""


def _fila(articulo) -> str:
    reparto = articulo.detalle_solicitantes
    detalle = f'<div class="reparto">{escape(reparto)}</div>' if reparto else ""

    # Algunos insumos del catalogo traen una presentacion larguisima; se achica
    # la tipografia en vez de partir la celda en dos renglones.
    medida = f"{articulo.cantidad_texto} {articulo.presentacion}"
    clase_medida = "medida" if len(medida) <= 16 else "medida medida-larga"
    return f"""
        <tr>
            <td style="width: 18pt;"><div class="casilla">&nbsp;</div></td>
            <td><div class="nombre">{escape(articulo.nombre)}</div>{detalle}</td>
            <td class="{clase_medida}" style="width: 80pt;">{escape(medida)}</td>
            <td class="anotar" style="width: 66pt;">. . . . . . . .</td>
        </tr>"""


def _hoja(documento: Documento, seccion: Seccion, indice: int, total_hojas: int, ultima: bool) -> str:
    canal = seccion.canal
    datos = "<br/>".join(f"<b>{escape(e)}:</b> {escape(v)}" for e, v in documento.meta)

    filas: List[str] = []
    for grupo in seccion.grupos:
        filas.append(f'<tr class="categoria"><td colspan="4">{escape(grupo.nombre)}</td></tr>')
        filas.extend(_fila(articulo) for articulo in grupo.articulos)

    nota = ""
    if documento.nota and indice == 0:
        nota = f'<div class="nota"><b>Nota de cocina:</b> {escape(documento.nota)}</div>'

    firmas = "".join(
        f'<td style="width: 45%;">{escape(firma)}</td>'
        + ('<td style="width: 10%; border: none;">&nbsp;</td>' if posicion == 0 else "")
        for posicion, firma in enumerate(documento.firmas)
    )

    salto = "" if ultima else ' style="page-break-after: always;"'

    return f"""
    <div{salto}>
        <table class="cabecera">
            <tr>
                <td style="width: 34pt;"><img src="logo.png" style="width: 28pt; height: 28pt;" /></td>
                <td>
                    <div class="marca">CLÍNICA MONTALVO</div>
                    <div class="marca-sub">Dulce Espera &middot; {escape(documento.titulo)}</div>
                </td>
                <td class="dato" style="text-align: right;">{datos}</td>
            </tr>
        </table>

        <table class="franja">
            <tr>
                <td>
                    <div class="titulo-canal" style="color: {canal['color']};">{escape(canal['nombre']).upper()}</div>
                    <div class="detalle-canal">{escape(canal['detalle'])}</div>
                </td>
                <td class="conteo">
                    Canal {indice + 1} de {total_hojas}<br/>
                    <b>{seccion.total_articulos}</b> insumos
                </td>
            </tr>
        </table>

        {nota}

        <table class="articulos">
            <thead>
                <tr>
                    <th style="width: 18pt;">&nbsp;</th>
                    <th>Insumo</th>
                    <th style="width: 80pt; text-align: right;">Cantidad</th>
                    <th style="width: 66pt;">Comprado</th>
                </tr>
            </thead>
            <tbody>
                {''.join(filas)}
            </tbody>
        </table>

        <table class="firmas">
            <tr>{firmas}</tr>
        </table>
    </div>"""


def render(documento: Documento) -> str:
    """HTML completo del documento, una hoja por canal."""
    if not documento.secciones:
        cuerpo = (
            '<table class="cabecera"><tr>'
            '<td style="width: 34pt;"><img src="logo.png" style="width: 28pt; height: 28pt;" /></td>'
            f'<td><div class="marca">CLÍNICA MONTALVO</div>'
            f'<div class="marca-sub">Dulce Espera &middot; {escape(documento.titulo)}</div></td>'
            "</tr></table>"
            '<div class="vacio">Este documento no tiene insumos que comprar.</div>'
        )
    else:
        total = len(documento.secciones)
        cuerpo = "".join(
            _hoja(documento, seccion, indice, total, indice == total - 1)
            for indice, seccion in enumerate(documento.secciones)
        )

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <title>{escape(documento.subtitulo)}</title>
    <style>{HOJA_CSS}</style>
</head>
<body>
    <div id="pie-pagina">
        {escape(documento.subtitulo)} &middot; Página <pdf:pagenumber /> de <pdf:pagecount />
    </div>
    {cuerpo}
</body>
</html>"""
