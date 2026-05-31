"""Logica de Adendas (ampliacion de presupuesto)."""
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.catalogos import EstadoAsignacion
from app.models.incidente import Asignacion
from app.models.transaccional import Adenda
from app.models.usuario import Usuario


ESTADO_EN_ESPERA = "en_espera_aprobacion"


def _ensure_estado_en_espera(db: Session) -> EstadoAsignacion:
    """Garantiza el estado 'en_espera_aprobacion' en el catalogo."""
    est = db.query(EstadoAsignacion).filter_by(nombre=ESTADO_EN_ESPERA).first()
    if est:
        return est
    est = EstadoAsignacion(nombre=ESTADO_EN_ESPERA)
    db.add(est)
    db.commit()
    db.refresh(est)
    return est


def crear_adenda(
    db: Session,
    asignacion: Asignacion,
    tecnico: Usuario,
    monto_adicional: float,
    descripcion: str,
) -> Adenda:
    """
    Tecnico registra una adenda. La asignacion queda en 'en_espera_aprobacion'
    hasta que el cliente responda.
    """
    if asignacion.estado and asignacion.estado.nombre in (
        "cancelada",
        "completada",
        "rechazada",
    ):
        raise HTTPException(
            409,
            f"No se puede registrar adenda sobre una asignacion '{asignacion.estado.nombre}'",
        )

    # Validar que no haya otra adenda pendiente sobre la misma asignacion.
    abierta = (
        db.query(Adenda)
        .filter(
            Adenda.id_asignacion == asignacion.id_asignacion,
            Adenda.estado == "pendiente",
        )
        .first()
    )
    if abierta:
        raise HTTPException(
            409,
            f"Ya existe una adenda pendiente (#{abierta.id_adenda}) sobre esta asignacion",
        )

    estado_espera = _ensure_estado_en_espera(db)

    ad = Adenda(
        id_tenant=asignacion.id_tenant,
        id_asignacion=asignacion.id_asignacion,
        id_tecnico=tecnico.id_usuario,
        monto_adicional=monto_adicional,
        descripcion=descripcion,
        estado="pendiente",
    )
    db.add(ad)

    # Congelar la asignacion
    asignacion.id_estado_asignacion = estado_espera.id_estado_asignacion

    db.commit()
    db.refresh(ad)
    return ad


def responder_adenda(
    db: Session,
    adenda: Adenda,
    cliente: Usuario,
    decision: str,
    motivo: str | None = None,
) -> Adenda:
    """
    Cliente aprueba o rechaza. Al aprobar, suma el monto al costo_estimado
    de la asignacion y reanuda el estado a 'aceptada'. Al rechazar, la
    asignacion queda 'cancelada' y se anota motivo_cancelacion.
    """
    if adenda.estado != "pendiente":
        raise HTTPException(
            409,
            f"Esta adenda ya fue {adenda.estado}, no se puede responder de nuevo",
        )

    asig = db.query(Asignacion).get(adenda.id_asignacion)
    if not asig:
        raise HTTPException(404, "Asignacion asociada a la adenda no existe")

    # Validar que el cliente sea dueno del incidente.
    incidente = asig.incidente
    if not incidente or incidente.id_usuario != cliente.id_usuario:
        raise HTTPException(403, "Solo el dueno del incidente puede responder la adenda")

    ahora = datetime.now(timezone.utc)
    adenda.respondida_at = ahora
    adenda.motivo_cliente = motivo

    if decision == "aprobar":
        adenda.estado = "aprobada"
        actual = float(asig.costo_estimado or 0)
        asig.costo_estimado = actual + float(adenda.monto_adicional)
        # Reanudar al estado 'aceptada' (continua el servicio)
        estado_aceptada = db.query(EstadoAsignacion).filter_by(nombre="aceptada").first()
        if estado_aceptada:
            asig.id_estado_asignacion = estado_aceptada.id_estado_asignacion
    else:  # rechazar
        adenda.estado = "rechazada"
        estado_cancelada = db.query(EstadoAsignacion).filter_by(nombre="cancelada").first()
        if estado_cancelada:
            asig.id_estado_asignacion = estado_cancelada.id_estado_asignacion
        asig.cancelada_at = ahora
        asig.cancelada_por = "cliente"
        asig.motivo_cancelacion = (
            f"Adenda rechazada: {motivo}" if motivo else "Adenda rechazada por el cliente"
        )

    db.commit()
    db.refresh(adenda)
    return adenda
