# 🔧 Guía Frontend: Endpoints del Técnico (A.2 - CU-20)

## 📋 Resumen de Cambios

Los endpoints de **`iniciar-viaje`** y **`completar`** ahora están en el router del **TÉCNICO** (`/tecnicos/`), no en el taller.

**Razón**: El técnico es quien reporta que sale hacia el cliente y quien marca el trabajo como completado.

---

## 🔑 Autenticación del Técnico

### 1. Login del Técnico

**Endpoint**:
```
POST /tecnicos/login
Content-Type: application/json

{
  "email": "tecnico@ejemplo.com",
  "password": "password123"
}
```

**Respuesta**:
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "tecnico": {
    "id_tecnico": 5,
    "id_taller": 1,
    "nombre": "Juan Pérez",
    "telefono": "3115551234",
    "disponible": true,
    "latitud": 4.7110,
    "longitud": -74.0721,
    "activo": true,
    "created_at": "2026-04-22T10:30:00"
  }
}
```

**Almacenar**:
- `access_token` → usar en headers `Authorization: Bearer <token>`
- `id_tecnico` → necesario para los endpoints de asignaciones

---

## ⏯️ Endpoint 1: Iniciar Viaje

El técnico sale hacia el cliente. Transición: `aceptada` → `en_camino`

### Request

```
PUT /tecnicos/mis-asignaciones/{id_asignacion}/iniciar-viaje
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "latitud_tecnico": 4.7120,
  "longitud_tecnico": -74.0730
}
```

**Parámetros**:
- `id_asignacion` (path) - ID de la asignación que está en estado "aceptada"
- `latitud_tecnico` (body, opcional) - GPS actual del técnico
- `longitud_tecnico` (body, opcional) - GPS actual del técnico

### Response (200 OK)

```json
{
  "id_asignacion": 9,
  "id_incidente": 15,
  "id_tecnico": 5,
  "id_taller": 1,
  "eta_minutos": 30,
  "nota_taller": "Llegará en 30 min",
  "created_at": "2026-04-22T10:35:00",
  "updated_at": "2026-04-22T10:36:15",
  "estado": {
    "id_estado_asignacion": 3,
    "nombre": "en_camino"
  },
  "incidente": {
    "id_incidente": 15,
    "id_usuario": 2,
    "titulo": "Llanta pinchada",
    "descripcion": "Llanta trasera izquierda pinchada en autopista norte",
    "ubicacion": "Carrera 50 con Calle 80, Bogotá",
    "latitud": 4.7100,
    "longitud": -74.0700,
    "estado": {
      "id_estado": 2,
      "nombre": "en_proceso"
    }
  }
}
```

### Errores Posibles

| Status | Mensaje |
|--------|---------|
| 404 | "Asignación no encontrada o no asignada a ti" |
| 400 | "La asignación está en 'rechazada', solo se puede iniciar viaje desde 'aceptada'" |
| 401 | Token inválido o expirado |
| 500 | Error en catálogo de estados |

---

## ✅ Endpoint 2: Completar Asignación

El técnico marca el trabajo como completado. Transición: `en_camino` → `completada`

### Request

```
PUT /tecnicos/mis-asignaciones/{id_asignacion}/completar
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "costo_estimado": 85000,
  "resumen_trabajo": "Se cambió la llanta, se verificó alineación y presión de aire"
}
```

**Parámetros**:
- `id_asignacion` (path) - ID de la asignación que está en estado "en_camino"
- `costo_estimado` (body, opcional, número ≥ 0) - Costo final del servicio
- `resumen_trabajo` (body, opcional, string max 1000) - Descripción del trabajo realizado

### Response (200 OK)

```json
{
  "id_asignacion": 9,
  "id_incidente": 15,
  "id_tecnico": 5,
  "id_taller": 1,
  "eta_minutos": 30,
  "nota_taller": "Llegará en 30 min\n[TRABAJO] Se cambió la llanta, se verificó alineación y presión de aire",
  "created_at": "2026-04-22T10:35:00",
  "updated_at": "2026-04-22T10:45:30",
  "estado": {
    "id_estado_asignacion": 5,
    "nombre": "completada"
  },
  "incidente": {
    "id_incidente": 15,
    "id_usuario": 2,
    "titulo": "Llanta pinchada",
    "descripcion": "Llanta trasera izquierda pinchada en autopista norte",
    "ubicacion": "Carrera 50 con Calle 80, Bogotá",
    "latitud": 4.7100,
    "longitud": -74.0700,
    "estado": {
      "id_estado": 4,
      "nombre": "atendido"
    }
  }
}
```

### Efectos Secundarios

- ✅ `asignacion.estado` → `completada`
- ✅ `incidente.estado` → `atendido` (automático)
- ✅ Se registra en `historial_estado_asignacion` y `historial_estado_incidente`
- ✅ El cliente puede ahora evaluar el servicio con `POST /incidencias/{id}/evaluar`

### Errores Posibles

| Status | Mensaje |
|--------|---------|
| 404 | "Asignación no encontrada o no asignada a ti" |
| 400 | "La asignación está en 'aceptada', solo se puede completar desde 'en_camino'" |
| 401 | Token inválido o expirado |
| 500 | Error en catálogo de estados |

---

## 🛠️ Cambios en el Frontend Angular

### 1. Crear Servicio para Técnico (si no existe)

**`src/app/services/tecnico.service.ts`**:

```typescript
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class TecnicoService {
  private apiUrl = 'http://localhost:8000/tecnicos';

  constructor(private http: HttpClient) {}

  loginTecnico(email: string, password: string): Observable<any> {
    console.log('[TecnicoService] login →', { email });
    return this.http.post(`${this.apiUrl}/login`, { email, password });
  }

  iniciarViaje(idAsignacion: number, latitud: number, longitud: number): Observable<any> {
    console.log('[TecnicoService] iniciarViaje →', { idAsignacion, latitud, longitud });
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${localStorage.getItem('tecnico_token')}`
    });
    return this.http.put(
      `${this.apiUrl}/mis-asignaciones/${idAsignacion}/iniciar-viaje`,
      { latitud_tecnico: latitud, longitud_tecnico: longitud },
      { headers }
    );
  }

  completarServicio(idAsignacion: number, costo: number, resumen: string): Observable<any> {
    console.log('[TecnicoService] completarServicio →', { idAsignacion, costo, resumen });
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${localStorage.getItem('tecnico_token')}`
    });
    return this.http.put(
      `${this.apiUrl}/mis-asignaciones/${idAsignacion}/completar`,
      { costo_estimado: costo, resumen_trabajo: resumen },
      { headers }
    );
  }
}
```

### 2. En el Componente donde Aceptas la Asignación

Después de aceptar, el técnico necesita:
1. Obtener su geolocalización
2. Hacer clic en "Iniciar Viaje"

**Ejemplo**:

```typescript
import { TecnicoService } from '../services/tecnico.service';

