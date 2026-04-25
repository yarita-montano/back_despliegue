## 🔄 REFACTORIZACIÓN PROFUNDA: Eliminación de Tabla Técnico

### Cambio de Arquitectura

```
❌ ANTES (Arquitectura Duplicada):
┌─────────────────┐
│   USUARIO       │  (clientes + admin)
├─────────────────┤
│ id_usuario      │
│ id_rol          │
│ nombre, email   │
└─────────────────┘

┌─────────────────┐
│   TECNICO       │  (tabla separada, sin login)
├─────────────────┤
│ id_tecnico      │
│ id_taller (FK)  │
│ nombre, email   │
│ password_hash   │
└─────────────────┘
                        ↓
┌─────────────────┐  
│  ASIGNACION     │
├─────────────────┤
│ id_asignacion   │
│ id_tecnico (FK) │ ← Desconectado de usuario
│ id_taller       │
└─────────────────┘


✅ DESPUÉS (Arquitectura Limpia):
┌─────────────────────────────┐
│       USUARIO               │
├─────────────────────────────┤
│ id_usuario                  │
│ id_rol = 3 (para técnico)   │
│ nombre, email, password     │
│ activo                      │
└─────────────────────────────┘
        ↑          ↑
        │          │
        │    ┌─────────────────────────┐
        │    │  USUARIO_TALLER         │
        │    ├─────────────────────────┤
        │    │ id_usuario (FK)         │
        │    │ id_taller (FK)          │
        │    │ disponible              │
        │    │ latitud, longitud       │
        │    │ activo                  │
        │    └─────────────────────────┘
        │            ↓
        │    ┌─────────────────────┐
        └───→│   TALLER            │
             ├─────────────────────┤
             │ id_taller           │
             │ nombre, email       │
             └─────────────────────┘
                      ↓
             ┌──────────────────────┐
             │   ASIGNACION         │
             ├──────────────────────┤
             │ id_usuario (FK)      │ ← Usuario técnico directo
             │ id_taller (FK)       │
             │ id_incidente         │
             └──────────────────────┘
```

### Cambios en Código

#### 1. **Modelos ORM**
```
usuario.py:
  ✅ Agregar relationship: talleres_asociados → UsuarioTaller

usuario_taller.py: (NUEVO)
  ✅ Tabla de asociación usuario ↔ taller
  
taller.py:
  ✅ Cambiar relationship: tecnicos → usuarios_tecnicos
  ❌ Eliminar relación directa: tecnicos

incidente.py:
  ✅ Cambiar FK: id_tecnico → id_usuario
```

#### 2. **API Endpoints (talleres.py)**

Antes (comentados):
```
# Endpoints CRUD de Tecnico (tabla antigua) desactivados
```

Ahora (activos):
```
GET    /mi-taller/tecnicos              → Listar técnicos vinculados
GET    /mi-taller/tecnicos/{id}         → Obtener técnico
POST   /mi-taller/tecnicos              → Crear usuario técnico + vincular
PUT    /mi-taller/tecnicos/{id}         → Actualizar (disponibilidad, ubicación)
DELETE /mi-taller/tecnicos/{id}         → Remover técnico del taller
```

#### 3. **Schemas (taller_schema.py)**

Nuevos:
- `UsuarioTallerCreate` → Para crear técnico
- `UsuarioTallerUpdate` → Para actualizar datos
- `UsuarioTallerResponse` → Respuesta detallada
- `UsuarioTallerListResponse` → Respuesta para listados

Actualizados:
- `AsignacionTallerResponse`: `id_tecnico` → `id_usuario`
- `TecnicoAsignacionResponse`: `id_tecnico` → `id_usuario`

#### 4. **Flujo de Creación de Técnico**

Antes:
```
Taller POST /mi-taller/tecnicos
  ↓
Crear registro en tabla tecnico
  ↓
¿Técnico tiene login? → Email + password_hash
  ❌ Problema: No reutiliza tabla usuario
```

