--
-- MIGRACIÓN: Eliminación de tabla Tecnico → Usuario + UsuarioTaller
-- Fecha: 2026-04-22
--
-- DESCRIPCIÓN:
-- Se refactoriza la arquitectura para eliminar la tabla 'tecnico' separada.
-- Los técnicos ahora son usuarios con rol=3 en la tabla 'usuario'.
-- Se crea tabla 'usuario_taller' para vincular técnicos a talleres.
--
-- VENTAJAS:
-- 1. Elimina duplicación de data (tabla tecnico vs usuario)
-- 2. Técnicos pueden tener login con credenciales propias
-- 3. Un técnico puede trabajar en múltiples talleres si es necesario
-- 4. Simplifica la autenticación (todo por /usuarios/login)
-- 5. Relación explícita usuario-taller permite mejor auditoría
--

-- ============ PASO 1: CREAR TABLA usuario_taller ============

CREATE TABLE IF NOT EXISTS usuario_taller (
    id_usuario_taller SERIAL PRIMARY KEY,
    id_usuario INTEGER NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    id_taller INTEGER NOT NULL REFERENCES taller(id_taller) ON DELETE CASCADE,
    
    -- Estado del técnico en este taller
    disponible BOOLEAN DEFAULT TRUE NOT NULL,
    activo BOOLEAN DEFAULT TRUE NOT NULL,
    
    -- Ubicación actual del técnico
    latitud FLOAT,
    longitud FLOAT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Constraint: Un usuario técnico no puede vincularse dos veces al mismo taller
    UNIQUE(id_usuario, id_taller)
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_usuario_taller_id_usuario ON usuario_taller(id_usuario);
CREATE INDEX IF NOT EXISTS idx_usuario_taller_id_taller ON usuario_taller(id_taller);
CREATE INDEX IF NOT EXISTS idx_usuario_taller_disponible ON usuario_taller(disponible);


-- ============ PASO 2: MIGRAR DATOS DE tecnico → usuario_taller (SI EXISTEN) ============

-- Si hay datos en la tabla tecnico antigua, migrarlos:
-- NOTA: Descomenta esto SOLO si tienes datos críticos en la tabla tecnico
/*
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'tecnico') THEN
        -- Crear usuarios técnicos a partir de registros en tecnico
        INSERT INTO usuario (id_rol, nombre, email, telefono, password_hash, activo)
        SELECT 
            3 AS id_rol,
            t.nombre,
            t.email,
            t.telefono,
            t.password_hash,
            t.activo
        FROM tecnico t
        WHERE t.email NOT IN (SELECT email FROM usuario WHERE email IS NOT NULL)
        ON CONFLICT (email) DO NOTHING;
        
        -- Vincular usuarios técnicos a talleres
        INSERT INTO usuario_taller (id_usuario, id_taller, disponible, activo, latitud, longitud, created_at)
        SELECT 
            u.id_usuario,
            t.id_taller,
            t.disponible,
            t.activo,
            t.latitud,
            t.longitud,
            t.created_at
        FROM tecnico t
        JOIN usuario u ON u.email = t.email AND u.id_rol = 3
        ON CONFLICT (id_usuario, id_taller) DO NOTHING;
        
        RAISE NOTICE 'Migración completada: % técnicos migrados', 
            (SELECT COUNT(*) FROM usuario_taller);
    END IF;
END $$;
*/


-- ============ PASO 3: ACTUALIZAR FOREIGN KEY EN asignacion ============

-- Si la tabla asignacion aún tiene id_tecnico, cambiarla a id_usuario:
-- NOTA: Ejecutar SOLO si asignacion.id_tecnico existe
/*
-- 1. Agregar columna id_usuario si no existe
ALTER TABLE asignacion ADD COLUMN IF NOT EXISTS id_usuario INTEGER REFERENCES usuario(id_usuario);

-- 2. Migrar datos: id_tecnico → id_usuario (asumiendo email único)
UPDATE asignacion a
SET id_usuario = u.id_usuario
FROM tecnico t
JOIN usuario u ON u.email = t.email AND u.id_rol = 3
WHERE a.id_tecnico = t.id_tecnico;

-- 3. Eliminar columna id_tecnico si ya no se necesita
-- ALTER TABLE asignacion DROP COLUMN id_tecnico;
*/


-- ============ PASO 4: ELIMINAR TABLA tecnico (OPCIONAL) ============

-- SOLO ejecutar esto si ya no hay datos críticos en la tabla tecnico
-- y has confirmado que la migración a usuario_taller fue exitosa:
/*
DROP TABLE IF EXISTS tecnico CASCADE;
*/


-- ============ VERIFICACIÓN ============

-- Verificar que usuario_taller se creó correctamente
SELECT 
    'usuario_taller' AS tabla,
    COUNT(*) AS registros,
    COUNT(DISTINCT id_usuario) AS usuarios_unicos,
    COUNT(DISTINCT id_taller) AS talleres_unicos
FROM usuario_taller;

-- Verificar usuarios técnicos (rol=3)
SELECT 
    'usuario (rol=3)' AS tabla,
    COUNT(*) AS registros
FROM usuario
WHERE id_rol = 3;

-- Listar técnicos vinculados a talleres
SELECT 
    ut.id_usuario_taller,
    u.id_usuario,
    u.nombre,
    u.email,
    t.id_taller,
    t.nombre AS taller_nombre,
    ut.disponible,
    ut.activo,
    ut.created_at
FROM usuario_taller ut
JOIN usuario u ON ut.id_usuario = u.id_usuario
JOIN taller t ON ut.id_taller = t.id_taller
ORDER BY t.id_taller, u.nombre;
