"""Tests de pago_service.estimar_costo con aprendizaje historico.

Verifica que cuando hay >= 3 cotizaciones ACEPTADAS de la misma categoria
en los ultimos 90 dias, estimar_costo usa ese promedio en vez del de
tarifa_base. Si no, cae a tarifa_base, y como ultimo recurso al fallback.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal


def _incidente_de(db_session, usuario, vehiculo, categoria):
    from app.models.catalogos import EstadoIncidente
    from app.models.incidente import Incidente

    estado = db_session.query(EstadoIncidente).first()
    inc = Incidente(
        id_usuario=usuario.id_usuario,
        id_vehiculo=vehiculo.id_vehiculo,
        id_estado=estado.id_estado,
        id_categoria=categoria.id_categoria,
        latitud=-16.5,
        longitud=-68.15,
    )
    db_session.add(inc)
    db_session.commit()
    db_session.refresh(inc)
    return inc


def test_estimar_usa_historico_si_hay_3_o_mas_aceptadas(
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
):
    from app.models.catalogos import CategoriaProblema
    from app.models.cotizacion import Cotizacion, EstadoCotizacion
    from app.models.taller import TallerServicio
    from app.services.pago_service import estimar_costo

    cat = db_session.query(CategoriaProblema).filter_by(codigo="llantas").one()
    aceptada = db_session.query(EstadoCotizacion).filter_by(nombre="aceptada").one()

    tenant = tenant_factory()
    taller = taller_factory(tenant)
    # tarifa_base barata para asegurar que el historico ES distinto
    db_session.add(TallerServicio(
        id_taller=taller.id_taller,
        id_categoria=cat.id_categoria,
        tarifa_base=Decimal("10"),
    ))

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)

    # 3 cotizaciones aceptadas historicas con monto total ~80
    for monto_servicio in (70, 80, 90):
        inc = _incidente_de(db_session, cliente, vehiculo, cat)
        c = Cotizacion(
            id_tenant=tenant.id_tenant,
            id_incidente=inc.id_incidente,
            id_taller=taller.id_taller,
            id_estado_cotizacion=aceptada.id_estado_cotizacion,
            monto_servicio=Decimal(str(monto_servicio)),
            monto_repuestos=Decimal("0"),
            monto_traslado=Decimal("0"),
        )
        db_session.add(c)
    db_session.commit()

    nuevo_incidente = _incidente_de(db_session, cliente, vehiculo, cat)
    estimado = estimar_costo(db_session, nuevo_incidente)

    # Promedio historico = 80, NO la tarifa_base de 10
    assert estimado >= Decimal("70")
    assert estimado <= Decimal("90")


def test_estimar_cae_a_tarifa_base_si_no_hay_historico_suficiente(
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
):
    from app.models.catalogos import CategoriaProblema
    from app.models.taller import TallerServicio
    from app.services.pago_service import estimar_costo

    cat = db_session.query(CategoriaProblema).filter_by(codigo="grua_auxilio").one()
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    db_session.add(TallerServicio(
        id_taller=taller.id_taller,
        id_categoria=cat.id_categoria,
        tarifa_base=Decimal("45"),
    ))
    db_session.commit()

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    incidente = _incidente_de(db_session, cliente, vehiculo, cat)

    estimado = estimar_costo(db_session, incidente)
    # Sin historico suficiente → promedio de tarifa_base de talleres (45 en este escenario, pero pueden haber otros talleres en la fixture)
    assert estimado > 0
    assert estimado != Decimal("20")  # no fallback


def test_estimar_fallback_si_sin_historico_y_sin_tarifa(
    db_session,
    cliente_factory,
    vehiculo_factory,
):
    from app.models.catalogos import CategoriaProblema
    from app.services.pago_service import estimar_costo, ESTIMACION_FALLBACK_USD

    # Sin TallerServicio para esta categoria.
    cat = db_session.query(CategoriaProblema).filter_by(codigo="rutinario").one()
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    incidente = _incidente_de(db_session, cliente, vehiculo, cat)

    # Borrar cualquier tarifa_base que pueda haber
    from app.models.taller import TallerServicio
    db_session.query(TallerServicio).filter_by(id_categoria=cat.id_categoria).update(
        {"tarifa_base": None}
    )
    db_session.commit()

    estimado = estimar_costo(db_session, incidente)
    assert estimado == ESTIMACION_FALLBACK_USD
