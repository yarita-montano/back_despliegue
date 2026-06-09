"""
Seguimiento publico en vivo de un incidente (opcion C).

Permite compartir un enlace para que alguien SIN la app vea, en una pagina web
publica, la ubicacion del cliente y la del tecnico en tiempo (casi) real.

  POST /incidencias/{id}/compartir   -> (auth, dueno del incidente) genera token + url
  GET  /public/seguimiento/{token}   -> (PUBLICO, sin auth) posiciones + estado + ETA

El endpoint publico no tiene contexto de tenant. Como las tablas son
tenant-scoped con filtro global include_legacy=False, se usa el escape-hatch
current_tenant.set(0) para la lectura. La autorizacion la da el token de
compartir (no la cuenta del receptor).
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    SHARE_TOKEN_EXPIRE_HOURS,
    create_share_token,
    get_current_user,
    verify_share_token,
)
from app.core.tenant_context import current_tenant
from app.db.session import get_db
from app.models.incidente import Asignacion, Incidente
from app.models.taller import Taller
from app.models.usuario import Usuario
from app.models.usuario_taller import UsuarioTaller
from app.schemas.seguimiento_schema import (
    CompartirSeguimientoResponse,
    PuntoGeo,
    SeguimientoPublicoResponse,
)
from app.services import tracking_service

router = APIRouter(tags=["Seguimiento publico"])


@router.post(
    "/incidencias/{id_incidente}/compartir",
    response_model=CompartirSeguimientoResponse,
    summary="Generar enlace publico de seguimiento en vivo del incidente",
)
def compartir_seguimiento(
    id_incidente: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    El dueno del incidente genera un enlace compartible. Cualquiera con ese
    enlace puede ver el seguimiento en vivo sin tener la app ni cuenta.
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
        raise HTTPException(404, "Incidente no encontrado o no te pertenece")

    token = create_share_token(id_incidente)
    base = get_settings().FRONTEND_URL.rstrip("/")
    return CompartirSeguimientoResponse(
        token=token,
        url=f"{base}/seguir/{token}",
        expira_horas=SHARE_TOKEN_EXPIRE_HOURS,
    )


@router.get(
    "/public/seguimiento/{token}",
    response_model=SeguimientoPublicoResponse,
    summary="Seguimiento publico (sin auth): posiciones cliente/tecnico + ETA",
)
def seguimiento_publico(token: str, db: Session = Depends(get_db)):
    id_incidente = verify_share_token(token)
    if id_incidente is None:
        raise HTTPException(401, "Enlace invalido o expirado")

    # Lectura sin tenant: el token autoriza, no la cuenta. set(0) desactiva el
    # filtro global de tenant para esta consulta puntual.
    tok = current_tenant.set(0)
    try:
        incidente = (
            db.query(Incidente)
            .filter(Incidente.id_incidente == id_incidente)
            .first()
        )
        if not incidente:
            raise HTTPException(404, "Incidente no encontrado")

        estado = incidente.estado.nombre if incidente.estado else "desconocido"
        cliente = PuntoGeo(latitud=incidente.latitud, longitud=incidente.longitud)

        # Asignacion mas reciente del incidente (puede no existir todavia).
        asignacion = (
            db.query(Asignacion)
            .filter(Asignacion.id_incidente == id_incidente)
            .order_by(Asignacion.updated_at.desc())
            .first()
        )

        tecnico_punto = None
        nombre_tecnico = None
        taller_nombre = None
        eta_min = None
        distancia_km = None

        if asignacion and asignacion.id_usuario:
            taller = (
                db.query(Taller)
                .filter(Taller.id_taller == asignacion.id_taller)
                .first()
            )
            taller_nombre = taller.nombre if taller else None

            ubic = (
                db.query(UsuarioTaller)
                .filter(
                    UsuarioTaller.id_usuario == asignacion.id_usuario,
                    UsuarioTaller.id_taller == asignacion.id_taller,
                    UsuarioTaller.activo == True,  # noqa: E712
                )
                .first()
            )
            if ubic and ubic.latitud is not None and ubic.longitud is not None:
                tecnico_punto = PuntoGeo(latitud=ubic.latitud, longitud=ubic.longitud)
                u = (
                    db.query(Usuario)
                    .filter(Usuario.id_usuario == asignacion.id_usuario)
                    .first()
                )
                nombre_tecnico = u.nombre if u else "Tecnico"
                # ETA con haversine LOCAL (instantaneo, sin llamada externa). Este
                # endpoint se consulta por polling cada pocos segundos, asi que NO
                # debe depender de un servicio de routing externo (lento / rate-limit
                # / colgado), que dejaba la pagina en "Cargando" indefinidamente.
                try:
                    dist_km = tracking_service.haversine_km(
                        ubic.latitud,
                        ubic.longitud,
                        incidente.latitud,
                        incidente.longitud,
                    )
                    distancia_km = round(dist_km, 2)
                    eta_min = max(
                        0,
                        round((dist_km / tracking_service.VELOCIDAD_DEFAULT_KMH) * 60),
                    )
                except Exception:
                    # ETA es best-effort; si falla seguimos sin ella.
                    pass

        return SeguimientoPublicoResponse(
            id_incidente=id_incidente,
            estado=estado,
            cliente=cliente,
            tecnico=tecnico_punto,
            nombre_tecnico=nombre_tecnico,
            taller_nombre=taller_nombre,
            eta_min=eta_min,
            distancia_km=distancia_km,
            actualizado=datetime.now(timezone.utc),
        )
    finally:
        current_tenant.reset(tok)
