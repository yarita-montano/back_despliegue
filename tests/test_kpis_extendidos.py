"""Tests de los KPIs nuevos del segundo parcial:
   - casos_cancelados
   - zonas_mas_incidentes
   - sla_cumplimiento
"""
from datetime import datetime, timedelta, timezone


def _now():
    return datetime.now(timezone.utc)


def test_kpi_resumen_incluye_campos_nuevos(
    client, db_session, tenant_factory, taller_factory, taller_auth_headers,
):
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    r = client.get("/tenants/me/kpis", headers=taller_auth_headers(taller))
    assert r.status_code == 200, r.text
    data = r.json()
    assert "casos_cancelados" in data
    assert "zonas_mas_incidentes" in data
    assert "sla_cumplimiento" in data
    assert isinstance(data["zonas_mas_incidentes"], list)
    assert data["sla_cumplimiento"]["sla_minutos"] == 60


def test_kpi_casos_cancelados_cuenta_correcto(
    db_session,
    tenant_factory,
    cliente_factory,
    vehiculo_factory,
    incidente_factory,
):
    from app.models.catalogos import EstadoIncidente
    from app.services import kpi_service

    tenant = tenant_factory()
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)

    estado_cancelado = (
        db_session.query(EstadoIncidente).filter_by(nombre="cancelado").first()
    )
    assert estado_cancelado is not None, "El catalogo necesita estado 'cancelado'"

    # 2 cancelados + 1 no-cancelado
    for _ in range(2):
        inc = incidente_factory(cliente, vehiculo)
        inc.id_tenant = tenant.id_tenant
        inc.id_estado = estado_cancelado.id_estado
    inc = incidente_factory(cliente, vehiculo)
    inc.id_tenant = tenant.id_tenant  # queda con estado default != cancelado
    db_session.commit()

    total = kpi_service.incidentes_cancelados(
        db_session, _now() - timedelta(hours=1), _now(), id_tenant=tenant.id_tenant,
    )
    assert total == 2


def test_kpi_zonas_agrupa_por_redondeo(
    db_session,
    tenant_factory,
    cliente_factory,
    vehiculo_factory,
    incidente_factory,
):
    from app.services import kpi_service

    tenant = tenant_factory()
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)

    # Dos incidentes en la misma celda (~ -16.50, -68.15) y uno lejos
    for lat, lng in [(-16.501, -68.151), (-16.502, -68.149), (-15.0, -70.0)]:
        inc = incidente_factory(cliente, vehiculo, lat=lat, lng=lng)
        inc.id_tenant = tenant.id_tenant
    db_session.commit()

    zonas = kpi_service.zonas_mas_incidentes(
        db_session, _now() - timedelta(hours=1), _now(), id_tenant=tenant.id_tenant,
    )
    assert len(zonas) >= 2
    # La zona con mas incidentes debe agrupar al menos 2
    top = zonas[0]
    assert top["total"] >= 2


def test_kpi_sla_calculo(
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    incidente_factory,
):
    from sqlalchemy import text

    from app.models.catalogos import EstadoAsignacion
    from app.models.incidente import (
        Asignacion,
        HistorialEstadoAsignacion,
    )
    from app.services import kpi_service

    tenant = tenant_factory()
    taller = taller_factory(tenant)
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)

    estado_completada = (
        db_session.query(EstadoAsignacion).filter_by(nombre="completada").first()
    )
    assert estado_completada is not None

    # Caso A: incidente creado hace 30 min, asig completada ahora -> cumple SLA (60min)
    inc_a = incidente_factory(cliente, vehiculo)
    inc_a.id_tenant = tenant.id_tenant
    asig_a = Asignacion(
        id_tenant=tenant.id_tenant,
        id_incidente=inc_a.id_incidente,
        id_taller=taller.id_taller,
        id_estado_asignacion=estado_completada.id_estado_asignacion,
    )
    db_session.add(asig_a)
    db_session.commit()
    db_session.refresh(asig_a)

    db_session.execute(
        text("UPDATE incidente SET created_at = NOW() - INTERVAL '30 minutes' WHERE id_incidente = :i"),
        {"i": inc_a.id_incidente},
    )
    db_session.add(HistorialEstadoAsignacion(
        id_asignacion=asig_a.id_asignacion,
        id_estado_nuevo=estado_completada.id_estado_asignacion,
    ))
    db_session.commit()

    # Caso B: incidente hace 120 min, completada ahora -> NO cumple SLA
    inc_b = incidente_factory(cliente, vehiculo)
    inc_b.id_tenant = tenant.id_tenant
    asig_b = Asignacion(
        id_tenant=tenant.id_tenant,
        id_incidente=inc_b.id_incidente,
        id_taller=taller.id_taller,
        id_estado_asignacion=estado_completada.id_estado_asignacion,
    )
    db_session.add(asig_b)
    db_session.commit()
    db_session.refresh(asig_b)

    db_session.execute(
        text("UPDATE incidente SET created_at = NOW() - INTERVAL '120 minutes' WHERE id_incidente = :i"),
        {"i": inc_b.id_incidente},
    )
    db_session.add(HistorialEstadoAsignacion(
        id_asignacion=asig_b.id_asignacion,
        id_estado_nuevo=estado_completada.id_estado_asignacion,
    ))
    db_session.commit()

    res = kpi_service.cumplimiento_sla(
        db_session,
        _now() - timedelta(hours=1),
        _now() + timedelta(minutes=5),
        id_tenant=tenant.id_tenant,
        sla_minutos=60,
    )
    assert res["total_completadas"] == 2
    assert res["cumplen_sla"] == 1
    assert res["porcentaje"] == 50.0


def test_kpi_aisla_cancelados_por_tenant(
    db_session,
    tenant_factory,
    cliente_factory,
    vehiculo_factory,
    incidente_factory,
):
    from app.models.catalogos import EstadoIncidente
    from app.services import kpi_service

    tenant_a = tenant_factory()
    tenant_b = tenant_factory()
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    estado_cancelado = (
        db_session.query(EstadoIncidente).filter_by(nombre="cancelado").first()
    )

    inc_a = incidente_factory(cliente, vehiculo)
    inc_a.id_tenant = tenant_a.id_tenant
    inc_a.id_estado = estado_cancelado.id_estado

    inc_b = incidente_factory(cliente, vehiculo)
    inc_b.id_tenant = tenant_b.id_tenant
    inc_b.id_estado = estado_cancelado.id_estado
    db_session.commit()

    total_a = kpi_service.incidentes_cancelados(
        db_session, _now() - timedelta(hours=1), _now(), id_tenant=tenant_a.id_tenant,
    )
    assert total_a == 1
