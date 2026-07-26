from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Insumo(Base):
    __tablename__ = "insumos"

    id_publico = Column(String(36), primary_key=True, index=True)
    nombre = Column(String(150), nullable=True)
    categoria = Column(String(100), nullable=True)
    presentacion = Column(String(100), nullable=True)
    activo = Column(Integer, default=1)  # TINYINT maps to Integer in SQLAlchemy
    fecha_actualizacion = Column(DateTime, nullable=True)

    # Relationships
    detalles = relationship("DetallePedido", back_populates="insumo")


class Pedido(Base):
    __tablename__ = "pedidos"

    id_publico = Column(String(36), primary_key=True, index=True)
    solicitante = Column(String(100), nullable=True)
    fecha_solicitud = Column(DateTime, nullable=True)
    estado = Column(String(30), default="pendiente")
    fecha_estado = Column(DateTime, nullable=True)
    motivo = Column(String(500), nullable=True)

    # Relationships
    lineas = relationship("DetallePedido", back_populates="pedido", cascade="all, delete-orphan")


class DetallePedido(Base):
    __tablename__ = "detalle_pedido"

    id_publico = Column(String(36), primary_key=True, index=True)
    pedido_id_publico = Column(String(36), ForeignKey("pedidos.id_publico"), nullable=True)
    insumo_id_publico = Column(String(36), ForeignKey("insumos.id_publico"), nullable=True)
    cantidad = Column(Numeric(10, 2), nullable=True)

    # Relationships
    pedido = relationship("Pedido", back_populates="lineas")
    insumo = relationship("Insumo", back_populates="detalles")


class Coordinador(Base):
    __tablename__ = "coordinadores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)
    telefono = Column(String(20), nullable=False)
    activo = Column(Integer, default=1)


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True)
    password = Column(String(100), nullable=False)
    nombre_display = Column(String(100), nullable=False)
    rol = Column(String(50), default='cocina')
    activo = Column(Integer, default=1)

