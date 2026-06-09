"""
Router del asistente de reportes en lenguaje natural (solo admin rol 4).

Flujo de tres pasos:
  POST /admin/reportes/interpretar  -> NL a spec con Gemini (o aclaracion)
  POST /admin/reportes/ejecutar     -> previsualizacion tabular
  POST /admin/reportes/exportar     -> archivo PDF / Excel
  GET  /admin/reportes/catalogo     -> lista de reportes predefinidos

El catalogo es cerrado: el front solo pasa un report_id del whitelist y los
params; el backend re-valida ambos.
"""
from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.core.security import get_current_admin
from app.db.session import get_db
from app.schemas.reportes_schema import (
    CatalogoItem,
    EjecutarReporteRequest,
    EjecutarReporteResponse,
    ExportarReporteRequest,
    NlReporteRequest,
    NlReporteResponse,
)
from app.services import export_service
from app.services import reportes_data_service as data
from app.services import reportes_nl_service as nl

router = APIRouter(
    prefix="/admin/reportes",
    tags=["Reportes IA"],
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "Requiere rol de administrador"},
    },
)


@router.get(
    "/catalogo",
    response_model=list[CatalogoItem],
    summary="Catalogo de reportes predefinidos",
)
def catalogo(_admin=Depends(get_current_admin)):
    return [
        CatalogoItem(
            report_id=c["report_id"],
            titulo=c["titulo"],
            descripcion=c["descripcion"],
            params=c["params"],
        )
        for c in data.CATALOGO
    ]


@router.post(
    "/interpretar",
    response_model=NlReporteResponse,
    summary="Interpretar una peticion en lenguaje natural",
)
@limiter.limit("12/minute")
def interpretar(
    request: Request,
    body: NlReporteRequest,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    try:
        return nl.interpretar(db, body.texto)
    except RuntimeError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e))


@router.post(
    "/ejecutar",
    response_model=EjecutarReporteResponse,
    summary="Ejecutar un reporte y obtener su tabla",
)
def ejecutar(
    body: EjecutarReporteRequest,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    try:
        titulo, columnas, filas = data.ejecutar(db, body.report_id, body.params)
    except KeyError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Reporte no reconocido: {body.report_id}"
        )
    return EjecutarReporteResponse(
        report_id=body.report_id,
        titulo=titulo,
        columnas=columnas,
        filas=filas,
        params_aplicados=body.params,
    )


@router.post("/exportar", summary="Exportar un reporte a PDF o Excel")
def exportar(
    body: ExportarReporteRequest,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    try:
        titulo, columnas, filas = data.ejecutar(db, body.report_id, body.params)
    except KeyError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Reporte no reconocido: {body.report_id}"
        )

    if body.formato == "excel":
        contenido = export_service.to_excel(titulo, columnas, filas)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ext = "xlsx"
    else:
        contenido = export_service.to_pdf(titulo, columnas, filas)
        media = "application/pdf"
        ext = "pdf"

    fecha = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = f"reporte_{body.report_id}_{fecha}.{ext}"
    return StreamingResponse(
        BytesIO(contenido),
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
