# 🔐 Guía Completa: Sistemas de Autenticación

## 📊 Resumen Ejecutivo

La plataforma YARY tiene **3 sistemas de autenticación independientes** con tokens JWT:

| Actores | Endpoint | Tabla BD | Rol | Campo Unique | Validación |
|---------|----------|----------|-----|--------------|-----------|
| **Cliente** (Usuario final) | `POST /usuarios/login` | `usuario` | `id_rol=1` | `email` | `get_current_user` |
| **Técnico** (Especialista) | `POST /usuarios/login` | `usuario` | `id_rol=3` | `email` | `get_current_user` + validar `id_rol=3` |
| **Taller** (Panel web) | `POST /talleres/login` | `taller` | N/A | `email` | `get_current_taller` |

---

## 1️⃣ LOGIN DE CLIENTE (Usuario Final)

### 📌 Descripción
Clientes de la app móvil se registran y autentican con email + password.

### 🔗 Endpoints

#### A. Registro (POST `/usuarios/registro`)
```bash
POST http://localhost:8000/usuarios/registro
Content-Type: application/json

{
  "nombre": "Juan Pérez",
  "email": "juan@example.com",
  "password": "seguro123!",
  "telefono": "+57 3001234567"
}
```

**Response (201 Created):**
```json
{
  "id_usuario": 1,
  "id_rol": 1,
  "nombre": "Juan Pérez",
  "email": "juan@example.com",
  "activo": true,
  "created_at": "2026-04-15T10:30:00"
}
```

**Errores:**
- `409 Conflict`: Email ya registrado
- `400 Bad Request`: Validación fallida

---

#### B. Login (POST `/usuarios/login`)
```bash
POST http://localhost:8000/usuarios/login
Content-Type: application/json

{
  "email": "juan@example.com",
  "password": "seguro123!"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "usuario": {
    "id_usuario": 1,
    "id_rol": 1,
    "nombre": "Juan Pérez",
    "email": "juan@example.com",
    "activo": true,
    "created_at": "2026-04-15T10:30:00"
  }
}
```

**Errores:**
- `401 Unauthorized`: Email o contraseña incorrectos
- `403 Forbidden`: Cuenta desactivada

---

#### C. Mi Perfil (GET `/usuarios/perfil`)
```bash
GET http://localhost:8000/usuarios/perfil
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "id_usuario": 1,
  "id_rol": 1,
  "nombre": "Juan Pérez",
  "email": "juan@example.com",
  "activo": true,
  "created_at": "2026-04-15T10:30:00",
  "rol": {
    "id_rol": 1,
    "nombre": "cliente"
  }
}
```

---

#### D. Actualizar Perfil (PUT `/usuarios/perfil`)
```bash
PUT http://localhost:8000/usuarios/perfil
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "nombre": "Juan Pérez Actualizado",
  "telefono": "+57 3105551234",
  "password": "nuevaPassword123!"
}
```

**Notas:**
- Todos los campos son opcionales
- El email NO se puede cambiar
- La contraseña se hashea automáticamente

---

#### E. Dar de Baja (DELETE `/usuarios/perfil`)
```bash
DELETE http://localhost:8000/usuarios/perfil
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "mensaje": "Tu cuenta (juan@example.com) ha sido desactivada correctamente..."
}
```

**Implementa baja lógica:** `activo = false` (no se eliminan datos, se preserva trazabilidad)

---

## 2️⃣ LOGIN DE TÉCNICO (Usuario con rol 3)

### 📌 Descripción
Los **técnicos son usuarios con `id_rol=3`** que se autentican con email + contraseña. Usan el mismo endpoint de login que los clientes, pero los endpoints específicos validan el rol.

**Arquitectura:**
- Tabla: `usuario` (compartida con clientes)
- Rol: `id_rol = 3`
- Vinculación a taller: tabla `usuario_taller` (un técnico puede trabajar en múltiples talleres)
- Autenticación: `get_current_user()` + validar `id_rol == 3`

---

### 🔗 Endpoint de Login

#### Login (POST `/usuarios/login`)
**Mismo endpoint que clientes, pero con credenciales de técnico:**

```bash
POST http://localhost:8000/usuarios/login
Content-Type: application/json

{
  "email": "tecnico@tallerexcelente.com",
  "password": "tecnico123"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "usuario": {
    "id_usuario": 42,
    "id_rol": 3,
    "nombre": "Juan Pérez",
    "email": "tecnico@tallerexcelente.com",
    "telefono": "3115551234",
    "activo": true,
    "created_at": "2026-04-22T10:30:00"
  }
}
```

