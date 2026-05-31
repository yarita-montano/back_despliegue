"""Tests del campo tiempo_estimado_min en cotizaciones + asignaciones."""


def _crear_incidente_categoria(db_session, usuario, vehiculo, categoria, lat=-16.5, lng=-68.15):
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


def test_taller_responde_con_tiempo_estimado(
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

    cat = db_session.query(CategoriaProblema).filter_by(codigo="chaperia_pintura").one()
    pendiente = db_session.query(EstadoCotizacion).filter_by(nombre="pendiente").one()

    tenant = tenant_factory()
    taller = taller_factory(tenant)
    taller.latitud, taller.longitud = -16.5, -68.15
    db_session.add(TallerServicio(id_taller=taller.id_taller, id_categoria=cat.id_categoria))

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    incidente = _crear_incidente_categoria(db_session, cliente, vehiculo, cat)

    cot = Cotizacion(
        id_tenant=tenant.id_tenant,
        id_incidente=incidente.id_incidente,
        id_taller=taller.id_taller,
        id_estado_cotizacion=pendiente.id_estado_cotizacion,
    )
    db_session.add(cot)
    db_session.commit()
    db_session.refresh(cot)

    headers = taller_auth_headers(taller)
    r = client.post(
        f"/cotizaciones/{cot.id_cotizacion}/responder",
        json={
            "monto_servicio": 400,
            "monto_repuestos": 100,
            "garantia_dias": 30,
            "tiempo_estimado_min": 180,
            "nota": "tres horas",
        },
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["tiempo_estimado_min"] == 180


def test_aceptar_cotizacion_propaga_tiempo_a_asignacion(
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
    incidente = _crear_incidente_categoria(db_session, cliente, vehiculo, cat)

    tenant = tenant_factory()
    taller = taller_factory(tenant)
    cot = Cotizacion(
        id_tenant=tenant.id_tenant,
        id_incidente=incidente.id_incidente,
        id_taller=taller.id_taller,
        id_estado_cotizacion=enviada.id_estado_cotizacion,
        monto_servicio=300,
        monto_repuestos=100,
        garantia_dias=15,
        tiempo_estimado_min=240,
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
    assert asig.tiempo_estimado_reparacion_min == 240