Ahora:
```
Taller POST /mi-taller/tecnicos (UsuarioTallerCreate)
  ↓
1. Crear Usuario(rol=3, email, password_hash)
2. Crear UsuarioTaller(id_usuario, id_taller, disponible=true)
  ↓
Técnico puede hacer login con POST /usuarios/login
Técnico accede a endpoints de técnico como usuario (id_rol=3)
```

#### 5. **Flujo de Asignación**

Antes:
```
POST /incidencias/{id}/aceptar-asignacion
  └─ Asignacion.id_tecnico = payload.id_tecnico
  └─ Motor busca en tabla tecnico
  ❌ Desconectado de autenticación
```

Ahora:
```
PUT /mi-taller/asignaciones/{id}/aceptar
  └─ Asignacion.id_usuario = payload.id_usuario
  └─ Valida Usuario(id_rol=3, activo=true)
  └─ Técnico puede hacer login con credenciales propias
  ✅ Conectado a autenticación
```

### Migraciones BD Requeridas

1. **Crear tabla usuario_taller**: Ver [002_tecnico_to_usuario_taller.sql](migrations/002_tecnico_to_usuario_taller.sql)

2. **Migrar datos (opcional)**:
   - Si hay técnicos existentes en tabla tecnico
   - Crear usuarios correspondientes en tabla usuario (rol=3)
   - Vincular vía usuario_taller

3. **Eliminar tabla tecnico (opcional)**:
   - Después de verificar migración exitosa
   - `DROP TABLE tecnico;`

### Ventajas de la Refactorización

| Aspecto | Antes | Después |
|---------|-------|---------|
| **Duplicación de Data** | ❌ Usuario + Tecnico | ✅ Solo Usuario |
| **Autenticación** | ❌ Tabla separada | ✅ POST /usuarios/login |
| **Relación Taller** | ❌ FK directo (1:N) | ✅ Tabla de asociación (M:N) |
| **Flexibilidad** | ❌ Técnico en 1 taller | ✅ Técnico en N talleres |
| **Consistency** | ❌ Dos modelos | ✅ Un modelo Usuario |
| **Código** | ❌ Múltiples funciones | ✅ Lógica centralizada |

### Testing Recomendado

```bash
# 1. Crear técnico (rol=3)
POST /mi-taller/tecnicos
{
  "nombre": "Juan Pérez",
  "email": "juan@taller.com",
  "password": "secure_password123",
  "telefono": "+57 310..."
}

# 2. Login como técnico
POST /usuarios/login
{
  "email": "juan@taller.com",
  "password": "secure_password123"
}
# Respuesta: { "access_token": "...", "token_type": "bearer" }

# 3. Acceder a endpoints de técnico
GET /tecnicos/asignacion-actual
# Header: Authorization: Bearer <token>

# 4. Motor de asignación
POST /incidencias
# Crea Asignacion con id_usuario (no id_tecnico)

# 5. Aceptar asignación
PUT /mi-taller/asignaciones/{id}/aceptar
{
  "id_usuario": 5,
  "eta_minutos": 30
}
```

### Archivos Modificados

- [usuario.py](app/models/usuario.py) - Agregar relationship
- [usuario_taller.py](app/models/usuario_taller.py) - NUEVO modelo
- [taller.py](app/models/taller.py) - Cambiar relationship
- [talleres.py](app/api/talleres.py) - Reactivar endpoints CRUD
- [taller_schema.py](app/schemas/taller_schema.py) - Nuevos schemas
- [002_tecnico_to_usuario_taller.sql](migrations/002_tecnico_to_usuario_taller.sql) - Script SQL

### Próximos Pasos

- [ ] Ejecutar migración SQL en BD
- [ ] Crear técnicos de prueba con nuevo flujo
- [ ] Probar endpoints de técnico
- [ ] Actualizar documentación de API
- [ ] Actualizar guías Flutter/Frontend
