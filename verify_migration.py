#!/usr/bin/env python
"""Script para verificar migración y hacer pruebas"""

from sqlalchemy import create_engine, text

def verificar_migracion():
    """Verificar que se creó tabla usuario_taller"""
    engine = create_engine('postgresql://postgres:12345678@localhost:5432/emergencias_vehiculares')
    conn = engine.connect()
    
    try:
        # Verificar tabla
        result = conn.execute(text("SELECT COUNT(*) FROM usuario_taller"))
        count = result.scalar()
        print(f'✅ Tabla usuario_taller creada. Registros: {count}')
        
        # Listar columnas
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name='usuario_taller' ORDER BY ordinal_position"
        ))
        cols = result.fetchall()
        print(f'✅ Columnas: {[row[0] for row in cols]}')
        
        # Verificar índices
        result = conn.execute(text(
            "SELECT indexname FROM pg_indexes WHERE tablename='usuario_taller'"
        ))
        indices = result.fetchall()
        print(f'✅ Índices: {[row[0] for row in indices]}')
        
        # Verificar constraint único
        result = conn.execute(text(
            "SELECT constraint_name FROM information_schema.table_constraints WHERE table_name='usuario_taller' AND constraint_type='UNIQUE'"
        ))
        constraints = result.fetchall()
        print(f'✅ Constraints UNIQUE: {[row[0] for row in constraints]}')
        
        print('\n✅ MIGRACIÓN COMPLETADA EXITOSAMENTE')
        return True
        
    except Exception as e:
        print(f'❌ Error: {e}')
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    verificar_migracion()
