"""Tests de Pagos Fase 1 (pre-autorizacion) y Fase 3 (penalizacion).

Usa monkeypatch para mockear stripe — los tests no llaman a la API real.
"""
from decimal import Decimal

import pytest


# ============================================================
# Mocks de Stripe
# ============================================================

class _StripeError(Exception):
    user_message = "stripe falla"


class _FakeIntent(dict):
    """Imita el objeto de Stripe (dict-like + .id attr)."""

    @property
    def id(self):
        return self["id"]


def _fake_create(**kwargs):
    return _FakeIntent({
        "id": "pi_test_123",
        "client_secret": "pi_test_123_secret_abc",
        "amount": kwargs.get("amount", 2000),
        "currency": kwargs.get("currency", "usd"),
        "capture_method": kwargs.get("capture_method", "automatic"),
        "status": "requires_payment_method",
    })


def _fake_capture(intent_id, amount_to_capture=None):
    return _FakeIntent({
        "id": intent_id,
        "amount_received": amount_to_capture,
        "status": "succeeded",
    })


@pytest.fixture(autouse=True)
def _stripe_stub(monkeypatch):
    """Mockea stripe.PaymentIntent.{create,capture} para todos los tests."""
    import stripe

    monkeypatch.setattr(stripe, "PaymentIntent", type(
        "FakePaymentIntent", (),
        {
            "create": staticmethod(_fake_create),
            "capture": staticmethod(_fake_capture),
        },
    ))
    monkeypatch.setattr(stripe, "error", type("e", (), {"StripeError": _StripeError}))


# ============================================================
# Fixtures de dominio
# ============================================================

@pytest.fixture
def _incidente_con_categoria(
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    incidente_factory,
):
    """Crea un incidente con categoria + tarifa registrada para estimar costo."""
    from app.models.catalogos import CategoriaProblema
    from app.models.taller import TallerServicio

    tenant = tenant_factory()
    taller = taller_factory(tenant)
    cat = db_session.query(CategoriaProblema).first()

    db_session.add(TallerServicio(
        id_taller=taller.id_taller,
        id_categoria=cat.id_categoria,
        tarifa_base=Decimal("75.00"),
    ))
    db_session.commit()

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    incidente = incidente_factory(cliente, vehiculo, categoria_codigo=cat.codigo)
    incidente.id_tenant = tenant.id_tenant
    db_session.commit()

    return {
        "tenant": tenant,
        "taller": taller,
        "cliente": cliente,
        "incidente": incidente,
        "tarifa": Decimal("75.00"),
    }


# ============================================================
# Tests
# ============================================================

def test_estimar_costo_usa_tarifa_promedio_de_categoria(
    db_session, _incidente_con_categoria,
):
    from app.services.pago_service import ESTIMACION_FALLBACK_USD, estimar_costo

    ctx = _incidente_con_categoria
    monto = estimar_costo(db_session, ctx["incidente"])
    # Debe ser un valor positivo > 0 (proviene de tarifas) y distinto al fallback.
    assert monto > Decimal("0")
    assert monto != ESTIMACION_FALLBACK_USD


def test_estimar_costo_fallback_sin_tarifas(
    db_session, cliente_factory, vehiculo_factory, incidente_factory,
):
    from app.services.pago_service import ESTIMACION_FALLBACK_USD, estimar_costo

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    inc = incidente_factory(cliente, vehiculo)
    inc.id_categoria = None  # forzar fallback
    db_session.commit()

    assert estimar_costo(db_session, inc) == ESTIMACION_FALLBACK_USD


