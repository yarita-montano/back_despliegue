"""Schemas del asistente de reportes en lenguaje natural (admin rol 4)."""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ReporteParams(BaseModel):
    """Parametros extraidos de la peticion. Todos opcionales: el data service
    aplica defaults (ultimos 30 dias, SLA 60 min, etc.) cuando faltan."""
    desde: Optional[str] = None          # ISO date (YYYY-MM-DD)
    hasta: Optional[str] = None          # ISO date (YYYY-MM-DD)
    id_tenant: Optional[int] = None
    sla_minutos: Optional[int] = None
    limite: Optional[int] = None
    anio: Optional[int] = None
    mes: Optional[int] = None


class NlReporteRequest(BaseModel):
    texto: str = Field(..., min_length=1, max_length=500)


class NlReporteResponse(BaseModel):
    """Salida de /interpretar. Si report_id es None, la IA no identifico un
    reporte del catalogo y se devuelve aclaracion + sugerencias."""
    report_id: Optional[str] = None
    titulo: Optional[str] = None
    params: ReporteParams = Field(default_factory=ReporteParams)
    confianza: float = 0.0
    aclaracion: Optional[str] = None
    sugerencias: Optional[List[str]] = None


class EjecutarReporteRequest(BaseModel):
    report_id: str
    params: ReporteParams = Field(default_factory=ReporteParams)


class EjecutarReporteResponse(BaseModel):
    """Forma tabular uniforme: el front pinta cualquier reporte con una sola
    tabla (columnas como cabecera, filas como dicts keyados por columna)."""
    report_id: str
    titulo: str
    columnas: List[str]
    filas: List[dict]
    params_aplicados: ReporteParams


class ExportarReporteRequest(BaseModel):
    report_id: str
    formato: Literal["pdf", "excel"]
    params: ReporteParams = Field(default_factory=ReporteParams)


class CatalogoItem(BaseModel):
    report_id: str
    titulo: str
    descripcion: str
    params: List[str]
