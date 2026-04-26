"""
Seed completo: catálogos + usuarios de prueba + taller + técnicos (como usuarios rol=3).

Uso:
    python seed_usuarios_temp.py

Requisito: tener la API arrancada al menos una vez para que create_all cree las tablas,
           o ejecutar primero: uvicorn app.main:app --reload (luego Ctrl+C).
"""
import os
import psycopg2
from argon2 import PasswordHasher
from dotenv import load_dotenv

load_dotenv()

ph = PasswordHasher()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:12345678@localhost:5432/emergencias_vehiculares",
)

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cur = conn.cursor()

# ──────────────────────────────────────────────────────────────────────────────
# 1. LIMPIAR — TRUNCATE CASCADE reinicia secuencias y respeta FK automáticamente
# ──────────────────────────────────────────────────────────────────────────────
print("Limpiando datos previos...")

TABLAS_TRUNCATE = [
    "historial_estado_asignacion",
    "historial_estado_incidente",
    "candidato_asignacion",
    "asignacion",
    "evidencia",
    "incidente",
    "vehiculo",
    "notificacion",
    "mensaje",
    "metrica",
    "pago",
    "usuario_taller",
    "taller_servicio",
    "usuario",
    "taller",
    "rol",
    "estado_incidente",
    "categoria_problema",
    "prioridad",
    "estado_asignacion",
    "tipo_evidencia",
    "metodo_pago",
    "estado_pago",
]

for tabla in TABLAS_TRUNCATE:
    try:
        cur.execute(f"TRUNCATE TABLE {tabla} RESTART IDENTITY CASCADE;")
    except Exception:
        pass  # tabla no existe aún (primera ejecución)

print("✅ Tablas limpiadas (secuencias reiniciadas)")

# ──────────────────────────────────────────────────────────────────────────────
# 2. CATÁLOGOS
# ──────────────────────────────────────────────────────────────────────────────
cur.execute("""
    INSERT INTO rol (nombre) VALUES
        ('cliente'), ('taller'), ('tecnico'), ('admin');
""")

cur.execute("""
    INSERT INTO estado_incidente (nombre, descripcion) VALUES
        ('pendiente',   'Reportado, sin asignar'),
        ('en_proceso',  'Taller asignado, en atención'),
        ('atendido',    'Resuelto'),
        ('cancelado',   'Cancelado por el usuario');
""")

cur.execute("""
    INSERT INTO categoria_problema (nombre, descripcion) VALUES
        ('bateria',  'Problemas de batería'),
        ('llanta',   'Llanta desinflada o reventada'),
        ('choque',   'Colisión o accidente'),
        ('motor',    'Fallas del motor'),
        ('llaves',   'Llaves perdidas o bloqueadas'),
        ('otros',    'Otros problemas'),
        ('incierto', 'Sin clasificar');
""")

cur.execute("""
    INSERT INTO prioridad (nivel, orden) VALUES
        ('baja', 1), ('media', 2), ('alta', 3), ('critica', 4);
""")

cur.execute("""
    INSERT INTO estado_asignacion (nombre) VALUES
        ('pendiente'), ('aceptada'), ('rechazada'), ('en_camino'), ('completada');
""")

cur.execute("""
    INSERT INTO tipo_evidencia (nombre) VALUES
        ('imagen'), ('audio'), ('texto');
""")

cur.execute("""
    INSERT INTO metodo_pago (nombre) VALUES
        ('tarjeta'), ('transferencia'), ('efectivo'), ('qr');
""")

cur.execute("""
    INSERT INTO estado_pago (nombre) VALUES
        ('pendiente'), ('procesando'), ('completado'), ('fallido'), ('reembolsado');
""")

print("✅ Catálogos creados")

# ──────────────────────────────────────────────────────────────────────────────
# 3. USUARIOS BASE (cliente + admin)
# ──────────────────────────────────────────────────────────────────────────────
cur.execute("""
    INSERT INTO usuario (id_rol, nombre, email, telefono, password_hash, activo)
    VALUES (1, 'Juan Conductor', 'conductor@ejemplo.com', '+57 3001234567', %s, TRUE);
""", (ph.hash('cliente123!'),))

