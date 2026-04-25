"""
Script para crear un usuario técnico (rol=3) con credenciales de login.

Los técnicos son USUARIOS (tabla usuario, id_rol=3).
Se autentican por POST /usuarios/login con email + password.
Luego acceden a endpoints de técnico: GET /tecnicos/asignacion-actual, etc.
"""
import psycopg2
from argon2 import PasswordHasher

ph = PasswordHasher()

try:
    conn = psycopg2.connect('postgresql://postgres:12345678@localhost:5432/emergencias_vehiculares')
    conn.autocommit = True
    cur = conn.cursor()

    print("=" * 80)
    print("CREANDO USUARIO TÉCNICO (rol=3) CON CREDENCIALES DE LOGIN")
    print("=" * 80)

    # 1. Verificar que rol=3 existe en la tabla rol
    cur.execute("SELECT id_rol FROM rol WHERE id_rol = 3;")
    if not cur.fetchone():
        print("❌ ERROR: rol id_rol=3 no existe en tabla 'rol'")
        print("   Necesitas ejecutar init_roles.sql primero")
        conn.close()
        exit(1)

    # 2. Crear usuario técnico en tabla usuario (id_rol=3)
    email_tecnico = 'tecnico.juan@taller.com'
    password_tecnico = 'tecnico123!'
    nombre_tecnico = 'Juan Pérez'
    telefono_tecnico = '+57 3105551111'
    
    password_hash = ph.hash(password_tecnico)
    
    print(f"\n1️⃣  Creando usuario técnico...")
    print(f"   Nombre:    {nombre_tecnico}")
    print(f"   Email:     {email_tecnico}")
    print(f"   Teléfono:  {telefono_tecnico}")
    print(f"   Rol:       3 (técnico)")
    
    cur.execute("""
        INSERT INTO usuario (id_rol, nombre, email, telefono, password_hash, activo)
        VALUES (3, %s, %s, %s, %s, TRUE)
        ON CONFLICT (email) DO UPDATE 
        SET password_hash = EXCLUDED.password_hash,
            activo = TRUE
        RETURNING id_usuario;
    """, (nombre_tecnico, email_tecnico, telefono_tecnico, password_hash))
    
    id_usuario_tecnico = cur.fetchone()[0]
    print(f"   ✅ Usuario técnico creado: ID={id_usuario_tecnico}")

    # 3. Mostrar credenciales y flujo correcto
    print("\n" + "=" * 80)
    print("✅ CREDENCIALES PARA LOGIN DEL TÉCNICO EN APP FLUTTER")
    print("=" * 80)
    print()
    print("  📱 APP FLUTTER - TÉCNICO")
    print(f"     Email:    {email_tecnico}")
    print(f"     Password: {password_tecnico}")
    print()
    print("     ✅ ENDPOINT CORRECTO:")
    print("        POST /usuarios/login")
    print()
    print("  Código Dart (Flutter):")
    print(f"""
    final response = await http.post(
      Uri.parse('http://10.0.2.2:8000/usuarios/login'),
      headers: {{'Content-Type': 'application/json'}},
      body: jsonEncode({{
        'email': '{email_tecnico}',
        'password': '{password_tecnico}'
      }}),
    );
    
    // Respuesta:
    // {{
    //   "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    //   "token_type": "bearer",
    //   "usuario": {{
    //     "id_usuario": {id_usuario_tecnico},
    //     "id_rol": 3,
    //     "nombre": "{nombre_tecnico}",
    //     "email": "{email_tecnico}",
    //     ...
    //   }}
    // }}
    """)
    print()
    print("=" * 80)

    # 4. Verificación final
    print("\\n4️⃣  Verificación final...")
    cur.execute("SELECT id_usuario, nombre, email, activo FROM usuario WHERE id_rol = 3 ORDER BY id_usuario;")
    
    usuarios_tecnicos = cur.fetchall()
    print(f"\\n   ✅ Usuarios técnicos (rol=3) en la base de datos:")
    for id_u, nom, email, activo in usuarios_tecnicos:
        estado = "🟢 ACTIVO" if activo else "🔴 INACTIVO"
        print(f"      • {id_u}: {nom} ({email}) {estado}")

    print("\\n" + "=" * 80)
    print("✅ SEED COMPLETADO - TÉCNICO LISTO PARA LOGIN")
    print("=" * 80)
    print("\\n📋 FLUJO DEL TÉCNICO:")
    print("   1. App Flutter: POST /usuarios/login (credenciales)")
    print("   2. Recibe JWT token + id_usuario")
    print("   3. GET /tecnicos/asignacion-actual (obtiene asignación)")
    print("   4. PUT /tecnicos/mis-asignaciones/{id}/iniciar-viaje")
    print("   5. PUT /tecnicos/mis-asignaciones/{id}/completar")
    print("=" * 80 + "\\n")

    conn.close()

except psycopg2.IntegrityError as e:
    print(f"❌ Error de integridad (¿email duplicado?): {e}")
    conn.rollback()
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
