from sqlalchemy import create_engine, text
from app.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    # Obtener usuario
    query = text("""
        SELECT id_usuario, nombre, email FROM usuario WHERE email = 'conductor@ejemplo.com'
    """)
    usuario = conn.execute(query).first()
    
    if usuario:
        print(f"✅ Usuario encontrado:")
        print(f"   ID: {usuario[0]}")
        print(f"   Nombre: {usuario[1]}")
        print(f"   Email: {usuario[2]}")
        
        # Contar vehículos activos
        query2 = text("""
            SELECT COUNT(*) FROM vehiculo WHERE id_usuario = :user_id AND activo = true
        """)
        result = conn.execute(query2, {"user_id": usuario[0]}).first()
        count = result[0] if result else 0
        
        print(f"\n   Vehículos activos: {count}")
        
        # Listar vehículos
        if count > 0:
            query3 = text("""
                SELECT id_vehiculo, placa, marca, modelo, anio, color FROM vehiculo 
                WHERE id_usuario = :user_id AND activo = true
                ORDER BY created_at DESC
            """)
            vehiculos = conn.execute(query3, {"user_id": usuario[0]}).fetchall()
            print("\n   Lista de vehículos:")
            for v in vehiculos:
                print(f"     - {v[1]} ({v[2]} {v[3]} {v[4]}) Color: {v[5]}")
    else:
        print("❌ Usuario no encontrado")
