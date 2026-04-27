"""
Seed completo via API (HTTP) usando endpoints con seguridad.

Crea:
- usuarios cliente (1 por escenario)
- vehiculos
- incidentes
- asignaciones en todos los estados (pendiente/aceptada/rechazada/en_camino/completada)
- mensajes
- evidencias (imagen/audio/texto)
- pagos (best-effort; requiere STRIPE_SECRET_KEY)

Uso:
  python seed_api_full.py

Config por env (opcional):
  SEED_BASE_URL
  SEED_ADMIN_EMAIL, SEED_ADMIN_PASSWORD
  SEED_TALLER_EMAIL, SEED_TALLER_PASSWORD
"""

from __future__ import annotations

import base64
import json
import os
import time
from typing import Any, Dict, List, Optional

import requests

BASE_URL = os.getenv("SEED_BASE_URL", "https://back-despliegue-cp05.onrender.com").rstrip("/")

ADMIN_EMAIL = os.getenv("SEED_ADMIN_EMAIL", "admin@plataforma.com")
ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "admin123!")

TALLER_EMAIL = os.getenv("SEED_TALLER_EMAIL", "gerente@tallerexcelente.com")
TALLER_PASSWORD = os.getenv("SEED_TALLER_PASSWORD", "taller123!")

# Coordenadas Santa Cruz de la Sierra (aprox.)
COORDS = [
    (-17.802625, -63.200045),
    (-17.801221, -63.183911),
    (-17.793012, -63.171450),
    (-17.785900, -63.206230),
    (-17.815320, -63.188120),
]

SCENARIOS = [
    {"estado_asignacion": "pendiente", "estado_incidente": "pendiente"},
    {"estado_asignacion": "aceptada", "estado_incidente": "pendiente"},
    {"estado_asignacion": "rechazada", "estado_incidente": "pendiente"},
    {"estado_asignacion": "en_camino", "estado_incidente": "en_proceso"},
    {"estado_asignacion": "completada", "estado_incidente": "atendido"},
]

# Archivos de evidencia en memoria (base64)
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
)
WAV_EMPTY = base64.b64decode(
    "UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YQAAAAA="
)


class ApiError(RuntimeError):
    pass


def _req(
    method: str,
    path: str,
    *,
    token: Optional[str] = None,
    json_body: Optional[dict] = None,
    data: Optional[dict] = None,
    files: Optional[dict] = None,
    expected: Optional[List[int]] = None,
) -> requests.Response:
    url = f"{BASE_URL}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if json_body is not None:
        headers["Content-Type"] = "application/json"

    resp = requests.request(
        method,
        url,
        headers=headers,
        json=json_body,
        data=data,
        files=files,
        timeout=30,
    )
    if expected and resp.status_code not in expected:
        raise ApiError(f"{method} {path} -> {resp.status_code}: {resp.text}")
    return resp