cur.execute("""
    INSERT INTO usuario (id_rol, nombre, email, telefono, password_hash, activo)
    VALUES (4, 'Administrador Sistema', 'admin@plataforma.com', '+57 3009999999', %s, TRUE);
""", (ph.hash('admin123!'),))

print("✅ Usuarios base creados (cliente + admin)")

# ──────────────────────────────────────────────────────────────────────────────
# 4. TALLER DE PRUEBA
# ──────────────────────────────────────────────────────────────────────────────
cur.execute("""
    INSERT INTO taller (nombre, email, telefono, password_hash,
                        latitud, longitud, direccion,
                        capacidad_max, disponible, activo, verificado)
    VALUES (
        'Taller Excelente',
        'gerente@tallerexcelente.com',
        '+57 3105552222',
        %s,
        -17.8454274, -63.1561987,
        'Av. Cristo Redentor #500, Santa Cruz',
        5, TRUE, TRUE, TRUE
    );
""", (ph.hash('taller123!'),))

print("✅ Taller creado")

# ──────────────────────────────────────────────────────────────────────────────
# 5. TÉCNICOS — usuarios con id_rol=3 vinculados al taller via usuario_taller
# ──────────────────────────────────────────────────────────────────────────────
cur.execute("SELECT id_taller FROM taller WHERE email = 'gerente@tallerexcelente.com';")
id_taller = cur.fetchone()[0]

tecnicos = [
    ("Juan Pérez - Técnico",   "tecnico.juan@taller.com",   "+57 3105551111", "tecnico123!"),
    ("Carlos Gómez - Técnico", "tecnico.carlos@taller.com", "+57 3105551112", "tecnico456!"),
]

for nombre, email, telefono, password in tecnicos:
    cur.execute("""
        INSERT INTO usuario (id_rol, nombre, email, telefono, password_hash, activo)
        VALUES (3, %s, %s, %s, %s, TRUE)
        RETURNING id_usuario;
    """, (nombre, email, telefono, ph.hash(password)))
    id_usuario = cur.fetchone()[0]

    cur.execute("""
        INSERT INTO usuario_taller (id_usuario, id_taller, disponible, activo)
        VALUES (%s, %s, TRUE, TRUE);
    """, (id_usuario, id_taller))

print("✅ Técnicos creados (usuarios rol=3 + usuario_taller)")

# ──────────────────────────────────────────────────────────────────────────────
# 6. RESUMEN
# ──────────────────────────────────────────────────────────────────────────────
print('\n' + '=' * 70)
print('RESUMEN DE SEED')
print('=' * 70)

TABLAS_RESUMEN = [
    'rol', 'estado_incidente', 'categoria_problema', 'prioridad',
    'estado_asignacion', 'tipo_evidencia', 'metodo_pago', 'estado_pago',
    'usuario', 'taller', 'usuario_taller',
]

for tabla in TABLAS_RESUMEN:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {tabla};")
        count = cur.fetchone()[0]
        print(f"  {tabla:25s} → {count} registros")
    except Exception:
        pass

print('=' * 70)
print('\n📱 CREDENCIALES DE LOGIN\n')
print('  🔵 CLIENTE (App Móvil Flutter)')
print('     Email:    conductor@ejemplo.com')
print('     Password: cliente123!')
print('     Endpoint: POST /usuarios/login')
print()
print('  🔴 ADMIN (Panel Web Angular)')
print('     Email:    admin@plataforma.com')
print('     Password: admin123!')
print('     Endpoint: POST /usuarios/login')
print()
print('  🟡 TALLER (Panel Web Angular)')
print('     Email:    gerente@tallerexcelente.com')
print('     Password: taller123!')
print('     Endpoint: POST /talleres/login')
print()
print('  🔧 TÉCNICOS (App Móvil Flutter — misma pantalla que cliente)')
print('     Email:    tecnico.juan@taller.com   / tecnico123!')
print('     Email:    tecnico.carlos@taller.com / tecnico456!')
print('     Endpoint: POST /usuarios/login  (redirige a pantalla técnico si rol=3)')
print()
print('  ⚙️  SIGUIENTE PASO (opcional): python seed_estados_prueba.py')
print('     Crea 5 incidentes de prueba en todos los estados de asignación.')
print('\n' + '=' * 70)

conn.close()
print('\n✅ Seed completo.')
