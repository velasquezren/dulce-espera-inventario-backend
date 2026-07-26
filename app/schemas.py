from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, computed_field

# --- INSUMO SCHEMAS ---

class InsumoOut(BaseModel):
    id_publico: str
    nombre: Optional[str] = None
    categoria: Optional[str] = None
    presentacion: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# --- PEDIDO SCHEMAS ---

class DetallePedidoCreate(BaseModel):
    insumo_id_publico: str = Field(..., description="ID público del insumo")
    cantidad: Decimal = Field(..., gt=0, decimal_places=2, description="Cantidad mayor a 0 con hasta 2 decimales")


class PedidoCreate(BaseModel):
    solicitante: str = Field(..., min_length=1, max_length=100, description="Identificación del solicitante")
    lineas: List[DetallePedidoCreate] = Field(..., min_length=1, description="Debe contener al menos una línea de pedido")
    motivo: Optional[str] = Field(None, max_length=500, description="Motivo o comentario de la solicitud")


class DetallePedidoOut(BaseModel):
    id_publico: str
    insumo_id_publico: str
    cantidad: Decimal
    insumo: Optional[InsumoOut] = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def nombre_insumo(self) -> Optional[str]:
        """Provides flat access to the insumo name for frontend convenience."""
        return self.insumo.nombre if self.insumo else None

    @computed_field
    @property
    def categoria_insumo(self) -> Optional[str]:
        """Provides flat access to the insumo category."""
        return self.insumo.categoria if self.insumo else None

    @computed_field
    @property
    def presentacion_insumo(self) -> Optional[str]:
        """Provides flat access to the insumo presentation."""
        return self.insumo.presentacion if self.insumo else None


class PedidoOut(BaseModel):
    id_publico: str
    solicitante: Optional[str] = None
    fecha_solicitud: Optional[datetime] = None
    estado: str
    fecha_estado: Optional[datetime] = None
    motivo: Optional[str] = None
    lineas: List[DetallePedidoOut] = []

    model_config = ConfigDict(from_attributes=True)


class CoordinadorOut(BaseModel):
    id: int
    nombre: str
    telefono: str
    activo: int

    model_config = ConfigDict(from_attributes=True)


# --- LOGIN SCHEMAS ---

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, description="Nombre de usuario")
    password: str = Field(..., min_length=1, description="Contraseña")


# --- FILEMAKER SCHEMAS ---

class ActualizarEstadoRequest(BaseModel):
    id_publico: str = Field(..., description="UUID del pedido")
    estado: str = Field(..., description="Nuevo estado: pendiente, aceptado, rechazado, comprado, entregado, cancelado")

