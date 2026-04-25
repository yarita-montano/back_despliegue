# 📱 Guía Flutter: Endpoints del Técnico (A.2 - CU-20)
## PARTE 2: Iniciar Viaje (en_camino)

### 📌 Resumen
El técnico hace clic en "Iniciar Viaje" y el sistema:
1. Obtiene su GPS actual
2. Envía la ubicación al servidor
3. Cambia estado de asignación a `en_camino`
4. Cambia estado del incidente a `en_proceso`

---

## 1️⃣ Endpoint: Iniciar Viaje

### Request
```bash
PUT http://localhost:8000/tecnicos/mis-asignaciones/24/iniciar-viaje
Authorization: Bearer <tecnico_token>
Content-Type: application/json

{
  "latitud_tecnico": 4.7120,
  "longitud_tecnico": -74.0730
}
```

**Parámetros**:
- `id_asignacion` (path) - ID de la asignación actual
- `latitud_tecnico` (body, opcional) - GPS actual
- `longitud_tecnico` (body, opcional) - GPS actual

### Response (200 OK)
```json
{
  "id_asignacion": 24,
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
    "titulo": "Llanta pinchada",
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

---

## 💻 Implementar en Flutter

### Paso 1: Crear Modelo `AsignacionResponse`

**lib/models/asignacion_response.dart**:

```dart
class AsignacionResponse {
  final int idAsignacion;
  final int idIncidente;
  final int idTecnico;
  final int idTaller;
  final int? etaMinutos;
  final String? notaTaller;
  final String createdAt;
  final String updatedAt;
  final EstadoAsignacion estado;
  final IncidenteData incidente;

  AsignacionResponse({
    required this.idAsignacion,
    required this.idIncidente,
    required this.idTecnico,
    required this.idTaller,
    this.etaMinutos,
    this.notaTaller,
    required this.createdAt,
    required this.updatedAt,
    required this.estado,
    required this.incidente,
  });

  factory AsignacionResponse.fromJson(Map<String, dynamic> json) {
    return AsignacionResponse(
      idAsignacion: json['id_asignacion'],
      idIncidente: json['id_incidente'],
      idTecnico: json['id_tecnico'],
      idTaller: json['id_taller'],
      etaMinutos: json['eta_minutos'],
      notaTaller: json['nota_taller'],
      createdAt: json['created_at'],
      updatedAt: json['updated_at'],
      estado: EstadoAsignacion.fromJson(json['estado']),
      incidente: IncidenteData.fromJson(json['incidente']),
    );
  }
}

class EstadoAsignacion {
  final int idEstado;
  final String nombre;

  EstadoAsignacion({required this.idEstado, required this.nombre});

  factory EstadoAsignacion.fromJson(Map<String, dynamic> json) {
    return EstadoAsignacion(
      idEstado: json['id_estado_asignacion'],
      nombre: json['nombre'],
    );
  }
}

class IncidenteData {
  final int idIncidente;
  final String titulo;
  final String? ubicacion;
  final double? latitud;
  final double? longitud;
  final EstadoIncidente estado;

  IncidenteData({
    required this.idIncidente,
    required this.titulo,
    this.ubicacion,
    this.latitud,
    this.longitud,
    required this.estado,
  });

  factory IncidenteData.fromJson(Map<String, dynamic> json) {
    return IncidenteData(
      idIncidente: json['id_incidente'],
      titulo: json['titulo'],
      ubicacion: json['ubicacion'],
      latitud: json['latitud']?.toDouble(),
      longitud: json['longitud']?.toDouble(),
      estado: EstadoIncidente.fromJson(json['estado']),
    );
  }
}

class EstadoIncidente {
  final int idEstado;
  final String nombre;

  EstadoIncidente({required this.idEstado, required this.nombre});

