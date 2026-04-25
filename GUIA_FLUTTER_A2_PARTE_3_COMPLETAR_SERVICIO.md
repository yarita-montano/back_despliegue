# 📱 Guía Flutter: Endpoints del Técnico (A.2 - CU-20)
## PARTE 3: Completar Servicio

### 📌 Resumen
El técnico completa el trabajo en el cliente y hace clic en "Completar Servicio":
1. Ingresa el costo del servicio (opcional)
2. Escribe un resumen del trabajo realizado (opcional)
3. Envía los datos al servidor
4. Estado cambia a `completada`
5. Incidente cambia automáticamente a `atendido`
6. Cliente puede evaluar el servicio

---

## 1️⃣ Endpoint: Completar Servicio

### Request
```bash
PUT http://localhost:8000/tecnicos/mis-asignaciones/24/completar
Authorization: Bearer <tecnico_token>
Content-Type: application/json

{
  "costo_estimado": 85000,
  "resumen_trabajo": "Se cambió la llanta trasera izquierda, se verificó alineación y presión de aire"
}
```

**Parámetros**:
- `id_asignacion` (path) - ID de la asignación en estado "en_camino"
- `costo_estimado` (body, opcional, número ≥ 0) - Costo final
- `resumen_trabajo` (body, opcional, string max 1000) - Descripción del trabajo