def test_preautorizar_crea_payment_intent_y_pago_tipo_preauth(
    client, db_session, _incidente_con_categoria, cliente_auth_headers,
):
    from app.models.incidente import Incidente
    from app.models.transaccional import Pago

    ctx = _incidente_con_categoria
    cliente = ctx["cliente"]
    incidente = ctx["incidente"]

    r = client.post(
        f"/pagos/preautorizar/{incidente.id_incidente}",
        headers=cliente_auth_headers(cliente),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["client_secret"] == "pi_test_123_secret_abc"
    assert body["payment_intent_id"] == "pi_test_123"
    assert body["monto_usd"] > 0

    db_session.expire_all()
    inc_db = db_session.query(Incidente).get(incidente.id_incidente)
    assert inc_db.stripe_preauth_id == "pi_test_123"
    assert float(inc_db.monto_preautorizacion) > 0

    pago = (
        db_session.query(Pago)
        .filter(Pago.id_incidente == incidente.id_incidente, Pago.tipo == "preauth")
        .first()
    )
    assert pago is not None
    assert pago.referencia_externa == "pi_test_123"


def test_no_dueno_no_puede_preautorizar(
    client, _incidente_con_categoria, cliente_factory, cliente_auth_headers,
):
    ctx = _incidente_con_categoria
    intruso = cliente_factory()
    r = client.post(
        f"/pagos/preautorizar/{ctx['incidente'].id_incidente}",
        headers=cliente_auth_headers(intruso),
    )
    assert r.status_code == 403


def test_capturar_crea_pago_servicio_con_comision(
    client, db_session, _incidente_con_categoria, cliente_auth_headers,
):
    from app.models.transaccional import Pago

    ctx = _incidente_con_categoria
    cliente = ctx["cliente"]
    incidente = ctx["incidente"]

    # Primero pre-autorizar
    r1 = client.post(
        f"/pagos/preautorizar/{incidente.id_incidente}",
        headers=cliente_auth_headers(cliente),
    )
    assert r1.status_code == 200

    # Capturar monto final menor (Stripe libera la diferencia)
    r2 = client.post(
        f"/pagos/capturar/{incidente.id_incidente}",
        json={"monto_final": 60.0},
        headers=cliente_auth_headers(cliente),
    )
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["tipo"] == "servicio"
    assert body["monto_total"] == 60.0
    assert body["comision_plataforma"] == 6.0  # 10%
    assert body["monto_taller"] == 54.0

    pago_servicio = (
        db_session.query(Pago)
        .filter(Pago.id_incidente == incidente.id_incidente, Pago.tipo == "servicio")
        .first()
    )
    assert pago_servicio is not None


def test_capturar_rechaza_monto_mayor_a_preauth(
    client, _incidente_con_categoria, cliente_auth_headers,
):
    ctx = _incidente_con_categoria
    cliente = ctx["cliente"]
    incidente = ctx["incidente"]

    client.post(
        f"/pagos/preautorizar/{incidente.id_incidente}",
        headers=cliente_auth_headers(cliente),
    )

    r = client.post(
        f"/pagos/capturar/{incidente.id_incidente}",
        json={"monto_final": 500.0},  # mucho mayor a 75
        headers=cliente_auth_headers(cliente),
    )
    assert r.status_code == 409
    assert "adenda" in r.json()["detail"].lower()


def test_capturar_sin_preauth_da_409(
    client, _incidente_con_categoria, cliente_auth_headers,
):
    ctx = _incidente_con_categoria
    cliente = ctx["cliente"]
    r = client.post(
        f"/pagos/capturar/{ctx['incidente'].id_incidente}",
        headers=cliente_auth_headers(cliente),
    )
    assert r.status_code == 409


def test_cancelar_con_tecnico_en_camino_genera_penalizacion(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    incidente_factory,
    asignacion_factory,
    cliente_auth_headers,
):
    from app.models.catalogos import EstadoIncidente
    from app.models.transaccional import Pago

    tenant = tenant_factory()
    taller = taller_factory(tenant)
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    inc = incidente_factory(cliente, vehiculo)
    inc.id_tenant = tenant.id_tenant
    # Estado pendiente o en_proceso para poder cancelar.
    est_pendiente = db_session.query(EstadoIncidente).filter_by(nombre="pendiente").first()
    if est_pendiente:
        inc.id_estado = est_pendiente.id_estado
    db_session.commit()

    # Asignacion en_camino
    asignacion_factory(tenant, taller, inc, estado_nombre="en_camino")

    r = client.patch(
        f"/incidencias/{inc.id_incidente}/cancelar",
        headers=cliente_auth_headers(cliente),
    )
    assert r.status_code == 200, r.text

    pen = (
        db_session.query(Pago)
        .filter(Pago.id_incidente == inc.id_incidente, Pago.tipo == "penalizacion")
        .first()
    )
    assert pen is not None
    assert float(pen.monto_total) == 5.0


def test_cancelar_sin_tecnico_en_camino_no_genera_penalizacion(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    incidente_factory,
    asignacion_factory,
    cliente_auth_headers,
):
    from app.models.catalogos import EstadoIncidente
    from app.models.transaccional import Pago

    tenant = tenant_factory()
    taller = taller_factory(tenant)
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    inc = incidente_factory(cliente, vehiculo)
    inc.id_tenant = tenant.id_tenant
    est_pendiente = db_session.query(EstadoIncidente).filter_by(nombre="pendiente").first()
    if est_pendiente:
        inc.id_estado = est_pendiente.id_estado
    db_session.commit()

    # Asignacion en estado 'aceptada' (todavia no en_camino)
    asignacion_factory(tenant, taller, inc, estado_nombre="aceptada")

    r = client.patch(
        f"/incidencias/{inc.id_incidente}/cancelar",
        headers=cliente_auth_headers(cliente),
    )
    assert r.status_code == 200

    pen = (
        db_session.query(Pago)
        .filter(Pago.id_incidente == inc.id_incidente, Pago.tipo == "penalizacion")
        .first()
    )
    assert pen is None
