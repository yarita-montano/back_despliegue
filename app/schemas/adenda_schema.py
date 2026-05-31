"""Schemas Pydantic para Adendas (ampliacion de presupuesto)."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class CrearAdendaRequest(BaseModel):
    """Tecnico/taller registra una adenda."""
    monto_adicional: float = Field(..., gt=0, le=100000)
    descripcion: str = Field(..., min_length=5, max_length=1000)


class ResponderAdendaRequest(BaseModel):
    """Cliente aprueba o rechaza la adenda."""
    decision: Literal["aprobar", "rechazar"]
    motivo: Optional[str] = Field(None, max_length=500)


class AdendaResponse(BaseModel):
    id_adenda: int
    id_asignacion: int
    id_tecnico: Optional[int] = None
    monto_adicional: float
    descripcion: str
    estado: str
    motivo_cliente: Optional[str] = None
    created_at: datetime
    respondida_at: Optional[datetime] = None

    class Config:
        from_attributes = True
