# 📱 GUÍA FLUTTER A.2 PARTE 0: Obtener Asignación Actual

## 📌 Objetivo

Después que el técnico inicia sesión, debe **ver la información de su asignación activa** (si tiene una). Esta es la información que necesita para saber adónde ir y qué hacer.

---

## 🔗 Endpoint Backend

```
GET /tecnicos/asignacion-actual

Autenticación: Bearer {token}

Response (200):
{
  "id_asignacion": 24,
  "id_incidente": 15,
  "id_tecnico": 3,
  "id_taller": 2,
  "eta_minutos": 35,
  "nota_taller": "Cliente reportó ruido extraño",
  "estado": {
    "id_estado_asignacion": 2,
    "nombre": "aceptada"  // o "en_camino"
  },
  "incidente": {
    "id_incidente": 15,
    "descripcion_usuario": "Mi carro no prende",
    "resumen_ia": "Problema eléctrico detectado",
    "latitud": 4.7120,
    "longitud": -74.0730,
    "usuario": {
      "id_usuario": 5,
      "nombre": "Juan López",
      "telefono": "3001234567"
    },
    "vehiculo": {
      "id_vehiculo": 8,
      "placa": "ABC-123",
      "marca": "Toyota",
      "modelo": "Corolla",
      "anio": 2020,
      "color": "Blanco"
    },
    "categoria": {
      "id_categoria": 1,
      "nombre": "Problema Eléctrico"
    },
    "prioridad": {
      "id_prioridad": 2,
      "nivel": "Alta",
      "orden": 2
    }
  }
}

Error (404):
{
  "detail": "No tienes asignaciones activas en este momento"
}
```

---

## 🔄 Flujo de Uso

```
Login (Parte 1)
      ↓
Obtener Asignación Actual (PARTE 0) ← ESTÁS AQUÍ
      ↓
Ver Detalles del Incidente
      ↓
Navegar a Ubicación
      ↓
Iniciar Viaje (Parte 2)
      ↓
Completar Servicio (Parte 3)
      ↓
Asignación Desaparece (vuelve a 404)
```

---

## 🎯 Modelos Dart

### 1️⃣ EstadoAsignacion

```dart
class EstadoAsignacion {
  final int idEstadoAsignacion;
  final String nombre;  // "aceptada", "en_camino", "completada", "rechazada"

  EstadoAsignacion({
    required this.idEstadoAsignacion,
    required this.nombre,
  });

  factory EstadoAsignacion.fromJson(Map<String, dynamic> json) {
    return EstadoAsignacion(
      idEstadoAsignacion: json['id_estado_asignacion'] ?? 0,
      nombre: json['nombre'] ?? '',
    );
  }
}
```

### 2️⃣ ClienteData (usuario en incidente)

```dart
class ClienteData {
  final int idUsuario;
  final String nombre;
  final String? telefono;

  ClienteData({
    required this.idUsuario,
    required this.nombre,
    this.telefono,
  });

  factory ClienteData.fromJson(Map<String, dynamic> json) {
    return ClienteData(
      idUsuario: json['id_usuario'] ?? 0,
      nombre: json['nombre'] ?? '',
      telefono: json['telefono'],
    );
  }
}
```

### 3️⃣ VehiculoData

```dart
class VehiculoData {
  final int idVehiculo;
  final String placa;
  final String? marca;
  final String? modelo;
  final int? anio;
  final String? color;

  VehiculoData({
    required this.idVehiculo,
    required this.placa,
    this.marca,
    this.modelo,
    this.anio,
    this.color,
  });

  factory VehiculoData.fromJson(Map<String, dynamic> json) {
    return VehiculoData(
      idVehiculo: json['id_vehiculo'] ?? 0,
      placa: json['placa'] ?? '',
      marca: json['marca'],
      modelo: json['modelo'],
      anio: json['anio'],
      color: json['color'],
    );
  }
}
```

### 4️⃣ CategoriaData

```dart
class CategoriaData {
  final int idCategoria;
  final String nombre;

  CategoriaData({
    required this.idCategoria,
    required this.nombre,
  });

  factory CategoriaData.fromJson(Map<String, dynamic> json) {
    return CategoriaData(
      idCategoria: json['id_categoria'] ?? 0,
      nombre: json['nombre'] ?? '',
    );
  }
}
```

### 5️⃣ PrioridadData

```dart
class PrioridadData {
  final int idPrioridad;
  final String nivel;  // "Baja", "Media", "Alta", "Urgente"
  final int orden;

  PrioridadData({
    required this.idPrioridad,
    required this.nivel,
    required this.orden,
  });

  factory PrioridadData.fromJson(Map<String, dynamic> json) {
    return PrioridadData(
      idPrioridad: json['id_prioridad'] ?? 0,
      nivel: json['nivel'] ?? '',
      orden: json['orden'] ?? 0,
    );
  }
}
```

