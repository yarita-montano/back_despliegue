"""
USUARIO_TALLER: Tabla de asociación que vincula técnicos (usuario rol=3) con talleres.

Esta tabla reemplaza la antigua tabla 'tecnico' (que era un registro operativo sin login).
Ahora los técnicos son usuarios con rol=3 de la tabla usuario, y se vinculan a talleres
a través de esta tabla de asociación.

Beneficios:
- Un técnico puede pertenecer a múltiples talleres (si es necesario)
- Reutiliza tabla usuario existente (no duplica data)
- Mantiene historial de disponibilidad y ubicación por taller
"""
from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base


class UsuarioTaller(Base):
    """
    Vinculación de un usuario técnico (rol=3) a un taller específico.
    
    Permite que un técnico trabaje en uno o más talleres, y guarda metadatos
    específicos por taller (disponibilidad, ubicación, etc).
    """
    __tablename__ = "usuario_taller"
    __table_args__ = (
        UniqueConstraint("id_usuario", "id_taller", name="uq_usuario_taller"),
    )

    id_usuario_taller = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=False, index=True)
    id_taller = Column(Integer, ForeignKey("taller.id_taller"), nullable=False, index=True)

    # Estado del técnico en este taller específico
    disponible = Column(Boolean, default=True, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)

    # Ubicación actual (se actualiza cuando el técnico reporta su posición)
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    usuario = relationship("Usuario", back_populates="talleres_asociados")
    taller = relationship("Taller", back_populates="usuarios_tecnicos")
