import hashlib
import time
import uuid
from datetime import datetime
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, DBAPIError
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db, engine
from app import models, schemas

# Initialize the FastAPI app
app = FastAPI(
    title="Backend Dulce Espera",
    description="API para la gestión de pedidos e insumos del sistema Dulce Espera.",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- GLOBAL DATABASE ERROR HANDLERS ---
# If the MySQL database is unreachable or down, return 503 Service Unavailable

@app.exception_handler(OperationalError)
def db_operational_error_handler(request, exc: OperationalError):
    import logging
    logger = logging.getLogger("uvicorn")
    logger.exception("OperationalError in DB:")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "detail": "No se pudo conectar a la base de datos MySQL. "
                      "Por favor, verifique la conexión y vuelva a intentarlo."
        }
    )

@app.exception_handler(DBAPIError)
def db_api_error_handler(request, exc: DBAPIError):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "detail": "Error en la base de datos. Por favor, intente de nuevo más tarde."
        }
    )

# --- ENDPOINTS ---

@app.get("/health", status_code=status.HTTP_200_OK, tags=["Control de Salud"])
def health_check(db: Session = Depends(get_db)):
    """
    Endpoint de salud rápido para verificar la API y la conexión a la base de datos.
    """
    try:
        # Simple query to check DB availability
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio está activo pero la base de datos no responde."
        )


@app.get("/insumos", response_model=List[schemas.InsumoOut], tags=["Insumos"])
def obtener_insumos(db: Session = Depends(get_db)):
    """
    Devuelve la lista de insumos activos cargados en el sistema.
    Retorna una lista vacía si aún no se han exportado insumos desde FileMaker.
    """
    insumos = db.query(models.Insumo).filter(models.Insumo.activo == 1).all()
    return insumos


@app.post("/pedidos", response_model=schemas.PedidoOut, status_code=status.HTTP_201_CREATED, tags=["Pedidos"])
def crear_pedido(pedido_in: schemas.PedidoCreate, db: Session = Depends(get_db)):
    """
    Crea un nuevo pedido de insumos.
    - Genera un UUID para el pedido.
    - Valida que todos los insumos solicitados existan y estén activos en la base de datos.
    - Valida que las cantidades sean mayores que cero (gestionado por el esquema de Pydantic).
    - Inserta los detalles de pedido correspondientes en una sola transacción.
    """
    pedido_uuid = str(uuid.uuid4())
    ahora = datetime.now()

    # 1. Verificar insumos
    insumo_ids = {linea.insumo_id_publico for linea in pedido_in.lineas}
    
    # Query active insumos matching the requested IDs
    insumos_activos = db.query(models.Insumo).filter(
        models.Insumo.id_publico.in_(insumo_ids),
        models.Insumo.activo == 1
    ).all()
    
    insumos_activos_dict = {i.id_publico: i for i in insumos_activos}

    # Validar que todos los insumos del pedido realmente existan y estén activos
    for linea in pedido_in.lineas:
        if linea.insumo_id_publico not in insumos_activos_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El insumo con ID público '{linea.insumo_id_publico}' no existe o no está activo en el catálogo."
            )

    # 2. Iniciar transacción e insertar datos
    try:
        # Crear pedido
        db_pedido = models.Pedido(
            id_publico=pedido_uuid,
            solicitante=pedido_in.solicitante,
            fecha_solicitud=ahora,
            estado="pendiente",
            fecha_estado=ahora
        )
        db.add(db_pedido)

        # Crear líneas de detalle
        for linea in pedido_in.lineas:
            detalle_uuid = str(uuid.uuid4())
            db_detalle = models.DetallePedido(
                id_publico=detalle_uuid,
                pedido_id_publico=pedido_uuid,
                insumo_id_publico=linea.insumo_id_publico,
                cantidad=linea.cantidad
            )
            db.add(db_detalle)

        db.commit()
    except Exception as e:
        db.rollback()
        raise e

    # 3. Retornar el pedido con todas sus relaciones cargadas en una sola consulta
    pedido_creado = db.query(models.Pedido).options(
        joinedload(models.Pedido.lineas).joinedload(models.DetallePedido.insumo)
    ).filter(models.Pedido.id_publico == pedido_uuid).first()

    if not pedido_creado:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al recuperar el pedido recién creado."
        )

    return pedido_creado


