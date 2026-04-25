#!/usr/bin/env python
"""Script para verificar e insertar estados de incidente en PostgreSQL"""

from sqlalchemy import create_engine, text
from app.core.config import get_settings

def main():
    try:
        settings = get_settings()
        # Crear conexión
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as conn:
            # Verificar datos existentes
            print("📋 Verificando tabla estado_incidente...\n")
            
            result = conn.execute(text("SELECT id_estado, nombre FROM estado_incidente ORDER BY id_estado"))
            estados = result.fetchall()
            
            if estados:
                print("✅ Estados encontrados:")
                for id_est, nombre in estados:
                    print(f"   ID: {id_est} → {nombre}")
                print()
            else:
                print("❌ La tabla estado_incidente está vacía. Insertando datos...\n")
                
                # Insertar estados
                insertar = text("""
                    INSERT INTO estado_incidente (nombre) 
                    VALUES ('pendiente'), ('en_proceso'), ('atendido'), ('cancelado')
                """)
                conn.execute(insertar)
                conn.commit()
                
                # Verificar inserción
                result = conn.execute(text("SELECT id_estado, nombre FROM estado_incidente ORDER BY id_estado"))
                estados = result.fetchall()
                
                print("✅ Estados insertados exitosamente:")
                for id_est, nombre in estados:
                    print(f"   ID: {id_est} → {nombre}")
                print()
        
        print("✅ Listo para probar incidencias!\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