**Errores:**
- `401 Unauthorized`: Email o contraseña incorrectos
- `403 Forbidden`: Cuenta desactivada

---

### ✅ Endpoints Específicos del Técnico (Autenticado)

#### 1. Obtener Asignación Actual (GET `/tecnicos/asignacion-actual`)
```bash
GET http://localhost:8000/tecnicos/asignacion-actual
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "id_asignacion": 42,
  "id_incidente": 100,
  "id_usuario": 42,
  "id_taller": 5,
  "estado": { "id_estado_asignacion": 2, "nombre": "aceptada" },
  "incidente": { /* detalles del incidente */ }
}
```

**Errores:**
- `403 Forbidden`: Usuario no es técnico (rol ≠ 3)
- `404 Not Found`: Sin asignaciones activas

---

#### 2. Iniciar Viaje (PUT `/tecnicos/mis-asignaciones/{id_asignacion}/iniciar-viaje`)
```bash
PUT http://localhost:8000/tecnicos/mis-asignaciones/42/iniciar-viaje
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "latitud_tecnico": 4.7150,
  "longitud_tecnico": -74.0700
}
```

**Transición de estado:** `aceptada` → `en_camino`

**Response (200 OK):** AsignacionTecnico actualizada

**Errores:**
- `403 Forbidden`: Usuario no es técnico
- `400 Bad Request`: Asignación no está en estado "aceptada"
- `404 Not Found`: Asignación no asignada a ti

---

#### 3. Completar Servicio (PUT `/tecnicos/mis-asignaciones/{id_asignacion}/completar`)
```bash
PUT http://localhost:8000/tecnicos/mis-asignaciones/42/completar
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "costo_estimado": 50000,
  "resumen_trabajo": "Se cambió la batería"
}
```

**Transición de estado:** `en_camino` → `completada` + incidente pasa a `atendido`

**Response (200 OK):** AsignacionTecnico actualizada

**Errores:**
- `403 Forbidden`: Usuario no es técnico
- `400 Bad Request`: Asignación no está en estado "en_camino"
- `404 Not Found`: Asignación no asignada a ti

---

## 3️⃣ LOGIN DE TALLER (Panel Web)

### 📌 Descripción
Los talleres tienen panel web para gestionar asignaciones, técnicos y servicios.

### 🔗 Endpoint

#### Login (POST `/talleres/login`)
```bash
POST http://localhost:8000/talleres/login
Content-Type: application/json

{
  "email": "taller@example.com",
  "password": "taller123"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "taller": {
    "id_taller": 5,
    "nombre": "Taller Excelente",
    "email": "taller@example.com",
    "telefono": "3101234567",
    "direccion": "Carrera 10 #20-30",
    "latitud": 4.7111,
    "longitud": -74.0721,
    "capacidad_max": 5,
    "disponible": true,
    "activo": true,
    "verificado": true,
    "created_at": "2026-01-15T10:30:00"
  }
}
```

---

## 🔧 SISTEMA DE TOKENS JWT

### Estructura del Token
Todos los tokens son JWT con estructura:
```
{
  "sub": "ID",              // id_usuario | id_tecnico | id_taller
  "tipo": "usuario|tecnico|taller",
  "exp": 1234567890,       // Expiration time
  "iat": 1234567800        // Issued at
}
```

### Duración
- Default: 60 minutos (configurable en `app/core/config.py`)
- Variable: `ACCESS_TOKEN_EXPIRE_MINUTES`

