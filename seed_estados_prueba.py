#!/usr/bin/env python3
"""
Seed de incidentes en los 5 estados de asignacion.

Relaciona a:
  CLIENTE  →  conductor@ejemplo.com   (password: cliente123!)
  TALLER   →  gerente@tallerexcelente.com (password: taller123!)

Crea 5 incidentes — uno por cada estado posible — para que el taller
vea datos reales en cada pestaña de su app y el cliente vea flujos
en distintas fases.

REQUISITOS PREVIOS:
- Haber ejecutado `seed_usuarios_temp.py` al menos una vez
  (crea catalogos + usuario conductor + taller gerente).
- El taller se reubicara automaticamente cerca del incidente.

Uso:
    python seed_estados_prueba.py
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:12345678@localhost:5432/emergencias_vehiculares",
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Ubicacion base (Santa Cruz, Bolivia). El taller se coloca aqui.
LAT_REF = -17.8454274
LNG_REF = -63.1561987

EMAIL_CLIENTE = "conductor@ejemplo.com"
EMAIL_TALLER = "gerente@tallerexcelente.com"

# Escenarios: 1 incidente por estado de asignacion.
# Offset en grados desde el punto de referencia (~1km por 0.009 grados).
ESCENARIOS = [
    {
        "estado_asignacion": "pendiente",
        "estado_incidente": "pendiente",
        "offset_lat": 0.003,
        "offset_lng": 0.004,
        "categoria_nombre": "llanta",
        "prioridad_nivel": "alta",
        "descripcion": "Se me pincho la llanta en la autopista, estoy solo",
        "resumen_ia": "Llanta pinchada en autopista; prioridad alta por contexto",
        "confianza": 0.92,
        "eta_minutos": None,
        "nota_taller": None,
    },
    {
        "estado_asignacion": "aceptada",
        "estado_incidente": "en_proceso",
        "offset_lat": 0.018,
        "offset_lng": -0.010,
        "categoria_nombre": "bateria",
        "prioridad_nivel": "media",
        "descripcion": "No enciende el auto, creo que es la bateria",
        "resumen_ia": "Bateria descargada, vehiculo sin encendido",
        "confianza": 0.88,
        "eta_minutos": 25,
        "nota_taller": "Salimos en 5 minutos con cables y bateria nueva",
    },
    {
        "estado_asignacion": "rechazada",
        "estado_incidente": "pendiente",
        "offset_lat": -0.015,
        "offset_lng": 0.022,
        "categoria_nombre": "motor",
        "prioridad_nivel": "alta",
        "descripcion": "El motor hace un ruido raro y sale humo",
        "resumen_ia": "Posible falla mayor de motor, sobrecalentamiento",
        "confianza": 0.74,
        "eta_minutos": None,
        "nota_taller": "Sin stock de repuesto para este modelo, por favor elige otro taller",
    },
    {
        "estado_asignacion": "en_camino",
        "estado_incidente": "en_proceso",
        "offset_lat": 0.045,
        "offset_lng": 0.030,
        "categoria_nombre": "llaves",
        "prioridad_nivel": "media",
        "descripcion": "Deje las llaves adentro del auto",
        "resumen_ia": "Llaves dentro del vehiculo, necesita cerrajero",
        "confianza": 0.95,
        "eta_minutos": 10,
        "nota_taller": "En camino, a 10 min aprox",
    },
    {
        "estado_asignacion": "completada",
        "estado_incidente": "atendido",
        "offset_lat": -0.025,
        "offset_lng": -0.018,
        "categoria_nombre": "bateria",
        "prioridad_nivel": "baja",
        "descripcion": "Bateria floja, necesito reemplazo",
        "resumen_ia": "Reemplazo de bateria en estacionamiento",
        "confianza": 0.90,
        "eta_minutos": 0,
        "nota_taller": "Servicio finalizado, bateria reemplazada satisfactoriamente",
    },
]


def _first(db, sql, params=None):
    return db.execute(text(sql), params or {}).fetchone()


def seed():
    db = SessionLocal()
    try:
        print("=" * 80)
        print("SEED INCIDENTES POR ESTADO - Taller <-> Cliente")
        print("=" * 80)

        # 1. Localizar usuario y taller
        usuario = _first(db, "SELECT id_usuario FROM usuario WHERE email = :e",
                         {"e": EMAIL_CLIENTE})
        if not usuario:
            print(f"ERROR: No existe usuario {EMAIL_CLIENTE}. "
                  "Ejecuta primero seed_usuarios_temp.py")
            return
        id_usuario = usuario[0]
        print(f"Cliente encontrado: id_usuario={id_usuario}")

        taller = _first(db, "SELECT id_taller FROM taller WHERE email = :e",
                        {"e": EMAIL_TALLER})
        if not taller:
            print(f"ERROR: No existe taller {EMAIL_TALLER}. "
                  "Ejecuta primero seed_usuarios_temp.py")
            return
        id_taller = taller[0]
        print(f"Taller encontrado: id_taller={id_taller}")

        # 2. Reubicar taller cerca del punto de referencia
        db.execute(text("""
            UPDATE taller SET
                latitud = :lat,
                longitud = :lng,
                direccion = 'Av. Cristo Redentor #500, Santa Cruz',
                activo = TRUE,
                verificado = TRUE
            WHERE id_taller = :id
        """), {"lat": LAT_REF + 0.002, "lng": LNG_REF - 0.001, "id": id_taller})
        db.commit()
        print(f"Taller reubicado a ({LAT_REF + 0.002}, {LNG_REF - 0.001}) ~0.3 km")

        # 3. Asegurar que el taller atienda todas las categorias
        db.execute(text("""
            INSERT INTO taller_servicio (id_taller, id_categoria, servicio_movil)
            SELECT :id_taller, c.id_categoria, TRUE
            FROM categoria_problema c
            ON CONFLICT (id_taller, id_categoria) DO NOTHING;
        """), {"id_taller": id_taller})
        db.commit()

        # 4. Asegurar que tenga al menos un tecnico disponible
        tec_count = _first(db,
            "SELECT COUNT(*) FROM tecnico WHERE id_taller = :id AND activo = TRUE",
            {"id": id_taller})[0]
        if tec_count == 0:
            db.execute(text("""
                INSERT INTO tecnico (id_taller, nombre, disponible, activo)
                VALUES (:id, 'Tecnico Demo', TRUE, TRUE)
            """), {"id": id_taller})
            db.commit()
            print("Agregado tecnico demo.")

        # 5. Asegurar que el cliente tenga un vehiculo
        veh = _first(db,
            "SELECT id_vehiculo FROM vehiculo WHERE id_usuario = :id AND activo = TRUE",
            {"id": id_usuario})
        if not veh:
            db.execute(text("""
                INSERT INTO vehiculo (id_usuario, placa, marca, modelo, anio, color, activo)
                VALUES (:id, 'ABC-1234', 'Toyota', 'Corolla', 2018, 'Blanco', TRUE)
            """), {"id": id_usuario})
            db.commit()
            veh = _first(db,
                "SELECT id_vehiculo FROM vehiculo WHERE id_usuario = :id AND activo = TRUE",
                {"id": id_usuario})
            print(f"Vehiculo creado: id_vehiculo={veh[0]}")
        id_vehiculo = veh[0]

        # 6. Cargar IDs de catalogos
        catalogos = {}
        for nombre in ["pendiente", "aceptada", "rechazada", "en_camino", "completada"]:
            row = _first(db,
                "SELECT id_estado_asignacion FROM estado_asignacion WHERE nombre = :n",
                {"n": nombre})
            if not row:
                print(f"ERROR: estado_asignacion '{nombre}' no existe. Seed incompleto.")
                return
            catalogos[f"asig_{nombre}"] = row[0]

        for nombre in ["pendiente", "en_proceso", "atendido", "cancelado"]:
            row = _first(db,
                "SELECT id_estado FROM estado_incidente WHERE nombre = :n",
                {"n": nombre})
            if row:
                catalogos[f"inc_{nombre}"] = row[0]

        # 7. Limpiar datos previos de prueba de este cliente (para idempotencia)
        print("\nLimpiando datos previos de prueba del cliente...")
        db.execute(text("""
            DELETE FROM historial_estado_asignacion
            WHERE id_asignacion IN (
                SELECT a.id_asignacion FROM asignacion a
                JOIN incidente i ON i.id_incidente = a.id_incidente
                WHERE i.id_usuario = :id_usuario
                  AND i.descripcion_usuario LIKE '[SEED]%'
            );
        """), {"id_usuario": id_usuario})
        db.execute(text("""
            DELETE FROM asignacion
            WHERE id_incidente IN (
                SELECT id_incidente FROM incidente
                WHERE id_usuario = :id_usuario
                  AND descripcion_usuario LIKE '[SEED]%'
            );
        """), {"id_usuario": id_usuario})
        db.execute(text("""
            DELETE FROM candidato_asignacion
            WHERE id_incidente IN (
                SELECT id_incidente FROM incidente
                WHERE id_usuario = :id_usuario
                  AND descripcion_usuario LIKE '[SEED]%'
            );
        """), {"id_usuario": id_usuario})
        db.execute(text("""
            DELETE FROM historial_estado_incidente
            WHERE id_incidente IN (
                SELECT id_incidente FROM incidente
                WHERE id_usuario = :id_usuario
                  AND descripcion_usuario LIKE '[SEED]%'
            );
        """), {"id_usuario": id_usuario})
        db.execute(text("""
            DELETE FROM incidente
            WHERE id_usuario = :id_usuario
              AND descripcion_usuario LIKE '[SEED]%'
        """), {"id_usuario": id_usuario})
        db.commit()

        # 8. Crear los 5 escenarios
        print("\nCreando incidentes + asignaciones:\n")
        for i, esc in enumerate(ESCENARIOS, 1):
            cat = _first(db,
                "SELECT id_categoria FROM categoria_problema WHERE nombre = :n",
                {"n": esc["categoria_nombre"]})
            pri = _first(db,
                "SELECT id_prioridad FROM prioridad WHERE nivel = :n",
                {"n": esc["prioridad_nivel"]})
            if not cat or not pri:
                print(f"   [{i}] Saltado: falta categoria/prioridad")
                continue

            id_estado_inc = catalogos.get(f"inc_{esc['estado_incidente']}", 1)
            id_estado_asig = catalogos[f"asig_{esc['estado_asignacion']}"]

            lat = LAT_REF + esc["offset_lat"]
            lng = LNG_REF + esc["offset_lng"]
            descripcion = f"[SEED] {esc['descripcion']}"

            # INSERT incidente
            row = db.execute(text("""
                INSERT INTO incidente (
                    id_usuario, id_vehiculo, id_estado,
                    id_categoria, id_prioridad,
                    latitud, longitud,
                    descripcion_usuario, resumen_ia, clasificacion_ia_confianza,
                    requiere_revision_manual
                )
                VALUES (
                    :id_usuario, :id_vehiculo, :id_estado,
                    :id_categoria, :id_prioridad,
                    :lat, :lng,
                    :descripcion, :resumen, :confianza,
                    FALSE
                )
                RETURNING id_incidente
            """), {
                "id_usuario": id_usuario,
                "id_vehiculo": id_vehiculo,
                "id_estado": id_estado_inc,
                "id_categoria": cat[0],
                "id_prioridad": pri[0],
                "lat": lat,
                "lng": lng,
                "descripcion": descripcion,
                "resumen": esc["resumen_ia"],
                "confianza": esc["confianza"],
            })
            id_incidente = row.fetchone()[0]

            # INSERT candidato_asignacion (este taller, seleccionado=TRUE)
            db.execute(text("""
                INSERT INTO candidato_asignacion (
                    id_incidente, id_taller, distancia_km, score_total, seleccionado
                )
                VALUES (:id_inc, :id_tall, 0.8, 92.5, TRUE)
            """), {"id_inc": id_incidente, "id_tall": id_taller})

            # INSERT asignacion con el estado correspondiente
            db.execute(text("""
                INSERT INTO asignacion (
                    id_incidente, id_taller, id_estado_asignacion,
                    eta_minutos, nota_taller
                )
                VALUES (:id_inc, :id_tall, :id_estado, :eta, :nota)
            """), {
                "id_inc": id_incidente,
                "id_tall": id_taller,
                "id_estado": id_estado_asig,
                "eta": esc["eta_minutos"],
                "nota": esc["nota_taller"],
            })

            db.commit()
            print(f"   [{i}] incidente #{id_incidente}: "
                  f"{esc['estado_asignacion']:<11} | "
                  f"{esc['categoria_nombre']:<8} | "
                  f"prioridad={esc['prioridad_nivel']:<7} | "
                  f"({lat:.4f}, {lng:.4f})")

        # 9. Verificacion
        print("\n" + "=" * 80)
        print("VERIFICACION")
        print("=" * 80)
        filas = db.execute(text("""
            SELECT i.id_incidente, ea.nombre, c.nombre, p.nivel, i.latitud, i.longitud
            FROM incidente i
            JOIN asignacion a ON a.id_incidente = i.id_incidente
            JOIN estado_asignacion ea ON ea.id_estado_asignacion = a.id_estado_asignacion
            LEFT JOIN categoria_problema c ON c.id_categoria = i.id_categoria
            LEFT JOIN prioridad p ON p.id_prioridad = i.id_prioridad
            WHERE i.id_usuario = :id_usuario
              AND i.descripcion_usuario LIKE '[SEED]%'
              AND a.id_taller = :id_taller
            ORDER BY i.id_incidente
        """), {"id_usuario": id_usuario, "id_taller": id_taller}).fetchall()

        print(f"\nTotal de incidentes sembrados: {len(filas)}")
        for id_i, estado, cat, pri, lat, lng in filas:
            print(f"   #{id_i}: {estado:<11} {cat:<8} {pri:<8}  ({lat:.4f}, {lng:.4f})")

        print("\n" + "=" * 80)
        print("CREDENCIALES:")
        print(f"   CLIENTE: {EMAIL_CLIENTE}   / cliente123!")
        print(f"   TALLER : {EMAIL_TALLER} / taller123!")
        print("=" * 80)
        print("\nEn el app del taller (GET /talleres/mi-taller/asignaciones?estado=X):")
        print("   pendiente  -> 1 solicitud lista para ACEPTAR o RECHAZAR")
        print("   aceptada   -> 1 solicitud ya aceptada")
        print("   rechazada  -> 1 solicitud rechazada (cliente puede cambiar de taller)")
        print("   en_camino  -> 1 solicitud con tecnico en camino")
        print("   completada -> 1 solicitud finalizada")
        print("=" * 80)

    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
