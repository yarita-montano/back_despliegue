"""Tests del endpoint /talleres/compatibles con desglose completo.

Verifica que el endpoint publico devuelve:
  - tiempo_reparacion_min (config del taller en TallerServicio)
  - eta_llegada_min (calculado con VELOCIDAD_DEFAULT_KMH)
"""
from decimal import Decimal


def test_compatibles_devuelve_eta_llegada_y_tiempo_reparacion(
    client,
    db_session,
    tenant_factory,
    taller_factory,
):
    from app.models.catalogos import CategoriaProblema
    from app.models.taller import TallerServicio
    from app.services.tracking_service import VELOCIDAD_DEFAULT_KMH

    cat = db_session.query(CategoriaProblema).filter_by(codigo="llantas").one()
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    taller.latitud, taller.longitud = -16.5000, -68.1500
    taller.tarifa_traslado = Decimal("2.50")
    db_session.add(TallerServicio(
        id_taller=taller.id_taller,
        id_categoria=cat.id_categoria,
        tarifa_base=Decimal("80"),
        tiempo_estimado_min=45,
    ))
    db_session.commit()

    # Cliente a ~1.1 km al norte del taller
    r = client.get(
        f"/talleres/compatibles?id_categoria={cat.id_categoria}"
        f"&latitud=-16.4900&longitud=-68.1500&radio_km=10"
    )
    assert r.status_code == 200, r.text
    items = r.json()
    mio = next((x for x in items if x["id_taller"] == taller.id_taller), None)
    assert mio is not None, "El taller deberia aparecer en compatibles"

    # tiempo_reparacion_min viene de TallerServicio
    assert mio["tiempo_reparacion_min"] == 45

    # eta_llegada_min = (distancia / VELOCIDAD_DEFAULT_KMH) * 60
    assert mio["eta_llegada_min"] is not None
    assert mio["eta_llegada_min"] >= 1
    esperado = max(1, int(round((mio["distancia_km"] / VELOCIDAD_DEFAULT_KMH) * 60)))
    assert mio["eta_llegada_min"] == esperado

    # Desglose de precio (bug previo)
    assert mio["tarifa_base"] == 80.0
    assert mio["monto_traslado"] is not None
    assert mio["total_estimado"] is not None
    assert mio["total_estimado"] >= 80.0


def test_taller_guarda_tiempo_estimado_via_put_servicios(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    taller_auth_headers,
):
    from app.models.catalogos import CategoriaProblema
    from app.models.taller import TallerServicio

    cat = db_session.query(CategoriaProblema).filter_by(codigo="grua_auxilio").one()
    tenant = tenant_factory()
    taller = taller_factory(tenant)

    r = client.put(
        "/talleres/mi-taller/servicios",
        json={
            "servicios": [
                {
                    "id_categoria": cat.id_categoria,
                    "servicio_movil": True,
                    "tarifa_base": 60,
                    "tiempo_estimado_min": 90,
                }
            ]
        },
        headers=taller_auth_headers(taller),
    )
    assert r.status_code == 200, r.text
    assert r.json()[0]["tiempo_estimado_min"] == 90

    persistido = (
        db_session.query(TallerServicio)
        .filter_by(id_taller=taller.id_taller, id_categoria=cat.id_categoria)
        .first()
    )
    assert persistido.tiempo_estimado_min == 90


def test_tarifa_y_tiempo_son_independientes_entre_talleres(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    taller_auth_headers,
):
    """Dos talleres distintos para la MISMA categoria deben poder tener
    tarifa_base y tiempo_estimado_min completamente diferentes."""
    from app.models.catalogos import CategoriaProblema
    from app.models.taller import TallerServicio

    cat = db_session.query(CategoriaProblema).filter_by(codigo="llantas").one()

    tenant_a = tenant_factory()
    tenant_b = tenant_factory()
    taller_a = taller_factory(tenant_a)
    taller_b = taller_factory(tenant_b)

    # Taller A: tarifa 50, 30 min
    client.put(
        "/talleres/mi-taller/servicios",
        json={"servicios": [{
            "id_categoria": cat.id_categoria,
            "servicio_movil": True,
            "tarifa_base": 50,
            "tiempo_estimado_min": 30,
        }]},
        headers=taller_auth_headers(taller_a),
    )

    # Taller B: tarifa 120, 90 min
    client.put(
        "/talleres/mi-taller/servicios",
        json={"servicios": [{
            "id_categoria": cat.id_categoria,
            "servicio_movil": True,
            "tarifa_base": 120,
            "tiempo_estimado_min": 90,
        }]},
        headers=taller_auth_headers(taller_b),
    )

    # Cada taller persiste lo suyo, sin pisarse
    sa = db_session.query(TallerServicio).filter_by(
        id_taller=taller_a.id_taller, id_categoria=cat.id_categoria,
    ).first()
    sb = db_session.query(TallerServicio).filter_by(
        id_taller=taller_b.id_taller, id_categoria=cat.id_categoria,
    ).first()

    assert float(sa.tarifa_base) == 50.0
    assert sa.tiempo_estimado_min == 30
    assert float(sb.tarifa_base) == 120.0
    assert sb.tiempo_estimado_min == 90

    # Y cada uno solo ve sus propios servicios via GET
    ra = client.get("/talleres/mi-taller/servicios", headers=taller_auth_headers(taller_a))
    assert ra.status_code == 200
    listadosA = ra.json()
    assert len(listadosA) == 1
    assert listadosA[0]["tarifa_base"] == 50.0
    assert listadosA[0]["tiempo_estimado_min"] == 30
