"""
USUARIO: clientes de la app móvil y admins.
VEHICULO: vehículos registrados por los clientes.

Los talleres y técnicos NO viven en esta tabla: tienen sus propias tablas.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base


class Usuario(Base):
    __tablename__ = "usuario"

    id_usuario = Column(Integer, primary_key=True, index=True)
    id_rol = Column(Integer, ForeignKey("rol.id_rol"), nullable=False)

    nombre = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    telefono = Column(String(20), nullable=True)

    password_hash = Column(String(255), nullable=False)  # Argon2 / bcrypt
    push_token = Column(String(255), nullable=True)

    activo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    rol = relationship("Rol", back_populates="usuarios")
    vehiculos = relationship("Vehiculo", back_populates="usuario")
    incidentes = relationship("Incidente", back_populates="usuario")
    asignaciones_tecnico = relationship("Asignacion", back_populates="usuario_tecnico", foreign_keys="Asignacion.id_usuario")
    talleres_asociados = relationship("UsuarioTaller", back_populates="usuario", cascade="all, delete-orphan")


class Vehiculo(Base):
    __tablename__ = "vehiculo"

    id_vehiculo = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=False, index=True)

    placa = Column(String(20), nullable=False)
    marca = Column(String(50), nullable=True)
    modelo = Column(String(50), nullable=True)
    anio = Column(Integer, nullable=True)
    color = Column(String(30), nullable=True)

    activo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    usuario = relationship("Usuario", back_populates="vehiculos")
    incidentes = relationship("Incidente", back_populates="vehiculo")