export class SolicitudDetalleComponent {
  // ...

  iniciarViajeAhora() {
    if (!this.asignacion) return;

    // Obtener GPS del dispositivo
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const lat = position.coords.latitude;
          const lon = position.coords.longitude;

          console.log('[SolicitudDetalle] iniciarViajeAhora →', { lat, lon });

          this.tecnicoService.iniciarViaje(this.asignacion.id_asignacion, lat, lon)
            .subscribe(
              (resp) => {
                console.log('[SolicitudDetalle] iniciarViajeAhora ← OK', resp);
                this.asignacion = resp;
                this.mostrarNotificacion('¡Viaje iniciado!');
              },
              (error) => {
                console.error('[SolicitudDetalle] iniciarViajeAhora ← ERROR', error);
                this.mostrarError(error.error.detail || 'Error al iniciar viaje');
              }
            );
        },
        (error) => {
          console.error('Error obteniendo GPS:', error);
          this.mostrarError('No se pudo obtener tu ubicación');
        }
      );
    }
  }

  completarServicioAhora() {
    if (!this.asignacion) return;

    // Mostrar formulario modal con campos:
    // - Costo estimado (number)
    // - Resumen de trabajo (textarea)

    this.tecnicoService.completarServicio(
      this.asignacion.id_asignacion,
      this.costo,
      this.resumen
    ).subscribe(
      (resp) => {
        console.log('[SolicitudDetalle] completarServicio ← OK', resp);
        this.asignacion = resp;
        this.mostrarNotificacion('Servicio completado');
      },
      (error) => {
        console.error('[SolicitudDetalle] completarServicio ← ERROR', error);
        this.mostrarError(error.error.detail || 'Error al completar servicio');
      }
    );
  }
}
```

### 3. Almacenar el Token de Técnico

En `auth.service.ts` o `storage.service.ts`:

```typescript
// Guardar después de login
localStorage.setItem('tecnico_token', response.access_token);
localStorage.setItem('tecnico_id', response.tecnico.id_tecnico);
localStorage.setItem('tipo_auth', 'tecnico'); // para saber qué tipo de usuario es