@app.get("/pedidos", response_model=List[schemas.PedidoOut], tags=["Pedidos"])
def consultar_pedidos(solicitante: str, db: Session = Depends(get_db)):
    """
    Devuelve la lista de pedidos realizados por un solicitante específico,
    incluyendo sus correspondientes líneas de detalle e información del insumo.
    """
    if not solicitante.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El parámetro 'solicitante' no puede estar vacío."
        )

    # Obtenemos los pedidos del solicitante, ordenados por fecha de solicitud descendente.
    # Usamos joinedload para evitar el problema de N+1 consultas.
    pedidos = db.query(models.Pedido).options(
        joinedload(models.Pedido.lineas).joinedload(models.DetallePedido.insumo)
    ).filter(
        models.Pedido.solicitante == solicitante
    ).order_by(
        models.Pedido.fecha_solicitud.desc()
    ).all()

    return pedidos


@app.get("/coordinadores", response_model=List[schemas.CoordinadorOut], tags=["Coordinadores"])
def obtener_coordinadores(db: Session = Depends(get_db)):
    """
    Devuelve la lista de coordinadores activos registrados en el sistema,
    para que la cocina pueda seleccionar a quién enviarle el pedido.
    """
    return db.query(models.Coordinador).filter(models.Coordinador.activo == 1).all()


# --- AUTENTICACIÓN ---

@app.post("/login", tags=["Autenticación"])
def login(login_in: schemas.LoginRequest, db: Session = Depends(get_db)):
    """
    Autenticación simple contra la tabla 'usuarios' en MySQL.
    Retorna un token, nombre y rol del usuario autenticado.
    Los usuarios se gestionan directamente en phpMyAdmin.
    """
    usuario = db.query(models.Usuario).filter(
        models.Usuario.username == login_in.username,
        models.Usuario.activo == 1
    ).first()

    if not usuario or usuario.password != login_in.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas. Verifique usuario y contraseña."
        )

    token = hashlib.sha256(f"{usuario.username}{time.time()}".encode()).hexdigest()[:32]

    return {
        "status": "success",
        "token": token,
        "nombre": usuario.nombre_display,
        "username": usuario.username,
        "rol": usuario.rol
    }


# --- ENDPOINTS PARA FILEMAKER ---

@app.get("/api/pedidos-pendientes", tags=["FileMaker"])
def pedidos_pendientes(estado: str = "pendiente", db: Session = Depends(get_db)):
    """
    Devuelve los pedidos filtrados por estado en formato JSON plano.
    Diseñado para que FileMaker lo consuma con 'Insertar desde URL' (GET).

    Uso desde FileMaker:
      Insertar desde URL [ $respuesta ; "https://tu-api/api/pedidos-pendientes" ]
      Insertar desde URL [ $respuesta ; "https://tu-api/api/pedidos-pendientes?estado=aceptado" ]
    """
    pedidos = db.query(models.Pedido).options(
        joinedload(models.Pedido.lineas).joinedload(models.DetallePedido.insumo)
    ).filter(
        models.Pedido.estado == estado.lower().strip()
    ).order_by(
        models.Pedido.fecha_solicitud.asc()
    ).all()

    resultado = []
    for p in pedidos:
        lineas_plano = []
        for l in p.lineas:
            lineas_plano.append({
                "insumo_id_publico": l.insumo_id_publico,
                "nombre_insumo": l.insumo.nombre if l.insumo else None,
                "categoria": l.insumo.categoria if l.insumo else None,
                "presentacion": l.insumo.presentacion if l.insumo else None,
                "cantidad": float(l.cantidad) if l.cantidad else 0
            })
        resultado.append({
            "id_publico": p.id_publico,
            "solicitante": p.solicitante,
            "fecha_solicitud": p.fecha_solicitud.isoformat() if p.fecha_solicitud else None,
            "estado": p.estado,
            "fecha_estado": p.fecha_estado.isoformat() if p.fecha_estado else None,
            "total_lineas": len(lineas_plano),
            "lineas": lineas_plano
        })

    return {"pedidos": resultado, "total": len(resultado)}


