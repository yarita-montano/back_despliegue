"""
Schemas del seguimiento publico en vivo (opcion C).

Define el contrato que consume la pagina web publica /seguir/{token} y la
respuesta al generar el enlace compartible.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PuntoGeo(BaseModel):
    latitud: float
    longitud: float


class CompartirSeguimientoResponse(BaseModel):
    """Respuesta al generar un enlace de seguimiento compartible."""
    token: str
    url: str
    expira_horas: int


class SeguimientoPublicoResponse(BaseModel):
    """
    Estado en vivo que ve la pagina publica. `tecnico` es null mientras no haya
    tecnico asignado o aun no haya compartido su ubicacion.
    """
    id_incidente: int
    estado: str
    cliente: PuntoGeo
    tecnico: Optional[PuntoGeo] = None
    nombre_tecnico: Optional[str] = None
    taller_nombre: Optional[str] = None
    eta_min: Optional[int] = None
    distancia_km: Optional[float] = None
    actualizado: datetime