// Limpiar al logout
localStorage.removeItem('tecnico_token');
localStorage.removeItem('tecnico_id');
```

### 4. Actualizar Headers en Interceptor (si existe)

Si tienes un HTTP interceptor, asegúrate de incluir el token de técnico:

```typescript
// en http.interceptor.ts o auth.interceptor.ts
intercept(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
  const tecnicoToken = localStorage.getItem('tecnico_token');
  const tallerToken = localStorage.getItem('taller_token');
  const usuarioToken = localStorage.getItem('access_token');

  let token: string | null = null;
  if (tecnicoToken) {
    token = tecnicoToken;
  } else if (tallerToken) {
    token = tallerToken;
  } else if (usuarioToken) {
    token = usuarioToken;
  }

  if (token) {
    request = request.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
  }

  return next.handle(request);
}
```

---

## 📱 Flujo Completo (Técnico)

1. **Login del Técnico**
   ```
   POST /tecnicos/login
   → Guardar tecnico_token, tecnico_id
   ```

2. **Ver Asignación en estado "aceptada"**
   ```
   GET /talleres/mi-taller/asignaciones/{id}
   → Mostrar botón "Iniciar Viaje"
   ```

3. **Técnico hace clic en "Iniciar Viaje"**
   ```
   PUT /tecnicos/mis-asignaciones/{id}/iniciar-viaje
   → Enviar GPS actual del técnico
   → Estado cambia a "en_camino"
   ```

4. **Técnico llega al cliente y hace el trabajo**
   ```
   (Aquí es donde ocurre el trabajo real)
   ```

5. **Técnico hace clic en "Completar Servicio"**
   ```
   PUT /tecnicos/mis-asignaciones/{id}/completar
   → Enviar costo estimado + resumen del trabajo
   → Estado cambia a "completada"
   → Incidente cambia automáticamente a "atendido"
   ```

6. **Cliente recibe notificación y puede evaluar**
   ```
   POST /incidencias/{id}/evaluar
   → Cliente califica el servicio (estrellas + comentario)
   ```

---

## ❌ Problemas Comunes

### Error: "La asignación está en '...' "

**Significa**: La asignación no está en el estado esperado.

- Para `iniciar-viaje`: Debe estar en `aceptada`
- Para `completar`: Debe estar en `en_camino`

**Solución**: Verifica el estado actual llamando a:
```
GET /talleres/mi-taller/asignaciones/{id}
```

---

### Error: "Asignación no encontrada o no asignada a ti"

**Significa**: 
- La asignación no existe, O
- La asignación no está asignada a este técnico

**Solución**: Verifica que:
1. El `id_asignacion` es correcto
2. El técnico tiene `id_tecnico` asignado en la asignación
3. Usas el token de técnico correcto

---

### Error 401: "No se pudieron validar las credenciales"

**Significa**: El token expiró o es inválido

**Solución**: Vuelve a hacer login:
```
POST /tecnicos/login
```

---

## 📊 Estados de la Asignación (A.2)

```
pendiente ──[aceptar]──> aceptada ──[iniciar-viaje]──> en_camino ──[completar]──> completada
                                                                                       ↓
                                                                              [incidente → atendido]
```

---

## 🔗 URLs de Referencia

| Acción | Endpoint |
|--------|----------|
| Login técnico | `POST /tecnicos/login` |
| Iniciar viaje | `PUT /tecnicos/mis-asignaciones/{id}/iniciar-viaje` |
| Completar servicio | `PUT /tecnicos/mis-asignaciones/{id}/completar` |
| Ver mis asignaciones (taller) | `GET /talleres/mi-taller/asignaciones` |
| Aceptar asignación (taller) | `PUT /talleres/mi-taller/asignaciones/{id}/aceptar` |

---

## ✅ Checklist para el Frontend

- [ ] Crear servicio `TecnicoService`
- [ ] Agregar endpoint de login de técnico
- [ ] Agregar endpoint `iniciarViaje()`
- [ ] Agregar endpoint `completarServicio()`
- [ ] Almacenar `tecnico_token` en localStorage
- [ ] Actualizar interceptor de HTTP para incluir token de técnico
- [ ] Agregar botón "Iniciar Viaje" en vista de asignación
- [ ] Agregar formulario modal para "Completar Servicio"
- [ ] Obtener GPS del dispositivo con `navigator.geolocation`
- [ ] Mostrar notificaciones de éxito/error

---

## 📞 Soporte

Si hay errores, verifica los **logs del servidor** en la terminal donde corre uvicorn:

```
INFO:     [HISTORIAL] Asignación 9: estado anterior=2, nuevo=3, obs=Técnico 5 en camino
```

Esto confirma que el cambio de estado se registró correctamente en la auditoría.
