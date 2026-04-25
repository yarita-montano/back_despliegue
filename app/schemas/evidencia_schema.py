"""
Esquemas Pydantic para Evidencias (CU-06).
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class EvidenciaResponse(BaseModel):
    id_evidencia: int
    id_incidente: int
    id_tipo_evidencia: int
    url_archivo: str
    transcripcion_audio: Optional[str] = None
    descripcion_ia: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TipoEvidenciaResponse(BaseModel):
    id_tipo_evidencia: int
    nombre: str

    class Config:
        from_attributes = True
