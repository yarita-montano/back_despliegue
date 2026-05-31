"""
E2E del flujo nuevo borrador -> confirmar -> asignacion.

Cubre lo que se rompió en producción y nos hizo iterar varios commits:
1. POST /incidencias crea el incidente en estado 'borrador' (NO 'pendiente').
2. El borrador no aparece en historial (`GET /incidencias/mis-incidencias`).
3. Si el cliente vuelve a llamar POST /incidencias teniendo un borrador previo
   (con evidencia/metrica adjuntas porque la IA falló a medio camino), el
   endpoint limpia las dependencias y devuelve 201, NO 500.
4. POST /incidencias/{id}/confirmar:
   - Promueve el incidente borrador -> pendiente.
   - Crea CandidatoAsignacion para los talleres compatibles.
   - Crea UNA fila Asignacion en estado pendiente para el taller elegido.
   - Setea id_tenant del incidente al tenant del taller destinatario.
5. La Asignacion creada aparece en `GET /talleres/mi-taller/asignaciones?estado=pendiente`
   del taller elegido (era el bug donde "desde el taller no salía nada").
6. DELETE /incidencias/{id}/borrador descarta el borrador y queda fuera del historial.
"""
from __future__ import annotations


def _ensure_estados_incidente(db_session):
    """Crea los estados de incidente que el endpoint espera."""
    from app.models.catalogos import EstadoIncidente

    deseados = [
        ("borrador", "Borrador: el cliente aún no confirmó el taller"),
        ("pendiente", "Reportado, sin asignar"),
        ("en_proceso", "Taller asignado, en atención"),
        ("atendido", "Resuelto"),
        ("cancelado", "Cancelado por el usuario"),
    ]
    existentes = {e.nombre for e in db_session.query(EstadoIncidente).all()}
    for nombre, descripcion in deseados:
        if nombre not in existentes:
            db_session.add(EstadoIncidente(nombre=nombre, descripcion=descripcion))
    db_session.commit()


def _ensure_estados_asignacion(db_session):
    from app.models.catalogos import EstadoAsignacion

    deseados = ["pendiente", "aceptada", "rechazada", "en_camino", "llegado", "completada", "cancelada"]
    existentes = {e.nombre for e in db_session.query(EstadoAsignacion).all()}
    for nombre in deseados:
        if nombre not in existentes:
            db_session.add(EstadoAsignacion(nombre=nombre))
    db_session.commit()


def _categoria_para_test(db_session):
    """Devuelve una categoría existente, da igual cuál — solo necesitamos id_categoria
    para que el matching encuentre talleres y para promoverlo en confirmar."""
    from app.models.catalogos import CategoriaProblema

    return db_session.query(CategoriaProblema).first()


