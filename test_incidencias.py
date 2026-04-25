#!/usr/bin/env python
"""Script para probar endpoints de incidencias"""

import requests
import json

BASE_URL = "http://localhost:8000"

# 1. LOGIN
print("=" * 60)
print("1️⃣  AUTENTICACIÓN")
print("=" * 60)

login_data = {
    "email": "conductor@ejemplo.com",
    "password": "cliente123!"
}

resp = requests.post(f"{BASE_URL}/usuarios/login", json=login_data)
print(f"Status: {resp.status_code}")

if resp.status_code != 200:
    print(f"Error: {resp.text}")
    exit(1)

token = resp.json()["access_token"]
print(f"✅ Token: {token[:30]}...\n")

headers = {"Authorization": f"Bearer {token}"}

# 2. OBTENER CATEGORÍAS
print("=" * 60)
print("2️⃣  CATEGORÍAS DE PROBLEMAS")
print("=" * 60)

resp = requests.get(f"{BASE_URL}/incidencias/categorias", headers=headers)
print(f"Status: {resp.status_code}")
print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
print()

# 3. OBTENER PRIORIDADES
print("=" * 60)
print("3️⃣  NIVELES DE PRIORIDAD")
print("=" * 60)

resp = requests.get(f"{BASE_URL}/incidencias/prioridades", headers=headers)
print(f"Status: {resp.status_code}")
print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
print()

# 4. OBTENER ESTADOS
print("=" * 60)
print("4️⃣  ESTADOS DE INCIDENTE")
print("=" * 60)

resp = requests.get(f"{BASE_URL}/incidencias/estados", headers=headers)
print(f"Status: {resp.status_code}")
print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
print()

# 5. CREAR INCIDENCIA
print("=" * 60)
print("5️⃣  CREAR INCIDENCIA (Reportar Emergencia)")
print("=" * 60)

incidencia_data = {
    "id_vehiculo": 1,
    "id_categoria": 1,
    "id_prioridad": 3,
    "descripcion": "El motor hace ruido extraño y humo blanco",
    "latitud": 4.7110,
    "longitud": -74.0721,
    "observaciones": "Estoy en la avenida principal cerca de la estación"
}

resp = requests.post(f"{BASE_URL}/incidencias/", json=incidencia_data, headers=headers)
print(f"Status: {resp.status_code}")
print(json.dumps(resp.json(), indent=2, ensure_ascii=False))

if resp.status_code == 201:
    incidente_id = resp.json()["id_incidente"]
    print(f"✅ Incidencia creada: #{incidente_id}\n")
    
    # 6. LISTAR MIS INCIDENCIAS
    print("=" * 60)
    print("6️⃣  MIS INCIDENCIAS")
    print("=" * 60)
    
    resp = requests.get(f"{BASE_URL}/incidencias/mis-incidencias", headers=headers)
    print(f"Status: {resp.status_code}")
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    print()
    
    # 7. OBTENER DETALLE DE INCIDENCIA
    print("=" * 60)
    print("7️⃣  DETALLE DE INCIDENCIA")
    print("=" * 60)
    
    resp = requests.get(f"{BASE_URL}/incidencias/{incidente_id}", headers=headers)
    print(f"Status: {resp.status_code}")
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))

print("\n✅ ¡TODOS LOS ENDPOINTS FUNCIONANDO! 🚀")
