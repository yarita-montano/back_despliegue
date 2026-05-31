"""Tests de porcentajes de compensacion por cancelacion configurables.

Verifica que cuando el admin del tenant cambia los porcentajes
(pct_cancel_pendiente / pct_cancel_aceptada / pct_cancel_en_camino),
la compensacion calculada al cancelar usa esos valores en vez de los
defaults hardcoded.
"""


def _asignacion(db_session, tenant, taller, incidente, estado_nombre, tarifa=10):
    from app.models.catalogos import EstadoAsignacion
    from app.models.incidente import Asignacion

    estado = db_session.query(EstadoAsignacion).filter_by(nombre=estado_nombre).first()
    taller.tarifa_traslado = tarifa
    asig = Asignacion(
        id_tenant=tenant.id_tenant,
        id_incidente=incidente.id_incidente,
        id_taller=taller.id_taller,
        id_estado_asignacion=estado.id_estado_asignacion,
    )
    db_session.add(asig)
    db_session.commit()
    db_session.refresh(asig)
    return asig


def test_admin_actualiza_porcentajes_de_cancelacion(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    taller_auth_headers,
):
    tenant = tenant_factory()
    taller = taller_factory(tenant)

    r = client.patch(
        "/tenants/me/cancelacion-pct",
        json={
            "pct_cancel_pendiente": 10,
            "pct_cancel_aceptada": 25,
            "pct_cancel_en_camino": 75,
        },
        headers=taller_auth_headers(taller),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pct_cancel_pendiente"] == 10
    assert body["pct_cancel_aceptada"] == 25
    assert body["pct_cancel_en_camino"] == 75


def test_compensacion_usa_porcentajes_del_tenant(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
    incidente_factory,
):
    tenant = tenant_factory()
    # Configurar porcentajes custom
    tenant.pct_cancel_pendiente = 0
    tenant.pct_cancel_aceptada = 25  # custom, no default 50
    tenant.pct_cancel_en_camino = 80  # custom, no default 100
    db_session.commit()

    taller = taller_factory(tenant)
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    incidente = incidente_factory(cliente, vehiculo)
    incidente.id_tenant = tenant.id_tenant
    db_session.commit()

    # Tarifa = 100, asignacion en_camino → debe ser 100 * 80% = 80
    asig = _asignacion(db_session, tenant, taller, incidente, "en_camino", tarifa=100)

    r = client.post(
        f"/asignaciones/{asig.id_asignacion}/cancelar",
        json={"motivo": "Ya no necesito el servicio"},
        headers=cliente_auth_headers(cliente),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert float(body["compensacion_monto"]) == 80.0


def test_compensacion_aceptada_usa_pct_custom(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
    incidente_factory,
):
    tenant = tenant_factory()
    tenant.pct_cancel_aceptada = 30  # custom, default era 50
    db_session.commit()

    taller = taller_factory(tenant)
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    incidente = incidente_factory(cliente, vehiculo)
    incidente.id_tenant = tenant.id_tenant
    db_session.commit()

    # Tarifa = 50, asignacion aceptada → 50 * 30% = 15
    asig = _asignacion(db_session, tenant, taller, incidente, "aceptada", tarifa=50)

    r = client.post(
        f"/asignaciones/{asig.id_asignacion}/cancelar",
        json={"motivo": "test"},
        headers=cliente_auth_headers(cliente),
    )
    assert r.status_code == 200, r.text
    assert float(r.json()["compensacion_monto"]) == 15.0
