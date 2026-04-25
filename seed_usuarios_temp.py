import psycopg2
from argon2 import PasswordHasher

ph = PasswordHasher()
conn = psycopg2.connect('postgresql://postgres:12345678@localhost:5432/emergencias_vehiculares')
conn.autocommit = True
cur = conn.cursor()

# Limpiar tablas previas (para evitar duplicados)
try:
    cur.execute("DELETE FROM tecnico;")
    cur.execute("DELETE FROM taller;")
    cur.execute("DELETE FROM usuario;")
    cur.execute("DELETE FROM rol CASCADE;")
    print("✅ Tablas limpiadas")
except Exception as e:
    print(f"⚠️ Error al limpiar (puede ser normal): {e}")

# Catalogos
cur.execute("INSERT INTO rol (nombre) VALUES ('cliente'),('taller'),('tecnico'),('admin');")
cur.execute("""INSERT INTO estado_incidente (nombre, descripcion) VALUES
    ('pendiente','Reportado, sin asignar'),
    ('en_proceso','Taller asignado, en atencion'),
    ('atendido','Resuelto'),
    ('cancelado','Cancelado por el usuario');""")
cur.execute("""INSERT INTO categoria_problema (nombre, descripcion) VALUES
    ('bateria','Problemas de bateria'),
    ('llanta','Llanta desinflada o reventada'),
    ('choque','Colision o accidente'),
    ('motor','Fallas del motor'),
    ('llaves','Llaves perdidas o bloqueadas'),
    ('otros','Otros problemas'),
    ('incierto','Sin clasificar');""")
cur.execute("""INSERT INTO prioridad (nivel, orden) VALUES
    ('baja',1),('media',2),('alta',3),('critica',4);""")
cur.execute("""INSERT INTO estado_asignacion (nombre) VALUES
    ('pendiente'),('aceptada'),('rechazada'),('en_camino'),('completada');""")
cur.execute("INSERT INTO tipo_evidencia (nombre) VALUES ('imagen'),('audio'),('texto');")
cur.execute("INSERT INTO metodo_pago (nombre) VALUES ('tarjeta'),('transferencia'),('efectivo'),('qr');")
cur.execute("""INSERT INTO estado_pago (nombre) VALUES
    ('pendiente'),('procesando'),('completado'),('fallido'),('reembolsado');""")
print("✅ Catálogos creados")

# Usuarios de prueba
cur.execute("""INSERT INTO usuario (id_rol, nombre, email, telefono, password_hash, activo)
    VALUES (1, 'Juan Conductor', 'conductor@ejemplo.com', '+57 3001234567', %s, TRUE);""",
    (ph.hash('cliente123!'),))
cur.execute("""INSERT INTO usuario (id_rol, nombre, email, telefono, password_hash, activo)
    VALUES (4, 'Administrador Sistema', 'admin@plataforma.com', '+57 3009999999', %s, TRUE);""",
    (ph.hash('admin123!'),))
print("✅ Usuarios creados")

# Taller de prueba
cur.execute("""INSERT INTO taller (nombre, email, telefono, password_hash, latitud, longitud, direccion, capacidad_max, activo, verificado)
    VALUES ('Taller Excelente','gerente@tallerexcelente.com','+57 3105552222',%s,6.2442,-75.5812,'Cra 45 #123-45, Medellin',5,TRUE,TRUE);""",
    (ph.hash('taller123!'),))
print("✅ Taller creado")

# Tecnicos del taller 1
cur.execute("""INSERT INTO tecnico (id_taller, nombre, telefono, disponible, activo) VALUES
    (1,'Juan Perez - Tecnico','+57 3105551111',TRUE,TRUE),
    (1,'Carlos Gomez - Tecnico','+57 3105551112',TRUE,TRUE);""")
print("✅ Técnicos creados")

# Verificar
print('\n' + '='*70)
print('RESUMEN DE SEED')
print('='*70)
for tabla in ['rol','estado_incidente','categoria_problema','prioridad','estado_asignacion',
              'tipo_evidencia','metodo_pago','estado_pago','usuario','taller','tecnico']:
    cur.execute(f'SELECT COUNT(*) FROM {tabla};')
    count = cur.fetchone()[0]
    print(f'  {tabla:25s} → {count} registros')

print('='*70)
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
print('  🟢 TÉCNICOS (Sub-entidades del Taller, sin login directo)')
print('     - Juan Pérez (ID=1, Taller=1)')
print('     - Carlos Gómez (ID=2, Taller=1)')
print('     Acceso:   GET /talleres/mi-taller/tecnicos (requiere token de taller)')
print('\n' + '='*70)

conn.close()
print('\n✅ Seed completo.')
