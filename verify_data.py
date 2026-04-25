#!/usr/bin/env python3
"""
Script para verificar que existan datos en las tablas necesarias 
para el Motor de Asignación Inteligente de Talleres.
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

def verificar_datos():
    """Verifica datos en todas las tablas críticas."""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("VERIFICACIÓN DE DATOS - MOTOR DE ASIGNACIÓN")
        print("=" * 80)
        
        # 1. Categorías
        print("\n1. CATEGORÍAS (tabla: categoria_problema)")
        result = db.execute(text("SELECT COUNT(*) as total FROM categoria_problema")).fetchone()
        print(f"   ✓ Categorías: {result[0]} registros")
        
        # 2. Prioridades
        print("\n2. PRIORIDADES (tabla: prioridad)")
        result = db.execute(text("SELECT COUNT(*) as total FROM prioridad")).fetchone()
        print(f"   ✓ Prioridades: {result[0]} registros")
        
        # 3. Talleres
        print("\n3. TALLERES (tabla: taller)")
        result = db.execute(text("""
            SELECT COUNT(*) as total FROM taller WHERE activo = TRUE
        """)).fetchone()
        total_talleres = result[0]
        print(f"   ✓ Talleres activos: {total_talleres} registros")
        
        if total_talleres > 0:
            # Mostrar primeros 5 talleres con sus datos
            talleres = db.execute(text("""
                SELECT id_taller, nombre, capacidad_max, 
                       latitud, longitud, telefono, activo
                FROM taller 
                WHERE activo = TRUE
                LIMIT 5
            """)).fetchall()
            print("   Ejemplos:")
            for t in talleres:
                print(f"     - [{t[0]}] {t[1]} | Cap: {t[2]} | Lat: {t[3]}, Lon: {t[4]} | Tel: {t[5]}")
        
        # 4. Servicios por Taller
        print("\n4. SERVICIOS DE TALLERES (tabla: taller_servicio)")
        result = db.execute(text("""
            SELECT COUNT(*) as total FROM taller_servicio
        """)).fetchone()
        print(f"   ✓ Relaciones taller-servicio: {result[0]} registros")
        
        # Contar talleres con servicios
        result = db.execute(text("""
            SELECT COUNT(DISTINCT id_taller) as talleres_con_servicios 
            FROM taller_servicio
        """)).fetchone()
        print(f"   ✓ Talleres con servicios asignados: {result[0]}")
        
        # 5. Usuarios (Técnicos)
        print("\n5. USUARIOS / TÉCNICOS (tabla: usuario)")
        result = db.execute(text("""
            SELECT COUNT(*) as total FROM usuario WHERE activo = TRUE
        """)).fetchone()
        print(f"   ✓ Usuarios activos: {result[0]} registros")
        
        # Contar por rol
        roles = db.execute(text("""
            SELECT id_rol, COUNT(*) as total 
            FROM usuario 
            WHERE activo = TRUE 
            GROUP BY id_rol
        """)).fetchall()
        print("   Distribución por rol:")
        for rol, count in roles:
            print(f"     - Rol {rol}: {count} usuarios")
        
        # 6. Incidentes
        print("\n6. INCIDENTES (tabla: incidente)")
        result = db.execute(text("""
            SELECT COUNT(*) as total FROM incidente
        """)).fetchone()
        print(f"   ✓ Total incidentes: {result[0]} registros")
        
        # Incidentes por estado
        estados = db.execute(text("""
            SELECT id_estado, COUNT(*) as total 
            FROM incidente 
            GROUP BY id_estado
        """)).fetchall()
        print("   Distribución por estado:")
        for estado, count in estados:
            print(f"     - id_estado {estado}: {count} incidentes")
        
        # 7. Candidatos de Asignación
        print("\n7. CANDIDATOS DE ASIGNACIÓN (tabla: candidato_asignacion)")
        result = db.execute(text("""
            SELECT COUNT(*) as total FROM candidato_asignacion
        """)).fetchone()
        print(f"   ✓ Candidatos registrados: {result[0]}")
        
        # 8. Asignaciones
        print("\n8. ASIGNACIONES (tabla: asignacion)")
        result = db.execute(text("""
            SELECT COUNT(*) as total FROM asignacion
        """)).fetchone()
        print(f"   ✓ Asignaciones: {result[0]} registros")
        
        # 9. Verificar integridad referencial
        print("\n" + "=" * 80)
        print("VERIFICACIÓN DE INTEGRIDAD REFERENCIAL")
        print("=" * 80)
        
        # Verificar que los talleres tengan coordenadas
        result = db.execute(text("""
            SELECT COUNT(*) as sin_coordenadas 
            FROM taller 
            WHERE activo = TRUE 
            AND (latitud IS NULL OR longitud IS NULL)
        """)).fetchone()
        if result[0] == 0:
            print("✓ Todos los talleres tienen coordenadas (latitud/longitud)")
        else:
            print(f"⚠️  {result[0]} talleres SIN coordenadas")
        
        # Verificar que los talleres tengan capacidad máxima
        result = db.execute(text("""
            SELECT COUNT(*) as sin_capacidad 
            FROM taller 
            WHERE activo = TRUE 
            AND (capacidad_max IS NULL OR capacidad_max = 0)
        """)).fetchone()
        if result[0] == 0:
            print("✓ Todos los talleres tienen capacidad máxima definida")
        else:
            print(f"⚠️  {result[0]} talleres SIN capacidad máxima")
        
        # Verificar que los incidentes tengan categoría
        result = db.execute(text("""
            SELECT COUNT(*) as sin_categoria 
            FROM incidente 
            WHERE id_categoria IS NULL
        """)).fetchone()
        if result[0] == 0:
            print("✓ Todos los incidentes tienen categoría")
        else:
            print(f"⚠️  {result[0]} incidentes SIN categoría")
        
        print("\n" + "=" * 80)
        print("RESUMEN EJECUTIVO")
        print("=" * 80)
        
        # Validación final
        validaciones = []
        
        # 1. ¿Hay talleres activos?
        result = db.execute(text("""
            SELECT COUNT(*) FROM taller WHERE activo = TRUE
        """)).fetchone()
        hay_talleres = result[0] > 0
        validaciones.append(("Talleres activos", hay_talleres))
        
        # 2. ¿Los talleres tienen coordenadas?
        result = db.execute(text("""
            SELECT COUNT(*) FROM taller 
            WHERE activo = TRUE 
            AND latitud IS NOT NULL AND longitud IS NOT NULL
        """)).fetchone()
        talleres_con_coords = result[0] > 0
        validaciones.append(("Talleres con coordenadas", talleres_con_coords))
        
        # 3. ¿Hay servicios para talleres?
        result = db.execute(text("""
            SELECT COUNT(*) FROM taller_servicio
        """)).fetchone()
        hay_servicios = result[0] > 0
        validaciones.append(("Servicios de talleres", hay_servicios))
        
        # 4. ¿Hay usuarios/técnicos?
        result = db.execute(text("""
            SELECT COUNT(*) FROM usuario WHERE activo = TRUE
        """)).fetchone()
        hay_usuarios = result[0] > 0
        validaciones.append(("Usuarios activos", hay_usuarios))
        
        # 5. ¿Hay incidentes?
        result = db.execute(text("""
            SELECT COUNT(*) FROM incidente
        """)).fetchone()
        hay_incidentes = result[0] > 0
        validaciones.append(("Incidentes", hay_incidentes))
        
        for validacion, resultado in validaciones:
            estado = "✅" if resultado else "❌"
            print(f"{estado} {validacion}")
        
        print("\n" + "=" * 80)
        if all(r for _, r in validaciones):
            print("✅ SISTEMA LISTO - Todos los datos necesarios están disponibles")
        else:
            print("⚠️  FALTAN DATOS - Ver detalles arriba")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error al verificar datos: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verificar_datos()
