"""
Trazabilidad — Escribe cambios de estado en historial y envía notificaciones push.
CU-33 - Registra cada transición de estado en las tablas de historial.
"""
from typing import Optional
import logging
from sqlalchemy.orm import Session
from app.models.incidente import (
    Asignacion, Incidente,
    HistorialEstadoAsignacion, HistorialEstadoIncidente,
)
from app.models.catalogos import EstadoAsignacion, EstadoIncidente

logger = logging.getLogger("trazabilidad")

# Mensajes de notificación por estado de asignación
_NOTIF_ASIGNACION = {
    "aceptada":   ("Solicitud aceptada", "Tu solicitud fue aceptada por el taller. Un técnico está siendo asignado."),
    "en_camino":  ("Técnico en camino", "El técnico ya salió hacia tu ubicación."),
    "completada": ("Servicio completado", "El técnico ha completado el servicio. ¡Gracias por usar Yary!"),
    "rechazada":  ("Solicitud rechazada", "Tu solicitud fue rechazada por el taller."),
}

# Mensajes de notificación por estado de incidente para el taller
_NOTIF_INCIDENTE_TALLER = {
    "pendiente":   ("Nueva solicitud de asistencia", "Has recibido una nueva solicitud de emergencia vehicular."),
}


def registrar_cambio_estado_asignacion(
    db: Session,
    asignacion: Asignacion,
    id_estado_anterior: Optional[int],
    id_estado_nuevo: int,
    observacion: Optional[str] = None,
) -> HistorialEstadoAsignacion:
    """
    Registra transición de estado de una asignación en el historial.
    
    Args:
        db: Sesión de BD
        asignacion: Objeto asignación
        id_estado_anterior: ID del estado anterior (puede ser None si es inicial)
        id_estado_nuevo: ID del nuevo estado
        observacion: Nota opcional explicando el cambio
    
    Returns:
        El evento registrado en historial
    """
    evento = HistorialEstadoAsignacion(
        id_asignacion=asignacion.id_asignacion,
        id_estado_anterior=id_estado_anterior,
        id_estado_nuevo=id_estado_nuevo,
        observacion=observacion,
    )
    db.add(evento)
    logger.info(
        f"[HISTORIAL] Asignación {asignacion.id_asignacion}: "
        f"estado anterior={id_estado_anterior}, nuevo={id_estado_nuevo}, obs={observacion}"
    )
    return evento


def registrar_cambio_estado_incidente(
    db: Session,
    incidente: Incidente,
    id_estado_anterior: Optional[int],
    id_estado_nuevo: int,
    observacion: Optional[str] = None,
) -> HistorialEstadoIncidente:
    """
    Registra transición de estado de un incidente en el historial.
    
    Args:
        db: Sesión de BD
        incidente: Objeto incidente
        id_estado_anterior: ID del estado anterior (puede ser None si es inicial)
        id_estado_nuevo: ID del nuevo estado
        observacion: Nota opcional explicando el cambio
    
    Returns:
        El evento registrado en historial
    """
    evento = HistorialEstadoIncidente(
        id_incidente=incidente.id_incidente,
        id_estado_anterior=id_estado_anterior,
        id_estado_nuevo=id_estado_nuevo,
        observacion=observacion,
    )
    db.add(evento)
    logger.info(
        f"[HISTORIAL] Incidente {incidente.id_incidente}: "
        f"estado anterior={id_estado_anterior}, nuevo={id_estado_nuevo}, obs={observacion}"
    )
    return evento


def cambiar_estado_asignacion(
    db: Session,
    asignacion: Asignacion,
    nombre_estado_nuevo: str,
    observacion: Optional[str] = None,
) -> EstadoAsignacion:
    """
    Busca el nuevo estado por nombre, registra en historial, actualiza la asignación
    y envía notificación push al cliente si corresponde. NO hace commit.
    """
    nuevo = db.query(EstadoAsignacion).filter_by(nombre=nombre_estado_nuevo).first()
    if not nuevo:
        raise ValueError(f"Catálogo estado_asignacion '{nombre_estado_nuevo}' no existe")

    id_anterior = asignacion.id_estado_asignacion
    registrar_cambio_estado_asignacion(
        db, asignacion, id_anterior, nuevo.id_estado_asignacion, observacion
    )
    asignacion.id_estado_asignacion = nuevo.id_estado_asignacion

    # Notificación push al cliente
    if nombre_estado_nuevo in _NOTIF_ASIGNACION:
        titulo, mensaje = _NOTIF_ASIGNACION[nombre_estado_nuevo]
        _notificar_cliente_por_asignacion(db, asignacion, titulo, mensaje, nombre_estado_nuevo)

    # Métricas de tiempo
    _actualizar_metrica_asignacion(db, asignacion, nombre_estado_nuevo)

    return nuevo


