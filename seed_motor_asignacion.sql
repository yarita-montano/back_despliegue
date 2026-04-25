-- Script para agregar datos de prueba necesarios para el Motor de Asignación
-- Este script SOLO agrega datos (INSERT), no modifica la estructura

-- ============================================================
-- 1. AGREGAR SERVICIOS AL TALLER
-- ============================================================
-- El taller con id_taller=1 atenderá las categorías principales
-- Esto es necesario para que el motor encuentre coincidencias

INSERT INTO taller_servicio (id_taller, id_categoria, servicio_movil)
VALUES 
  (1, 1, TRUE),   -- Categoría 1: Batería - Servicio móvil
  (1, 2, TRUE),   -- Categoría 2: Llanta - Servicio móvil
  (1, 3, FALSE),  -- Categoría 3: Choque - No móvil (requiere taller)
  (1, 4, TRUE),   -- Categoría 4: Motor - Servicio móvil
  (1, 5, TRUE),   -- Categoría 5: Llaves - Servicio móvil
  (1, 6, FALSE),  -- Categoría 6: Otros - No móvil
  (1, 7, FALSE)   -- Categoría 7: Incierto - No móvil
ON CONFLICT (id_taller, id_categoria) DO NOTHING;

-- ============================================================
-- 2. ASIGNAR CATEGORÍAS A INCIDENTES SIN CATEGORÍA
-- ============================================================
-- Actualizar incidentes que no tienen categoría asignada
-- Se les asigna categoría 1 (Batería) como prueba

UPDATE incidente 
SET id_categoria = 1 
WHERE id_categoria IS NULL;

-- ============================================================
-- 3. AGREGAR TÉCNICOS AL TALLER (opcional pero recomendado)
-- ============================================================
-- Si el motor necesita contar técnicos disponibles

INSERT INTO tecnico (id_taller, nombre, disponible, activo)
VALUES 
  (1, 'Juan Pérez', TRUE, TRUE),
  (1, 'Carlos García', TRUE, TRUE),
  (1, 'Miguel López', FALSE, TRUE)  -- Ocupado
ON CONFLICT DO NOTHING;

-- ============================================================
-- VERIFICACIÓN
-- ============================================================
-- Ejecutar estas queries para verificar que los datos se agregaron:

-- SELECT * FROM taller_servicio WHERE id_taller = 1;
-- SELECT COUNT(*) FROM incidente WHERE id_categoria IS NOT NULL;
-- SELECT * FROM tecnico WHERE id_taller = 1;