### 6️⃣ IncidenteData (completo)

```dart
class IncidenteData {
  final int idIncidente;
  final String? descripcionUsuario;
  final String? resumenIa;
  final double latitud;
  final double longitud;
  final DateTime createdAt;

  final ClienteData usuario;
  final VehiculoData vehiculo;
  final CategoriaData? categoria;
  final PrioridadData? prioridad;

  IncidenteData({
    required this.idIncidente,
    this.descripcionUsuario,
    this.resumenIa,
    required this.latitud,
    required this.longitud,
    required this.createdAt,
    required this.usuario,
    required this.vehiculo,
    this.categoria,
    this.prioridad,
  });

  factory IncidenteData.fromJson(Map<String, dynamic> json) {
    return IncidenteData(
      idIncidente: json['id_incidente'] ?? 0,
      descripcionUsuario: json['descripcion_usuario'],
      resumenIa: json['resumen_ia'],
      latitud: (json['latitud'] ?? 0.0).toDouble(),
      longitud: (json['longitud'] ?? 0.0).toDouble(),
      createdAt: DateTime.parse(json['created_at'] ?? DateTime.now().toString()),
      usuario: ClienteData.fromJson(json['usuario'] ?? {}),
      vehiculo: VehiculoData.fromJson(json['vehiculo'] ?? {}),
      categoria: json['categoria'] != null ? CategoriaData.fromJson(json['categoria']) : null,
      prioridad: json['prioridad'] != null ? PrioridadData.fromJson(json['prioridad']) : null,
    );
  }
}
```

### 7️⃣ AsignacionActualResponse (respuesta del endpoint)

```dart
class AsignacionActualResponse {
  final int idAsignacion;
  final int idIncidente;
  final int idTecnico;
  final int idTaller;
  final int? etaMinutos;
  final String? notaTaller;
  final DateTime createdAt;
  final DateTime updatedAt;

  final EstadoAsignacion estado;
  final IncidenteData incidente;

  AsignacionActualResponse({
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

  factory AsignacionActualResponse.fromJson(Map<String, dynamic> json) {
    return AsignacionActualResponse(
      idAsignacion: json['id_asignacion'] ?? 0,
      idIncidente: json['id_incidente'] ?? 0,
      idTecnico: json['id_tecnico'] ?? 0,
      idTaller: json['id_taller'] ?? 0,
      etaMinutos: json['eta_minutos'],
      notaTaller: json['nota_taller'],
      createdAt: DateTime.parse(json['created_at'] ?? DateTime.now().toString()),
      updatedAt: DateTime.parse(json['updated_at'] ?? DateTime.now().toString()),
      estado: EstadoAsignacion.fromJson(json['estado'] ?? {}),
      incidente: IncidenteData.fromJson(json['incidente'] ?? {}),
    );
  }
}
```

---

## 🔧 Servicio API

Agregar método en `TecnicoAsignacionesService`:

```dart
class TecnicoAsignacionesService {
  static const String baseUrl = 'http://192.168.x.x:8000';

  // ... métodos existentes ...

  /// Obtener la asignación activa del técnico
  static Future<AsignacionActualResponse?> obtenerAsignacionActual() async {
    try {
      final token = await TecnicoAuthService.getTecnicoToken();
      if (token == null) {
        throw Exception('Token no disponible');
      }

      final response = await http.get(
        Uri.parse('$baseUrl/tecnicos/asignacion-actual'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
      ).timeout(
        const Duration(seconds: 10),
        onTimeout: () => throw Exception('Timeout - Servidor no responde'),
      );

      if (response.statusCode == 200) {
        return AsignacionActualResponse.fromJson(jsonDecode(response.body));
      } else if (response.statusCode == 404) {
        // No hay asignación activa
        return null;
      } else {
        throw Exception('Error ${response.statusCode}: ${response.body}');
      }
    } catch (e) {
      debugPrint('Error al obtener asignación actual: $e');
      rethrow;
    }
  }
}
```

---

## 📱 Pantalla: Dashboard del Técnico

Después del login, el técnico ve esta pantalla:

