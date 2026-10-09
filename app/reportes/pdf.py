"""Conversion de HTML a PDF."""

import io
import os

from fastapi import HTTPException
from xhtml2pdf import pisa

RECURSOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recursos")


def _resolver_recurso(uri: str, rel) -> str:
    """
    Resuelve las imagenes contra archivos del propio servidor.

    Antes el logo se descargaba de Vercel en cada generacion: si esa red fallaba
    o tardaba, la generacion del PDF se quedaba colgada. Ahora el documento no
    depende de nada externo.
    """
    candidato = os.path.join(RECURSOS, os.path.basename(uri))
    return candidato if os.path.isfile(candidato) else uri


def a_pdf(html: str) -> io.BytesIO:
    buffer = io.BytesIO()
    resultado = pisa.CreatePDF(html, dest=buffer, encoding="utf-8", link_callback=_resolver_recurso)
    if resultado.err:
        raise HTTPException(status_code=500, detail="No se pudo generar el PDF del reporte")
    buffer.seek(0)
    return buffer
