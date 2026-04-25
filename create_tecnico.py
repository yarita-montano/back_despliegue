"""
Script para crear un técnico como usuario con rol=3 (Técnico).
El técnico se autentica en el endpoint POST /usuarios/login con tipo JWT "tecnico".
"""
import psycopg2
from argon2 import PasswordHasher

ph = PasswordHasher()

try:
    conn = psycopg2.connect('postgresql://postgres:12345678@localhost:5432/emergencias_vehiculares')
    conn.autocommit = True
    cur = conn.cursor()

    print("=" * 70)
    print("CREANDO TÉCNICO COMO USUARIO CON ROL=3")
    print("=" * 70)

    # Datos del técnico
    id_taller = 1  # Taller Excelente
    nombre_tecnico = 'Juan Pérez'
    email_tecnico = 'tecnico.juan@taller.com'
    password_tecnico = 'tecnico123!'
    telefono = '+57 3105551111'
    id_rol = 3  # Rol de Técnico

    # Hashear contraseña
    password_hash = ph.hash(password_tecnico)

    # Crear el usuario técnico
    cur.execute("""
        INSERT INTO usuario (
            id_rol,
            nombre,
            email,
            telefono,
            password_hash,
            activo
        ) VALUES (%s, %s, %s, %s, %s, TRUE)
        ON CONFLICT (email) DO UPDATE SET 
            password_hash = EXCLUDED.password_hash,
            activo = TRUE
        RETURNING id_usuario;
    """, (id_rol, nombre_tecnico, email_tecnico, telefono, password_hash))

    id_usuario = cur.fetchone()[0]

    print(f"\n✅ TÉCNICO CREADO EXITOSAMENTE COMO USUARIO")
    print(f"   ID Usuario: {id_usuario}")
    print(f"   Nombre: {nombre_tecnico}")
    print(f"   Email: {email_tecnico}")
    print(f"   Rol: Técnico (3)")
    print(f"   Teléfono: {telefono}")
    print(f"   Activo: SÍ")

    print("\n" + "=" * 70)
    print("CREDENCIALES PARA LOGIN EN FLUTTER")
    print("=" * 70)
    print(f"\n  📱 TÉCNICO (App Móvil Flutter)")
    print(f"     Email:    {email_tecnico}")
    print(f"     Password: {password_tecnico}")
    print(f"     Endpoint: POST /tecnicos/login")

    print("\n" + "=" * 70)
    print("CÓDIGO DART PARA FLUTTER")
    print("=" * 70)
    print(f"""
    // En TecnicoLoginScreen o TecnicoAuthService
    final response = await http.post(
      Uri.parse('http://10.0.2.2:8000/tecnicos/login'),
      headers: {{'Content-Type': 'application/json'}},
      body: jsonEncode({{
        'email': '{email_tecnico}',
        'password': '{password_tecnico}'
      }}),
    );

    if (response.statusCode == 200) {{
      final data = jsonDecode(response.body);
      final token = data['access_token'];
      // Guardar token en FlutterSecureStorage
    }}
    """)

    print("\n" + "=" * 70)
    print("VERIFICACIÓN")
    print("=" * 70)
    print("""
  1. El técnico puede hacer login en POST /tecnicos/login
  2. Obtiene un token con tipo: "tecnico"
  3. Usa ese token en endpoints como:
     - GET /tecnicos/asignacion-actual
     - PUT /tecnicos/mis-asignaciones/{id}/iniciar-viaje
     - PUT /tecnicos/mis-asignaciones/{id}/completar
  4. NO puede usar token de usuario en endpoints de técnico (401 Unauthorized)
    """)

    print("\n✨ LISTO - El técnico puede hacer login ahora\n")

    conn.close()

except Exception as e:
    print(f"\n❌ ERROR: {e}\n")
    import traceback
    traceback.print_exc()
