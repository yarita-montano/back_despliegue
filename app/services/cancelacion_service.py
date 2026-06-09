"""Logica de cancelacion con compensacion."""
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.tenant_context import current_tenant
from app.models.catalogos import EstadoAsignacion, EstadoIncidente, EstadoPago, MetodoPago
from app.models.cotizacion import Cotizacion
from app.models.incidente import (
    Asignacion,
    HistorialEstadoAsignacion,
    HistorialEstadoIncidente,
    Incidente,
)
from app.models.tenant import Tenant
from app.models.transaccional import Pago
from app.models.usuario import Usuario


# Fallback usado solo si el tenant no esta cargado. Los porcentajes reales
# vienen de Tenant.pct_cancel_* y son configurables por el admin.
COMPENSACION_DEFAULT = {
    "pendiente": Decimal("0.00"),
    "aceptada": Decimal("0.50"),
    "en_camino": Decimal("1.00"),
    "llegado": Decimal("1.00"),
}

ESTADOS_NO_CANCELABLES = {"completada", "cancelada"}


def _factor_compensacion(tenant: Tenant | None, estado: str) -> Decimal | None:
    """Lee el porcentaje configurado en el tenant y lo convierte a factor.
    'llegado' usa el mismo porcentaje que 'en_camino'.
    """
    if estado not in COMPENSACION_DEFAULT:
        return None
    if tenant is None:
        return COMPENSACION_DEFAULT[estado]
    pct_map = {
        "pendiente": tenant.pct_cancel_pendiente,
        "aceptada": tenant.pct_cancel_aceptada,
        "en_camino": tenant.pct_cancel_en_camino,
        "llegado": tenant.pct_cancel_en_camino,
    }
    pct = pct_map.get(estado)
    if pct is None:
        return COMPENSACION_DEFAULT[estado]
    return (Decimal(str(pct)) / Decimal("100")).quantize(Decimal("0.01"))


def _base_estimada_servicio_directo(db: Session, asignacion: Asignacion) -> Decimal:
    """
    Estima la base de compensacion para un servicio DIRECTO (sin cotizacion):
    tarifa_base del servicio del taller + traslado por distancia, igual que el
    total que se le muestra al cliente al elegir taller. Se lee con tenant=0
    porque el cliente no tiene tenant y Taller/TallerServicio son tenant-scoped.
    """
    from app.models.taller import Taller, TallerServicio
    from app.services.tracking_service import haversine_km

    _tok = current_tenant.set(0)
    try:
        incidente = asignacion.incidente
        base = Decimal("0")

        ts = (
            db.query(TallerServicio)
            .filter(
                TallerServicio.id_taller == asignacion.id_taller,
                TallerServicio.id_categoria == incidente.id_categoria,
            )
            .first()
        )
        if ts and ts.tarifa_base:
            base += Decimal(str(ts.tarifa_base))

        taller = (
            db.query(Taller).filter(Taller.id_taller == asignacion.id_taller).first()
        )
        if (
            taller
            and taller.tarifa_traslado
            and incidente.latitud is not None
            and incidente.longitud is not None
            and taller.latitud is not None
            and taller.longitud is not None
        ):
            dist = haversine_km(
                float(taller.latitud),
                float(taller.longitud),
                float(incidente.latitud),
                float(incidente.longitud),
            )
            base += Decimal(str(taller.tarifa_traslado)) * Decimal(str(round(dist, 2)))

        return base.quantize(Decimal("0.01"))
    finally:
        current_tenant.reset(_tok)