```dart
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class TecnicoDashboardScreen extends StatefulWidget {
  const TecnicoDashboardScreen({Key? key}) : super(key: key);

  @override
  State<TecnicoDashboardScreen> createState() => _TecnicoDashboardScreenState();
}

class _TecnicoDashboardScreenState extends State<TecnicoDashboardScreen> {
  late Future<AsignacionActualResponse?> _asignacionFuture;
  bool _isLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _cargarAsignacion();
  }

  void _cargarAsignacion() {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _asignacionFuture = TecnicoAsignacionesService.obtenerAsignacionActual();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mi Asignación'),
        backgroundColor: Colors.blue.shade800,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _cargarAsignacion,
            tooltip: 'Actualizar',
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () {
              TecnicoAuthService.logout();
              Navigator.pushReplacementNamed(context, '/login');
            },
          ),
        ],
      ),
      body: FutureBuilder<AsignacionActualResponse?>(
        future: _asignacionFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(
              child: CircularProgressIndicator(),
            );
          }

          if (snapshot.hasError) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.error_outline, size: 50, color: Colors.red),
                  const SizedBox(height: 16),
                  Text(
                    'Error: ${snapshot.error}',
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: Colors.red),
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton.icon(
                    onPressed: _cargarAsignacion,
                    icon: const Icon(Icons.refresh),
                    label: const Text('Reintentar'),
                  ),
                ],
              ),
            );
          }

          if (!snapshot.hasData || snapshot.data == null) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.inbox_outlined, size: 80, color: Colors.grey),
                  const SizedBox(height: 16),
                  const Text(
                    'Sin asignaciones activas',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Espera a que el taller te asigne un trabajo',
                    style: TextStyle(color: Colors.grey, fontSize: 14),
                  ),
                  const SizedBox(height: 24),
                  ElevatedButton.icon(
                    onPressed: _cargarAsignacion,
                    icon: const Icon(Icons.refresh),
                    label: const Text('Actualizar'),
                  ),
                ],
              ),
            );
          }

          final asignacion = snapshot.data!;
          final incidente = asignacion.incidente;
          final estado = asignacion.estado.nombre;
          final esAceptada = estado == 'aceptada';
          final esEnCamino = estado == 'en_camino';

          return RefreshIndicator(
            onRefresh: () => _cargarAsignacion(),
            child: SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // ===== ESTADO =====
                  Card(
                    color: esAceptada ? Colors.yellow.shade100 : Colors.blue.shade100,
                    elevation: 2,
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Row(
                        children: [
                          Icon(
                            esAceptada ? Icons.check_circle : Icons.directions_car,
                            color: esAceptada ? Colors.orange : Colors.blue,
                            size: 40,
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Estado: ${estado.toUpperCase()}',
                                  style: TextStyle(
                                    fontSize: 16,
                                    fontWeight: FontWeight.bold,
                                    color: esAceptada ? Colors.orange : Colors.blue,
                                  ),
                                ),
                                if (asignacion.etaMinutos != null)
                                  Text(
                                    'ETA: ${asignacion.etaMinutos} min',
                                    style: const TextStyle(fontSize: 12, color: Colors.grey),
                                  ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // ===== CLIENTE =====
                  _buildSectionTitle('👤 Cliente'),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            incidente.usuario.nombre,
                            style: const TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          if (incidente.usuario.telefono != null) ...[
                            const SizedBox(height: 8),
                            Row(
                              children: [
                                const Icon(Icons.phone, size: 16, color: Colors.blue),
                                const SizedBox(width: 8),
                                Flexible(
                                  child: GestureDetector(
                                    onTap: () {
                                      // Abrir dialplan o copiar
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        SnackBar(
                                          content: Text(
                                            'Teléfono: ${incidente.usuario.telefono}',
                                          ),
                                        ),
                                      );
                                    },
                                    child: Text(
                                      incidente.usuario.telefono!,
                                      style: const TextStyle(color: Colors.blue),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // ===== VEHÍCULO =====
                  _buildSectionTitle('🚗 Vehículo'),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text(
                                incidente.vehiculo.placa,
                                style: const TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.blue,
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Text(
                                  '${incidente.vehiculo.marca ?? ''} ${incidente.vehiculo.modelo ?? ''} (${incidente.vehiculo.anio ?? ''})',
                                  style: const TextStyle(fontSize: 12, color: Colors.grey),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ],
                          ),
                          if (incidente.vehiculo.color != null) ...[
                            const SizedBox(height: 8),
                            Text(
                              'Color: ${incidente.vehiculo.color}',
                              style: const TextStyle(fontSize: 12),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // ===== PROBLEMA =====
                  _buildSectionTitle('⚠️ Problema'),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (incidente.categoria != null) ...[
                            Text(
                              'Categoría: ${incidente.categoria!.nombre}',
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                                color: Colors.orange,
                              ),
                            ),
                            const SizedBox(height: 8),
                          ],
                          if (incidente.prioridad != null) ...[
                            Row(
                              children: [
                                Icon(
                                  Icons.priority_high,
                                  color: _getPrioridadColor(incidente.prioridad!.nivel),
                                  size: 18,
                                ),
                                const SizedBox(width: 8),
                                Text(
                                  'Prioridad: ${incidente.prioridad!.nivel}',
                                  style: TextStyle(
                                    fontWeight: FontWeight.bold,
                                    color: _getPrioridadColor(incidente.prioridad!.nivel),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                          ],
                          if (incidente.descripcionUsuario != null) ...[
                            Text(
                              'Usuario: "${incidente.descripcionUsuario}"',
                              style: const TextStyle(fontSize: 12),
                            ),
                            const SizedBox(height: 8),
                          ],
                          if (incidente.resumenIa != null) ...[
                            Container(
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: Colors.blue.shade50,
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Row(
                                children: [
                                  const Icon(Icons.lightbulb, size: 16, color: Colors.blue),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      'IA: ${incidente.resumenIa}',
                                      style: const TextStyle(fontSize: 12),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // ===== NOTA DEL TALLER =====
                  if (asignacion.notaTaller != null) ...[
                    _buildSectionTitle('📝 Nota del Taller'),
                    Card(
                      color: Colors.amber.shade50,
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Text(asignacion.notaTaller!),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],

                  // ===== BOTONES DE ACCIÓN =====
                  if (esAceptada) ...[
                    ElevatedButton.icon(
                      onPressed: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => AsignacionDetalleScreen(
                              asignacion: asignacion,
                              onComplete: _cargarAsignacion,
                            ),
                          ),
                        );
                      },
                      icon: const Icon(Icons.directions_run),
                      label: const Text('Iniciar Viaje'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.green,
                        minimumSize: const Size.fromHeight(48),
                      ),
                    ),
                  ] else if (esEnCamino) ...[
                    ElevatedButton.icon(
                      onPressed: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => AsignacionDetalleScreen(
                              asignacion: asignacion,
                              onComplete: _cargarAsignacion,
                            ),
                          ),
                        );
                      },
                      icon: const Icon(Icons.done_all),
                      label: const Text('Completar Servicio'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.green,
                        minimumSize: const Size.fromHeight(48),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        title,
        style: const TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.bold,
          color: Colors.grey,
        ),
      ),
    );
  }

  Color _getPrioridadColor(String nivel) {
    switch (nivel.toLowerCase()) {
      case 'urgente':
        return Colors.red;
      case 'alta':
        return Colors.orange;
      case 'media':
        return Colors.amber;
      default:
        return Colors.green;
    }
  }
}
```

