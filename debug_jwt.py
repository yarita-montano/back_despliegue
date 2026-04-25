#!/usr/bin/env python3
"""Script para diagnosticar problemas con JWT"""

from app.core.config import get_settings
from app.core.security import create_access_token, verify_token
from datetime import datetime

settings = get_settings()
print('=== CONFIGURACION DEL SERVIDOR ===')
print(f'  SECRET_KEY: {settings.SECRET_KEY[:20]}...')
print(f'  ALGORITHM: {settings.ALGORITHM}')
print(f'  TOKEN_EXPIRE_MINUTES: {settings.ACCESS_TOKEN_EXPIRE_MINUTES}')
print(f'  DATABASE_URL: {settings.DATABASE_URL}\n')

# Generar token como lo hace el login
print('=== GENERANDO TOKEN ===')
token = create_access_token(subject_id=1, tipo='usuario')
print(f'Token: {token[:50]}...')
print(f'Largo: {len(token)} caracteres\n')

# Verificar token como lo hace get_current_user
print('=== VERIFICANDO TOKEN ===')
payload = verify_token(token)

if payload:
    print('OK - Token valido')
    print(f'  sub: {payload.get("sub")}')
    print(f'  tipo: {payload.get("tipo")}')
    exp_timestamp = payload.get('exp')
    exp_datetime = datetime.fromtimestamp(exp_timestamp)
    print(f'  exp: {exp_datetime}')
    duracion_seg = int(exp_timestamp - datetime.now().timestamp())
    print(f'  Expira en: {duracion_seg} segundos ({duracion_seg // 60} minutos)')
else:
    print('ERROR - Token invalido o expirado')
