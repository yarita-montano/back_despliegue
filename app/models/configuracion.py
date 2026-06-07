"""
Configuracion global de la plataforma (super-admin).

Tabla singleton: contiene una unica fila (id=1) con parametros que aplican a
TODOS los talleres del SaaS, sin distincion de tenant. Hoy solo aloja la
comision que la plataforma retiene de cada servicio, pero esta pensada para
crecer con futuros ajustes globales.
"""
from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.sql import func

from app.db.session import Base


class ConfiguracionPlataforma(Base):
    """
    Parametros globales de la plataforma. Se gestiona como singleton (id=1).
    """
    __tablename__ = "configuracion_plataforma"

    id = Column(Integer, primary_key=True, index=True)

    # comision_plataforma_pct: % que la plataforma retiene de cada servicio
    # (lo que NO recibe el taller). Antes estaba fijo en 10%.
    comision_plataforma_pct = Column(Integer, default=10, nullable=False, server_default="10")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
