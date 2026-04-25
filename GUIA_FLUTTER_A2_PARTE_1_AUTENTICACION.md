# 📱 Guía Flutter: Endpoints del Técnico (A.2 - CU-20)
## PARTE 1: Autenticación del Técnico

### 📌 Resumen
El técnico necesita un **login propio** con email y password. Se genera un JWT que se usa para los endpoints de iniciar viaje y completar servicio.

---

## 1️⃣ Endpoint: Login del Técnico

### Request
```bash
POST http://localhost:8000/tecnicos/login
Content-Type: application/json

{
  "email": "tecnico@tallerexcelente.com",
  "password": "tecnico123"
}
```

### Response (200 OK)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
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

---

## 💻 Implementar en Flutter

### Paso 1: Crear Modelo `TecnicoLoginResponse`

**lib/models/tecnico_login_response.dart**:

```dart
class TecnicoLoginResponse {
  final String accessToken;
  final String tokenType;
  final TecnicoData tecnico;

  TecnicoLoginResponse({
    required this.accessToken,
    required this.tokenType,
    required this.tecnico,
  });

  factory TecnicoLoginResponse.fromJson(Map<String, dynamic> json) {
    return TecnicoLoginResponse(
      accessToken: json['access_token'],
      tokenType: json['token_type'],
      tecnico: TecnicoData.fromJson(json['tecnico']),
    );
  }
}

class TecnicoData {
  final int idTecnico;
  final int idTaller;
  final String nombre;
  final String? telefono;
  final bool disponible;
  final double? latitud;
  final double? longitud;
  final bool activo;
  final String createdAt;

  TecnicoData({
    required this.idTecnico,
    required this.idTaller,
    required this.nombre,
    this.telefono,
    required this.disponible,
    this.latitud,
    this.longitud,
    required this.activo,
    required this.createdAt,
  });

  factory TecnicoData.fromJson(Map<String, dynamic> json) {
    return TecnicoData(
      idTecnico: json['id_tecnico'],
      idTaller: json['id_taller'],
      nombre: json['nombre'],
      telefono: json['telefono'],
      disponible: json['disponible'] ?? true,
      latitud: json['latitud']?.toDouble(),
      longitud: json['longitud']?.toDouble(),
      activo: json['activo'] ?? true,
      createdAt: json['created_at'],
    );
  }
}
```

---

### Paso 2: Crear Servicio de Autenticación del Técnico

**lib/services/tecnico_auth_service.dart**:

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../models/tecnico_login_response.dart';

class TecnicoAuthService {
  static const String _baseUrl = 'http://localhost:8000';
  static const String _tecnicoTokenKey = 'tecnico_token';
  static const String _tecnicoIdKey = 'tecnico_id';
  static const String _tallerIdKey = 'taller_id';

  final _storage = const FlutterSecureStorage();

  /// Login del técnico
  Future<TecnicoLoginResponse> loginTecnico(String email, String password) async {
    try {
      print('[TecnicoAuthService] loginTecnico → $email');

      final response = await http.post(
        Uri.parse('$_baseUrl/tecnicos/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email, 'password': password}),
      );

      if (response.statusCode == 200) {
        final data = TecnicoLoginResponse.fromJson(jsonDecode(response.body));
        
        // Guardar token y datos
        await _storage.write(key: _tecnicoTokenKey, value: data.accessToken);
        await _storage.write(key: _tecnicoIdKey, value: data.tecnico.idTecnico.toString());
        await _storage.write(key: _tallerIdKey, value: data.tecnico.idTaller.toString());

        print('[TecnicoAuthService] loginTecnico ← OK ${data.tecnico.nombre}');
        return data;
      } else {
        throw Exception('Error: ${response.statusCode} - ${response.body}');
      }
    } catch (e) {
      print('[TecnicoAuthService] loginTecnico ← ERROR: $e');
      rethrow;
    }
  }

  /// Obtener token guardado
  Future<String?> getTecnicoToken() async {
    return await _storage.read(key: _tecnicoTokenKey);
  }

  /// Obtener ID del técnico
  Future<int?> getTecnicoId() async {
    final id = await _storage.read(key: _tecnicoIdKey);
    return id != null ? int.parse(id) : null;
  }

  /// Obtener ID del taller
  Future<int?> getTallerId() async {
    final id = await _storage.read(key: _tallerIdKey);
    return id != null ? int.parse(id) : null;
  }

  /// Verificar si hay sesión activa
  Future<bool> isTecnicoLoggedIn() async {
    final token = await _storage.read(key: _tecnicoTokenKey);
    return token != null && token.isNotEmpty;
  }

  /// Logout
  Future<void> logout() async {
    print('[TecnicoAuthService] logout');
    await _storage.delete(key: _tecnicoTokenKey);
    await _storage.delete(key: _tecnicoIdKey);
    await _storage.delete(key: _tallerIdKey);
  }
}
```

---

### Paso 3: Implementar Login en la UI

**lib/screens/tecnico_login_screen.dart**:

```dart
import 'package:flutter/material.dart';
import '../services/tecnico_auth_service.dart';

class TecnicoLoginScreen extends StatefulWidget {
  @override
  _TecnicoLoginScreenState createState() => _TecnicoLoginScreenState();
}

class _TecnicoLoginScreenState extends State<TecnicoLoginScreen> {
  final _authService = TecnicoAuthService();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _login() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final response = await _authService.loginTecnico(
        _emailController.text.trim(),
        _passwordController.text,
      );

