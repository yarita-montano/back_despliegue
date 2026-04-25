# 🔄 CICLO DE ASIGNACIÓN DE TÉCNICO

## Flujo Completo: Cliente → Taller → Técnico

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         1️⃣  CLIENTE REPORTA EMERGENCIA                      │
└─────────────────────────────────────────────────────────────────────────────┘

POST /incidencias
├─ id_usuario: 2 (del JWT)
├─ id_vehiculo: 5
├─ descripcion_usuario: "Mi vehículo no enciende"
├─ latitud: 4.7110
└─ longitud: -74.0086

RESPUESTA (201 Created):
{
  "id_incidente": 15,
  "id_usuario": 2,
  "id_estado": 1,                    ← "pendiente"
  "descripcion_usuario": "...",
  "created_at": "2026-04-22T15:45:00"
}

┌─────────────────────────────────────────────────────────────────────────────┐
│                    2️⃣  IA ANALIZA Y MOTOR ELIGE CANDIDATOS                 │
└─────────────────────────────────────────────────────────────────────────────┘

POST /incidencias/15/analizar-ia
├─ Claude Sonnet 4.5 analiza la descripción
├─ Rellena id_categoria (ej: 4 = "Motor")
├─ Rellena id_prioridad (ej: 2 = "Media")
└─ Rellena resumen_ia

Motor de Asignación (async job):
├─ Busca talleres cercanos (radio 10-20 km)
├─ Calcula puntuación por:
│  ├─ Distancia
│  ├─ Disponibilidad de técnicos
│  ├─ Rating histórico
│  └─ Número de asignaciones activas
├─ Crea 3-5 "candidatos" en orden de puntuación
└─ Marca el primero como "seleccionado" automáticamente

TABLA: candidato_asignacion
┌─────────────────────────────────────────┐
│ id_incidente │ id_taller │ puntuacion  │
├─────────────────────────────────────────┤
│     15       │    2      │    95.2     │  ← seleccionado
│     15       │    3      │    87.5     │
│     15       │    5      │    72.1     │
└─────────────────────────────────────────┘

TABLA: incidente
└─ id_incidente: 15
   ├─ id_taller: 2 (taller seleccionado)
   ├─ id_estado: 1 (pendiente)
   └─ id_usuario: 2 (cliente)

┌─────────────────────────────────────────────────────────────────────────────┐
│              3️⃣  TALLER RECIBE NOTIFICACIÓN DE ASIGNACIÓN                   │
└─────────────────────────────────────────────────────────────────────────────┘

Taller ID 2 recibe una PUSH NOTIFICATION:
"Nuevo incidente - Cliente en Calle 10, Batería descargada"

El taller puede:
├─ VER DETALLES: GET /talleres/mi-taller/asignaciones/15
├─ ACEPTAR: PUT /talleres/mi-taller/asignaciones/15/aceptar
└─ RECHAZAR: PUT /talleres/mi-taller/asignaciones/15/rechazar

┌─────────────────────────────────────────────────────────────────────────────┐
│            4️⃣  TALLER ACEPTA Y ASIGNA UN TÉCNICO (IMPORTANTE!)             │
└─────────────────────────────────────────────────────────────────────────────┘

PUT /talleres/mi-taller/asignaciones/15/aceptar
{
  "id_usuario": 4,      ← 🔴 ID DEL USUARIO TÉCNICO (rol=3)
  "eta_minutos": 25,
  "nota": "Enviando a Juan, ETA 25 minutos"
}

VALIDACIONES EN EL BACKEND:
1. Usuario 4 existe
2. Usuario 4 tiene rol=3 (técnico)
3. Usuario 4 está activo
4. No puede tener una asignación activa simultáneamente
   (un técnico solo puede tener UNA asignación a la vez en estados "aceptada" o "en_camino")

SI PASA LAS VALIDACIONES:
TABLA: asignacion
┌──────────────────────────────────────────────────┐
│ id_asignacion │ id_usuario │ id_estado │ created  │
├──────────────────────────────────────────────────┤
│      120      │     4      │    2      │ ....... │
│               │            │ "aceptada"│         │
└──────────────────────────────────────────────────┘