@app.patch("/pedidos/actualizar-estado", tags=["FileMaker"])
def actualizar_estado_pedido(body: schemas.ActualizarEstadoRequest, db: Session = Depends(get_db)):
    """
    Actualiza el estado de un pedido existente.
    Diseñado para que FileMaker envíe un PATCH cuando el administrador
    aprueba o rechaza un pedido.

    Uso desde FileMaker:
      Establecer variable [ $json ; JSONSetElement("{}"; ["id_publico"; $id; JSONString]; ["estado"; "aceptado"; JSONString]) ]
      Establecer variable [ $curl ; "-X PATCH -H \"Content-Type: application/json\" -d " & Quote($json) ]
      Insertar desde URL [ $respuesta ; "https://tu-api/pedidos/actualizar-estado" ; $curl ]

    Estados válidos: pendiente, aceptado, rechazado, en revision, comprado, entregado, cancelado
    """
    pedido = db.query(models.Pedido).filter(
        models.Pedido.id_publico == body.id_publico
    ).first()

    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido con ID '{body.id_publico}' no encontrado."
        )

    estados_validos = ["pendiente", "aceptado", "rechazado", "en revision", "comprado", "entregado", "cancelado"]
    estado_normalizado = body.estado.lower().strip()

    if estado_normalizado not in estados_validos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado '{body.estado}' no válido. Opciones: {', '.join(estados_validos)}"
        )

    estado_anterior = pedido.estado
    pedido.estado = estado_normalizado
    pedido.fecha_estado = datetime.now()

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise e

    return {
        "status": "success",
        "id_publico": pedido.id_publico,
        "estado_anterior": estado_anterior,
        "estado_nuevo": pedido.estado,
        "fecha_estado": pedido.fecha_estado.isoformat()
    }


@app.get("/pedidos/todos", response_model=List[schemas.PedidoOut], tags=["Pedidos"])
def obtener_todos_pedidos(db: Session = Depends(get_db)):
    """
    Devuelve TODOS los pedidos del sistema sin filtrar por solicitante.
    Incluye líneas de detalle e información del insumo.
    La PWA usa este endpoint para mostrar el estado global de pedidos.
    """
    pedidos = db.query(models.Pedido).options(
        joinedload(models.Pedido.lineas).joinedload(models.DetallePedido.insumo)
    ).order_by(
        models.Pedido.fecha_solicitud.desc()
    ).all()

    return pedidos