def login_admin() -> str:
    resp = _req(
        "POST",
        "/usuarios/login",
        json_body={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        expected=[200],
    )
    return resp.json()["access_token"]


def login_taller() -> str:
    resp = _req(
        "POST",
        "/talleres/login",
        json_body={"email": TALLER_EMAIL, "password": TALLER_PASSWORD},
        expected=[200],
    )
    return resp.json()["access_token"]


def ensure_taller(admin_token: str) -> str:
    try:
        return login_taller()
    except ApiError:
        payload = {
            "nombre": "Taller Seed Santa Cruz",
            "email": TALLER_EMAIL,
            "password": TALLER_PASSWORD,
            "telefono": "+591 70000000",
            "direccion": "Av. Principal, Santa Cruz",
            "latitud": COORDS[0][0],
            "longitud": COORDS[0][1],
            "capacidad_max": 5,
            "verificado": True,
        }
        _req("POST", "/admin/talleres", token=admin_token, json_body=payload, expected=[201])
        return login_taller()


def ensure_cliente(email: str, password: str, nombre: str) -> str:
    try:
        _req(
            "POST",
            "/usuarios/registro",
            json_body={
                "nombre": nombre,
                "email": email,
                "password": password,
                "telefono": "+591 70000001",
            },
            expected=[201, 409],
        )
    except ApiError:
        pass

    resp = _req(
        "POST",
        "/usuarios/login",
        json_body={"email": email, "password": password},
        expected=[200],
    )
    return resp.json()["access_token"]


def ensure_tecnico(taller_token: str, nombre: str, email: str, password: str) -> dict:
    payload = {
        "nombre": nombre,
        "email": email,
        "telefono": "+591 70000002",
        "password": password,
    }
    try:
        resp = _req("POST", "/talleres/mi-taller/tecnicos", token=taller_token, json_body=payload, expected=[201])
        return resp.json()
    except ApiError:
        # Buscar existente
        resp = _req("GET", "/talleres/mi-taller/tecnicos", token=taller_token, expected=[200])
        for t in resp.json():
            if t.get("email") == email:
                return t
        raise


def crear_vehiculo(cliente_token: str, placa: str) -> dict:
    payload = {
        "placa": placa,
        "marca": "Toyota",
        "modelo": "Corolla",
        "anio": 2021,
        "color": "Blanco",
    }
    try:
        resp = _req("POST", "/vehiculos/", token=cliente_token, json_body=payload, expected=[201])
        return resp.json()
    except ApiError:
        resp = _req("GET", "/vehiculos/mis-autos", token=cliente_token, expected=[200])
        autos = resp.json()
        if autos:
            return autos[0]
        raise


def crear_incidente(cliente_token: str, id_vehiculo: int, lat: float, lng: float, descripcion: str) -> dict:
    payload = {
        "id_vehiculo": id_vehiculo,
        "descripcion_usuario": descripcion,
        "latitud": lat,
        "longitud": lng,
    }
    resp = _req("POST", "/incidencias/", token=cliente_token, json_body=payload, expected=[201])
    return resp.json()


def analizar_ia(cliente_token: str, id_incidente: int) -> None:
    _req("POST", f"/incidencias/{id_incidente}/analizar-ia", token=cliente_token, expected=[200])


def obtener_asignacion_taller(taller_token: str, id_incidente: int) -> dict:
    # Buscar la asignacion del incidente para este taller
    resp = _req("GET", "/talleres/mi-taller/asignaciones", token=taller_token, expected=[200])
    asignaciones = resp.json()
    for a in asignaciones:
        if a.get("id_incidente") == id_incidente:
            return a
    raise ApiError(f"No se encontro asignacion para incidente {id_incidente}")


def aceptar_asignacion(taller_token: str, id_asignacion: int, id_tecnico: int) -> dict:
    payload = {"id_usuario": id_tecnico, "eta_minutos": 15, "nota": "Seed aceptada"}
    resp = _req(
        "PUT",
        f"/talleres/mi-taller/asignaciones/{id_asignacion}/aceptar",
        token=taller_token,
        json_body=payload,
        expected=[200],
    )
    return resp.json()


def rechazar_asignacion(taller_token: str, id_asignacion: int) -> dict:
    payload = {"motivo": "Seed rechazo"}
    resp = _req(
        "PUT",
        f"/talleres/mi-taller/asignaciones/{id_asignacion}/rechazar",
        token=taller_token,
        json_body=payload,
        expected=[200],
    )
    return resp.json()


def login_tecnico(email: str, password: str) -> str:
    resp = _req(
        "POST",
        "/usuarios/login",
        json_body={"email": email, "password": password},
        expected=[200],
    )
    return resp.json()["access_token"]


def iniciar_viaje(tecnico_token: str, id_asignacion: int, lat: float, lng: float) -> None:
    _req(
        "PUT",
        f"/tecnicos/mis-asignaciones/{id_asignacion}/iniciar-viaje",
        token=tecnico_token,
        json_body={"latitud_tecnico": lat, "longitud_tecnico": lng},
        expected=[200],
    )


def completar_servicio(tecnico_token: str, id_asignacion: int) -> None:
    _req(
        "PUT",
        f"/tecnicos/mis-asignaciones/{id_asignacion}/completar",
        token=tecnico_token,
        json_body={"costo_estimado": 25.0, "resumen_trabajo": "Seed completado"},
        expected=[200],
    )


def actualizar_ubicacion(tecnico_token: str, lat: float, lng: float) -> None:
    _req(
        "PUT",
        "/tecnicos/mi-ubicacion",
        token=tecnico_token,
        json_body={"latitud": lat, "longitud": lng},
        expected=[200],
    )


def enviar_mensajes(cliente_token: str, taller_token: str, id_incidente: int) -> None:
    _req(
        "POST",
        f"/mensajes/{id_incidente}",
        token=cliente_token,
        json_body={"contenido": "Seed: mensaje del cliente"},
        expected=[201],
    )
    _req(
        "POST",
        f"/mensajes/{id_incidente}/taller",
        token=taller_token,
        json_body={"contenido": "Seed: mensaje del taller"},
        expected=[201],
    )


def subir_evidencias(cliente_token: str, id_incidente: int) -> None:
    resp = _req("GET", "/incidencias/evidencias/tipos", token=cliente_token, expected=[200])
    tipos = {t["nombre"]: t["id_tipo_evidencia"] for t in resp.json()}

    # texto
    if "texto" in tipos:
        _req(
            "POST",
            f"/incidencias/{id_incidente}/evidencias",
            token=cliente_token,
            data={"id_tipo_evidencia": str(tipos["texto"]), "id_incidente": str(id_incidente)},
            files={"archivo": ("nota.txt", b"Seed evidencia texto", "text/plain")},
            expected=[201],
        )

    # imagen
    if "imagen" in tipos:
        _req(
            "POST",
            f"/incidencias/{id_incidente}/evidencias",
            token=cliente_token,
            data={"id_tipo_evidencia": str(tipos["imagen"]), "id_incidente": str(id_incidente)},
            files={"archivo": ("foto.png", PNG_1X1, "image/png")},
            expected=[201],
        )

    # audio
    if "audio" in tipos:
        _req(
            "POST",
            f"/incidencias/{id_incidente}/evidencias",
            token=cliente_token,
            data={"id_tipo_evidencia": str(tipos["audio"]), "id_incidente": str(id_incidente)},
            files={"archivo": ("audio.wav", WAV_EMPTY, "audio/wav")},
            expected=[201],
        )


def crear_pago(cliente_token: str, id_incidente: int) -> None:
    # id_metodo_pago=1 (tarjeta) por defecto
    payload = {"id_incidente": id_incidente, "id_metodo_pago": 1, "monto_total": 25.0}
    try:
        _req("POST", "/pagos/crear-intent", token=cliente_token, json_body=payload, expected=[200])
    except ApiError as exc:
        print(f"[WARN] Pago no creado: {exc}")


def main() -> None:
    print(f"BASE_URL: {BASE_URL}")

    try:
        admin_token = login_admin()
    except ApiError as exc:
        raise SystemExit(
            "No se pudo autenticar admin. "
            "Asegura que ADMIN_EMAIL/ADMIN_PASSWORD existen en la API. "
            f"Detalle: {exc}"
        )

    taller_token = ensure_taller(admin_token)

    # Crear tecnicos (1 por estado activo)
    tecnicos: List[Dict[str, Any]] = []
    for i in range(1, 4):
        email = f"tecnico.seed{i}@taller.com"
        nombre = f"Tecnico Seed {i}"
        password = f"TecnicoSeed{i}123!"
        tecnico = ensure_tecnico(taller_token, nombre, email, password)
        tecnico["password"] = password
        tecnicos.append(tecnico)

    # Crear clientes (1 por escenario)
    clientes = []
    for i in range(len(SCENARIOS)):
        email = f"cliente.seed{i+1}@demo.com"
        password = "ClienteSeed123!"
        nombre = f"Cliente Seed {i+1}"
        token = ensure_cliente(email, password, nombre)
        clientes.append({"email": email, "password": password, "token": token})

    # Crear incidentes y transicionar estados
    for idx, scenario in enumerate(SCENARIOS):
        cliente = clientes[idx]
        lat, lng = COORDS[idx % len(COORDS)]

        vehiculo = crear_vehiculo(cliente["token"], placa=f"SCZ-{idx+1:03d}")
        incidente = crear_incidente(
            cliente["token"],
            vehiculo["id_vehiculo"],
            lat,
            lng,
            descripcion=f"[SEED] Incidente {scenario['estado_asignacion']}",
        )
        id_incidente = incidente["id_incidente"]

        # IA para generar categoria/prioridad + crear asignacion
        analizar_ia(cliente["token"], id_incidente)
        time.sleep(1)

        asignacion = obtener_asignacion_taller(taller_token, id_incidente)
        id_asignacion = asignacion["id_asignacion"]

        estado = scenario["estado_asignacion"]
        if estado == "pendiente":
            pass
        elif estado == "rechazada":
            rechazar_asignacion(taller_token, id_asignacion)
        elif estado == "aceptada":
            aceptar_asignacion(taller_token, id_asignacion, tecnicos[0]["id_usuario"])
        elif estado == "en_camino":
            aceptar_asignacion(taller_token, id_asignacion, tecnicos[1]["id_usuario"])
            tecnico_token = login_tecnico(tecnicos[1]["email"], tecnicos[1]["password"])
            actualizar_ubicacion(tecnico_token, lat, lng)
            iniciar_viaje(tecnico_token, id_asignacion, lat, lng)
        elif estado == "completada":
            aceptar_asignacion(taller_token, id_asignacion, tecnicos[2]["id_usuario"])
            tecnico_token = login_tecnico(tecnicos[2]["email"], tecnicos[2]["password"])
            actualizar_ubicacion(tecnico_token, lat, lng)
            iniciar_viaje(tecnico_token, id_asignacion, lat, lng)
            completar_servicio(tecnico_token, id_asignacion)

        # Extras: evidencias, mensajes, pagos
        try:
            subir_evidencias(cliente["token"], id_incidente)
        except ApiError as exc:
            print(f"[WARN] Evidencias no creadas: {exc}")

        try:
            enviar_mensajes(cliente["token"], taller_token, id_incidente)
        except ApiError as exc:
            print(f"[WARN] Mensajes no creados: {exc}")

        crear_pago(cliente["token"], id_incidente)

        print(f"OK escenario {estado} -> incidente {id_incidente} / asignacion {id_asignacion}")

    print("\nSeed via API completado.")


if __name__ == "__main__":
    main()