---

## ✅ Checklist de Implementación

- [ ] Importar `http` en pubspec.yaml
- [ ] Crear todos los modelos Dart (EstadoAsignacion, ClienteData, etc.)
- [ ] Crear modelo `AsignacionActualResponse`
- [ ] Implementar método `obtenerAsignacionActual()` en `TecnicoAsignacionesService`
- [ ] Crear pantalla `TecnicoDashboardScreen`
- [ ] Agregarpantalla al router/navegación
- [ ] Después del login, navegar a `TecnicoDashboardScreen` (no a home genérico)
- [ ] Probar que carga bien si hay asignación
- [ ] Probar que muestra "Sin asignaciones" si técnico no tiene trabajo
- [ ] Implementar refresh manual (swipe down)
- [ ] Probar botones: "Iniciar Viaje" (si aceptada) o "Completar Servicio" (si en_camino)
- [ ] Agregar logout (ir a login screen)

---

## 🧪 Prueba del Endpoint

```bash
# Con token válido
curl -X GET http://localhost:8000/tecnicos/asignacion-actual \
  -H "Authorization: Bearer {token_tecnico}"

# Respuesta si hay asignación activa (200):
{
  "id_asignacion": 24,
  "id_incidente": 15,
  "id_tecnico": 3,
  "id_taller": 2,
  "estado": {"id_estado_asignacion": 2, "nombre": "aceptada"},
  "incidente": {...},
  ...
}

# Respuesta si NO hay asignación (404):
{"detail": "No tienes asignaciones activas en este momento"}
```

---

## 🔑 Puntos Clave

✅ **Endpoint único**: El técnico siempre tiene 0 o 1 asignación activa  
✅ **Estados válidos**: Solo "aceptada" o "en_camino"  
✅ **Información completa**: Cliente, vehículo, problema, categoría, prioridad  
✅ **Refresh automático**: El usuario puede actualizar con swipe down  
✅ **Sin asignación**: Muestra pantalla vacía (no error)  
✅ **Navegación**: De aquí van a "Iniciar Viaje" o "Completar"  

---

**Próxima parte**: PARTE 2 - Iniciar Viaje (obtener GPS)  
**Después**: PARTE 3 - Completar Servicio (reportar costo)
