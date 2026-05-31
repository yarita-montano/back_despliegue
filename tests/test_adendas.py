"""Tests de Adendas (Pagos Fase 2): ampliacion de presupuesto."""
import pytest


@pytest.fixture
def _setup_asig_con_tecnico(
    db_session,
    tenant_factory,
    taller_factory,
    tecnico_factory,
    cliente_factory,
    vehiculo_factory,
    incidente_factory,
    asignacion_factory,
):
    """Crea una asignacion 'aceptada' con tecnico vinculado, costo inicial."""
    from decimal import Decimal

    tenant = tenant_factory()
    taller = taller_factory(tenant)
    tecnico = tecnico_factory(taller)
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    incidente = incidente_factory(cliente, vehiculo)
    incidente.id_tenant = tenant.id_tenant
    db_session.commit()

    asig = asignacion_factory(tenant, taller, incidente, tecnico=tecnico)
    asig.costo_estimado = Decimal("500.00")
    db_session.commit()
    return {
        "tenant": tenant,
        "taller": taller,
        "tecnico": tecnico,
        "cliente": cliente,
        "asignacion": asig,
        "incidente": incidente,
    }


def test_tecnico_crea_adenda_congela_asignacion(
    client,
    db_session,
    _setup_asig_con_tecnico,
    tecnico_auth_headers,
):
    from app.models.catalogos import EstadoAsignacion
    from app.models.incidente import Asignacion

    ctx = _setup_asig_con_tecnico
    asig = ctx["asignacion"]
    tecnico = ctx["tecnico"]
    taller = ctx["taller"]

    headers = tecnico_auth_headers(tecnico, taller)
    r = client.post(
        f"/asignaciones/{asig.id_asignacion}/adendas",
        json={"monto_adicional": 200, "descripcion": "Bujias y filtro adicionales"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["estado"] == "pendiente"
    assert body["monto_adicional"] == 200

    db_session.expire_all()
    asig_actual = db_session.query(Asignacion).get(asig.id_asignacion)
    estado = db_session.query(EstadoAsignacion).get(asig_actual.id_estado_asignacion)
    assert estado.nombre == "en_espera_aprobacion"


def test_cliente_aprueba_adenda_suma_costo_y_reactiva(
    client,
    db_session,
    _setup_asig_con_tecnico,
    tecnico_auth_headers,
    cliente_auth_headers,
):
    from app.models.catalogos import EstadoAsignacion
    from app.models.incidente import Asignacion

    ctx = _setup_asig_con_tecnico
    asig = ctx["asignacion"]
    tecnico = ctx["tecnico"]
    taller = ctx["taller"]
    cliente = ctx["cliente"]

    r1 = client.post(
        f"/asignaciones/{asig.id_asignacion}/adendas",
        json={"monto_adicional": 150, "descripcion": "Lubricantes premium"},
        headers=tecnico_auth_headers(tecnico, taller),
    )
    assert r1.status_code == 201
    id_adenda = r1.json()["id_adenda"]

    r2 = client.post(
        f"/adendas/{id_adenda}/responder",
        json={"decision": "aprobar"},
        headers=cliente_auth_headers(cliente),
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["estado"] == "aprobada"

    db_session.expire_all()
    asig_actual = db_session.query(Asignacion).get(asig.id_asignacion)
    assert float(asig_actual.costo_estimado) == 500.0 + 150.0
    estado = db_session.query(EstadoAsignacion).get(asig_actual.id_estado_asignacion)
    assert estado.nombre == "aceptada"


def test_cliente_rechaza_adenda_cancela_asignacion(
    client,
    db_session,
    _setup_asig_con_tecnico,
    tecnico_auth_headers,
    cliente_auth_headers,
):
    from app.models.catalogos import EstadoAsignacion
    from app.models.incidente import Asignacion

    ctx = _setup_asig_con_tecnico
    asig = ctx["asignacion"]
    tecnico = ctx["tecnico"]
    taller = ctx["taller"]
    cliente = ctx["cliente"]

    r1 = client.post(
        f"/asignaciones/{asig.id_asignacion}/adendas",
        json={"monto_adicional": 300, "descripcion": "Cambio integral"},
        headers=tecnico_auth_headers(tecnico, taller),
    )
    id_adenda = r1.json()["id_adenda"]

    r2 = client.post(
        f"/adendas/{id_adenda}/responder",
        json={"decision": "rechazar", "motivo": "Excede mi presupuesto"},
        headers=cliente_auth_headers(cliente),
    )
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["estado"] == "rechazada"
    assert body["motivo_cliente"] == "Excede mi presupuesto"

    db_session.expire_all()
    asig_actual = db_session.query(Asignacion).get(asig.id_asignacion)
    estado = db_session.query(EstadoAsignacion).get(asig_actual.id_estado_asignacion)
    assert estado.nombre == "cancelada"
    assert asig_actual.cancelada_at is not None
    assert "Adenda rechazada" in (asig_actual.motivo_cancelacion or "")


def test_no_dos_adendas_pendientes_simultaneas(
    client,
    db_session,
    _setup_asig_con_tecnico,
    tecnico_auth_headers,
):
    ctx = _setup_asig_con_tecnico
    asig = ctx["asignacion"]
    tecnico = ctx["tecnico"]
    taller = ctx["taller"]

    headers = tecnico_auth_headers(tecnico, taller)
    r1 = client.post(
        f"/asignaciones/{asig.id_asignacion}/adendas",
        json={"monto_adicional": 100, "descripcion": "Primera"},
        headers=headers,
    )
    assert r1.status_code == 201

    r2 = client.post(
        f"/asignaciones/{asig.id_asignacion}/adendas",
        json={"monto_adicional": 50, "descripcion": "Segunda"},
        headers=headers,
    )
    assert r2.status_code == 409


def test_solo_dueno_responde_adenda(
    client,
    db_session,
    _setup_asig_con_tecnico,
    tecnico_auth_headers,
    cliente_factory,
    cliente_auth_headers,
):
    ctx = _setup_asig_con_tecnico
    asig = ctx["asignacion"]
    tecnico = ctx["tecnico"]
    taller = ctx["taller"]

    r1 = client.post(
        f"/asignaciones/{asig.id_asignacion}/adendas",
        json={"monto_adicional": 100, "descripcion": "Una adenda de prueba"},
        headers=tecnico_auth_headers(tecnico, taller),
    )
    assert r1.status_code == 201, r1.text
    id_adenda = r1.json()["id_adenda"]

    intruso = cliente_factory()
    r2 = client.post(
        f"/adendas/{id_adenda}/responder",
        json={"decision": "aprobar"},
        headers=cliente_auth_headers(intruso),
    )
    assert r2.status_code == 403


def test_solo_tecnico_crea_adenda(
    client,
    _setup_asig_con_tecnico,
    cliente_auth_headers,
):
    """Un cliente no puede registrar adenda — rol equivocado -> 403."""
    ctx = _setup_asig_con_tecnico
    asig = ctx["asignacion"]
    cliente = ctx["cliente"]

    r = client.post(
        f"/asignaciones/{asig.id_asignacion}/adendas",
        json={"monto_adicional": 100, "descripcion": "Intento sin permiso"},
        headers=cliente_auth_headers(cliente),
    )
    assert r.status_code == 403