  factory EstadoIncidente.fromJson(Map<String, dynamic> json) {
    return EstadoIncidente(
      idEstado: json['id_estado'],
      nombre: json['nombre'],
    );
  }
}
```

---

### Paso 2: Crear Servicio de Asignaciones del Técnico

**lib/services/tecnico_asignaciones_service.dart**:

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:geolocator/geolocator.dart';
import '../models/asignacion_response.dart';
import 'tecnico_auth_service.dart';

class TecnicoAsignacionesService {
  static const String _baseUrl = 'http://localhost:8000';
  final _authService = TecnicoAuthService();

  /// Obtener la ubicación actual del dispositivo
  Future<Position> _getCurrentLocation() async {
    print('[TecnicoAsignacionesService] _getCurrentLocation →');

    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      throw Exception('Servicio de ubicación deshabilitado');
    }

    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) {
        throw Exception('Permiso de ubicación denegado');
      }
    }

    if (permission == LocationPermission.deniedForever) {
      throw Exception('Permiso de ubicación denegado permanentemente');
    }

    return await Geolocator.getCurrentPosition(
      desiredAccuracy: LocationAccuracy.high,
    );
  }

  /// Iniciar viaje (aceptada → en_camino)
  Future<AsignacionResponse> iniciarViaje(int idAsignacion) async {
    try {
      print('[TecnicoAsignacionesService] iniciarViaje → $idAsignacion');

      // Obtener ubicación actual
      final position = await _getCurrentLocation();
      final latitud = position.latitude;
      final longitud = position.longitude;

      print('[TecnicoAsignacionesService] GPS: $latitud, $longitud');

      // Obtener token
      final token = await _authService.getTecnicoToken();
      if (token == null) {
        throw Exception('Token no disponible');
      }

      // Hacer request
      final response = await http.put(
        Uri.parse('$_baseUrl/tecnicos/mis-asignaciones/$idAsignacion/iniciar-viaje'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
        body: jsonEncode({
          'latitud_tecnico': latitud,
          'longitud_tecnico': longitud,
        }),
      );

      print('[TecnicoAsignacionesService] Response: ${response.statusCode}');

      if (response.statusCode == 200) {
        final data = AsignacionResponse.fromJson(jsonDecode(response.body));
        print('[TecnicoAsignacionesService] iniciarViaje ← OK ${data.estado.nombre}');
        return data;
      } else {
        throw Exception('Error ${response.statusCode}: ${response.body}');
      }
    } catch (e) {
      print('[TecnicoAsignacionesService] iniciarViaje ← ERROR: $e');
      rethrow;
    }
  }
}
```

---

### Paso 3: Agregar Dependencia de Geolocalización

**Actualizar `pubspec.yaml`**:

```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.1.0
  flutter_secure_storage: ^9.0.0
  geolocator: ^11.0.0
```

**Configurar permisos en Android** (`android/app/src/main/AndroidManifest.xml`):

```xml
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
```

**Configurar permisos en iOS** (`ios/Runner/Info.plist`):

```xml
<key>NSLocationWhenInUseUsageDescription</key>
<string>Esta app necesita tu ubicación para reportar que estás en camino</string>
<key>NSLocationAlwaysAndWhenInUseUsageDescription</key>
<string>Esta app necesita tu ubicación para reportar que estás en camino</string>
```

---

### Paso 4: Crear Pantalla para Iniciar Viaje

**lib/screens/asignacion_detalle_screen.dart**:

```dart
import 'package:flutter/material.dart';
import '../services/tecnico_asignaciones_service.dart';
import '../models/asignacion_response.dart';

class AsignacionDetalleScreen extends StatefulWidget {
  final int idAsignacion;

  const AsignacionDetalleScreen({required this.idAsignacion});

  @override
  _AsignacionDetalleScreenState createState() =>
      _AsignacionDetalleScreenState();
}

class _AsignacionDetalleScreenState extends State<AsignacionDetalleScreen> {
  final _asignacionesService = TecnicoAsignacionesService();
  AsignacionResponse? _asignacion;
  bool _loading = false;
  bool _iniciandoViaje = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _cargarAsignacion();
  }

  void _cargarAsignacion() async {
    // TODO: Implementar carga de asignación desde API
    // Por ahora es un placeholder
    print('[AsignacionDetalle] Cargar asignación ${widget.idAsignacion}');
  }

  void _iniciarViajeAhora() async {
    setState(() => _iniciandoViaje = true);

    try {
      print('[AsignacionDetalle] _iniciarViajeAhora');

      final resultado = await _asignacionesService.iniciarViaje(
        widget.idAsignacion,
      );

      setState(() {
        _asignacion = resultado;
      });

      // Mostrar notificación
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('✅ ¡Viaje iniciado! Estado: ${resultado.estado.nombre}'),
          backgroundColor: Colors.green,
        ),
      );

      print('[AsignacionDetalle] Viaje iniciado correctamente');
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('❌ Error: $e'),
          backgroundColor: Colors.red,
        ),
      );
      print('[AsignacionDetalle] Error: $e');
    } finally {
      setState(() => _iniciandoViaje = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Detalle de Asignación'),
      ),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Información del incidente
            Card(
              child: Padding(
                padding: EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Incidente',
                      style: Theme.of(context).textTheme.headline6,
                    ),
                    SizedBox(height: 8),
                    Text('Título: $_asignacion?.incidente.titulo ?? "N/A"'),
                    Text('Ubicación: $_asignacion?.incidente.ubicacion ?? "N/A"'),
                    SizedBox(height: 8),
                    Container(
                      padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.blue[100],
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        'Estado: ${_asignacion?.incidente.estado.nombre ?? "N/A"}',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            SizedBox(height: 16),

            // Estado de la asignación
            Card(
              child: Padding(
                padding: EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Estado de la Asignación',
                      style: Theme.of(context).textTheme.headline6,
                    ),
                    SizedBox(height: 8),
                    Container(
                      padding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      decoration: BoxDecoration(
                        color: _asignacion?.estado.nombre == 'aceptada'
                            ? Colors.orange[100]
                            : Colors.green[100],
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        _asignacion?.estado.nombre ?? 'N/A',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            SizedBox(height: 24),

            // Botón Iniciar Viaje (solo si está en estado "aceptada")
            if (_asignacion?.estado.nombre == 'aceptada')
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: _iniciandoViaje ? null : _iniciarViajeAhora,
                  icon: _iniciandoViaje
                      ? SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor:
                                AlwaysStoppedAnimation<Color>(Colors.white),
                          ),
                        )
                      : Icon(Icons.navigation),
                  label: Text('Iniciar Viaje'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.blue,
                    padding: EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              ),

            // Mostrar botón "Completar Servicio" si está en camino
            if (_asignacion?.estado.nombre == 'en_camino')
              Padding(
                padding: EdgeInsets.only(top: 16),
                child: SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: () {
                      // TODO: Navegar a pantalla de completar servicio
                      print('[AsignacionDetalle] Ir a completar servicio');
                    },
                    icon: Icon(Icons.check_circle),
                    label: Text('Completar Servicio'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.green,
                      padding: EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
```

