"""
Endpoints de Notificaciones.

  POST /notificaciones/push-token          → registrar FCM token (usuario)
  POST /notificaciones/taller/push-token   → registrar FCM token (taller)
  GET  /notificaciones/mis-notificaciones  → listar notificaciones del usuario
  GET  /notificaciones/taller              → listar notificaciones del taller
  PUT  /notificaciones/{id}/leer           → marcar como leída (usuario)
  PUT  /notificaciones/taller/{id}/leer    → marcar como leída (taller)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.user_model import Usuario
from app.models.taller import Taller
from app.models.transaccional import Notificacion
from app.schemas.transaccional_schema import PushTokenRequest, NotificacionResponse
from app.core.security import get_current_user, get_current_taller

router = APIRouter(
    prefix="/notificaciones",
    tags=["Notificaciones"],
)


# ── USUARIOS ──────────────────────────────────────────────────────────────────

@router.post(
    "/push-token",
    summary="Registrar FCM token del usuario (móvil)",
    status_code=status.HTTP_204_NO_CONTENT,
)
def registrar_push_token_usuario(
    payload: PushTokenRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    current_user.push_token = payload.push_token
    db.commit()


@router.get(
    "/mis-notificaciones",
    response_model=List[NotificacionResponse],
    summary="Listar notificaciones del usuario autenticado",
)
def listar_notificaciones_usuario(
    solo_no_leidas: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    q = db.query(Notificacion).filter(Notificacion.id_usuario == current_user.id_usuario)
    if solo_no_leidas:
        q = q.filter(Notificacion.leido == False)
    return q.order_by(Notificacion.created_at.desc()).limit(50).all()


@router.put(
    "/{id_notificacion}/leer",
    summary="Marcar notificación como leída (usuario)",
    status_code=status.HTTP_204_NO_CONTENT,
)
def marcar_leida_usuario(
    id_notificacion: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    notif = db.query(Notificacion).filter(
        Notificacion.id_notificacion == id_notificacion,
        Notificacion.id_usuario == current_user.id_usuario,
    ).first()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificación no encontrada")
    notif.leido = True
    db.commit()


# ── TALLER ────────────────────────────────────────────────────────────────────

@router.post(
    "/taller/push-token",
    summary="Registrar FCM token del taller (web)",
    status_code=status.HTTP_204_NO_CONTENT,
)
def registrar_push_token_taller(
    payload: PushTokenRequest,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    current_taller.push_token = payload.push_token
    db.commit()


@router.get(
    "/taller",
    response_model=List[NotificacionResponse],
    summary="Listar notificaciones del taller autenticado",
)
def listar_notificaciones_taller(
    solo_no_leidas: bool = False,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    q = db.query(Notificacion).filter(Notificacion.id_taller == current_taller.id_taller)
    if solo_no_leidas:
        q = q.filter(Notificacion.leido == False)
    return q.order_by(Notificacion.created_at.desc()).limit(50).all()


@router.put(
    "/taller/{id_notificacion}/leer",
    summary="Marcar notificación como leída (taller)",
    status_code=status.HTTP_204_NO_CONTENT,
)
def marcar_leida_taller(
    id_notificacion: int,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    notif = db.query(Notificacion).filter(
        Notificacion.id_notificacion == id_notificacion,
        Notificacion.id_taller == current_taller.id_taller,
    ).first()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificación no encontrada")
    notif.leido = True
    db.commit()
