#!/usr/bin/env python
"""Script de pruebas completas para refactorización de técnicos"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_health():
    """Verificar que servidor esté activo"""
    print("\n🔍 TEST 1: Health Check")
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✅ Servidor respondiendo: {resp.status_code}")
        return True
    except Exception as e:
        print(f"❌ Servidor no disponible: {e}")
        return False

def test_crear_tecnico(taller_token):
    """Crear un usuario técnico vinculado a taller"""
    print("\n🔍 TEST 2: Crear Técnico (POST /mi-taller/tecnicos)")
    
    tecnico_data = {
        "nombre": "Juan Pérez Técnico",
        "email": f"tecnico.juan.{int(datetime.now().timestamp())}@taller.com",
        "password": "TecnicoPassword123!",
        "telefono": "+57 310 555 1234"
    }
    
    headers = {
        "Authorization": f"Bearer {taller_token}",
        "Content-Type": "application/json"
    }
    
    try:
        resp = requests.post(
            f"{BASE_URL}/talleres/mi-taller/tecnicos",
            json=tecnico_data,
            headers=headers,
            timeout=10
        )
        
        if resp.status_code == 201:
            data = resp.json()
            print(f"✅ Técnico creado exitosamente")
            print(f"   ID Usuario Taller: {data['id_usuario_taller']}")
            print(f"   ID Usuario: {data['id_usuario']}")
            print(f"   Nombre: {data['nombre']}")
            print(f"   Email: {data['email']}")
            print(f"   Disponible: {data['disponible']}")
            return {
                "email": tecnico_data["email"],
                "password": tecnico_data["password"],
                "id_usuario": data["id_usuario"],
                "id_usuario_taller": data["id_usuario_taller"]
            }
        else:
            print(f"❌ Error {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        print(f"❌ Excepción: {e}")
        return None

def test_login_taller():
    """Login de un taller para obtener token"""
    print("\n🔍 TEST 0: Login Taller (obtener token para crear técnico)")
    
    login_data = {
        "email": "taller.excelente@example.com",
        "password": "taller123"
    }
    
    try:
        resp = requests.post(
            f"{BASE_URL}/talleres/login",
            json=login_data,
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("access_token")
            print(f"✅ Login taller exitoso")
            print(f"   Token: {token[:50]}...")
            return token
        else:
            print(f"❌ Login fallido {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        print(f"❌ Excepción en login: {e}")
        return None

def test_login_tecnico(email, password):
    """Login de técnico para obtener token"""
    print(f"\n🔍 TEST 3: Login Técnico (POST /usuarios/login)")
    
    login_data = {
        "email": email,
        "password": password
    }
    
    try:
        resp = requests.post(
            f"{BASE_URL}/usuarios/login",
            json=login_data,
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("access_token")
            print(f"✅ Login técnico exitoso")
            print(f"   Token: {token[:50]}...")
            print(f"   Token Type: {data.get('token_type')}")
            return token
        else:
            print(f"❌ Login fallido {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        print(f"❌ Excepción: {e}")
        return None

def test_listar_tecnicos(taller_token):
    """Listar técnicos del taller"""
    print("\n🔍 TEST 4: Listar Técnicos (GET /mi-taller/tecnicos)")
    
    headers = {"Authorization": f"Bearer {taller_token}"}
    
    try:
        resp = requests.get(
            f"{BASE_URL}/talleres/mi-taller/tecnicos",
            headers=headers,
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Técnicos listados: {len(data)} registros")
            for tech in data:
                print(f"   - {tech['nombre']} ({tech['email']}) - Disponible: {tech['disponible']}")
            return data
        else:
            print(f"❌ Error {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        print(f"❌ Excepción: {e}")
        return None

def test_obtener_tecnico(taller_token, id_usuario_taller):
    """Obtener detalles de un técnico"""
    print(f"\n🔍 TEST 5: Obtener Técnico (GET /mi-taller/tecnicos/{id_usuario_taller})")
    
    headers = {"Authorization": f"Bearer {taller_token}"}
    
    try:
        resp = requests.get(
            f"{BASE_URL}/talleres/mi-taller/tecnicos/{id_usuario_taller}",
            headers=headers,
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Técnico encontrado")
            print(f"   ID Usuario Taller: {data['id_usuario_taller']}")
            print(f"   Nombre: {data['nombre']}")
            print(f"   Email: {data['email']}")
            print(f"   Disponible: {data['disponible']}")
            print(f"   Activo: {data['activo']}")
            return data
        else:
            print(f"❌ Error {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        print(f"❌ Excepción: {e}")
        return None

def test_actualizar_tecnico(taller_token, id_usuario_taller):
    """Actualizar datos de un técnico"""
    print(f"\n🔍 TEST 6: Actualizar Técnico (PUT /mi-taller/tecnicos/{id_usuario_taller})")
    
    update_data = {
        "disponible": False,
        "latitud": 4.7110,
        "longitud": -74.0721
    }
    
    headers = {
        "Authorization": f"Bearer {taller_token}",
        "Content-Type": "application/json"
    }
    
    try:
        resp = requests.put(
            f"{BASE_URL}/talleres/mi-taller/tecnicos/{id_usuario_taller}",
            json=update_data,
            headers=headers,
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Técnico actualizado")
            print(f"   Disponible: {data['disponible']}")
            print(f"   Latitud: {data['latitud']}")
            print(f"   Longitud: {data['longitud']}")
            return data
        else:
            print(f"❌ Error {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        print(f"❌ Excepción: {e}")
        return None

def test_asignacion_actual(tecnico_token):
    """Obtener asignación actual del técnico"""
    print(f"\n🔍 TEST 7: Obtener Asignación Actual (GET /tecnicos/asignacion-actual)")
    
    headers = {"Authorization": f"Bearer {tecnico_token}"}
    
    try:
        resp = requests.get(
            f"{BASE_URL}/tecnicos/asignacion-actual",
            headers=headers,
            timeout=10
        )
        
        if resp.status_code == 404:
            print(f"✅ Sin asignaciones activas (esperado): {resp.json()['detail']}")
            return None
        elif resp.status_code == 200:
            data = resp.json()
            print(f"✅ Asignación encontrada")
            print(f"   ID: {data.get('id_asignacion')}")
            return data
        else:
            print(f"❌ Error {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        print(f"❌ Excepción: {e}")
        return None

def run_all_tests():
    """Ejecutar todas las pruebas"""
    print("=" * 70)
    print("🧪 INICIANDO SUITE DE PRUEBAS - REFACTORIZACIÓN TÉCNICOS")
    print("=" * 70)
    
    # 1. Health check
    if not test_health():
        print("\n❌ SERVIDOR NO DISPONIBLE. Abortar pruebas.")
        return
    
    # 2. Login taller
    taller_token = test_login_taller()
    if not taller_token:
        print("\n❌ No se pudo obtener token del taller. Abortar pruebas.")
        return
    
    # 3. Crear técnico
    tecnico_info = test_crear_tecnico(taller_token)
    if not tecnico_info:
        print("\n❌ No se pudo crear técnico. Abortar pruebas.")
        return
    
    # 4. Login técnico
    tecnico_token = test_login_tecnico(tecnico_info["email"], tecnico_info["password"])
    if not tecnico_token:
        print("\n❌ No se pudo hacer login del técnico.")
    
    # 5. Listar técnicos
    test_listar_tecnicos(taller_token)
    
    # 6. Obtener técnico
    test_obtener_tecnico(taller_token, tecnico_info["id_usuario_taller"])
    
    # 7. Actualizar técnico
    test_actualizar_tecnico(taller_token, tecnico_info["id_usuario_taller"])
    
    # 8. Obtener asignación actual (si existe token de técnico)
    if tecnico_token:
        test_asignacion_actual(tecnico_token)
    
    print("\n" + "=" * 70)
    print("✅ SUITE DE PRUEBAS COMPLETADA")
    print("=" * 70)

if __name__ == "__main__":
    run_all_tests()
