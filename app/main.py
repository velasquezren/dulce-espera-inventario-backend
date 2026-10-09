import hashlib
import html
import time
import uuid
from datetime import datetime
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, DBAPIError
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db, engine
from app import estados, models, schemas
from app.routers import reportes

# Initialize the FastAPI app
app = FastAPI(
    title="Backend Dulce Espera",
    description="API para la gestión de pedidos e insumos del sistema Dulce Espera.",
    version="1.0.0"
)

# Enable Gzip compression for fast network transfers
app.add_middleware(GZipMiddleware, minimum_size=500)

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

# --- UTILIDADES ---

def esc(valor) -> str:
    """
    Escapa texto antes de interpolarlo en las plantillas HTML de los reportes.

    Los reportes se construyen con f-strings, así que cualquier texto que no
    venga de este archivo puede cerrar una etiqueta e inyectar marcado. El
    campo 'solicitante' lo escribe quien crea el pedido y los nombres del
    catálogo llegan desde FileMaker, de modo que ninguno de los dos es de
    confianza. Devuelve cadena vacía para None para no imprimir "None".
    """
    return html.escape(str(valor)) if valor is not None else ""


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
    insumos = db.query(models.Insumo).filter(
        models.Insumo.activo == 1
    ).order_by(models.Insumo.nombre.asc()).all()
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
    import logging
    logger = logging.getLogger("uvicorn")
    logger.info(f"RECIBIDO CREAR PEDIDO: {pedido_in.model_dump()}")

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
            fecha_estado=ahora,
            motivo=pedido_in.motivo
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

@app.get("/api/pedidos/pendientes", tags=["FileMaker"])
def obtener_pedidos_pendientes_fm(db: Session = Depends(get_db)):
    """
    Devuelve un JSON estructurado de forma limpia con los pedidos que tengan estado = 'pendiente'.
    Cada pedido incluye su lista de detalles anidada, incluyendo detalles descriptivos de los insumos.
    """
    pedidos = db.query(models.Pedido).options(
        joinedload(models.Pedido.lineas).joinedload(models.DetallePedido.insumo)
    ).filter(
        models.Pedido.estado == "pendiente"
    ).order_by(
        models.Pedido.fecha_solicitud.asc()
    ).all()

    resultado = []
    for p in pedidos:
        detalles_lista = []
        for l in p.lineas:
            detalles_lista.append({
                "id_publico": l.id_publico,
                "insumo_id_publico": l.insumo_id_publico,
                "nombre_insumo": l.insumo.nombre if l.insumo else None,
                "categoria_insumo": l.insumo.categoria if l.insumo else None,
                "grupo_insumo": l.insumo.grupo if l.insumo else None,
                "presentacion_insumo": l.insumo.presentacion if l.insumo else None,
                "cantidad": float(l.cantidad) if l.cantidad else 0.0
            })
        resultado.append({
            "id_publico": p.id_publico,
            "solicitante": p.solicitante,
            "fecha_solicitud": p.fecha_solicitud.strftime("%Y-%m-%d %H:%M:%S") if p.fecha_solicitud else None,
            "motivo": p.motivo,
            "detalles": detalles_lista
        })

    return resultado


@app.get("/api/pedidos/detalles-pendientes-flat", tags=["FileMaker"])
def obtener_detalles_pendientes_flat_fm(db: Session = Depends(get_db)):
    """
    Devuelve una lista completamente plana (flat) con todas las líneas de detalles
    de los pedidos que están en estado = 'pendiente'.
    Esto simplifica el consumo desde FileMaker al evitar la necesidad de recorrer arrays aninados.
    """
    pedidos = db.query(models.Pedido).options(
        joinedload(models.Pedido.lineas).joinedload(models.DetallePedido.insumo)
    ).filter(
        models.Pedido.estado == "pendiente"
    ).order_by(
        models.Pedido.fecha_solicitud.asc()
    ).all()

    resultado = []
    for p in pedidos:
        for l in p.lineas:
            resultado.append({
                "pedido_id_publico": p.id_publico,
                "solicitante": p.solicitante,
                "fecha_solicitud": p.fecha_solicitud.strftime("%Y-%m-%d %H:%M:%S") if p.fecha_solicitud else None,
                "estado": p.estado,
                "motivo": p.motivo,
                "detalle_id_publico": l.id_publico,
                "insumo_id_publico": l.insumo_id_publico,
                "nombre_insumo": l.insumo.nombre if l.insumo else None,
                "categoria_insumo": l.insumo.categoria if l.insumo else None,
                "grupo_insumo": l.insumo.grupo if l.insumo else None,
                "presentacion_insumo": l.insumo.presentacion if l.insumo else None,
                "cantidad": float(l.cantidad) if l.cantidad else 0.0
            })

    return resultado



def _cambiar_estado(id_publico: str, nuevo_estado: str, db: Session) -> dict:
    """
    Aplica un cambio de estado respetando el flujo del pedido.

    Lo usan los dos endpoints de PATCH (el de FileMaker y el de la aplicacion)
    para que las reglas no dependan de por donde entre la peticion.
    """
    pedido = db.query(models.Pedido).filter(models.Pedido.id_publico == id_publico).first()
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido con ID '{id_publico}' no encontrado.",
        )

    destino = estados.normalizar(nuevo_estado)
    if destino is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado '{nuevo_estado}' no valido. Opciones: {', '.join(estados.ESTADOS)}",
        )

    problema = estados.motivo_de_rechazo(pedido.estado, destino)
    if problema:
        # 409: la peticion esta bien escrita, pero choca con el estado actual.
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=problema)

    estado_anterior = pedido.estado

    # Repetir el mismo estado no es un error ni vuelve a mover la fecha:
    # evita que un doble clic en FileMaker muestre una alerta sin motivo.
    if estados.normalizar(estado_anterior) != destino:
        pedido.estado = destino
        pedido.fecha_estado = datetime.now()
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

    return {
        "status": "success",
        "id_publico": pedido.id_publico,
        "estado_anterior": estado_anterior,
        "estado_nuevo": pedido.estado,
        "fecha_estado": pedido.fecha_estado.strftime("%Y-%m-%d %H:%M:%S") if pedido.fecha_estado else None,
    }


@app.patch("/api/pedidos/actualizar-estado", tags=["FileMaker"])
def actualizar_estado_pedido_fm(body: schemas.ActualizarEstadoRequest, db: Session = Depends(get_db)):
    """
    Cambia el estado de un pedido desde FileMaker.

    Si el cambio no corresponde al flujo del pedido responde 409 con una
    explicacion en texto, que es lo que FileMaker muestra en su dialogo.
    """
    return _cambiar_estado(body.id_publico, body.estado, db)


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
            "motivo": p.motivo,
            "total_lineas": len(lineas_plano),
            "lineas": lineas_plano
        })

    return {"pedidos": resultado, "total": len(resultado)}


@app.patch("/pedidos/actualizar-estado", tags=["Pedidos"])
def actualizar_estado_pedido(body: schemas.ActualizarEstadoRequest, db: Session = Depends(get_db)):
    """Cambia el estado de un pedido. Misma regla que la ruta de FileMaker."""
    return _cambiar_estado(body.id_publico, body.estado, db)


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


# Los documentos de compras (HTML, PDF y Excel) viven en su propio modulo.
app.include_router(reportes.router)
