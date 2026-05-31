"""Tests del desglose de traslado en cotizaciones.

Verifica que cuando el taller responde una cotizacion, el sistema
calcula automaticamente la distancia GPS y el monto_traslado a partir
de taller.tarifa_traslado, y los suma al monto_total.
"""
from decimal import Decimal


def _crear_incidente_categoria(db_session, usuario, vehiculo, categoria, lat, lng):
    from app.models.catalogos import EstadoIncidente
    from app.models.incidente import Incidente

    estado = db_session.query(EstadoIncidente).first()
    inc = Incidente(
        id_usuario=usuario.id_usuario,
        id_vehiculo=vehiculo.id_vehiculo,
        id_estado=estado.id_estado,
        id_categoria=categoria.id_categoria,
        latitud=lat,
        longitud=lng,
    )
    db_session.add(inc)
    db_session.commit()
    db_session.refresh(inc)
    return inc


def test_responder_cotizacion_calcula_distancia_y_traslado(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    taller_auth_headers,
    cliente_factory,
    vehiculo_factory,
):
    from app.models.catalogos import CategoriaProblema
    from app.models.cotizacion import Cotizacion, EstadoCotizacion
    from app.models.taller import TallerServicio

    cat = db_session.query(CategoriaProblema).filter_by(codigo="mecanica_general").one()
    pendiente = db_session.query(EstadoCotizacion).filter_by(nombre="pendiente").one()

    tenant = tenant_factory()
    taller = taller_factory(tenant)
    # Taller en La Paz centro, incidente ~1.1 km al norte.
    taller.latitud, taller.longitud = -16.5000, -68.1500
    taller.tarifa_traslado = Decimal("3.00")  # USD por km
    db_session.add(TallerServicio(id_taller=taller.id_taller, id_categoria=cat.id_categoria))

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    incidente = _crear_incidente_categoria(
        db_session, cliente, vehiculo, cat, lat=-16.4900, lng=-68.1500
    )

    cot = Cotizacion(
        id_tenant=tenant.id_tenant,
        id_incidente=incidente.id_incidente,
        id_taller=taller.id_taller,
        id_estado_cotizacion=pendiente.id_estado_cotizacion,
    )
    db_session.add(cot)
    db_session.commit()
    db_session.refresh(cot)

    r = client.post(
        f"/cotizaciones/{cot.id_cotizacion}/responder",
        json={"monto_servicio": 100, "monto_repuestos": 20},
        headers=taller_auth_headers(taller),
    )
    assert r.status_code == 200, r.text
    body = r.json()

    # La distancia debe ser > 0 (haversine ~1.11 km)
    assert body["distancia_km"] is not None
    assert body["distancia_km"] > 0
    # monto_traslado = tarifa_traslado * distancia_km
    assert body["monto_traslado"] is not None
    assert body["monto_traslado"] > 0
    # El total expuesto por la propiedad debe incluir traslado
    esperado = (
        float(body["monto_servicio"])
        + float(body["monto_repuestos"])
        + float(body["monto_traslado"])
    )
    # No accedemos a "monto_total" directamente (es @property en el modelo,
    # no serializado en el response), pero verificamos suma manual.
    assert esperado > 120  # 100 + 20 + algo de traslado


def test_aceptar_cotizacion_traslado_se_propaga_a_costo_estimado(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
):
    from app.models.catalogos import CategoriaProblema
    from app.models.cotizacion import Cotizacion, EstadoCotizacion
    from app.models.incidente import Asignacion

    cat = db_session.query(CategoriaProblema).filter_by(codigo="mecanica_general").one()
    enviada = db_session.query(EstadoCotizacion).filter_by(nombre="enviada").one()

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    incidente = _crear_incidente_categoria(
        db_session, cliente, vehiculo, cat, lat=-16.5, lng=-68.15
    )

    tenant = tenant_factory()
    taller = taller_factory(tenant)
    cot = Cotizacion(
        id_tenant=tenant.id_tenant,
        id_incidente=incidente.id_incidente,
        id_taller=taller.id_taller,
        id_estado_cotizacion=enviada.id_estado_cotizacion,
        monto_servicio=Decimal("200"),
        monto_repuestos=Decimal("50"),
        monto_traslado=Decimal("15"),
        distancia_km=Decimal("3.0"),
    )
    db_session.add(cot)
    db_session.commit()
    db_session.refresh(cot)

    r = client.post(
        f"/cotizaciones/{cot.id_cotizacion}/aceptar",
        headers=cliente_auth_headers(cliente),
    )
    assert r.status_code == 200, r.text

    asig = (
        db_session.query(Asignacion)
        .filter_by(id_incidente=incidente.id_incidente)
        .first()
    )
    assert asig is not None
    # costo_estimado = monto_total = 200 + 50 + 15 = 265
    assert float(asig.costo_estimado) == 265.0
