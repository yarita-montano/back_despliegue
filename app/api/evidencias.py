"""
Router de Evidencias (CU-06).

Permite al usuario subir fotos/audios de su incidente.
El archivo se guarda en Cloudinary; la URL se guarda en PostgreSQL.

Endpoints:
  POST   /incidencias/{id}/evidencias         → subir archivo
  GET    /incidencias/{id}/evidencias         → listar evidencias del incidente
  GET    /incidencias/evidencias/tipos        → catálogo de tipos (imagen|audio|texto)
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.usuario import Usuario
from app.models.incidente import Incidente, Evidencia
from app.models.catalogos import TipoEvidencia
from app.schemas.evidencia_schema import EvidenciaResponse, TipoEvidenciaResponse
from app.core.security import get_current_user
from app.services.cloudinary_service import subir_evidencia

router = APIRouter(
    prefix="/incidencias",
    tags=["Evidencias (CU-06)"],
    responses={
        401: {"description": "No autorizado"},
        404: {"description": "Incidencia no encontrada"},
    },
)


@router.get(
    "/evidencias/tipos",
    response_model=List[TipoEvidenciaResponse],
    summary="Catálogo de tipos de evidencia",
)
def listar_tipos_evidencia(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return db.query(TipoEvidencia).all()


@router.post(
    "/{id_incidente}/evidencias",
    response_model=EvidenciaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subir una evidencia a un incidente",
)
async def subir_evidencia_incidente(
    id_incidente: int,
    id_tipo_evidencia: int = Form(..., description="1=imagen, 2=audio, 3=texto"),
    archivo: UploadFile = File(..., description="Archivo a subir"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Sube un archivo a Cloudinary y registra la URL en la tabla `evidencia`.

    Seguridad: solo el dueño del incidente puede subir evidencias a él.
    """
    incidente = (
        db.query(Incidente)
        .filter(
            Incidente.id_incidente == id_incidente,
            Incidente.id_usuario == current_user.id_usuario,
        )
        .first()
    )
    if not incidente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incidente no encontrado o no te pertenece",
        )

    tipo = db.query(TipoEvidencia).filter(
        TipoEvidencia.id_tipo_evidencia == id_tipo_evidencia
    ).first()
    if not tipo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de evidencia inválido",
        )

    resultado = await subir_evidencia(
        archivo=archivo,
        tipo=tipo.nombre,
        id_incidente=id_incidente,
    )

    nueva_evidencia = Evidencia(
        id_incidente=id_incidente,
        id_tipo_evidencia=id_tipo_evidencia,
        url_archivo=resultado["url"],
    )
    db.add(nueva_evidencia)
    db.commit()
    db.refresh(nueva_evidencia)

    return nueva_evidencia


@router.get(
    "/{id_incidente}/evidencias",
    response_model=List[EvidenciaResponse],
    summary="Listar evidencias de un incidente",
)
def listar_evidencias_incidente(
    id_incidente: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    incidente = (
        db.query(Incidente)
        .filter(
            Incidente.id_incidente == id_incidente,
            Incidente.id_usuario == current_user.id_usuario,
        )
        .first()
    )
    if not incidente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incidente no encontrado o no te pertenece",
        )

    return (
        db.query(Evidencia)
        .filter(Evidencia.id_incidente == id_incidente)
        .order_by(Evidencia.created_at.desc())
        .all()
    )
