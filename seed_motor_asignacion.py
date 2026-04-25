#!/usr/bin/env python3
"""
Script para agregar datos de prueba necesarios para el Motor de Asignación.
Solo ejecuta INSERTs, no modifica la estructura de la base de datos.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Conexión directa a la base de datos
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/yary"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def seed_data():
    """Agrega datos de prueba para el Motor de Asignación."""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("AGREGANDO DATOS DE PRUEBA - MOTOR DE ASIGNACIÓN")
        print("=" * 80)
        
        # 1. Agregar servicios al taller
        print("\n1️⃣  Agregando servicios al taller (id_taller=1)...")
        
        sql_servicios = """
        INSERT INTO taller_servicio (id_taller, id_categoria, servicio_movil)
        VALUES 
          (1, 1, TRUE),   -- Batería - Servicio móvil
          (1, 2, TRUE),   -- Llanta - Servicio móvil
          (1, 3, FALSE),  -- Choque - No móvil
          (1, 4, TRUE),   -- Motor - Servicio móvil
          (1, 5, TRUE),   -- Llaves - Servicio móvil
          (1, 6, FALSE),  -- Otros - No móvil
          (1, 7, FALSE)   -- Incierto - No móvil
        ON CONFLICT (id_taller, id_categoria) DO NOTHING;
        """
        
        db.execute(text(sql_servicios))
        db.commit()
        
        # Verificar servicios insertados
        result = db.execute(text("""
            SELECT COUNT(*) FROM taller_servicio WHERE id_taller = 1
        """)).fetchone()
        print(f"   ✓ Servicios agregados: {result[0]} registros")
        
        # 2. Asignar categorías a incidentes sin categoría
        print("\n2️⃣  Asignando categoría a incidentes sin categoría...")
        
        # Primero, verificar cuántos incidentes sin categoría hay
        result = db.execute(text("""
            SELECT COUNT(*) FROM incidente WHERE id_categoria IS NULL
        """)).fetchone()
        incidentes_sin_cat = result[0]
        print(f"   Incidentes sin categoría encontrados: {incidentes_sin_cat}")
        
        if incidentes_sin_cat > 0:
            sql_categorias = """
            UPDATE incidente 
            SET id_categoria = 1 
            WHERE id_categoria IS NULL;
            """
            db.execute(text(sql_categorias))
            db.commit()
            print(f"   ✓ {incidentes_sin_cat} incidentes actualizados con categoría 1 (Batería)")
        
        # 3. Agregar técnicos al taller
        print("\n3️⃣  Agregando técnicos al taller...")
        
        sql_tecnicos = """
        INSERT INTO tecnico (id_taller, nombre, disponible, activo)
        VALUES 
          (1, 'Juan Pérez', TRUE, TRUE),
          (1, 'Carlos García', TRUE, TRUE),
          (1, 'Miguel López', FALSE, TRUE)
        ON CONFLICT DO NOTHING;
        """
        
        db.execute(text(sql_tecnicos))
        db.commit()
        
        # Verificar técnicos insertados
        result = db.execute(text("""
            SELECT COUNT(*) FROM tecnico WHERE id_taller = 1
        """)).fetchone()
        print(f"   ✓ Técnicos agregados: {result[0]} registros")
        
        # VERIFICACIÓN FINAL
        print("\n" + "=" * 80)
        print("VERIFICACIÓN FINAL")
        print("=" * 80)
        
        # Verificar servicios
        result = db.execute(text("""
            SELECT ts.id_categoria, cp.nombre 
            FROM taller_servicio ts
            JOIN categoria_problema cp ON ts.id_categoria = cp.id_categoria
            WHERE ts.id_taller = 1
            ORDER BY ts.id_categoria
        """)).fetchall()
        print("\n✅ Servicios del taller:")
        for cat_id, cat_name in result:
            print(f"   - Categoría {cat_id}: {cat_name}")
        
        # Verificar incidentes con categoría
        result = db.execute(text("""
            SELECT COUNT(*) FROM incidente WHERE id_categoria IS NOT NULL
        """)).fetchone()
        print(f"\n✅ Incidentes con categoría: {result[0]}/6")
        
        # Verificar técnicos
        result = db.execute(text("""
            SELECT nombre, disponible FROM tecnico 
            WHERE id_taller = 1
            ORDER BY nombre
        """)).fetchall()
        print(f"\n✅ Técnicos del taller:")
        for nombre, disponible in result:
            estado = "disponible" if disponible else "ocupado"
            print(f"   - {nombre} ({estado})")
        
        print("\n" + "=" * 80)
        print("✅ DATOS AGREGADOS EXITOSAMENTE")
        print("=" * 80)
        print("\nEl Motor de Asignación puede ahora:")
        print("  • Buscar talleres por categoría")
        print("  • Calcular scores considerando técnicos disponibles")
        print("  • Crear candidatos de asignación")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error al agregar datos: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
