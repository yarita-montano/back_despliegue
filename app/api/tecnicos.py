"""
Router del Técnico.

El Técnico es un USUARIO (tabla usuario, id_rol=3) que se autentica normalmente.
Desde la app móvil (Flutter) usa POST /usuarios/login con sus credenciales.

Endpoints:
  GET /tecnicos/asignacion-actual                      → asignación activa
  PUT /tecnicos/mi-ubicacion                           → actualizar ubicación GPS en tiempo real
  GET /tecnicos/mis-asignaciones/{id}/evidencias       → ver evidencias del incidente
  PUT /tecnicos/mis-asignaciones/{id}/iniciar-viaje    → aceptada → en_camino
  PUT /tecnicos/mis-asignaciones/{id}/completar        → en_camino → completada
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.user_model import Usuario
from app.models.incidente import Asignacion, Incidente, Evidencia
from app.models.usuario_taller import UsuarioTaller
from app.models.catalogos import EstadoAsignacion, EstadoIncidente
from app.schemas.taller_schema import (
    TecnicoAsignacionResponse, IniciarViajeRequest, CompletarAsignacionRequest,
    UbicacionTecnicoRequest, EvidenciaMiniT, MensajeResponse
)
from app.core.security import get_current_user
from app.services.trazabilidad import cambiar_estado_asignacion, cambiar_estado_incidente

router = APIRouter(
    prefix="/tecnicos",
    tags=["Gestión de Técnicos (app móvil)"],
    responses={
        401: {"description": "No autorizado - Token inválido o usuario no es técnico"},
        403: {"description": "Prohibido - Usuario no es técnico"},
        404: {"description": "No encontrado - Sin asignaciones activas"},
    },
)


@router.get(
    "/asignacion-actual",
    response_model=TecnicoAsignacionResponse,
    summary="Obtener asignación activa del técnico",
    description="Retorna la asignación activa del técnico (estado 'aceptada' o 'en_camino'). Requiere ser un usuario con rol de técnico (id_rol=3).",
)
def obtener_asignacion_actual(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    # Verificar que el usuario es técnico (rol=3)
    if current_user.id_rol != 3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo usuarios con rol técnico pueden acceder a este endpoint",
        )
    
    # Buscar asignaciones activas del técnico (id_usuario)
    asignacion = db.query(Asignacion).filter(
        Asignacion.id_usuario == current_user.id_usuario,
        Asignacion.id_estado_asignacion.in_(
            db.query(EstadoAsignacion.id_estado_asignacion).filter(
                EstadoAsignacion.nombre.in_(["aceptada", "en_camino"])
            )
        ),
    ).first()

    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tienes asignaciones activas en este momento",
        )

    return asignacion


# ============ UBICACIÓN EN TIEMPO REAL ============

@router.put(
    "/mi-ubicacion",
    response_model=MensajeResponse,
    summary="Actualizar ubicación GPS del técnico",
    description="El técnico reporta su posición actual. Se guarda en usuario_taller para que el taller y el cliente puedan verla.",
)
def actualizar_ubicacion(
    payload: UbicacionTecnicoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.id_rol != 3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo técnicos pueden usar este endpoint",
        )

    vinculo = db.query(UsuarioTaller).filter(
        UsuarioTaller.id_usuario == current_user.id_usuario,
        UsuarioTaller.activo == True,
    ).first()

    if not vinculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tienes vínculo activo con ningún taller",
        )

    vinculo.latitud = payload.latitud
    vinculo.longitud = payload.longitud
    db.commit()

    return {"mensaje": f"Ubicación actualizada: {payload.latitud}, {payload.longitud}"}


# ============ EVIDENCIAS ============

@router.get(
    "/mis-asignaciones/{id_asignacion}/evidencias",
    response_model=List[EvidenciaMiniT],
    summary="Ver evidencias del incidente",
    description="Lista todas las evidencias (fotos, audios, texto) que el cliente subió al reportar el incidente.",
)
def listar_evidencias(
    id_asignacion: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.id_rol != 3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo técnicos pueden usar este endpoint",
        )

    asignacion = db.query(Asignacion).filter(
        Asignacion.id_asignacion == id_asignacion,
        Asignacion.id_usuario == current_user.id_usuario,
    ).first()

    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignación no encontrada o no asignada a ti",
        )

    evidencias = db.query(Evidencia).filter(
        Evidencia.id_incidente == asignacion.id_incidente
    ).all()

    return evidencias


# ============ A.2 — CU-20: TRANSICIONES EN_CAMINO Y COMPLETADA ============

@router.put(
    "/mis-asignaciones/{id_asignacion}/iniciar-viaje",
    response_model=TecnicoAsignacionResponse,
    summary="Técnico sale hacia el cliente (aceptada → en_camino)",
    description="Marca que el técnico salió hacia el incidente. Requiere rol=3 (técnico).",
)
def iniciar_viaje(
    id_asignacion: int,
    payload: IniciarViajeRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    # Verificar rol técnico
    if current_user.id_rol != 3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo técnicos pueden usar este endpoint",
        )
    
    asignacion = db.query(Asignacion).filter(
        Asignacion.id_asignacion == id_asignacion,
        Asignacion.id_usuario == current_user.id_usuario,
    ).first()

    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignación no encontrada o no asignada a ti",
        )

    estado_actual = db.get(EstadoAsignacion, asignacion.id_estado_asignacion)
    if not estado_actual or estado_actual.nombre != "aceptada":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"La asignación está en '{estado_actual.nombre if estado_actual else '?'}', "
                f"solo se puede iniciar viaje desde 'aceptada'"
            ),
        )

    try:
        cambiar_estado_asignacion(
            db, asignacion, "en_camino",
            observacion=f"Técnico {current_user.id_usuario} ({current_user.nombre}) en camino",
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Sincronizar estado del incidente: cualquier estado (excepto terminal) → en_proceso
    incidente = db.get(Incidente, asignacion.id_incidente)
    if incidente:
        estado_inc_actual = db.get(EstadoIncidente, incidente.id_estado)
        if estado_inc_actual and estado_inc_actual.nombre not in ["atendido", "cancelado"]:
            try:
                cambiar_estado_incidente(
                    db, incidente, "en_proceso",
                    observacion=f"Técnico {current_user.nombre} en camino",
                )
            except ValueError as e:
                raise HTTPException(status_code=500, detail=str(e))

    db.commit()
    db.refresh(asignacion)
    return asignacion


@router.put(
    "/mis-asignaciones/{id_asignacion}/completar",
    response_model=TecnicoAsignacionResponse,
    summary="Servicio completado (en_camino → completada)",
    description="Marca el servicio como completado. Requiere rol=3 (técnico).",
)
def completar_asignacion(
    id_asignacion: int,
    payload: CompletarAsignacionRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    # Verificar rol técnico
    if current_user.id_rol != 3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo técnicos pueden usar este endpoint",
        )
    
    asignacion = db.query(Asignacion).filter(
        Asignacion.id_asignacion == id_asignacion,
        Asignacion.id_usuario == current_user.id_usuario,
    ).first()

    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignación no encontrada o no asignada a ti",
        )

    estado_actual = db.get(EstadoAsignacion, asignacion.id_estado_asignacion)
    if not estado_actual or estado_actual.nombre != "en_camino":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"La asignación está en '{estado_actual.nombre if estado_actual else '?'}', "
                f"solo se puede completar desde 'en_camino'"
            ),
        )

    if payload.costo_estimado is not None:
        asignacion.costo_estimado = payload.costo_estimado
    if payload.resumen_trabajo is not None:
        prev = asignacion.nota_taller or ""
        asignacion.nota_taller = f"{prev}\n[TRABAJO] {payload.resumen_trabajo}".strip()

    try:
        cambiar_estado_asignacion(
            db, asignacion, "completada",
            observacion=payload.resumen_trabajo or "Servicio completado por técnico",
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Cerrar el incidente: cualquier estado activo → atendido
    incidente = db.get(Incidente, asignacion.id_incidente)
    if incidente:
        estado_inc_actual = db.get(EstadoIncidente, incidente.id_estado)
        if estado_inc_actual and estado_inc_actual.nombre not in ["atendido", "cancelado"]:
            try:
                cambiar_estado_incidente(
                    db, incidente, "atendido",
                    observacion=f"Técnico {current_user.nombre} completó el servicio",
                )
            except ValueError as e:
                raise HTTPException(status_code=500, detail=str(e))

    db.commit()
    db.refresh(asignacion)
    return asignacion
