"""Tests de idempotencia del modo offline en POST /incidencias."""
import uuid


def _crear_payload(vehiculo, idem_key=None):
    payload = {
        "id_vehiculo": vehiculo.id_vehiculo,
        "descripcion_usuario": "Choque trasero, no enciende",
        "latitud": -16.5,
        "longitud": -68.15,
    }
    if idem_key:
        payload["idempotency_key"] = idem_key
    return payload


def test_idempotency_misma_key_no_duplica(
    client,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
):
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    headers = cliente_auth_headers(cliente)
    key = uuid.uuid4().hex

    payload = _crear_payload(vehiculo, idem_key=key)

    r1 = client.post("/incidencias/", json=payload, headers=headers)
    assert r1.status_code == 201, r1.text
    id1 = r1.json()["id_incidente"]

    # Segundo envio con el mismo key -> debe devolver el mismo registro
    r2 = client.post("/incidencias/", json=payload, headers=headers)
    assert r2.status_code in (200, 201), r2.text
    id2 = r2.json()["id_incidente"]

    assert id1 == id2


def test_idempotency_keys_distintas_crean_distintos(
    client,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
):
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    headers = cliente_auth_headers(cliente)

    payload1 = _crear_payload(vehiculo, idem_key=uuid.uuid4().hex)
    r1 = client.post("/incidencias/", json=payload1, headers=headers)
    assert r1.status_code == 201, r1.text

    # Sin confirmar: el endpoint elimina el borrador previo y crea uno nuevo,
    # asi que keys distintos deben terminar en dos id_incidente distintos.
    payload2 = _crear_payload(vehiculo, idem_key=uuid.uuid4().hex)
    r2 = client.post("/incidencias/", json=payload2, headers=headers)
    assert r2.status_code == 201, r2.text

    assert r1.json()["id_incidente"] != r2.json()["id_incidente"]


def test_idempotency_misma_key_distintos_usuarios_no_colisiona(
    client,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
):
    """El unique es (id_usuario, idempotency_key): mismo key entre usuarios OK."""
    cliente_a = cliente_factory()
    cliente_b = cliente_factory()
    veh_a = vehiculo_factory(cliente_a)
    veh_b = vehiculo_factory(cliente_b)
    key = uuid.uuid4().hex

    r1 = client.post(
        "/incidencias/",
        json=_crear_payload(veh_a, idem_key=key),
        headers=cliente_auth_headers(cliente_a),
    )
    assert r1.status_code == 201

    r2 = client.post(
        "/incidencias/",
        json=_crear_payload(veh_b, idem_key=key),
        headers=cliente_auth_headers(cliente_b),
    )
    assert r2.status_code == 201
    assert r1.json()["id_incidente"] != r2.json()["id_incidente"]


def test_post_sin_idempotency_key_funciona_igual(
    client,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
):
    """Compatibilidad: clientes que no manden el key siguen funcionando."""
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    headers = cliente_auth_headers(cliente)

    r = client.post("/incidencias/", json=_crear_payload(vehiculo), headers=headers)
    assert r.status_code == 201, r.text