TABLA: historial_estado_asignacion
┌─────────────────────────────────────────────────────┐
│ id_hist │ id_asignacion │ estado_anterior │ estado_nuevo │
├─────────────────────────────────────────────────────┤
│  3451   │     120       │  "pendiente"    │  "aceptada"  │
│         │               │ observación:    │              │
│         │               │ "Aceptada por   │              │
│         │               │  taller 2.      │              │
│         │               │  Técnico: 4"    │              │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                   5️⃣  TÉCNICO VE SU ASIGNACIÓN ACTUAL                      │
└─────────────────────────────────────────────────────────────────────────────┘

Técnico Juan (id_usuario: 4) abre su app móvil

GET /tecnicos/asignacion-actual
Header: Authorization: Bearer <jwt_tecnico>

VALIDACIONES:
1. ¿El JWT es válido?
2. ¿El usuario es técnico (id_rol == 3)?
3. ¿Tiene una asignación en estado "aceptada" o "en_camino"?

SI CUMPLE:
RESPUESTA (200 OK):
{
  "id_asignacion": 120,
  "id_incidente": 15,
  "id_taller": 2,
  "id_usuario": 4,              ← Técnico Juan
  "id_estado_asignacion": 2,    ← "aceptada"
  "eta_minutos": 25,
  "costo_estimado": 85000,
  "cliente": {
    "nombre": "María García",
    "telefono": "+57 312 555 1234"
  },
  "vehiculo": {
    "marca": "Toyota",
    "modelo": "Corolla",
    "placa": "ABC-123"
  },
  "incidente": {
    "descripcion_usuario": "Batería descargada",
    "categoria": "Batería",
    "latitud": 4.7110,
    "longitud": -74.0086
  },
  "eta_minutos": 25,
  "created_at": "2026-04-22T15:47:30"
}

SI NO HAY ASIGNACIÓN:
RESPUESTA (404 Not Found):
{
  "detail": "No tienes asignaciones activas en este momento"
}

┌─────────────────────────────────────────────────────────────────────────────┐
│           6️⃣  TÉCNICO SALE HACIA EL CLIENTE (INICIA VIAJE)                │
└─────────────────────────────────────────────────────────────────────────────┘

Juan toca el botón "Saliendo hacia el cliente"

PUT /tecnicos/mis-asignaciones/120/iniciar-viaje
{
  "latitud": 4.7085,
  "longitud": -74.0105
}

TRANSICIÓN DE ESTADO:
"aceptada" → "en_camino"

TABLA: asignacion
┌──────────────────────────────────────────┐
│ id_asignacion │ id_estado │ latitud      │
├──────────────────────────────────────────┤
│     120       │    3      │ 4.7085       │
│               │"en_camino"│ longitud...  │
└──────────────────────────────────────────┘

TABLA: historial_estado_asignacion
(nuevo registro)
┌──────────────────────────────────────────────────┐
│ id_asignacion │ estado_anterior │ estado_nuevo   │
├──────────────────────────────────────────────────┤
│      120      │  "aceptada"     │   "en_camino"  │
│               │                 │ observación:   │
│               │                 │ "Juan sale a   │
│               │                 │  las 15:49"    │
└──────────────────────────────────────────────────┘

CLIENTE RECIBE NOTIFICACIÓN:
"Tu técnico está en camino (ETA 18 minutos)"

┌─────────────────────────────────────────────────────────────────────────────┐
│         7️⃣  TÉCNICO COMPLETA EL SERVICIO (MARCA COMO LISTO)               │
└─────────────────────────────────────────────────────────────────────────────┘

Juan llega y repara la batería (25 minutos después)

Toca "Servicio completado"

PUT /tecnicos/mis-asignaciones/120/completar
{
  "observaciones": "Batería reemplazada, vehículo funcionando OK",
  "fotos_antes": [url1, url2],
  "fotos_despues": [url3, url4]
}