### Response (200 OK)
```json
{
  "id_asignacion": 24,
  "id_incidente": 15,
  "id_tecnico": 5,
  "id_taller": 1,
  "eta_minutos": 30,
  "nota_taller": "Llegará en 30 min\n[TRABAJO] Se cambió la llanta trasera...",
  "created_at": "2026-04-22T10:35:00",
  "updated_at": "2026-04-22T10:45:30",
  "estado": {
    "id_estado_asignacion": 5,
    "nombre": "completada"
  },
  "incidente": {
    "id_incidente": 15,
    "titulo": "Llanta pinchada",
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

---

## 💻 Implementar en Flutter

### Paso 1: Actualizar TecnicoAsignacionesService

**lib/services/tecnico_asignaciones_service.dart** (agregar método):

```dart
/// Completar servicio (en_camino → completada)
Future<AsignacionResponse> completarServicio(
  int idAsignacion, {
  double? costoEstimado,
  String? resumenTrabajo,
}) async {
  try {
    print('[TecnicoAsignacionesService] completarServicio → $idAsignacion');

    // Obtener token
    final token = await _authService.getTecnicoToken();
    if (token == null) {
      throw Exception('Token no disponible');
    }

    // Preparar body
    final body = <String, dynamic>{};
    if (costoEstimado != null) {
      body['costo_estimado'] = costoEstimado;
    }
    if (resumenTrabajo != null && resumenTrabajo.isNotEmpty) {
      body['resumen_trabajo'] = resumenTrabajo;
    }

    print('[TecnicoAsignacionesService] Body: $body');

    // Hacer request
    final response = await http.put(
      Uri.parse('$_baseUrl/tecnicos/mis-asignaciones/$idAsignacion/completar'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode(body),
    );

    print('[TecnicoAsignacionesService] Response: ${response.statusCode}');

    if (response.statusCode == 200) {
      final data = AsignacionResponse.fromJson(jsonDecode(response.body));
      print('[TecnicoAsignacionesService] completarServicio ← OK ${data.estado.nombre}');
      return data;
    } else {
      throw Exception('Error ${response.statusCode}: ${response.body}');
    }
  } catch (e) {
    print('[TecnicoAsignacionesService] completarServicio ← ERROR: $e');
    rethrow;
  }
}
```

---

### Paso 2: Crear Modelo para Formulario

**lib/models/completar_servicio_form.dart**:

```dart
class CompletarServicioForm {
  final double? costoEstimado;
  final String? resumenTrabajo;

  CompletarServicioForm({
    this.costoEstimado,
    this.resumenTrabajo,
  });

  bool get isValid {
    // Al menos uno de los dos campos debe tener valor
    return (costoEstimado != null && costoEstimado! > 0) ||
        (resumenTrabajo != null && resumenTrabajo!.isNotEmpty);
  }
}
```

---

### Paso 3: Crear Modal/Diálogo para Completar Servicio

**lib/widgets/completar_servicio_dialog.dart**:

```dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../models/completar_servicio_form.dart';

class CompletarServicioDialog extends StatefulWidget {
  final Function(CompletarServicioForm) onConfirm;

  const CompletarServicioDialog({
    required this.onConfirm,
  });

  @override
  _CompletarServicioDialogState createState() =>
      _CompletarServicioDialogState();
}

class _CompletarServicioDialogState extends State<CompletarServicioDialog> {
  final _costoController = TextEditingController();
  final _resumenController = TextEditingController();
  bool _loading = false;

  @override
  void dispose() {
    _costoController.dispose();
    _resumenController.dispose();
    super.dispose();
  }

  void _confirmar() async {
    // Validar que al menos un campo tenga valor
    final costo = _costoController.text.isNotEmpty
        ? double.tryParse(_costoController.text)
        : null;
    final resumen =
        _resumenController.text.isEmpty ? null : _resumenController.text;

    if (costo == null && (resumen == null || resumen.isEmpty)) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Por favor ingresa costo o resumen del trabajo'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    if (costo != null && costo < 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('El costo no puede ser negativo'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    if (resumen != null && resumen.length > 1000) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('El resumen no puede exceder 1000 caracteres'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    setState(() => _loading = true);

    try {
      final form = CompletarServicioForm(
        costoEstimado: costo,
        resumenTrabajo: resumen,
      );

      await widget.onConfirm(form);
      Navigator.of(context).pop();
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('Completar Servicio'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Campo de costo
            Text(
              'Costo estimado (COP)',
              style: Theme.of(context).textTheme.subtitle2,
            ),
            SizedBox(height: 8),
            TextField(
              controller: _costoController,
              keyboardType: TextInputType.number,
              decoration: InputDecoration(
                hintText: 'ej: 85000',
                prefixText: '\$ ',
                border: OutlineInputBorder(),
              ),
              inputFormatters: [
                FilteringTextInputFormatter.digitsOnly,
              ],
            ),
            SizedBox(height: 16),

            // Campo de resumen
            Text(
              'Resumen del trabajo realizado',
              style: Theme.of(context).textTheme.subtitle2,
            ),
            SizedBox(height: 8),
            TextField(
              controller: _resumenController,
              maxLines: 4,
              maxLength: 1000,
              decoration: InputDecoration(
                hintText: 'Describe qué se hizo (cambio de llanta, ajustes, etc.)',
                border: OutlineInputBorder(),
              ),
            ),
            SizedBox(height: 8),
            Text(
              'Al menos uno de los dos campos es obligatorio',
              style: TextStyle(fontSize: 12, color: Colors.grey[600]),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text('Cancelar'),
        ),
        ElevatedButton(
          onPressed: _loading ? null : _confirmar,
          child: _loading
              ? SizedBox(
                  height: 20,
                  width: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : Text('Completar'),
        ),
      ],
    );
  }
}

```

---

### Paso 4: Integrar en Pantalla de Asignación

**lib/screens/asignacion_detalle_screen.dart** (actualizar):

```dart
// Agregar imports
import 'package:flutter/services.dart';
import '../widgets/completar_servicio_dialog.dart';
import '../models/completar_servicio_form.dart';

// En la clase _AsignacionDetalleScreenState, agregar método:

void _abrirDialogoCompletar() {
  showDialog(
    context: context,
    builder: (context) => CompletarServicioDialog(
      onConfirm: (form) => _completarServicio(form),
    ),
  );
}

void _completarServicio(CompletarServicioForm form) async {
  try {
    print('[AsignacionDetalle] _completarServicio');
    print('  Costo: ${form.costoEstimado}');
    print('  Resumen: ${form.resumenTrabajo}');

    final resultado = await _asignacionesService.completarServicio(
      widget.idAsignacion,
      costoEstimado: form.costoEstimado,
      resumenTrabajo: form.resumenTrabajo,
    );

    setState(() {
      _asignacion = resultado;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('✅ Servicio completado correctamente'),
        backgroundColor: Colors.green,
      ),
    );

    print('[AsignacionDetalle] Servicio completado: ${resultado.estado.nombre}');
  } catch (e) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('❌ Error: $e'),
        backgroundColor: Colors.red,
      ),
    );
    print('[AsignacionDetalle] Error: $e');
  }
}

// En el método build(), actualizar el botón "Completar Servicio":

// Mostrar botón "Completar Servicio" si está en camino
if (_asignacion?.estado.nombre == 'en_camino')
  Padding(
    padding: EdgeInsets.only(top: 16),
    child: SizedBox(
      width: double.infinity,
      child: ElevatedButton.icon(
        onPressed: _abrirDialogoCompletar,  // ← Cambiar aquí
        icon: Icon(Icons.check_circle),
        label: Text('Completar Servicio'),
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.green,
          padding: EdgeInsets.symmetric(vertical: 12),
        ),
      ),
    ),
  ),
```

---

### Paso 5: Mostrar Estado Final

Agregar al método build() después de completar:

```dart
// Si está completada, mostrar mensaje de éxito
if (_asignacion?.estado.nombre == 'completada')
  Padding(
    padding: EdgeInsets.only(top: 16),
    child: Container(
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.green[100],
        border: Border.all(color: Colors.green),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '✅ Servicio Completado',
            style: TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 16,
              color: Colors.green[800],
            ),
          ),
          SizedBox(height: 8),
          Text(
            'El cliente ya puede evaluar el servicio',
            style: TextStyle(color: Colors.green[700]),
          ),
        ],
      ),
    ),
  ),
