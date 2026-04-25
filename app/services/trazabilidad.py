"""
Trazabilidad — Escribe cambios de estado en historial.
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
    Busca el nuevo estado por nombre, registra en historial,
    y actualiza la asignación. NO hace commit — el caller decide cuándo.
    
    Args:
        db: Sesión de BD
        asignacion: Objeto asignación a actualizar
        nombre_estado_nuevo: Nombre del estado destino (ej: "aceptada", "en_camino")
        observacion: Nota opcional para el historial
    
    Returns:
        El objeto EstadoAsignacion del nuevo estado
    
    Raises:
        ValueError: Si el catálogo no contiene ese nombre de estado
    """
    nuevo = db.query(EstadoAsignacion).filter_by(nombre=nombre_estado_nuevo).first()
    if not nuevo:
        raise ValueError(f"Catálogo estado_asignacion '{nombre_estado_nuevo}' no existe")

    id_anterior = asignacion.id_estado_asignacion
    registrar_cambio_estado_asignacion(
        db, asignacion, id_anterior, nuevo.id_estado_asignacion, observacion
    )
    asignacion.id_estado_asignacion = nuevo.id_estado_asignacion
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