def cambiar_estado_incidente(
    db: Session,
    incidente: Incidente,
    nombre_estado_nuevo: str,
    observacion: Optional[str] = None,
) -> EstadoIncidente:
    """
    Busca el nuevo estado por nombre, registra en historial,
    y actualiza el incidente. NO hace commit — el caller decide cuándo.
    
    Args:
        db: Sesión de BD
        incidente: Objeto incidente a actualizar
        nombre_estado_nuevo: Nombre del estado destino (ej: "en_proceso", "atendido")
        observacion: Nota opcional para el historial
    
    Returns:
        El objeto EstadoIncidente del nuevo estado
    
    Raises:
        ValueError: Si el catálogo no contiene ese nombre de estado
    """
    nuevo = db.query(EstadoIncidente).filter_by(nombre=nombre_estado_nuevo).first()
    if not nuevo:
        raise ValueError(f"Catálogo estado_incidente '{nombre_estado_nuevo}' no existe")

    id_anterior = incidente.id_estado
    registrar_cambio_estado_incidente(
        db, incidente, id_anterior, nuevo.id_estado, observacion
    )
    incidente.id_estado = nuevo.id_estado
    return nuevo


# ── Helpers de notificación ───────────────────────────────────────────────────

def _notificar_cliente_por_asignacion(
    db: Session,
    asignacion: Asignacion,
    titulo: str,
    mensaje: str,
    nombre_estado: str,
) -> None:
    """Crea notificación y envía push al cliente dueño del incidente."""
    try:
        from app.models.incidente import Incidente as IncidenteModel
        from app.models.user_model import Usuario as UsuarioModel
        from app.services.notificacion_service import crear_y_enviar_notificacion

        incidente = db.get(IncidenteModel, asignacion.id_incidente)
        if not incidente or not incidente.id_usuario:
            return

        usuario = db.get(UsuarioModel, incidente.id_usuario)

        crear_y_enviar_notificacion(
            db,
            titulo=titulo,
            mensaje=mensaje,
            id_usuario=incidente.id_usuario,
            id_incidente=asignacion.id_incidente,
            push_token=usuario.push_token if usuario else None,
            data={"tipo": "estado_asignacion", "estado": nombre_estado,
                  "id_asignacion": str(asignacion.id_asignacion)},
        )
    except Exception as exc:
        logger.error(f"[TRAZABILIDAD] Error enviando notificación push: {exc}")


def _actualizar_metrica_asignacion(
    db: Session,
    asignacion: Asignacion,
    nombre_estado_nuevo: str,
) -> None:
    """Actualiza timestamps de Metrica al cambiar estado de asignación."""
    try:
        from datetime import datetime, timezone
        from app.models.transaccional import Metrica

        metrica = db.query(Metrica).filter(
            Metrica.id_incidente == asignacion.id_incidente
        ).first()
        if not metrica:
            return

        ahora = datetime.now(timezone.utc)

        if nombre_estado_nuevo == "aceptada":
            metrica.fecha_asignacion = ahora
            if metrica.fecha_inicio:
                delta = (ahora - metrica.fecha_inicio).total_seconds() / 60
                metrica.tiempo_respuesta_min = int(delta)

        elif nombre_estado_nuevo == "en_camino":
            metrica.fecha_llegada_tecnico = ahora
            if metrica.fecha_asignacion:
                delta = (ahora - metrica.fecha_asignacion).total_seconds() / 60
                metrica.tiempo_llegada_min = int(delta)

        elif nombre_estado_nuevo == "completada":
            metrica.fecha_fin = ahora
            if metrica.fecha_inicio:
                delta = (ahora - metrica.fecha_inicio).total_seconds() / 60
                metrica.tiempo_resolucion_min = int(delta)

    except Exception as exc:
        logger.error(f"[TRAZABILIDAD] Error actualizando métrica: {exc}")