---

## 🗺️ Flujo de Iniciar Viaje

```
┌──────────────────────┐
│ Pantalla Asignación  │
│ (Estado: aceptada)   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Botón "Iniciar Viaje"│
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Obtener GPS Actual   │
│ (Geolocation)        │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ PUT /tecnicos/mis-asignaciones/{id}/ │
│ iniciar-viaje                        │
│ {latitud, longitud}                  │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────┐
│ Estado → en_camino   │
│ Mostrar ✅           │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Mostrar botón        │
│ "Completar Servicio" │
└──────────────────────┘
```

---

## ✅ Checklist - Parte 2

- [ ] Agregar dependencias `geolocator` en `pubspec.yaml`
- [ ] Crear modelos `AsignacionResponse`, `EstadoAsignacion`, etc.
- [ ] Crear `TecnicoAsignacionesService` con `iniciarViaje()`
- [ ] Configurar permisos de ubicación (Android)
- [ ] Configurar permisos de ubicación (iOS)
- [ ] Crear pantalla `AsignacionDetalleScreen`
- [ ] Agregar botón "Iniciar Viaje"
- [ ] Mostrar notificación de éxito
- [ ] Manejo de errores (ubicación no disponible, etc.)

---

## ❌ Errores Posibles

| Error | Causa | Solución |
|-------|-------|----------|
| "Permiso de ubicación denegado" | Permisos no concedidos | Solicitar permisos al usuario |
| "Servicio de ubicación deshabilitado" | GPS apagado | Pedir al usuario que encienda GPS |
| 404 Not Found | Endpoint no existe | Verificar URL: `/tecnicos/mis-asignaciones/` |
| 400 Bad Request | Asignación no en estado "aceptada" | Verificar estado actual |
| 401 Unauthorized | Token expirado | Hacer login nuevamente |

---

## 🔐 Seguridad

✅ **Token guardado en `FlutterSecureStorage`**  
✅ **Headers con `Authorization: Bearer {token}`**  
✅ **Permisos de ubicación solicitados explícitamente**  
✅ **URL de API configurable**

---

## 📞 Próxima Parte

La **Parte 3** cubrirá:
- ✅ Endpoint: Completar Servicio
- 💰 Formulario para costo estimado
- 📝 Formulario para resumen del trabajo
- 🔄 Actualizar estado a `completada`

---

## 🐛 Debugging

```dart
// Ver ubicación actual
final position = await Geolocator.getCurrentPosition();
print('Lat: ${position.latitude}, Lon: ${position.longitude}');

// Ver estado de la asignación
print('Estado: ${_asignacion?.estado.nombre}');
print('Incidente: ${_asignacion?.incidente.titulo}');
```
