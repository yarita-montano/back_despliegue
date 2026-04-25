#!/usr/bin/env python3
"""
Script para ejecutar el Motor de Asignación Inteligente en incidentes existentes.
Genera candidatos de asignación y crea asignaciones automáticas.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import math
import logging

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/yary"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constantes del Motor
RADIO_BUSQUEDA_KM = 30
MIN_CANDIDATOS = 3
MAX_CANDIDATOS = 10

def calcular_distancia_haversine(lat1, lon1, lat2, lon2):
    """Calcula distancia entre dos puntos geográficos en km."""
    R = 6371  # Radio de la Tierra en km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    distancia = R * c
    
    return distancia

def contar_asignaciones_activas(db, id_taller):
    """Cuenta incidentes activos asignados a un taller."""
    result = db.execute(text("""
        SELECT COUNT(*) FROM asignacion a
        JOIN incidente i ON a.id_incidente = i.id_incidente
        WHERE a.id_taller = :id_taller
        AND a.id_estado_asignacion IN (1, 2)  -- pendiente, aceptada
        AND i.id_estado = 1  -- pendiente
    """), {"id_taller": id_taller}).fetchone()
    return result[0] if result else 0

def ejecutar_motor():
    """Ejecuta el Motor de Asignación en todos los incidentes sin candidatos."""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("EJECUTANDO MOTOR DE ASIGNACIÓN INTELIGENTE")
        print("=" * 80)
        
        # 1. Buscar incidentes sin candidatos
        print("\n1️⃣  Buscando incidentes sin candidatos...")
        
        incidentes = db.execute(text("""
            SELECT i.id_incidente, i.latitud, i.longitud, cp.nombre as categoria_nombre
            FROM incidente i
            LEFT JOIN categoria_problema cp ON i.id_categoria = cp.id_categoria
            WHERE NOT EXISTS (
                SELECT 1 FROM candidato_asignacion WHERE id_incidente = i.id_incidente
            )
            ORDER BY i.id_incidente
        """)).fetchall()
        
        print(f"   Incidentes encontrados: {len(incidentes)}")
        
        if not incidentes:
            print("   ⚠️  No hay incidentes sin candidatos")
            return
        
        # 2. Ejecutar Motor para cada incidente
        print("\n2️⃣  Ejecutando Motor de Asignación para cada incidente...")
        
        resultados = []
        
        for idx, (id_incidente, lat_incidente, lon_incidente, categoria_nombre) in enumerate(incidentes, 1):
            print(f"\n   [{idx}/{len(incidentes)}] Incidente ID {id_incidente}")
            print(f"        Categoría: {categoria_nombre}")
            print(f"        Ubicación: ({lat_incidente}, {lon_incidente})")
            
            try:
                # Buscar talleres en rango y con la categoría
                talleres = db.execute(text("""
                    SELECT 
                        t.id_taller, t.nombre, t.latitud, t.longitud, t.capacidad_max,
                        COUNT(CASE WHEN ta.id_estado_asignacion IN (1, 2) THEN 1 END) as incidentes_activos,
                        COUNT(DISTINCT CASE WHEN u.id_rol = 3 AND u.activo = TRUE THEN u.id_usuario END) as tecnicos_disponibles
                    FROM taller t
                    LEFT JOIN asignacion ta ON t.id_taller = ta.id_taller
                    LEFT JOIN incidente i ON ta.id_incidente = i.id_incidente AND i.id_estado = 1
                    LEFT JOIN usuario u ON u.id_rol = 3 AND u.activo = TRUE
                    WHERE t.activo = TRUE
                    AND EXISTS (
                        SELECT 1 FROM taller_servicio ts 
                        WHERE ts.id_taller = t.id_taller 
                        AND ts.id_categoria = (SELECT id_categoria FROM incidente WHERE id_incidente = :id_inc)
                    )
                    GROUP BY t.id_taller, t.nombre, t.latitud, t.longitud, t.capacidad_max
                """), {"id_inc": id_incidente}).fetchall()
                
                print(f"        Talleres compatibles: {len(talleres)}")
                
                if not talleres:
                    print(f"        ⚠️  No hay talleres disponibles para esta categoría")
                    resultados.append((id_incidente, False, "No hay talleres compatibles"))
                    continue
                
                # Calcular scores
                candidatos_con_score = []
                
                for taller in talleres:
                    id_taller, nombre_taller, lat_taller, lon_taller, cap_max, inc_activos, tec_disp = taller
                    
                    # Distancia
                    distancia = calcular_distancia_haversine(
                        lat_incidente, lon_incidente,
                        lat_taller, lon_taller
                    )
                    
                    if distancia > RADIO_BUSQUEDA_KM:
                        continue
                    
                    # Scoring: 40% distancia + 30% capacidad + 30% técnicos
                    score_distancia = max(0, 1 - (distancia / RADIO_BUSQUEDA_KM))
                    score_capacidad = max(0, (cap_max - inc_activos) / cap_max)
                    score_tecnicos = min(1, tec_disp / 2)
                    
                    score_total = (
                        (score_distancia * 0.40) +
                        (score_capacidad * 0.30) +
                        (score_tecnicos * 0.30)
                    ) * 100
                    
                    candidatos_con_score.append({
                        'id_taller': id_taller,
                        'nombre': nombre_taller,
                        'distancia': distancia,
                        'score': score_total
                    })
                
                # Ordenar por score descendente
                candidatos_con_score.sort(key=lambda x: x['score'], reverse=True)
                
                # Tomar top 10
                top_candidatos = candidatos_con_score[:MAX_CANDIDATOS]
                
                print(f"        Candidatos después de filtrar: {len(top_candidatos)}")
                
                # Guardar candidatos en BD
                for pos, candidato in enumerate(top_candidatos):
                    es_seleccionado = (pos == 0)  # El primero es el seleccionado
                    
                    db.execute(text("""
                        INSERT INTO candidato_asignacion 
                        (id_incidente, id_taller, distancia_km, score_total, seleccionado)
                        VALUES (:id_inc, :id_taller, :distancia, :score, :seleccionado)
                    """), {
                        "id_inc": id_incidente,
                        "id_taller": candidato['id_taller'],
                        "distancia": candidato['distancia'],
                        "score": candidato['score'],
                        "seleccionado": es_seleccionado
                    })
                
                db.commit()
                
                # Crear asignación automática con el mejor candidato
                mejor = top_candidatos[0]
                
                # Estado asignacion: 1 = pendiente
                db.execute(text("""
                    INSERT INTO asignacion 
                    (id_incidente, id_taller, id_estado_asignacion)
                    VALUES (:id_inc, :id_taller, 1)
                """), {
                    "id_inc": id_incidente,
                    "id_taller": mejor['id_taller']
                })
                
                db.commit()
                
                print(f"        ✅ Motor ejecutado:")
                print(f"           - Candidatos guardados: {len(top_candidatos)}")
                print(f"           - Mejor taller: {mejor['nombre']} (Score: {mejor['score']:.2f}%)")
                
                resultados.append((id_incidente, True, {
                    'candidatos': len(top_candidatos),
                    'mejor': mejor
                }))
                
            except Exception as e:
                print(f"        ❌ Error: {str(e)}")
                db.rollback()
                resultados.append((id_incidente, False, str(e)))
        
        # 3. Resumen final
        print("\n" + "=" * 80)
        print("RESUMEN DE EJECUCIÓN")
        print("=" * 80)
        
        exitosos = sum(1 for _, ok, _ in resultados if ok)
        fallidos = sum(1 for _, ok, _ in resultados if not ok)
        
        print(f"\n✅ Exitosos: {exitosos}/{len(resultados)}")
        print(f"❌ Fallidos: {fallidos}/{len(resultados)}")
        
        if exitosos > 0:
            print("\nDetalles de asignaciones creadas:")
            for id_inc, ok, data in resultados:
                if ok:
                    print(f"  - Incidente {id_inc}: {data['candidatos']} candidatos (Mejor: {data['mejor']['nombre']})")
        
        # 4. Verificación en BD
        print("\n" + "=" * 80)
        print("VERIFICACIÓN EN BASE DE DATOS")
        print("=" * 80)
        
        result = db.execute(text("""
            SELECT COUNT(*) FROM candidato_asignacion
        """)).fetchone()
        print(f"\n✅ Total candidatos en BD: {result[0]}")
        
        result = db.execute(text("""
            SELECT COUNT(*) FROM asignacion
        """)).fetchone()
        print(f"✅ Total asignaciones en BD: {result[0]}")
        
        result = db.execute(text("""
            SELECT id_incidente, COUNT(*) as candidatos 
            FROM candidato_asignacion 
            GROUP BY id_incidente 
            ORDER BY id_incidente
        """)).fetchall()
        
        if result:
            print("\n✅ Candidatos por incidente:")
            for inc_id, count in result:
                print(f"   - Incidente {inc_id}: {count} candidatos")
        
        print("\n" + "=" * 80)
        print("✅ MOTOR DE ASIGNACIÓN EJECUTADO")
        print("=" * 80)
        print("\nEl taller ahora verá:")
        print("  • Asignaciones pendientes en el dashboard")
        print("  • Detalles de cada candidato")
        print("  • Opción de aceptar/rechazar")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    ejecutar_motor()