### Uso en Requests
```bash
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 🛡️ VALIDACIÓN DE TOKENS Y ROLES

### Token JWT
Todos los tokens tienen la misma estructura:
```json
{
  "sub": "ID",              // id_usuario o id_taller
  "tipo": "usuario|taller",  // Tipo de actor
  "exp": 1234567890,        // Expiration
  "iat": 1234567800         // Issued at
}
```

### Validación por Endpoint

| Endpoint | Token | Validación Adicional | Función |
|----------|-------|----------------------|---------|
| `/usuarios/login`, `/usuarios/registro`, `/usuarios/perfil` | `tipo="usuario"` | Ninguna | `get_current_user()` |
| `/tecnicos/*` | `tipo="usuario"` | `id_rol == 3` | `get_current_user()` + validar rol |
| `/talleres/*` | `tipo="taller"` | Ninguna | `get_current_taller()` |

**Patrón:** Técnicos usan el mismo token que clientes, pero endpoints específicos validan el rol.

---

## 📋 MATRIZ DE SEGURIDAD

```
┌────────────────────────────────────────────────────────────┐
│ CLIENTE (Usuario rol=1)                                    │
├────────────────────────────────────────────────────────────┤
│ ✅ Tabla: usuario (id_rol=1)                               │
│ ✅ Email: único                                            │
│ ✅ Password: hash Argon2                                   │
│ ✅ Endpoints: login, registro, perfil                      │
│ ✅ Token tipo: "usuario"                                   │
│ ✅ Función validación: get_current_user()                  │
│ ✅ Acciones: reportar incidencia, editar perfil            │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ TÉCNICO (Usuario rol=3)                                    │
├────────────────────────────────────────────────────────────┤
│ ✅ Tabla: usuario (id_rol=3)                               │
│ ✅ Vinculación: usuario_taller (puede estar en varios)     │
│ ✅ Email: único                                            │
│ ✅ Password: hash Argon2                                   │
│ ✅ Endpoint login: POST /usuarios/login                    │
│ ✅ Token tipo: "usuario"                                   │
│ ✅ Función validación: get_current_user() + id_rol==3      │
│ ✅ Acciones: iniciar-viaje, completar-asignacion           │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ TALLER (Panel Web)                                         │
├────────────────────────────────────────────────────────────┤
│ ✅ Tabla: taller (independiente)                           │
│ ✅ Email: único                                            │
│ ✅ Password: hash Argon2                                   │
│ ✅ Endpoints: login, mi-taller, gestión                    │
│ ✅ Token tipo: "taller"                                    │
│ ✅ Función validación: get_current_taller()                │
│ ✅ Acciones: aceptar, rechazar, gestionar técnicos         │
└────────────────────────────────────────────────────────────┘
```

---

## 🏗️ ARQUITECTURA DE TÉCNICOS

### Estructura de Datos

**tabla `usuario` (para técnicos, id_rol=3):**
```sql
SELECT * FROM usuario WHERE id_rol = 3;
-- id_usuario, nombre, email, password_hash, activo, ...
```

**tabla `usuario_taller` (vinculación):**
```sql
SELECT * FROM usuario_taller WHERE id_usuario = ?;
-- Permite que un técnico trabaje en múltiples talleres
-- Guarda ubicación y disponibilidad por taller
```

### Cómo se Crea un Técnico

El taller crea técnicos vía endpoint (en panel web):
```
POST /talleres/mi-taller/tecnicos
Authorization: Bearer <token-taller>

{
  "nombre": "Juan Pérez",
  "email": "juan.tecnico@example.com",
  "password": "segura123"
}
```

Esto:
1. Crea usuario en tabla `usuario` con `id_rol=3`
2. Crea entrada en `usuario_taller` vinculando usuario al taller
3. El técnico puede luego hacer login con `POST /usuarios/login`

---

## 📱 Resumen para Frontend

### Cliente (Flutter - App móvil)
```dart
// 1. Registrarse
POST /usuarios/registro
{email, password, nombre, telefono}

// 2. Iniciar sesión
POST /usuarios/login
{email, password}
// Response: access_token con tipo="usuario", id_rol=1

// 3. Guardar token en FlutterSecureStorage
await storage.write(key: 'access_token', value: response.access_token);

// 4. Usar en header para todas las llamadas
Authorization: Bearer {access_token}

// 5. Acciones autenticadas
GET /usuarios/perfil
PUT /usuarios/perfil
DELETE /usuarios/perfil
POST /incidencias/*
GET /incidencias/*
```

### Técnico (Flutter - App móvil)
```dart
// 1. El taller lo crea vía panel web:
//    POST /talleres/mi-taller/tecnicos {nombre, email, password}
//
//    El técnico recibe su email + password (por fuera de la app)

// 2. Técnico inicia sesión en su app con:
POST /usuarios/login
{email: "tecnico@example.com", password: "..."}
// Response: access_token con tipo="usuario", id_rol=3

// 3. Guardar token
await storage.write(key: 'tecnico_token', value: response.access_token);

// 4. Usar en header con rol validado automáticamente
Authorization: Bearer {tecnico_token}

// 5. Acciones específicas de técnico (endpoints validan rol=3)
GET /tecnicos/asignacion-actual
PUT /tecnicos/mis-asignaciones/{id}/iniciar-viaje {latitud, longitud}
PUT /tecnicos/mis-asignaciones/{id}/completar {costo_estimado, resumen}
```

### Taller (Angular - Panel web)
```typescript
// 1. Login
POST /talleres/login
{email, password}

// 2. Guardar token en localStorage
// 3. Usar en HTTP Interceptor: Authorization: Bearer <token>

// 4. Acciones autenticadas
GET /talleres/mi-taller
PUT /talleres/mi-taller/asignaciones/{id}/aceptar
GET /talleres/mi-taller/tecnicos
```

---

## 🔍 Comparación: Cliente vs Técnico vs Taller

| Característica | Cliente | Técnico | Taller |
|---|---|---|---|
| Tipo de app | Móvil | Móvil | Web |
| Tabla BD | `usuario` (id_rol=1) | `usuario` (id_rol=3) | `taller` |
| Campo único | `email` | `email` | `email` |
| Autenticación | `POST /usuarios/login` | `POST /usuarios/login` | `POST /talleres/login` |
| Token `tipo` | "usuario" | "usuario" | "taller" |
| Validación rol | Ninguna (es cliente) | `id_rol==3` | Ninguna |
| Vinculación | Ninguna | `usuario_taller` (a taller) | N/A |
| Puede tener múltiples | Vehículos | Talleres | N/A |
| Crear asignaciones | No | No | Sí |
| Aceptar asignaciones | No | No | Sí |
| Iniciar viaje | No | **Sí** | No |
| Completar servicio | No | **Sí** | No |
| Reportar incidencia | **Sí** | No | No |
| Editar perfil | Sí | Sí | Sí |
| Dar de baja | Sí | Sí | No

---

## ✅ CHECKLIST FUNCIONAL

### Cliente (Usuario rol=1)
- [x] Registro: `POST /usuarios/registro`
- [x] Login: `POST /usuarios/login`
- [x] Perfil: `GET /usuarios/perfil`
- [x] Actualizar perfil: `PUT /usuarios/perfil`
- [x] Dar de baja: `DELETE /usuarios/perfil`
- [x] Token JWT tipo "usuario"

### Técnico (Usuario rol=3)
- [x] Login: `POST /usuarios/login` (usa email/password de técnico)
- [x] Obtener asignación: `GET /tecnicos/asignacion-actual`
- [x] Iniciar viaje: `PUT /tecnicos/mis-asignaciones/{id}/iniciar-viaje`
- [x] Completar: `PUT /tecnicos/mis-asignaciones/{id}/completar`
- [x] Validación rol en endpoints
- [x] Token JWT tipo "usuario" + id_rol=3

### Taller
- [x] Login: `POST /talleres/login`
- [x] Gestión de asignaciones
- [x] Crear técnicos: `POST /talleres/mi-taller/tecnicos`
- [x] Token JWT tipo "taller"

---

## 🔐 Flujo de Seguridad Completo

```
CLIENTE quiere reportar incidencia
  ↓
POST /usuarios/login (email, password)
  ↓ Valida: usuario existe + password correcto + activo=true
  ↓
JWT {sub: id_usuario, tipo: "usuario", exp: ...}
  ↓
GET /usuarios/perfil + header Authorization: Bearer <JWT>
  ↓ get_current_user() descodifica + valida token
  ↓ Retorna usuario autenticado
  ✅

---

TÉCNICO quiere iniciar viaje
  ↓
POST /usuarios/login (email técnico, password)
  ↓ Valida: usuario existe + password correcto + activo=true
  ↓
JWT {sub: id_usuario, tipo: "usuario", exp: ...}
  ↓
PUT /tecnicos/mis-asignaciones/42/iniciar-viaje + header
  ↓ get_current_user() descodifica + valida token
  ↓ Endpoint valida: current_user.id_rol == 3
  ↓ Endpoint valida: asignación pertenece al técnico
  ✅

---

TALLER quiere aceptar asignación
  ↓
POST /talleres/login (email taller, password)
  ↓ Valida: taller existe + password correcto + activo=true
  ↓
JWT {sub: id_taller, tipo: "taller", exp: ...}
  ↓
PUT /talleres/mi-taller/asignaciones/42/aceptar + header
  ↓ get_current_taller() descodifica + valida token
  ↓ Valida: taller es propietario de asignación
  ✅
```