```

---

## 🔄 Flujo de Completar Servicio

```
┌──────────────────────┐
│ Estado: en_camino    │
│ (Técnico trabajando) │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────────┐
│ Botón "Completar Servicio"   │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ Modal: Formulario            │
│ - Costo (opcional)           │
│ - Resumen (opcional)         │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ Validar formulario               │
│ (Al menos 1 campo requerido)     │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ PUT /tecnicos/mis-asignaciones/│
│ {id}/completar               │
│ {costo, resumen}             │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ Estado → completada          │
│ Incidente → atendido         │
│ ✅ Mostrar notificación      │
└──────────────────────────────┘
```

---

## ✅ Checklist - Parte 3

- [ ] Agregar método `completarServicio()` en `TecnicoAsignacionesService`
- [ ] Crear modelo `CompletarServicioForm`
- [ ] Crear widget `CompletarServicioDialog`
- [ ] Agregar TextInputFormatter para números
- [ ] Validar que al menos un campo tenga valor
- [ ] Validar costo ≥ 0 y resumen ≤ 1000 caracteres
- [ ] Integrar diálogo en pantalla de asignación
- [ ] Actualizar estado en UI después de completar
- [ ] Mostrar notificación de éxito
- [ ] Mostrar mensaje cuando está completada

---

## 💰 Validaciones del Formulario

```dart
✅ Validación 1: Al menos uno de los dos campos
   if (costo == null && resumen == null) → Error

✅ Validación 2: Costo no negativo
   if (costo < 0) → Error

✅ Validación 3: Resumen máximo 1000 caracteres
   if (resumen.length > 1000) → Error

✅ Validación 4: Solo números en costo
   TextInputFormatter.digitsOnly
```

---

## ❌ Errores Posibles

| Error | Causa | Solución |
|-------|-------|----------|
| "Al menos un campo es obligatorio" | Ambos vacíos | Llenar costo o resumen |
| "El costo no puede ser negativo" | Costo < 0 | Usar número positivo |
| "El resumen no puede exceder 1000 caracteres" | Texto muy largo | Reducir texto |
| 400 Bad Request | Asignación no en "en_camino" | Verificar estado |
| 401 Unauthorized | Token expirado | Hacer login nuevamente |

---

## 📊 Estados Finales

Después de completar correctamente:

```
Estado Anterior       →     Estado Nuevo
────────────────────────────────────────
Asignación: en_camino  →  Asignación: completada
Incidente: en_proceso  →  Incidente: atendido
```

Ahora el **cliente puede evaluar** el servicio con:
```
POST /incidencias/{id_incidente}/evaluar
{
  "estrellas": 5,
  "comentario": "Excelente servicio"
}
```

---

## 🐛 Debugging

```dart
// Ver valores del formulario
print('Costo: ${_costoController.text}');
print('Resumen: ${_resumenController.text}');
print('Costo parseado: ${double.tryParse(_costoController.text)}');

// Ver respuesta del servidor
print('Estado nuevo: ${_asignacion?.estado.nombre}');
print('Incidente estado: ${_asignacion?.incidente.estado.nombre}');

// Ver nota_taller concatenada
print('Nota: ${_asignacion?.notaTaller}');
```

---

## 📝 Ejemplo Completo de Flujo

```
1. Técnico acepta asignación
   Estado: aceptada, id_tecnico = 5

2. Técnico hace clic "Iniciar Viaje"
   Envía GPS
   Estado: en_camino

3. Técnico llega y hace el trabajo
   (Aquí ocurre el trabajo real en el cliente)

4. Técnico hace clic "Completar Servicio"
   Modal pide: Costo ($85,000) + Resumen ("Se cambió llanta")
   Estado: completada
   Incidente: atendido

5. Cliente recibe notificación
   Puede hacer click en "Evaluar Servicio"
   POST /incidencias/{id}/evaluar
   { estrellas: 5, comentario: "Perfecto" }

6. Taller ve la evaluación
   GET /talleres/mi-taller/evaluaciones
```

---

## 🎯 Resultado Final

✅ Técnico autenticado  
✅ Ve asignaciones en estado "aceptada"  
✅ Hace clic "Iniciar Viaje" → envía GPS  
✅ Hace clic "Completar Servicio" → ingresa costo + resumen  
✅ Estados se actualizan automáticamente  
✅ Cliente puede evaluar el servicio  
✅ Taller ve la evaluación  
✅ Audit trail completo en historial  

---

## 🚀 Próximos Pasos

- [ ] Pruebas end-to-end (E2E)
- [ ] Notificaciones push (FCM)
- [ ] Chat cliente ↔ taller
- [ ] Historial de asignaciones del técnico
- [ ] Métricas/ratings del técnico