@app.get("/pedidos/{id_publico}/reporte", response_class=HTMLResponse, tags=["Pedidos"])
def ver_reporte_pedido(id_publico: str, db: Session = Depends(get_db)):
    """
    Genera una página HTML imprimible y elegante con el reporte completo del pedido,
    diseñada para ser enviada por WhatsApp y abierta en cualquier dispositivo.
    """
    pedido = db.query(models.Pedido).options(
        joinedload(models.Pedido.lineas).joinedload(models.DetallePedido.insumo)
    ).filter(models.Pedido.id_publico == id_publico).first()

    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )

    fecha_str = pedido.fecha_solicitud.strftime("%Y-%m-%d %H:%M") if pedido.fecha_solicitud else "N/A"
    
    # Generar filas de la tabla
    lineas_html = ""
    for idx, linea in enumerate(pedido.lineas, 1):
        nombre = linea.insumo.nombre if linea.insumo else "Insumo sin nombre"
        presentacion = linea.insumo.presentacion if linea.insumo else "Unidades"
        categoria = linea.insumo.categoria if linea.insumo else "Otros"
        cantidad_val = float(linea.cantidad) if linea.cantidad else 0.0
        
        lineas_html += f"""
        <tr style="border-bottom: 1px solid #e2e8f0;">
            <td style="padding: 12px 10px; text-align: center; font-weight: bold; color: #64748b;">{idx}</td>
            <td style="padding: 12px 10px; font-weight: bold; color: #0f172a; text-align: left;">{nombre}</td>
            <td style="padding: 12px 10px; color: #475569; font-size: 13px; text-align: left;">{categoria}</td>
            <td style="padding: 12px 10px; text-align: right; font-weight: 800; color: #006156; font-size: 15px;">{cantidad_val:.2f}</td>
            <td style="padding: 12px 10px; color: #475569; font-weight: 500; font-size: 13px; text-align: left;">{presentacion}</td>
        </tr>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Pedido - Dulce Espera</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: #0f172a;
            background-color: #f8fafc;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            padding: 40px;
            box-sizing: border-box;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 3px solid #006156;
            padding-bottom: 24px;
            margin-bottom: 30px;
        }}
        .brand {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        .brand-title {{
            font-size: 24px;
            font-weight: 800;
            color: #006156;
            margin: 0;
            letter-spacing: -0.025em;
        }}
        .brand-subtitle {{
            font-size: 13px;
            color: #39ADA3;
            font-weight: 700;
            margin-top: 4px;
        }}
        .meta {{
            text-align: right;
            font-size: 13px;
            color: #475569;
            line-height: 1.5;
        }}
        .meta strong {{
            color: #0f172a;
        }}
        .details-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            margin-bottom: 40px;
        }}
        .details-table th {{
            background-color: #f8fafc;
            color: #006156;
            font-weight: 700;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.05em;
            padding: 12px 10px;
            border-bottom: 2px solid #cbd5e1;
        }}
        .print-btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background-color: #006156;
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-size: 14px;
            font-weight: 700;
            cursor: pointer;
            transition: background-color 0.15s ease;
            margin-bottom: 20px;
            gap: 8px;
            text-decoration: none;
        }}
        .print-btn:hover {{
            background-color: #004d45;
        }}
        .no-print {{
            display: flex;
            justify-content: flex-end;
            max-width: 800px;
            margin: 0 auto;
        }}
        .footer {{
            border-top: 1px solid #e2e8f0;
            padding-top: 20px;
            text-align: center;
            font-size: 12px;
            color: #64748b;
            margin-top: 50px;
            line-height: 1.5;
        }}
        @media print {{
            body {{
                background-color: #ffffff;
                padding: 0;
            }}
            .container {{
                border: none;
                box-shadow: none;
                padding: 0;
                max-width: 100%;
            }}
            .no-print {{
                display: none !important;
            }}
        }}
    </style>
</head>
<body>
    <div class="no-print">
        <button class="print-btn" onclick="window.print()">
            <svg style="width: 18px; height: 18px;" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"></path>
            </svg>
            Imprimir / Guardar PDF
        </button>
    </div>
    <div class="container">
        <div class="header">
            <div class="brand">
                <img src="https://dulce-espera-inventario.vercel.app/icon.svg" alt="Logo" style="width: 50px; height: 50px; object-fit: contain;" onerror="this.style.display='none'">
                <div>
                    <h1 class="brand-title">DULCE ESPERA</h1>
                    <div class="brand-subtitle">Cocina y Nutrición</div>
                </div>
            </div>
            <div class="meta">
                <div><strong>ID Solicitud:</strong> {pedido.id_publico[:8].upper()}</div>
                <div style="font-size: 10px; color: #94a3b8; margin-bottom: 4px;">UUID: {pedido.id_publico}</div>
                <div><strong>Fecha:</strong> {fecha_str}</div>
                <div><strong>Solicitante:</strong> {pedido.solicitante}</div>
                <div><strong>Estado:</strong> <span style="text-transform: uppercase; font-weight: 800; color: #b45309;">{pedido.estado}</span></div>
            </div>
        </div>

        <h2 style="font-size: 16px; margin-bottom: 20px; font-weight: 700; color: #1e293b; border-left: 4px solid #006156; padding-left: 10px; text-align: left;">
            Detalle del Pedido de Insumos
        </h2>

        <table class="details-table">
            <thead>
                <tr>
                    <th style="width: 50px; text-align: center;">Item</th>
                    <th style="text-align: left;">Descripción Insumo</th>
                    <th style="text-align: left;">Categoría</th>
                    <th style="text-align: right; width: 100px;">Cantidad</th>
                    <th style="text-align: left; width: 120px;">Presentación</th>
                </tr>
            </thead>
            <tbody>
                {lineas_html}
            </tbody>
        </table>

        <div style="margin-top: 80px; display: flex; justify-content: space-around;">
            <div style="text-align: center; width: 220px; border-top: 1px solid #cbd5e1; padding-top: 8px; font-size: 12px; color: #475569; font-weight: 600;">
                Firma Responsable
            </div>
            <div style="text-align: center; width: 220px; border-top: 1px solid #cbd5e1; padding-top: 8px; font-size: 12px; color: #475569; font-weight: 600;">
                Firma Autorización
            </div>
        </div>

        <div class="footer">
            Este es un documento de uso interno para la Clínica Dulce Espera.<br>
            Generado automáticamente el {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}.
        </div>
    </div>
</body>
</html>"""
    return HTMLResponse(content=html_content)
