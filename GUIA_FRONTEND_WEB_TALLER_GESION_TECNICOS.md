# 📱 Guía Frontend Web - Gestión de Técnicos (TALLER)

**Estado:** ✅ LISTO PARA IMPLEMENTAR  
**Fecha:** 22 de abril, 2026  
**Backend API:** FastAPI v0.135.3 @ localhost:8000  
**Autenticación:** JWT Token (tipo="taller")

---

## 🎯 Objetivo

Implementar en el web del taller la capacidad de:
1. **CREAR** nuevos técnicos (usuarios rol=3)
2. **LISTAR** todos los técnicos del taller
3. **EDITAR** disponibilidad, ubicación y datos del técnico
4. **ELIMINAR** (desactivar) técnico del taller
5. **ASIGNAR** técnico a una asignación de incidente

---

## 📚 Tabla de Contenidos

1. [Flujo de Autenticación](#flujo-de-autenticación)
2. [Endpoints Disponibles](#endpoints-disponibles)
3. [Gestión de Técnicos - CRUD](#gestión-de-técnicos---crud)
4. [Asignación de Técnico a Incidente](#asignación-de-técnico-a-incidente)
5. [Ejemplos de Implementación](#ejemplos-de-implementación)
6. [Validaciones y Errores](#validaciones-y-errores)
7. [Flujo Visual Completo](#flujo-visual-completo)

---

## 🔐 Flujo de Autenticación

### 1. Login del Taller
```bash
POST /talleres/login

Request:
{
  "email": "tallertaller@example.com",
  "password": "password123"
}

Response (200):
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "taller": {
    "id_taller": 2,
    "nombre": "Mecánica Central SC",
    "email": "tallertaller@example.com",
    "telefono": "+57 300 111 1111",
    "activo": true,
    "created_at": "2026-04-15T08:30:00"
  }
}
```

### 2. Almacenar Token
```javascript
// Frontend (React/Vue/Angular)
const response = await fetch('/talleres/login', {...});
const data = await response.json();

// Guardar en localStorage o sessionStorage
localStorage.setItem('taller_token', data.access_token);
localStorage.setItem('taller_id', data.taller.id_taller);
```

### 3. Usar Token en Todas las Peticiones
```javascript
const headers = {
  'Authorization': `Bearer ${localStorage.getItem('taller_token')}`,
  'Content-Type': 'application/json'
};

const response = await fetch('/talleres/mi-taller/tecnicos', {
  headers: headers
});
```

---

## 📡 Endpoints Disponibles

### Base URL
```
http://localhost:8000  (desarrollo)
https://api.example.com (producción)
```

### Headers Requeridos
```
Authorization: Bearer <token_taller>
Content-Type: application/json
```

---

## 👨‍🔧 Gestión de Técnicos - CRUD

### 1️⃣ CREAR TÉCNICO

**Endpoint:** `POST /talleres/mi-taller/tecnicos`

```javascript
async function crearTecnico(datosFormulario) {
  const payload = {
    nombre: datosFormulario.nombre,
    email: datosFormulario.email,
    password: datosFormulario.password,
    telefono: datosFormulario.telefono
  };

  const response = await fetch('/talleres/mi-taller/tecnicos', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('taller_token')}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  if (response.status === 201) {
    const tecnico = await response.json();
    console.log('✅ Técnico creado:', tecnico);
    return tecnico;
  } else if (response.status === 409) {
    const error = await response.json();
    console.error('❌ Email ya existe:', error.detail);
  } else {
    console.error('❌ Error:', response.status);
  }
}
```

**Request Body:**
```json
{
  "nombre": "Juan Pérez Mécanico",
  "email": "juan.perez@taller.com",
  "password": "JuanPass123!",
  "telefono": "+57 310 555 1234"
}
```

**Response (201 Created):**
```json
{
  "id_usuario_taller": 5,
  "id_usuario": 42,
  "id_taller": 2,
  "nombre": "Juan Pérez Mécanico",
  "email": "juan.perez@taller.com",
  "telefono": "+57 310 555 1234",
  "disponible": true,
  "activo": true,
  "latitud": null,
  "longitud": null,
  "created_at": "2026-04-22T10:30:00"
}
```

**Errores Posibles:**
```
409 Conflict - Email ya existe
  → Validar email antes de enviar
  → Mostrar: "Ya existe un usuario con ese email"

400 Bad Request - Datos inválidos
  → Validar formato de email
  → Validar longitud de password (mínimo 8 caracteres)
```

---

### 2️⃣ LISTAR TÉCNICOS

**Endpoint:** `GET /talleres/mi-taller/tecnicos?activos_solo=true`

```javascript
async function listarTecnicos(soloActivos = true) {
  const url = `/talleres/mi-taller/tecnicos?activos_solo=${soloActivos}`;
  
  const response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('taller_token')}`,
      'Content-Type': 'application/json'
    }
  });

  if (response.status === 200) {
    const tecnicos = await response.json();
    console.log(`✅ ${tecnicos.length} técnicos encontrados`);
    return tecnicos;
  } else {
    console.error('❌ Error al listar técnicos:', response.status);
  }
}

// Uso
const misTecnicos = await listarTecnicos(true);

// Renderizar en tabla/lista
misTecnicos.forEach(tech => {
  console.log(`${tech.nombre} - ${tech.email} - Disponible: ${tech.disponible}`);
});
```

**Query Parameters:**
- `activos_solo` (boolean, default: true)
  - true = Solo técnicos activos
  - false = Todos (incluyendo desactivados)

**Response (200):**
```json
[
  {
    "id_usuario_taller": 5,
    "id_usuario": 42,
    "nombre": "Juan Pérez Mécanico",
    "email": "juan.perez@taller.com",
    "telefono": "+57 310 555 1234",
    "disponible": true,
    "activo": true,
    "created_at": "2026-04-22T10:30:00"
  },
  {
    "id_usuario_taller": 6,
    "id_usuario": 43,
    "nombre": "Carlos Rodríguez",
    "email": "carlos@taller.com",
    "telefono": "+57 320 666 2222",
    "disponible": false,
    "activo": true,
    "created_at": "2026-04-20T14:15:00"
  }
]
```

---

### 3️⃣ OBTENER DETALLES DE TÉCNICO

**Endpoint:** `GET /talleres/mi-taller/tecnicos/{id_usuario_taller}`

```javascript
async function obtenerDetalleTecnico(idUsuarioTaller) {
  const response = await fetch(
    `/talleres/mi-taller/tecnicos/${idUsuarioTaller}`,
    {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('taller_token')}`,
        'Content-Type': 'application/json'
      }
    }
  );

  if (response.status === 200) {
    const tecnico = await response.json();
    console.log('✅ Detalles del técnico:', tecnico);
    return tecnico;
  } else if (response.status === 404) {
    console.error('❌ Técnico no encontrado');
  }
}
```

**Response (200):**
```json
{
  "id_usuario_taller": 5,
  "id_usuario": 42,
  "id_taller": 2,
  "nombre": "Juan Pérez Mécanico",
  "email": "juan.perez@taller.com",
  "telefono": "+57 310 555 1234",
  "disponible": true,
  "activo": true,
  "latitud": 4.7110,
  "longitud": -74.0086,
  "created_at": "2026-04-22T10:30:00"
}
```

---

### 4️⃣ EDITAR TÉCNICO

**Endpoint:** `PUT /talleres/mi-taller/tecnicos/{id_usuario_taller}`

```javascript
async function editarTecnico(idUsuarioTaller, datosActualizacion) {
  const response = await fetch(
    `/talleres/mi-taller/tecnicos/${idUsuarioTaller}`,
    {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('taller_token')}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(datosActualizacion)
    }
  );

  if (response.status === 200) {
    const tecnicoActualizado = await response.json();
    console.log('✅ Técnico actualizado:', tecnicoActualizado);
    return tecnicoActualizado;
  } else {
    console.error('❌ Error:', response.status);
  }
}

// Uso - Cambiar disponibilidad
await editarTecnico(5, {
  disponible: false
});

// Uso - Actualizar ubicación
await editarTecnico(5, {
  latitud: 4.7090,
  longitud: -74.0100
});

// Uso - Actualizar teléfono
await editarTecnico(5, {
  telefono: "+57 300 999 9999"
});

// Uso - Múltiples campos
await editarTecnico(5, {
  disponible: true,
  latitud: 4.7110,
  longitud: -74.0086,
  telefono: "+57 310 111 1111"
});
```

**Request Body (solo campos a actualizar):**
```json
{
  "disponible": false,
  "latitud": 4.7090,
  "longitud": -74.0100,
  "telefono": "+57 300 999 9999"
}
```

**Response (200):**
```json
{
  "id_usuario_taller": 5,
  "id_usuario": 42,
  "nombre": "Juan Pérez Mécanico",
  "email": "juan.perez@taller.com",
  "telefono": "+57 300 999 9999",
  "disponible": false,
  "activo": true,
  "latitud": 4.7090,
  "longitud": -74.0100,
  "created_at": "2026-04-22T10:30:00"
}
```

---

### 5️⃣ ELIMINAR/DESACTIVAR TÉCNICO

**Endpoint:** `DELETE /talleres/mi-taller/tecnicos/{id_usuario_taller}`

```javascript
async function desactivarTecnico(idUsuarioTaller) {
  const confirmacion = confirm(
    '¿Está seguro de que desea remover este técnico del taller? ' +
    'No se eliminarán sus datos, solo se marcará como inactivo.'
  );
  
  if (!confirmacion) return;

  const response = await fetch(
    `/talleres/mi-taller/tecnicos/${idUsuarioTaller}`,
    {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('taller_token')}`,
        'Content-Type': 'application/json'
      }
    }
  );

  if (response.status === 200) {
    const resultado = await response.json();
    console.log('✅', resultado.mensaje);
    // Refrescar lista de técnicos
    await listarTecnicos();
    return true;
  } else {
    console.error('❌ Error:', response.status);
  }
}
```

**Response (200):**
```json
{
  "mensaje": "Técnico removido del taller correctamente"
}
```

**⚠️ Nota Importante:**
- No elimina datos del técnico
- Solo marca como `activo=false`
- El técnico NO puede ser asignado a nuevos incidentes
- Si queda sin asignaciones activas, puede ser reactivado manualmente en BD

---

## 🎯 Asignación de Técnico a Incidente

### Flujo Completo

```
Cliente reporta emergencia
        ↓
Taller recibe asignación (estado: pendiente)
        ↓
Taller ACEPTA + ASIGNA TÉCNICO
        ↓
Técnico VE la asignación en su móvil
        ↓
Técnico INICIA VIAJE
        ↓
Técnico COMPLETA SERVICIO
```

### 1️⃣ OBTENER ASIGNACIONES PENDIENTES DEL TALLER

**Endpoint:** `GET /talleres/mi-taller/asignaciones`

```javascript
async function obtenerAsignacionesPendientes() {
  const response = await fetch(
    '/talleres/mi-taller/asignaciones?estado=pendiente',
    {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('taller_token')}`,
        'Content-Type': 'application/json'
      }
    }
  );

  if (response.status === 200) {
    const asignaciones = await response.json();
    console.log(`✅ ${asignaciones.length} asignaciones pendientes`);
    return asignaciones;
  }
}
```

**Response (200):**
```json
[
  {
    "id_asignacion": 120,
    "id_incidente": 15,
    "id_taller": 2,
    "id_usuario": null,
    "id_estado_asignacion": 1,
    "estado": "pendiente",
    "eta_minutos": null,
    "nota_taller": null,
    "incidente": {
      "descripcion_usuario": "Batería descargada",
      "categoria": "Batería",
      "latitud": 4.7110,
      "longitud": -74.0086
    },
    "cliente": {
      "nombre": "María García",
      "telefono": "+57 312 555 1234"
    },
    "created_at": "2026-04-22T10:15:00"
  }
]
```

---

### 2️⃣ ACEPTAR ASIGNACIÓN + ASIGNAR TÉCNICO

**Endpoint:** `PUT /talleres/mi-taller/asignaciones/{id_asignacion}/aceptar`

```javascript
async function aceptarYAsignarTecnico(
  idAsignacion,
  idUsuarioTaller,
  etaMinutos,
  nota = ""
) {
  // Primero, obtener el ID usuario del técnico
  const tecnico = await obtenerDetalleTecnico(idUsuarioTaller);
  
  const payload = {
    id_usuario: tecnico.id_usuario,  // ⭐ IMPORTANTE: usar id_usuario, no id_usuario_taller
    eta_minutos: etaMinutos,
    nota: nota
  };

  const response = await fetch(
    `/talleres/mi-taller/asignaciones/${idAsignacion}/aceptar`,
    {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('taller_token')}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    }
  );

  if (response.status === 200) {
    const asignacionActualizada = await response.json();
    console.log('✅ Asignación aceptada y técnico asignado');
    console.log('Estado:', asignacionActualizada.estado);
    console.log('Técnico asignado:', asignacionActualizada.id_usuario);
    return asignacionActualizada;
  } else if (response.status === 409) {
    const error = await response.json();
    console.error('❌ CONFLICTO:', error.detail);
    // Mostrar: "El técnico ya tiene una asignación activa"
  } else if (response.status === 404) {
    const error = await response.json();
    console.error('❌ Técnico no encontrado o inactivo:', error.detail);
  } else {
    console.error('❌ Error:', response.status);
  }
}

// Uso
const asignacionActualizada = await aceptarYAsignarTecnico(
  120,          // id_asignacion
  5,            // id_usuario_taller del técnico seleccionado
  25,           // ETA en minutos
  "Juan va en camino"  // nota opcional
);
```

**Request Body:**
```json
{
  "id_usuario": 42,
  "eta_minutos": 25,
  "nota": "Juan va en camino"
}
```

**Response (200):**
```json
{
  "id_asignacion": 120,
  "id_incidente": 15,
  "id_usuario": 42,
  "id_taller": 2,
  "id_estado_asignacion": 2,
  "estado": "aceptada",
  "eta_minutos": 25,
  "nota_taller": "Juan va en camino",
  "created_at": "2026-04-22T10:15:00"
}
```

**Errores Posibles:**
```
409 Conflict - Técnico tiene otra asignación activa
  Error: "El técnico ya tiene una asignación activa (ID: 119). 
          Un técnico solo puede tener una asignación a la vez."
  
  ⚠️ SOLUCIÓN: 
     - No asignarle otro trabajo
     - O esperar a que complete la asignación actual

404 Not Found - Técnico no existe o está inactivo
  Error: "Usuario técnico no encontrado o no está activo"
  
  ⚠️ SOLUCIÓN:
     - Verificar que el técnico está activo en BD
     - Recargar lista de técnicos
```

---

## 💻 Ejemplos de Implementación

### Ejemplo 1: HTML + JavaScript Vanilla

```html
<!-- HTML -->
<div id="gestion-tecnicos">
  <!-- Sección: Crear Técnico -->
  <section id="crear-seccion">
    <h2>➕ Crear Nuevo Técnico</h2>
    <form id="form-crear-tecnico">
      <input type="text" id="nombre" placeholder="Nombre" required />
      <input type="email" id="email" placeholder="Email" required />
      <input type="password" id="password" placeholder="Contraseña" required />
      <input type="tel" id="telefono" placeholder="Teléfono" required />
      <button type="submit">Crear Técnico</button>
    </form>
    <div id="mensaje-crear"></div>
  </section>

  <!-- Sección: Listar Técnicos -->
  <section id="listar-seccion">
    <h2>👨‍🔧 Mis Técnicos</h2>
    <table id="tabla-tecnicos">
      <thead>
        <tr>
          <th>Nombre</th>
          <th>Email</th>
          <th>Teléfono</th>
          <th>Disponible</th>
          <th>Acciones</th>
        </tr>
      </thead>
      <tbody id="cuerpo-tabla"></tbody>
    </table>
  </section>

  <!-- Sección: Asignaciones Pendientes -->
  <section id="asignaciones-seccion">
    <h2>📋 Asignaciones Pendientes</h2>
    <div id="lista-asignaciones"></div>
  </section>
</div>
```

```javascript
// JavaScript
const API_URL = 'http://localhost:8000';
const token = localStorage.getItem('taller_token');

// Función auxiliar para hacer peticiones
async function apiCall(endpoint, method = 'GET', body = null) {
  const options = {
    method,
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(`${API_URL}${endpoint}`, options);
  return {
    status: response.status,
    data: await response.json()
  };
}

// 1. Crear Técnico
document.getElementById('form-crear-tecnico').addEventListener('submit', async (e) => {
  e.preventDefault();

  const datos = {
    nombre: document.getElementById('nombre').value,
    email: document.getElementById('email').value,
    password: document.getElementById('password').value,
    telefono: document.getElementById('telefono').value
  };

  const { status, data } = await apiCall(
    '/talleres/mi-taller/tecnicos',
    'POST',
    datos
  );

  const mensajeDiv = document.getElementById('mensaje-crear');
  if (status === 201) {
    mensajeDiv.innerHTML = `✅ Técnico ${data.nombre} creado exitosamente`;
    document.getElementById('form-crear-tecnico').reset();
    await cargarTecnicos();  // Refrescar lista
  } else if (status === 409) {
    mensajeDiv.innerHTML = `❌ ${data.detail}`;
  } else {
    mensajeDiv.innerHTML = `❌ Error: ${data.detail}`;
  }
});

// 2. Listar Técnicos
async function cargarTecnicos() {
  const { status, data } = await apiCall('/talleres/mi-taller/tecnicos?activos_solo=true');

  if (status === 200) {
    const tbody = document.getElementById('cuerpo-tabla');
    tbody.innerHTML = data
      .map(
        (tech) => `
      <tr>
        <td>${tech.nombre}</td>
        <td>${tech.email}</td>
        <td>${tech.telefono}</td>
        <td>${tech.disponible ? '✅ Sí' : '❌ No'}</td>
        <td>
          <button onclick="editarTecnico(${tech.id_usuario_taller})">Editar</button>
          <button onclick="desactivarTecnico(${tech.id_usuario_taller})">Desactivar</button>
        </td>
      </tr>
    `
      )
      .join('');
  }
}

// 3. Desactivar Técnico
async function desactivarTecnico(idUsuarioTaller) {
  if (!confirm('¿Desactivar este técnico?')) return;

  const { status, data } = await apiCall(
    `/talleres/mi-taller/tecnicos/${idUsuarioTaller}`,
    'DELETE'
  );

  if (status === 200) {
    alert('✅ ' + data.mensaje);
    await cargarTecnicos();
  }
}

// 4. Cargar Asignaciones Pendientes
async function cargarAsignacionesPendientes() {
  const { status, data } = await apiCall(
    '/talleres/mi-taller/asignaciones?estado=pendiente'
  );

  if (status === 200) {
    const div = document.getElementById('lista-asignaciones');
    div.innerHTML = data
      .map(
        (asig) => `
      <div style="border: 1px solid #ccc; padding: 10px; margin: 10px 0;">
        <p><strong>Incidente:</strong> ${asig.incidente.descripcion_usuario}</p>
        <p><strong>Cliente:</strong> ${asig.cliente.nombre}</p>
        <p><strong>Ubicación:</strong> ${asig.incidente.latitud}, ${asig.incidente.longitud}</p>
        
        <select id="select-tecnico-${asig.id_asignacion}">
          <option value="">-- Seleccionar Técnico --</option>
          <!-- Los técnicos se cargan dinámicamente -->
        </select>
        
        <input type="number" id="eta-${asig.id_asignacion}" placeholder="ETA (minutos)" />
        
        <button onclick="aceptarAsignacion(${asig.id_asignacion})">
          ✅ Aceptar y Asignar
        </button>
      </div>
    `
      )
      .join('');

    // Cargar opciones de técnicos para cada asignación
    const { status: statusTec, data: tecnicos } = await apiCall(
      '/talleres/mi-taller/tecnicos?activos_solo=true'
    );
    if (statusTec === 200) {
      data.forEach((asig) => {
        const select = document.getElementById(`select-tecnico-${asig.id_asignacion}`);
        select.innerHTML = `<option value="">-- Seleccionar Técnico --</option>` +
          tecnicos
            .map((tech) => `<option value="${tech.id_usuario_taller}">${tech.nombre}</option>`)
            .join('');
      });
    }
  }
}

// 5. Aceptar Asignación
async function aceptarAsignacion(idAsignacion) {
  const idUsuarioTaller = document.getElementById(`select-tecnico-${idAsignacion}`).value;
  const eta = parseInt(document.getElementById(`eta-${idAsignacion}`).value);

  if (!idUsuarioTaller) {
    alert('❌ Selecciona un técnico');
    return;
  }

  // Obtener el ID usuario del técnico
  const { status: statusTec, data: tecnico } = await apiCall(
    `/talleres/mi-taller/tecnicos/${idUsuarioTaller}`
  );

  if (statusTec === 200) {
    const payload = {
      id_usuario: tecnico.id_usuario,
      eta_minutos: eta || null,
      nota: ''
    };

    const { status, data } = await apiCall(
      `/talleres/mi-taller/asignaciones/${idAsignacion}/aceptar`,
      'PUT',
      payload
    );

    if (status === 200) {
      alert('✅ Asignación aceptada. Técnico notificado.');
      await cargarAsignacionesPendientes();
    } else if (status === 409) {
      alert('❌ ' + data.detail);
    } else {
      alert('❌ Error: ' + data.detail);
    }
  }
}

// Cargar datos al inicio
window.addEventListener('DOMContentLoaded', async () => {
  await cargarTecnicos();
  await cargarAsignacionesPendientes();
});
```

---

### Ejemplo 2: React

```jsx
import React, { useState, useEffect } from 'react';

const GestionTecnicos = () => {
  const [tecnicos, setTecnicos] = useState([]);
  const [asignaciones, setAsignaciones] = useState([]);
  const [formData, setFormData] = useState({
    nombre: '',
    email: '',
    password: '',
    telefono: ''
  });

  const token = localStorage.getItem('taller_token');
  const API_URL = 'http://localhost:8000';

  const apiCall = async (endpoint, method = 'GET', body = null) => {
    const options = {
      method,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    };
    if (body) options.body = JSON.stringify(body);

    const response = await fetch(`${API_URL}${endpoint}`, options);
    return {
      status: response.status,
      data: await response.json()
    };
  };

  // Cargar técnicos
  const cargarTecnicos = async () => {
    const { status, data } = await apiCall('/talleres/mi-taller/tecnicos');
    if (status === 200) setTecnicos(data);
  };

  // Cargar asignaciones
  const cargarAsignaciones = async () => {
    const { status, data } = await apiCall(
      '/talleres/mi-taller/asignaciones?estado=pendiente'
    );
    if (status === 200) setAsignaciones(data);
  };

  // Crear técnico
  const handleCrearTecnico = async (e) => {
    e.preventDefault();
    const { status, data } = await apiCall(
      '/talleres/mi-taller/tecnicos',
      'POST',
      formData
    );

    if (status === 201) {
      alert('✅ Técnico creado');
      setFormData({ nombre: '', email: '', password: '', telefono: '' });
      cargarTecnicos();
    } else {
      alert(`❌ Error: ${data.detail}`);
    }
  };

  // Desactivar técnico
  const handleDesactivar = async (id) => {
    if (!window.confirm('¿Desactivar técnico?')) return;

    const { status, data } = await apiCall(
      `/talleres/mi-taller/tecnicos/${id}`,
      'DELETE'
    );

    if (status === 200) {
      alert('✅ ' + data.mensaje);
      cargarTecnicos();
    }
  };

  // Aceptar asignación
  const handleAceptarAsignacion = async (idAsignacion, idUsuarioTaller) => {
    const { status: statusTec, data: tecnico } = await apiCall(
      `/talleres/mi-taller/tecnicos/${idUsuarioTaller}`
    );

    if (statusTec === 200) {
      const { status, data } = await apiCall(
        `/talleres/mi-taller/asignaciones/${idAsignacion}/aceptar`,
        'PUT',
        {
          id_usuario: tecnico.id_usuario,
          eta_minutos: 25,
          nota: 'Técnico asignado'
        }
      );

      if (status === 200) {
        alert('✅ Asignación aceptada');
        cargarAsignaciones();
      } else if (status === 409) {
        alert('❌ ' + data.detail);
      }
    }
  };

  useEffect(() => {
    cargarTecnicos();
    cargarAsignaciones();
  }, []);

  return (
    <div>
      <h1>🔧 Gestión de Técnicos</h1>

      {/* Formulario Crear Técnico */}
      <form onSubmit={handleCrearTecnico}>
        <h2>Crear Técnico</h2>
        <input
          type="text"
          placeholder="Nombre"
          value={formData.nombre}
          onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
          required
        />
        <input
          type="email"
          placeholder="Email"
          value={formData.email}
          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
          required
        />
        <input
          type="password"
          placeholder="Contraseña"
          value={formData.password}
          onChange={(e) => setFormData({ ...formData, password: e.target.value })}
          required
        />
        <input
          type="tel"
          placeholder="Teléfono"
          value={formData.telefono}
          onChange={(e) => setFormData({ ...formData, telefono: e.target.value })}
          required
        />
        <button type="submit">Crear</button>
      </form>

      {/* Tabla de Técnicos */}
      <h2>Técnicos Activos</h2>
      <table>
        <thead>
          <tr>
            <th>Nombre</th>
            <th>Email</th>
            <th>Disponible</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {tecnicos.map((tech) => (
            <tr key={tech.id_usuario_taller}>
              <td>{tech.nombre}</td>
              <td>{tech.email}</td>
              <td>{tech.disponible ? '✅' : '❌'}</td>
              <td>
                <button onClick={() => handleDesactivar(tech.id_usuario_taller)}>
                  Desactivar
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Asignaciones Pendientes */}
      <h2>Asignaciones Pendientes</h2>
      {asignaciones.map((asig) => (
        <div key={asig.id_asignacion} style={{ border: '1px solid #ccc', padding: '10px' }}>
          <p><strong>{asig.incidente.descripcion_usuario}</strong></p>
          <p>Cliente: {asig.cliente.nombre}</p>
          
          <select onChange={(e) => {
            if (e.target.value) {
              handleAceptarAsignacion(asig.id_asignacion, parseInt(e.target.value));
            }
          }}>
            <option value="">Seleccionar técnico...</option>
            {tecnicos.map((tech) => (
              <option key={tech.id_usuario_taller} value={tech.id_usuario_taller}>
                {tech.nombre} {tech.disponible ? '(Disponible)' : '(Ocupado)'}
              </option>
            ))}
          </select>
        </div>
      ))}
    </div>
  );
};

export default GestionTecnicos;
```

---

## ⚠️ Validaciones y Errores

### 1. Email
```javascript
function validarEmail(email) {
  const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return regex.test(email);
}

// Uso en formulario
if (!validarEmail(formData.email)) {
  mostrarError('Email inválido');
  return;
}
```

### 2. Contraseña
```javascript
function validarPassword(password) {
  // Mínimo 8 caracteres
  return password.length >= 8;
}
```

### 3. Teléfono
```javascript
function validarTelefono(telefono) {
  // Formato: +57 300 111 1111 o 3001111111
  const regex = /^(\+57|0)?[0-9]{10}$/;
  return regex.test(telefono.replace(/\s/g, ''));
}
```

### 4. Errores HTTP Comunes

| Código | Problema | Solución |
|--------|----------|----------|
| **400** | Datos inválidos | Validar antes de enviar |
| **401** | Token expirado | Hacer nuevo login |
| **403** | No autorizado | Verificar token y rol |
| **404** | Recurso no encontrado | Verificar ID existe |
| **409** | Email duplicado / Técnico con asignación activa | Elegir otro email / esperar a que complete |
| **500** | Error del servidor | Revisar logs del backend |

---

## 📊 Flujo Visual Completo

```
┌─────────────────────────────────────────────────────────────────────┐
│                    WEB TALLER - DASHBOARD                            │
└─────────────────────────────────────────────────────────────────────┘

                            1️⃣ LOGIN TALLER
┌─────────────────────────────────────────────────────────────────────┐
│ POST /talleres/login                                                  │
│ ├─ email: "taller@example.com"                                       │
│ ├─ password: "password123"                                           │
│ └─ Response: { token, taller_id }                                    │
│    ↓ Guardar token en localStorage                                   │
└─────────────────────────────────────────────────────────────────────┘

                        2️⃣ GESTIÓN DE TÉCNICOS
┌─────────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ ➕ CREAR TÉCNICO                                                 │ │
│ │ POST /mi-taller/tecnicos                                        │ │
│ │ ├─ nombre, email, password, telefono                            │ │
│ │ └─ Response: UsuarioTaller creado ✅                            │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ 📋 LISTAR TÉCNICOS                                               │ │
│ │ GET /mi-taller/tecnicos?activos_solo=true                       │ │
│ │ └─ Response: Lista de técnicos                                   │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ ✏️  EDITAR TÉCNICO                                               │ │
│ │ PUT /mi-taller/tecnicos/{id}                                    │ │
│ │ └─ Cambiar: disponible, ubicación, teléfono                     │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ 🗑️  ELIMINAR TÉCNICO (Baja Lógica)                              │ │
│ │ DELETE /mi-taller/tecnicos/{id}                                 │ │
│ │ └─ Marca activo=false (no elimina datos)                         │ │
│ └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘

                    3️⃣ ACEPTAR ASIGNACIÓN + TÉCNICO
┌─────────────────────────────────────────────────────────────────────┐
│ GET /mi-taller/asignaciones?estado=pendiente                         │
│ ↓ Mostrar lista de incidentes sin asignar                            │
│                                                                       │
│ Taller selecciona técnico de lista ➕                                │
│ ↓                                                                     │
│ PUT /mi-taller/asignaciones/{id}/aceptar                             │
│ ├─ id_usuario: <técnico.id_usuario>  ⭐ OJO: id_usuario, no id_ut  │
│ ├─ eta_minutos: 25                                                   │
│ └─ VALIDACIÓN: Técnico NO puede tener 2+ activas                     │
│    └─ Si incumple → HTTP 409 Conflict ❌                            │
│                                                                       │
│ Si OK (200) ✅:                                                      │
│ └─ Asignación pasa a "aceptada"                                      │
│ └─ Técnico recibe notificación en móvil                              │
└─────────────────────────────────────────────────────────────────────┘

                        4️⃣ TÉCNICO EN MÓVIL
┌─────────────────────────────────────────────────────────────────────┐
│ Login técnico: POST /usuarios/login                                  │
│ ├─ email: "juan.perez@taller.com"                                    │
│ ├─ password: <su contraseña>                                         │
│ └─ Token técnico obtenido                                            │
│                                                                       │
│ Ver asignación: GET /tecnicos/asignacion-actual                      │
│ ├─ Muestra incidente, cliente, ubicación                             │
│ └─ Estado: "aceptada"                                                │
│                                                                       │
│ Iniciar viaje: PUT /tecnicos/mis-asignaciones/{id}/iniciar-viaje     │
│ └─ Estado: aceptada → en_camino                                      │
│                                                                       │
│ Completar: PUT /tecnicos/mis-asignaciones/{id}/completar             │
│ └─ Estado: en_camino → completada ✅                                │
│ └─ Técnico LIBRE para siguiente asignación                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Checklist de Implementación

- [ ] Implementar login del taller en web
- [ ] Guardar token en localStorage
- [ ] Crear formulario para agregar técnicos
- [ ] Implementar validación de email (no duplicados)
- [ ] Listar técnicos en tabla
- [ ] Agregar botón editar disponibilidad
- [ ] Agregar botón desactivar técnico
- [ ] Obtener asignaciones pendientes
- [ ] Mostrar form para seleccionar técnico
- [ ] Validar que técnico NO tiene asignación activa
- [ ] Mostrar error 409 si intenta asignar técnico ocupado
- [ ] Refrescar lista después de cada acción
- [ ] Agregar loading spinners durante peticiones
- [ ] Agregar notificaciones (success/error)
- [ ] Pruebas en desarrollo (localhost:8000)

---

## 📞 Resumen de Endpoints

```
├── AUTENTICACIÓN
│   └── POST /talleres/login
│
├── INFORMACIÓN DEL TALLER
│   ├── GET /talleres/mi-taller
│   └── PUT /talleres/mi-taller
│
├── GESTIÓN DE TÉCNICOS ⭐
│   ├── POST /talleres/mi-taller/tecnicos                    (CREATE)
│   ├── GET /talleres/mi-taller/tecnicos                     (READ - Lista)
│   ├── GET /talleres/mi-taller/tecnicos/{id_usuario_taller} (READ - Detalle)
│   ├── PUT /talleres/mi-taller/tecnicos/{id_usuario_taller} (UPDATE)
│   └── DELETE /talleres/mi-taller/tecnicos/{id_usuario_taller} (DELETE)
│
├── GESTIÓN DE ASIGNACIONES
│   ├── GET /talleres/mi-taller/asignaciones                 (Listar)
│   ├── GET /talleres/mi-taller/asignaciones/{id}            (Detalle)
│   ├── PUT /talleres/mi-taller/asignaciones/{id}/aceptar   (ACEPTAR + TÉCNICO) ⭐
│   ├── PUT /talleres/mi-taller/asignaciones/{id}/rechazar   (Rechazar)
│   └── GET /talleres/mi-taller/evaluaciones                 (Reseñas)
```

---

**Guía completada ✅**  
**Lista para implementación en frontend web**  
**Backend: API disponible en localhost:8000**