TRANSICIÓN DE ESTADO:
"en_camino" → "completada"

TABLA: asignacion
└─ id_asignacion: 120
   ├─ id_estado: 4 ("completada")
   ├─ observaciones: "Batería reemplazada..."
   └─ updated_at: "2026-04-22T16:14:30"

TABLA: incidente
└─ id_incidente: 15
   ├─ id_estado: 2 ("en_proceso" → "atendido")
   └─ observaciones_taller: "..."

CLIENTE RECIBE NOTIFICACIÓN:
"Tu servicio ha sido completado 🎉"
"Visualizar servicio" → puede ver fotos, costo, comentarios del técnico

┌─────────────────────────────────────────────────────────────────────────────┐
│                8️⃣  CLIENTE EVALÚA AL TÉCNICO Y TALLER (OPCIONAL)          │
└─────────────────────────────────────────────────────────────────────────────┘

Cliente María abre "Ver detalle del servicio"

POST /incidencias/15/evaluar
{
  "estrellas": 5,
  "comentario": "Muy rápido y profesional",
  "id_usuario": 4,    ← Evaluación al técnico Juan
  "id_taller": 2      ← Evaluación al taller
}

TABLA: evaluacion
┌────────────────────────────────┐
│ id_evaluacion │ id_usuario │ ⭐│
├────────────────────────────────┤
│     8451      │     4      │ 5 │
└────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                    📊 RESUMEN DE ESTADOS Y TRANSICIONES                     │
└─────────────────────────────────────────────────────────────────────────────┘

ASIGNACIÓN (tabla asignacion):
pendiente → aceptada → en_camino → completada
   ↓          ↓           ↓           ↓
  [Taller     [Técnico    [Técnico  [Evaluación]
   decide]    asignado]   llega]    [Fin]

Si taller rechaza:
pendiente → rechazada → [Cliente elige otro taller]

INCIDENTE (tabla incidente):
pendiente → en_proceso → atendido → cancelado (si aplica)
   ↓          ↓             ↓
[Se crea] [Taller         [Técnico
          acepta]         completa]

┌─────────────────────────────────────────────────────────────────────────────┐
│         🔴 RESTRICCIÓN IMPORTANTE: UN TÉCNICO = UNA ASIGNACIÓN A LA VEZ     │
└─────────────────────────────────────────────────────────────────────────────┘

VALIDACIÓN EN EL ENDPOINT /talleres/mi-taller/asignaciones/{id}/aceptar:

```python
# Verificar que el técnico NO tiene otra asignación activa
active_assignment = db.query(Asignacion).filter(
    Asignacion.id_usuario == payload.id_usuario,
    Asignacion.id_estado_asignacion.in_(
        db.query(EstadoAsignacion.id_estado_asignacion).filter(
            EstadoAsignacion.nombre.in_(["aceptada", "en_camino"])
        )
    )
).first()

if active_assignment:
    raise HTTPException(
        status_code=400,
        detail=f"El técnico ya tiene una asignación activa (ID: {active_assignment.id_asignacion})"
    )
```

ESTO SIGNIFICA:
- Si el técnico 4 está en una asignación "aceptada" o "en_camino"
- NO puede aceptar una nueva asignación
- DEBE completar primero la actual

CICLO PARA EL TÉCNICO:
1. GET /tecnicos/asignacion-actual → obtiene trabajo asignado
2. PUT /tecnicos/mis-asignaciones/{id}/iniciar-viaje → sale
3. PUT /tecnicos/mis-asignaciones/{id}/completar → termina
4. Ahora está libre para aceptar otra asignación

┌─────────────────────────────────────────────────────────────────────────────┐
│                        📱 ENDPOINTS POR ROL                                 │
└─────────────────────────────────────────────────────────────────────────────┘

👤 CLIENTE (Usuario rol=1):
├─ POST   /incidencias                              Reportar emergencia
├─ GET    /incidencias/mis-incidencias              Ver historial
├─ POST   /incidencias/{id}/analizar-ia             IA analiza
└─ POST   /incidencias/{id}/evaluar                 Evalúa técnico

