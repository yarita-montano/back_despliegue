#!/usr/bin/env python
"""
Script para validar que un técnico NO puede tener 2 asignaciones activas simultáneamente.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_restriccion_una_asignacion():
    """Verificar que un técnico no puede tener 2 asignaciones activas"""
    print("\n" + "="*80)
    print("🧪 TEST: UN TÉCNICO = UNA ASIGNACIÓN A LA VEZ")
    print("="*80)
    
    # 1. Login del taller
    print("\n1️⃣  Login del taller...")
    resp = requests.post(
        f"{BASE_URL}/talleres/login",
        json={"email": "taller.excelente@example.com", "password": "taller123"}
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    taller_token = resp.json()["access_token"]
    print("✅ Taller autenticado")
    
    # 2. Crear 2 técnicos
    print("\n2️⃣  Creando 2 técnicos...")
    headers = {"Authorization": f"Bearer {taller_token}"}
    
    tecnico1_data = {
        "nombre": "Técnico Uno",
        "email": f"tecnico.uno.{int(__import__('time').time())}@test.com",
        "password": "TecnicoPassword123!",
        "telefono": "+57 300 111 1111"
    }
    
    resp1 = requests.post(
        f"{BASE_URL}/talleres/mi-taller/tecnicos",
        json=tecnico1_data,
        headers=headers
    )
    assert resp1.status_code == 201, f"Crear técnico 1 failed: {resp1.text}"
    tecnico1_id = resp1.json()["id_usuario"]
    print(f"✅ Técnico 1 creado (ID: {tecnico1_id})")
    
    # 3. Obtener 2 asignaciones pendientes (necesitamos 2 incidentes)
    print("\n3️⃣  Obteniendo asignaciones pendientes...")
    
    resp_asignaciones = requests.get(
        f"{BASE_URL}/talleres/mi-taller/asignaciones",
        headers=headers
    )
    assert resp_asignaciones.status_code == 200, f"Get asignaciones failed: {resp_asignaciones.text}"
    
    asignaciones = resp_asignaciones.json()
    asignaciones_pendientes = [a for a in asignaciones if a.get("id_estado_asignacion") == 1]
    
    if len(asignaciones_pendientes) < 2:
        print(f"❌ No hay suficientes asignaciones pendientes (necesitamos 2, tenemos {len(asignaciones_pendientes)})")
        print("   Para este test necesitas crear 2 incidentes desde clientes.")
        return False
    
    asignacion_1 = asignaciones_pendientes[0]
    asignacion_2 = asignaciones_pendientes[1]
    
    print(f"✅ Asignación 1: ID {asignacion_1['id_asignacion']}")
    print(f"✅ Asignación 2: ID {asignacion_2['id_asignacion']}")
    
    # 4. Aceptar la primera asignación CON el técnico
    print(f"\n4️⃣  Aceptando asignación 1 CON técnico {tecnico1_id}...")
    
    resp_accept1 = requests.put(
        f"{BASE_URL}/talleres/mi-taller/asignaciones/{asignacion_1['id_asignacion']}/aceptar",
        json={
            "id_usuario": tecnico1_id,
            "eta_minutos": 20,
            "nota": "Primera asignación"
        },
        headers=headers
    )
    
    assert resp_accept1.status_code == 200, f"Aceptar asignación 1 failed: {resp_accept1.text}"
    print(f"✅ Asignación 1 aceptada - Técnico {tecnico1_id} asignado")
    print(f"   Estado: {resp_accept1.json()['id_estado_asignacion']} (aceptada)")
    
    # 5. INTENTA aceptar la segunda asignación CON el MISMO técnico
    print(f"\n5️⃣  INTENTANDO aceptar asignación 2 CON EL MISMO técnico {tecnico1_id}...")
    print("   (Esto DEBE fallar con error 409 Conflict)")
    
    resp_accept2 = requests.put(
        f"{BASE_URL}/talleres/mi-taller/asignaciones/{asignacion_2['id_asignacion']}/aceptar",
        json={
            "id_usuario": tecnico1_id,
            "eta_minutos": 25,
            "nota": "Segunda asignación (DEBE FALLAR)"
        },
        headers=headers
    )
    
    if resp_accept2.status_code == 409:
        print(f"✅✅✅ VALIDACIÓN CORRECTA ✅✅✅")
        print(f"   Status Code: {resp_accept2.status_code} (Conflict)")
        print(f"   Error: {resp_accept2.json()['detail']}")
        return True
    else:
        print(f"❌ ERROR: Se aceptó la asignación cuando NO debería")
        print(f"   Status Code: {resp_accept2.status_code}")
        print(f"   Response: {resp_accept2.json()}")
        return False

def test_tecnico_ve_asignacion():
    """Verificar que el técnico puede ver su asignación actual"""
    print("\n" + "="*80)
    print("🧪 TEST: TÉCNICO VE SU ASIGNACIÓN ACTUAL")
    print("="*80)
    
    # Crear técnico y obtener su token
    print("\n1️⃣  Creando técnico de prueba...")
    
    tecnico_email = f"test.tecnico.{int(__import__('time').time())}@test.com"
    tecnico_password = "TestPassword123!"
    
    # Registrar como usuario rol=3
    from sqlalchemy import create_engine, text
    from app.core.config import get_settings
    from app.core.security import hash_password
    
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL)
    
    password_hash = hash_password(tecnico_password)
    
    with engine.connect() as conn:
        conn.execute(text('''
            INSERT INTO usuario (id_rol, nombre, email, password_hash, activo)
            VALUES (:id_rol, :nombre, :email, :password_hash, :activo)
        '''), {
            'id_rol': 3,
            'nombre': 'Test Técnico',
            'email': tecnico_email,
            'password_hash': password_hash,
            'activo': True
        })
        conn.commit()
    
    # Login como técnico
    print("2️⃣  Login como técnico...")
    resp_login = requests.post(
        f"{BASE_URL}/usuarios/login",
        json={"email": tecnico_email, "password": tecnico_password}
    )
    assert resp_login.status_code == 200, f"Login failed: {resp_login.text}"
    tecnico_token = resp_login.json()["access_token"]
    print("✅ Técnico autenticado")
    
    # Ver asignación actual
    print("3️⃣  GET /tecnicos/asignacion-actual...")
    resp = requests.get(
        f"{BASE_URL}/tecnicos/asignacion-actual",
        headers={"Authorization": f"Bearer {tecnico_token}"}
    )
    
    if resp.status_code == 404:
        print(f"✅ Correcto: Sin asignaciones activas")
        print(f"   Mensaje: {resp.json()['detail']}")
        return True
    elif resp.status_code == 200:
        asignacion = resp.json()
        print(f"✅ El técnico tiene una asignación activa:")
        print(f"   ID Asignación: {asignacion.get('id_asignacion')}")
        print(f"   Cliente: {asignacion.get('cliente', {}).get('nombre')}")
        print(f"   Vehiculo: {asignacion.get('vehiculo', {}).get('placa')}")
        print(f"   ETA: {asignacion.get('eta_minutos')} minutos")
        return True
    else:
        print(f"❌ Error inesperado: {resp.status_code}")
        print(f"   Response: {resp.text}")
        return False

if __name__ == "__main__":
    print("\n")
    print("╔════════════════════════════════════════════════════════════════════════════╗")
    print("║         VALIDACIÓN DEL CICLO DE ASIGNACIÓN DE TÉCNICOS                    ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝")
    
    try:
        # Test 1: Restricción de una asignación a la vez
        result1 = test_restriccion_una_asignacion()
        
        # Test 2: Técnico ve su asignación
        result2 = test_tecnico_ve_asignacion()
        
        print("\n" + "="*80)
        print("📊 RESULTADOS FINALES")
        print("="*80)
        print(f"Test 1 (Restricción una asignación): {'✅ PASÓ' if result1 else '❌ FALLÓ'}")
        print(f"Test 2 (Técnico ve asignación):      {'✅ PASÓ' if result2 else '❌ FALLÓ'}")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO: {e}")
        import traceback
        traceback.print_exc()