def test_borrador_no_aparece_en_historial(
    client,
    db_session,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
):
    _ensure_estados_incidente(db_session)

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    headers = cliente_auth_headers(cliente)

    r = client.post(
        "/incidencias/",
        json={
            "id_vehiculo": vehiculo.id_vehiculo,
            "descripcion_usuario": "Mi auto humea, no enciende",
            "latitud": -17.78,
            "longitud": -63.18,
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    incidente_creado = r.json()
    id_incidente = incidente_creado["id_incidente"]
    assert id_incidente > 0

    # Historial: el borrador NO debe salir
    r2 = client.get("/incidencias/mis-incidencias", headers=headers)
    assert r2.status_code == 200, r2.text
    ids_en_historial = [item["id_incidente"] for item in r2.json()]
    assert id_incidente not in ids_en_historial, (
        f"El borrador #{id_incidente} no debería aparecer en el historial todavía, "
        f"pero salió en {ids_en_historial}"
    )


def test_segundo_reporte_limpia_borrador_previo_con_evidencia(
    client,
    db_session,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
):
    """
    Reproduce el bug que devolvía 500: cliente reporta -> backend crea borrador
    + métrica. Si la IA falla, el cliente vuelve a tocar Reportar; el endpoint
    debe limpiar el borrador previo (con sus hijos) sin violar FK.
    """
    _ensure_estados_incidente(db_session)

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    headers = cliente_auth_headers(cliente)

    # 1er intento: el endpoint crea borrador + métrica
    r = client.post(
        "/incidencias/",
        json={
            "id_vehiculo": vehiculo.id_vehiculo,
            "descripcion_usuario": "primer intento",
            "latitud": -17.78,
            "longitud": -63.18,
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    id_1 = r.json()["id_incidente"]

    # Simulamos que se subió una evidencia al borrador y luego la IA murió.
    # Insertamos directamente en evidencia para asegurar que el borrador
    # tiene un hijo con FK.
    from app.models.catalogos import TipoEvidencia
    from app.models.incidente import Evidencia

    tipo = db_session.query(TipoEvidencia).first()
    if tipo is None:
        tipo = TipoEvidencia(nombre="imagen")
        db_session.add(tipo)
        db_session.commit()
        db_session.refresh(tipo)

    db_session.add(Evidencia(
        id_incidente=id_1,
        id_tipo_evidencia=tipo.id_tipo_evidencia,
        url_archivo="https://placehold.co/600x400.png",
    ))
    db_session.commit()

    # 2do intento: debería limpiar todo lo anterior y crear un borrador nuevo.
    # ANTES del fix esto devolvía 500 por FK violation al borrar el padre.
    r2 = client.post(
        "/incidencias/",
        json={
            "id_vehiculo": vehiculo.id_vehiculo,
            "descripcion_usuario": "segundo intento",
            "latitud": -17.78,
            "longitud": -63.18,
        },
        headers=headers,
    )
    assert r2.status_code == 201, (
        f"Esperábamos 201 al re-crear con borrador previo + evidencia adjunta, "
        f"vino {r2.status_code}: {r2.text}"
    )
    id_2 = r2.json()["id_incidente"]
    assert id_2 != id_1, "Debió generar un nuevo id_incidente"

    # El borrador previo ya no debe existir
    from app.models.incidente import Incidente
    assert db_session.query(Incidente).filter_by(id_incidente=id_1).first() is None


def test_confirmar_promueve_estado_y_crea_asignacion_para_taller_destino(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
    taller_auth_headers,
):
    """
    Flujo feliz: cliente crea borrador, le seteamos id_categoria (simulando
    que la IA terminó), llama /confirmar con id_taller_preferido y validamos
    que el taller elegido recibe la Asignacion en pendiente.
    """
    _ensure_estados_incidente(db_session)
    _ensure_estados_asignacion(db_session)

    # Categoría + taller que la atiende cerca del cliente
    from app.models.taller import TallerServicio

    cat = _categoria_para_test(db_session)
    tenant = tenant_factory()
    taller_elegido = taller_factory(tenant)
    taller_elegido.latitud, taller_elegido.longitud = -17.78, -63.18
    taller_elegido.activo = True
    taller_elegido.disponible = True
    db_session.add(TallerServicio(id_taller=taller_elegido.id_taller, id_categoria=cat.id_categoria))

    # Un segundo taller compatible (para asegurar que solo el elegido recibe asignacion)
    tenant_b = tenant_factory()
    taller_otro = taller_factory(tenant_b)
    taller_otro.latitud, taller_otro.longitud = -17.79, -63.19
    taller_otro.activo = True
    taller_otro.disponible = True
    db_session.add(TallerServicio(id_taller=taller_otro.id_taller, id_categoria=cat.id_categoria))

    db_session.commit()

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    headers_cli = cliente_auth_headers(cliente)

    # 1. Crear borrador
    r = client.post(
        "/incidencias/",
        json={
            "id_vehiculo": vehiculo.id_vehiculo,
            "descripcion_usuario": "Mi auto humea",
            "latitud": -17.78,
            "longitud": -63.18,
        },
        headers=headers_cli,
    )
    assert r.status_code == 201, r.text
    id_incidente = r.json()["id_incidente"]

    # 2. Simulamos que la IA clasificó (seteamos id_categoria directamente)
    from app.models.incidente import Incidente
    inc = db_session.query(Incidente).filter_by(id_incidente=id_incidente).one()
    inc.id_categoria = cat.id_categoria
    db_session.commit()

    # 3. Confirmar eligiendo el taller_elegido
    r2 = client.post(
        f"/incidencias/{id_incidente}/confirmar",
        json={"id_taller_preferido": taller_elegido.id_taller},
        headers=headers_cli,
    )
    assert r2.status_code == 200, r2.text

    db_session.expire_all()
    inc = db_session.query(Incidente).filter_by(id_incidente=id_incidente).one()

    # 4. Estado del incidente debe ser 'pendiente' (no 'borrador')
    from app.models.catalogos import EstadoIncidente
    estado = db_session.query(EstadoIncidente).filter_by(id_estado=inc.id_estado).one()
    assert estado.nombre == "pendiente", f"estado actual = {estado.nombre}"

    # 5. El incidente heredó el tenant del taller destinatario
    assert inc.id_tenant == taller_elegido.id_tenant, (
        f"id_tenant del incidente debió ser {taller_elegido.id_tenant} "
        f"(el del taller elegido) pero quedó en {inc.id_tenant}"
    )

    # 6. Hay UNA asignacion en pendiente y apunta al taller_elegido (no al otro)
    from app.models.catalogos import EstadoAsignacion
    from app.models.incidente import Asignacion

    asignaciones = db_session.query(Asignacion).filter_by(id_incidente=id_incidente).all()
    assert len(asignaciones) == 1, f"Esperábamos 1 asignacion, hay {len(asignaciones)}"
    asig = asignaciones[0]
    assert asig.id_taller == taller_elegido.id_taller, (
        f"La asignacion quedó para taller {asig.id_taller} en vez del elegido "
        f"{taller_elegido.id_taller}"
    )
    estado_asig = db_session.query(EstadoAsignacion).filter_by(
        id_estado_asignacion=asig.id_estado_asignacion
    ).one()
    assert estado_asig.nombre == "pendiente"

    # 7. Candidatos creados para todos los talleres compatibles (>=1)
    from app.models.incidente import CandidatoAsignacion
    candidatos = db_session.query(CandidatoAsignacion).filter_by(id_incidente=id_incidente).all()
    assert len(candidatos) >= 1
    seleccionado = [c for c in candidatos if c.seleccionado]
    assert len(seleccionado) == 1, "Debe haber exactamente 1 candidato seleccionado"
    assert seleccionado[0].id_taller == taller_elegido.id_taller

    # 8. El taller elegido ve la asignacion en su dashboard
    headers_taller = taller_auth_headers(taller_elegido)
    r3 = client.get(
        "/talleres/mi-taller/asignaciones?estado=pendiente",
        headers=headers_taller,
    )
    assert r3.status_code == 200, r3.text
    ids_asign = [item["id_asignacion"] for item in r3.json()]
    assert asig.id_asignacion in ids_asign, (
        f"El taller elegido no ve la asignacion #{asig.id_asignacion} en su listado: "
        f"{ids_asign}"
    )

    # 9. El taller "otro" NO debe ver la asignacion (solo el elegido la recibe)
    headers_otro = taller_auth_headers(taller_otro)
    r4 = client.get(
        "/talleres/mi-taller/asignaciones?estado=pendiente",
        headers=headers_otro,
    )
    assert r4.status_code == 200, r4.text
    ids_otro = [item["id_asignacion"] for item in r4.json()]
    assert asig.id_asignacion not in ids_otro, (
        f"El taller 'otro' no debería ver la asignacion del taller elegido"
    )

    # 10. Tras confirmar, el incidente SÍ aparece en el historial del cliente
    r5 = client.get("/incidencias/mis-incidencias", headers=headers_cli)
    assert r5.status_code == 200, r5.text
    ids_historial = [item["id_incidente"] for item in r5.json()]
    assert id_incidente in ids_historial, (
        f"Tras confirmar, el incidente {id_incidente} debería estar en el historial"
    )


def test_descartar_borrador_no_aparece_en_historial(
    client,
    db_session,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
):
    """
    El cliente abandona el flujo (sale antes de elegir taller). El borrador
    se descarta vía DELETE y queda fuera del historial.
    """
    _ensure_estados_incidente(db_session)

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    headers = cliente_auth_headers(cliente)

    r = client.post(
        "/incidencias/",
        json={
            "id_vehiculo": vehiculo.id_vehiculo,
            "descripcion_usuario": "Voy a abandonar este reporte",
            "latitud": -17.78,
            "longitud": -63.18,
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    id_incidente = r.json()["id_incidente"]

    # Abandonamos el flujo
    r2 = client.delete(f"/incidencias/{id_incidente}/borrador", headers=headers)
    assert r2.status_code == 204, r2.text

    # No aparece en historial
    r3 = client.get("/incidencias/mis-incidencias", headers=headers)
    assert r3.status_code == 200
    ids = [item["id_incidente"] for item in r3.json()]
    assert id_incidente not in ids

    # Y no se puede confirmar (ya no existe)
    r4 = client.post(
        f"/incidencias/{id_incidente}/confirmar",
        json={},
        headers=headers,
    )
    assert r4.status_code == 404, r4.text


def test_confirmar_falla_si_incidente_ya_no_es_borrador(
    client,
    db_session,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
):
    """Si el incidente ya fue confirmado antes, /confirmar devuelve 400 explícito."""
    _ensure_estados_incidente(db_session)

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    headers = cliente_auth_headers(cliente)

    r = client.post(
        "/incidencias/",
        json={
            "id_vehiculo": vehiculo.id_vehiculo,
            "descripcion_usuario": "test",
            "latitud": -17.78,
            "longitud": -63.18,
        },
        headers=headers,
    )
    id_incidente = r.json()["id_incidente"]

    # Forzamos manualmente el estado a 'pendiente'
    from app.models.catalogos import EstadoIncidente
    from app.models.incidente import Incidente

    estado_pendiente = db_session.query(EstadoIncidente).filter_by(nombre="pendiente").one()
    inc = db_session.query(Incidente).filter_by(id_incidente=id_incidente).one()
    inc.id_estado = estado_pendiente.id_estado
    db_session.commit()

    r2 = client.post(f"/incidencias/{id_incidente}/confirmar", json={}, headers=headers)
    assert r2.status_code == 400, r2.text
    assert "borrador" in r2.json()["detail"].lower()
