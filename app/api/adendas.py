"""Endpoints de Adendas (ampliacion de presupuesto)."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.core.tenant_context import current_tenant
from app.db.session import get_db
from app.models.incidente import Asignacion
from app.models.transaccional import Adenda
from app.models.usuario import Usuario
from app.schemas.adenda_schema import (
    AdendaResponse,
    CrearAdendaRequest,
    ResponderAdendaRequest,
)
from app.services import adenda_service


router = APIRouter(tags=["Adendas"])


@router.post(
    "/asignaciones/{id_asignacion}/adendas",
    response_model=AdendaResponse,
    status_code=201,
    summary="Tecnico registra una ampliacion de presupuesto sobre la asignacion",
)
def crear_adenda_endpoint(
    id_asignacion: int,
    body: CrearAdendaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.id_rol != 3:
        raise HTTPException(403, "Solo un tecnico (rol=3) puede registrar adendas")

    tok = current_tenant.set(0)
    try:
        asig = db.query(Asignacion).get(id_asignacion)
    finally:
        current_tenant.reset(tok)
    if not asig:
        raise HTTPException(404, "Asignacion no existe")

    # Se valida que el usuario sea el tecnico asignado al servicio.
    if asig.id_usuario is not None and asig.id_usuario != current_user.id_usuario:
        raise HTTPException(403, "No eres el tecnico asignado a este servicio")

    return adenda_service.crear_adenda(
        db=db,
        asignacion=asig,
        tecnico=current_user,
        monto_adicional=body.monto_adicional,
        descripcion=body.descripcion,
    )


@router.get(
    "/asignaciones/{id_asignacion}/adendas",
    response_model=List[AdendaResponse],
    summary="Lista adendas de una asignacion",
)
def listar_adendas(
    id_asignacion: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    tok = current_tenant.set(0)
    try:
        asig = db.query(Asignacion).get(id_asignacion)
    finally:
        current_tenant.reset(tok)
    if not asig:
        raise HTTPException(404, "Asignacion no existe")

    # Solo el cliente dueno o el tecnico asignado pueden consultar la asignacion.
    incidente = asig.incidente
    es_cliente = incidente and incidente.id_usuario == current_user.id_usuario
    es_tecnico = asig.id_usuario == current_user.id_usuario
    if not (es_cliente or es_tecnico):
        raise HTTPException(403, "No tienes acceso a esta asignacion")

    return (
        db.query(Adenda)
        .filter(Adenda.id_asignacion == id_asignacion)
        .order_by(Adenda.created_at.desc())
        .all()
    )


@router.post(
    "/adendas/{id_adenda}/responder",
    response_model=AdendaResponse,
    summary="Cliente aprueba o rechaza la adenda pendiente",
)
def responder_adenda_endpoint(
    id_adenda: int,
    body: ResponderAdendaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    tok = current_tenant.set(0)
    try:
        ad = db.query(Adenda).get(id_adenda)
    finally:
        current_tenant.reset(tok)
    if not ad:
        raise HTTPException(404, "Adenda no existe")

    return adenda_service.responder_adenda(
        db=db,
        adenda=ad,
        cliente=current_user,
        decision=body.decision,
        motivo=body.motivo,
    )