def cancelar_asignacion(
    db: Session,
    asignacion: Asignacion,
    usuario: Usuario,
    motivo: str,
) -> tuple[Asignacion, str]:
    print(
        f"[CANCELACION] INICIO cancelar_asignacion asig={asignacion.id_asignacion} "
        f"incidente={asignacion.id_incidente} usuario={usuario.id_usuario} "
        f"estado={asignacion.estado.nombre if asignacion.estado else '?'}",
        flush=True,
    )

    if asignacion.incidente.id_usuario != usuario.id_usuario:
        raise HTTPException(403, "Solo el dueno del incidente puede cancelar")

    estado_actual = asignacion.estado.nombre
    if estado_actual in ESTADOS_NO_CANCELABLES:
        raise HTTPException(409, f"No se puede cancelar una asignacion '{estado_actual}'")

    # El tenant (porcentajes) y la cotizacion (base) se leen SIEMPRE con tenant=0:
    # el incidente del cliente puede tener id_tenant distinto/NULL al del taller,
    # y el filtro multi-tenant ocultaria ambos (factor por defecto + base 0). Asi
    # la compensacion se calcula bien sin importar desde que endpoint se cancele.
    # OJO: asignacion.costo_estimado SOLO se llena al COMPLETAR el servicio, asi
    # que en una cancelacion en curso suele estar en None; la base real es el
    # monto_total de la cotizacion (una por incidente+taller).
    _tok = current_tenant.set(0)
    try:
        tenant = db.query(Tenant).filter_by(id_tenant=asignacion.id_tenant).first()
        cotizacion = (
            db.query(Cotizacion)
            .filter(
                Cotizacion.id_incidente == asignacion.id_incidente,
                Cotizacion.id_taller == asignacion.id_taller,
            )
            .first()
        )
    finally:
        current_tenant.reset(_tok)

    factor = _factor_compensacion(tenant, estado_actual)
    if factor is None:
        raise HTTPException(500, f"Estado '{estado_actual}' sin regla de compensacion")

    if cotizacion is not None and cotizacion.monto_total > 0:
        base = Decimal(str(cotizacion.monto_total))
    elif asignacion.costo_estimado:
        base = Decimal(str(asignacion.costo_estimado))
    else:
        # Servicio DIRECTO (sin cotizacion) cancelado antes de completar: no hay
        # costo aun. Se estima con la tarifa del servicio del taller (tarifa_base
        # + traslado), igual que el total que se le muestra al cliente al elegir
        # taller, para que la compensacion no quede en 0.
        base = _base_estimada_servicio_directo(db, asignacion)
    compensacion = (base * factor).quantize(Decimal("0.01"))

    # Diagnostico: deja en el log de Render como se calculo la compensacion
    # (estado, factor, cotizacion, base). Util para validar; quitar luego.
    print(
        f"[CANCELACION] asig={asignacion.id_asignacion} estado={estado_actual} "
        f"factor={factor} cotizacion={'si' if cotizacion else 'no'} "
        f"monto_cot={cotizacion.monto_total if cotizacion else None} "
        f"costo_est={asignacion.costo_estimado} base={base} "
        f"compensacion={compensacion}",
        flush=True,
    )

    estado_cancelada = (
        db.query(EstadoAsignacion).filter(EstadoAsignacion.nombre == "cancelada").first()
    )
    if not estado_cancelada:
        raise HTTPException(500, "Catalogo estado_asignacion sin 'cancelada'")

    db.add(
        HistorialEstadoAsignacion(
            id_asignacion=asignacion.id_asignacion,
            id_estado_anterior=asignacion.id_estado_asignacion,
            id_estado_nuevo=estado_cancelada.id_estado_asignacion,
            observacion=f"Cancelado por cliente. Motivo: {motivo[:200]}",
        )
    )

    asignacion.id_estado_asignacion = estado_cancelada.id_estado_asignacion
    asignacion.cancelada_at = datetime.now(timezone.utc)
    asignacion.cancelada_por = "cliente"
    asignacion.motivo_cancelacion = motivo
    asignacion.compensacion_monto = compensacion
    asignacion.compensacion_pagada = compensacion == 0

    # Cerrar el incidente: la cancelacion del cliente termina el servicio, asi el
    # incidente deja de contar como "activo" (libera la regla "1 incidente activo
    # por usuario", 409) y queda coherente con la asignacion cancelada.
    incidente = db.get(Incidente, asignacion.id_incidente)
    if incidente:
        estado_inc_cancelado = (
            db.query(EstadoIncidente)
            .filter(EstadoIncidente.nombre == "cancelado")
            .first()
        )
        if (
            estado_inc_cancelado
            and incidente.id_estado != estado_inc_cancelado.id_estado
        ):
            db.add(
                HistorialEstadoIncidente(
                    id_incidente=incidente.id_incidente,
                    id_estado_anterior=incidente.id_estado,
                    id_estado_nuevo=estado_inc_cancelado.id_estado,
                    observacion=f"Cancelado por cliente (compensacion {compensacion}).",
                )
            )
            incidente.id_estado = estado_inc_cancelado.id_estado

    if compensacion > 0:
        estado_pago_pendiente = (
            db.query(EstadoPago).filter(EstadoPago.nombre == "pendiente").first()
        )
        if not estado_pago_pendiente:
            estado_pago_pendiente = db.query(EstadoPago).first()

        metodo = db.query(MetodoPago).first()

        if estado_pago_pendiente and metodo:
            comision = (compensacion * Decimal("0.10")).quantize(Decimal("0.01"))
            monto_taller = (compensacion - comision).quantize(Decimal("0.01"))

            db.add(
                Pago(
                    id_tenant=asignacion.id_tenant,
                    id_incidente=asignacion.id_incidente,
                    id_metodo_pago=metodo.id_metodo_pago,
                    id_estado_pago=estado_pago_pendiente.id_estado_pago,
                    tipo="penalizacion",
                    monto_total=compensacion,
                    comision_plataforma=comision,
                    monto_taller=monto_taller,
                    referencia_externa=f"compensacion-cancelacion-{asignacion.id_asignacion}",
                )
            )
            print(
                f"[CANCELACION] PAGO compensacion CREADO asig={asignacion.id_asignacion} "
                f"incidente={asignacion.id_incidente} tipo=penalizacion "
                f"monto={compensacion} comision={comision} monto_taller={monto_taller}",
                flush=True,
            )
        else:
            print(
                f"[CANCELACION] NO se creo pago: falta catalogo "
                f"estado_pago_pendiente={bool(estado_pago_pendiente)} metodo={bool(metodo)}",
                flush=True,
            )
    else:
        print(
            f"[CANCELACION] SIN pago: compensacion={compensacion} (<= 0). "
            f"Revisa factor/base arriba.",
            flush=True,
        )

    db.commit()
    db.refresh(asignacion)
    print(
        f"[CANCELACION] FIN asig={asignacion.id_asignacion} nuevo_estado=cancelada "
        f"compensacion_monto={asignacion.compensacion_monto} "
        f"compensacion_pagada={asignacion.compensacion_pagada}",
        flush=True,
    )
    return asignacion, "cancelada"
