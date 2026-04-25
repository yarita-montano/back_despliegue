#!/usr/bin/env python3
"""
Script para crear asignaciones de prueba al Taller Excelente en todos los estados.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/yary"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def crear_asignaciones_prueba():
    """Crea asignaciones de prueba al Taller Excelente en todos los estados."""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("CREANDO ASIGNACIONES DE PRUEBA - TALLER EXCELENTE")
        print("=" * 80)
        
        # 1. Limpiar asignaciones existentes
        print("\n1️⃣  Limpiando asignaciones previas...")
        db.execute(text("DELETE FROM asignacion"))
        db.commit()
        print("   ✓ Asignaciones eliminadas")
        
        # 2. Obtener incidentes
        print("\n2️⃣  Obteniendo incidentes disponibles...")
        incidentes = db.execute(text("""
            SELECT id_incidente FROM incidente LIMIT 5
        """)).fetchall()
        
        print(f"   Incidentes encontrados: {len(incidentes)}")
        
        # 3. Obtener estados de asignación
        print("\n3️⃣  Obteniendo estados de asignación...")
        estados = db.execute(text("""
            SELECT id_estado_asignacion, nombre 
            FROM estado_asignacion 
            ORDER BY id_estado_asignacion
        """)).fetchall()
        
        print(f"   Estados encontrados: {len(estados)}")
        for id_est, nombre_est in estados:
            print(f"     - {id_est}: {nombre_est}")
        
        # 4. Crear asignaciones al Taller Excelente (id_taller=1) en todos los estados
        print("\n4️⃣  Creando asignaciones al Taller Excelente en todos los estados...")
        
        id_taller = 1  # Taller Excelente
        contador = 0
        
        # Mapeo de estados para descripción
        estado_desc = {
            1: "pendiente",
            2: "aceptada",
            3: "rechazada",
            4: "en_camino",
            5: "completada"
        }
        
        for inc_idx, (id_incidente,) in enumerate(incidentes):
            for id_estado, nombre_estado in estados:
                if contador >= len(incidentes) * len(estados):
                    break
                
                nota = f"Asignación de prueba - Estado: {nombre_estado} (Score: {95 - contador}%)"
                
                db.execute(text("""
                    INSERT INTO asignacion 
                    (id_incidente, id_taller, id_estado_asignacion, nota_taller)
                    VALUES (:id_inc, :id_taller, :id_estado, :nota)
                """), {
                    "id_inc": id_incidente,
                    "id_taller": id_taller,
                    "id_estado": id_estado,
                    "nota": nota
                })
                
                contador += 1
                print(f"   ✓ Incidente {id_incidente} + Estado {nombre_estado}")
        
        db.commit()
        
        # 5. Verificación
        print("\n" + "=" * 80)
        print("VERIFICACIÓN")
        print("=" * 80)
        
        result = db.execute(text("""
            SELECT COUNT(*) FROM asignacion
        """)).fetchone()
        print(f"\n✅ Total asignaciones creadas: {result[0]}")
        
        result = db.execute(text("""
            SELECT 
                ea.nombre as estado,
                COUNT(*) as total
            FROM asignacion a
            JOIN estado_asignacion ea ON a.id_estado_asignacion = ea.id_estado_asignacion
            WHERE a.id_taller = 1
            GROUP BY ea.id_estado_asignacion, ea.nombre
            ORDER BY ea.id_estado_asignacion
        """)).fetchall()
        
        print("\n✅ Distribución por estado (Taller Excelente):")
        for estado_name, total in result:
            print(f"   - {estado_name}: {total} asignaciones")
        
        print("\n" + "=" * 80)
        print("✅ ASIGNACIONES DE PRUEBA CREADAS")
        print("=" * 80)
        print("\nAhora el taller verá:")
        print("  • Pendientes (azul)")
        print("  • Aceptadas (verde)")
        print("  • Rechazadas (rojo)")
        print("  • En camino (naranja)")
        print("  • Completadas (gris)")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    crear_asignaciones_prueba()