🏭 TALLER (tabla taller):
├─ POST   /talleres/login                           Login del taller
├─ GET    /talleres/mi-taller                       Ver info
├─ PUT    /talleres/mi-taller/asignaciones/{id}/aceptar      ← ASIGNA TÉCNICO
├─ PUT    /talleres/mi-taller/asignaciones/{id}/rechazar     
├─ GET    /talleres/mi-taller/asignaciones                   Ver asignaciones
├─ POST   /talleres/mi-taller/tecnicos               Crear técnico (usuario rol=3)
├─ GET    /talleres/mi-taller/tecnicos               Listar técnicos del taller
├─ PUT    /talleres/mi-taller/tecnicos/{id}         Actualizar técnico
└─ DELETE /talleres/mi-taller/tecnicos/{id}         Desactivar técnico

🔧 TÉCNICO (Usuario rol=3):
├─ POST   /usuarios/login                           Login como usuario rol=3
├─ GET    /tecnicos/asignacion-actual               ← VER ASIGNACIÓN
├─ PUT    /tecnicos/mis-asignaciones/{id}/iniciar-viaje       Salir
└─ PUT    /tecnicos/mis-asignaciones/{id}/completar           Terminar

┌─────────────────────────────────────────────────────────────────────────────┐
│                    🧪 EJEMPLO DE REQUEST/RESPONSE                           │
└─────────────────────────────────────────────────────────────────────────────┘

=== 1. CLIENTE REPORTA ===
POST http://localhost:8000/incidencias
Authorization: Bearer <JWT_CLIENTE>
Content-Type: application/json

{
  "id_vehiculo": 5,
  "descripcion_usuario": "Mi carro no enciende",
  "latitud": 4.7110,
  "longitud": -74.0086
}

Response (201):
{
  "id_incidente": 15,
  "id_usuario": 2,
  "id_estado": 1,
  "created_at": "2026-04-22T15:45:00"
}

=== 2. TALLER ACEPTA Y ASIGNA ===
PUT http://localhost:8000/talleres/mi-taller/asignaciones/15/aceptar
Authorization: Bearer <JWT_TALLER>
Content-Type: application/json

{
  "id_usuario": 4,
  "eta_minutos": 25,
  "nota": "Enviando a Juan"
}

Response (200):
{
  "id_asignacion": 120,
  "id_usuario": 4,
  "id_estado_asignacion": 2,
  "eta_minutos": 25
}

=== 3. TÉCNICO VE SU ASIGNACIÓN ===
GET http://localhost:8000/tecnicos/asignacion-actual
Authorization: Bearer <JWT_TECNICO>

Response (200):
{
  "id_asignacion": 120,
  "id_incidente": 15,
  "cliente": {
    "nombre": "María García",
    "telefono": "+57 312 555 1234"
  },
  "vehiculo": {
    "marca": "Toyota",
    "placa": "ABC-123"
  },
  "incidente": {
    "descripcion_usuario": "Mi carro no enciende",
    "latitud": 4.7110,
    "longitud": -74.0086
  },
  "eta_minutos": 25
}

=== 4. TÉCNICO INICIA VIAJE ===
PUT http://localhost:8000/tecnicos/mis-asignaciones/120/iniciar-viaje
Authorization: Bearer <JWT_TECNICO>
Content-Type: application/json

{
  "latitud": 4.7090,
  "longitud": -74.0100
}

Response (200):
{
  "id_asignacion": 120,
  "id_estado_asignacion": 3,  ← en_camino
  "latitud": 4.7090,
  "longitud": -74.0100
}

=== 5. TÉCNICO COMPLETA ===
PUT http://localhost:8000/tecnicos/mis-asignaciones/120/completar
Authorization: Bearer <JWT_TECNICO>
Content-Type: application/json

{
  "observaciones": "Batería reemplazada"
}

Response (200):
{
  "id_asignacion": 120,
  "id_estado_asignacion": 4,  ← completada
  "observaciones": "Batería reemplazada"
}