      print('[Login] Técnico: ${response.tecnico.nombre}');

      // Navegar a home del técnico
      Navigator.of(context).pushReplacementNamed('/tecnico-home');
    } catch (e) {
      setState(() {
        _error = 'Error: $e';
      });
      print('[Login Error] $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Login Técnico')),
      body: Padding(
        padding: EdgeInsets.all(16.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            TextField(
              controller: _emailController,
              decoration: InputDecoration(labelText: 'Email'),
              keyboardType: TextInputType.emailAddress,
            ),
            SizedBox(height: 16),
            TextField(
              controller: _passwordController,
              decoration: InputDecoration(labelText: 'Contraseña'),
              obscureText: true,
            ),
            SizedBox(height: 24),
            if (_error != null)
              Padding(
                padding: EdgeInsets.only(bottom: 16),
                child: Text(_error!, style: TextStyle(color: Colors.red)),
              ),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _loading ? null : _login,
                child: _loading
                    ? SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Text('Iniciar Sesión'),
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

### Paso 4: Guardar Token Seguro

**Agregar a `pubspec.yaml`**:

```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.1.0
  flutter_secure_storage: ^9.0.0
```

---

## 🔐 Flujo de Autenticación

```
┌─────────────────┐
│  Login Screen   │
│  (Email/Pass)   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│ POST /tecnicos/login        │
│ {email, password}           │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ GuardarFlutterSecureStorage │
│ - token                     │
│ - id_tecnico                │
│ - id_taller                 │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────┐
│  Home Técnico   │
│  (Token válido) │
└─────────────────┘
```

---

## ✅ Checklist - Parte 1

- [ ] Crear modelos `TecnicoLoginResponse` y `TecnicoData`
- [ ] Crear `TecnicoAuthService` con método `loginTecnico()`
- [ ] Configurar `flutter_secure_storage` en `pubspec.yaml`
- [ ] Crear pantalla de login
- [ ] Guardar token después de login exitoso
- [ ] Implementar logout
- [ ] Navegar a home del técnico después de login

---

## 📞 Próxima Parte

La **Parte 2** cubrirá:
- ⏯️ Endpoint: Iniciar Viaje
- 📍 Obtener geolocalización del dispositivo
- 🔄 Actualizar estado de asignación

---

## ⚠️ Notas Importantes

1. **Token**: Se almacena en `FlutterSecureStorage` (no en SharedPreferences)
2. **Email**: El técnico debe tener email asignado por el taller
3. **Password**: Se asigna cuando el taller crea/edita el técnico
4. **URL**: Reemplaza `localhost:8000` con la URL de producción

---

## 🐛 Debugging

```dart
// Ver si está logueado
bool loggedIn = await _authService.isTecnicoLoggedIn();
print('¿Técnico logueado? $loggedIn');

// Ver el token
String? token = await _authService.getTecnicoToken();
print('Token: $token');

// Ver ID del técnico
int? id = await _authService.getTecnicoId();
print('ID Técnico: $id');
```
