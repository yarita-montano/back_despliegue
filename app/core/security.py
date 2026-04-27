"""
Funciones de seguridad: hash de contraseñas, JWT y autenticación.

La plataforma tiene DOS sistemas de autenticación independientes:
- Usuario (clientes de la app móvil): get_current_user
- Taller (panel web del taller):      get_current_taller

Cada uno se autentica contra su propia tabla y emite tokens con un claim
"tipo" para evitar que un token de uno se use en endpoints del otro.
"""
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.db.session import get_db
import calendar

ph = PasswordHasher()
settings = get_settings()

# Swagger usa este tokenUrl para el botón "Authorize".
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/usuarios/login")


# ==========================================
# HASH DE CONTRASEÑAS
# ==========================================

def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except VerifyMismatchError:
        return False


# ==========================================
# JWT
# ==========================================

def create_access_token(
    subject_id: int,
    tipo: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict] = None,
) -> str:
    """
    Crea un JWT con:
      - sub:  id del sujeto (id_usuario o id_taller)
      - tipo: "usuario" | "taller"
    """
    if tipo not in ("usuario", "taller", "tecnico"):
        raise ValueError("tipo debe ser 'usuario', 'taller' o 'tecnico'")

    to_encode: dict = {"sub": str(subject_id), "tipo": tipo}
    if extra_claims:
        to_encode.update(extra_claims)

    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    # Convertir a timestamp UTC explícitamente usando calendar.timegm
    # Esto evita problemas de zona horaria en Windows
    to_encode["exp"] = calendar.timegm(expire.timetuple())

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


# ==========================================
# DEPENDENCIAS DE AUTENTICACIÓN
# ==========================================

_credenciales_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No se pudieron validar las credenciales",
    headers={"WWW-Authenticate": "Bearer"},
)


def _decode_token(token: str) -> dict:
    payload = verify_token(token)
    if payload is None:
        raise _credenciales_exception
    return payload


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    Autentica a un Usuario (cliente / admin) de la app móvil.
    Rechaza tokens emitidos para un Taller.
    """
    from app.models.usuario import Usuario

    payload = _decode_token(token)
    if payload.get("tipo") != "usuario":
        raise _credenciales_exception

    sub = payload.get("sub")
    if sub is None:
        raise _credenciales_exception

    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise _credenciales_exception

    usuario = db.query(Usuario).filter(Usuario.id_usuario == user_id).first()
    if usuario is None:
        raise _credenciales_exception

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario ha sido desactivado",
        )

    return usuario


def get_current_admin(
    current_user=Depends(get_current_user),
):
    """
    Requiere rol de administrador (id_rol=4).
    Úsalo como dependencia en cualquier endpoint exclusivo de admin.
    """
    if current_user.id_rol != 4:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador",
        )
    return current_user


def get_current_taller(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    Autentica a un Taller (panel web del taller).
    Rechaza tokens emitidos para un Usuario.
    """
    from app.models.taller import Taller

    payload = _decode_token(token)
    if payload.get("tipo") != "taller":
        raise _credenciales_exception

    sub = payload.get("sub")
    if sub is None:
        raise _credenciales_exception

    try:
        taller_id = int(sub)
    except (TypeError, ValueError):
        raise _credenciales_exception

    taller = db.query(Taller).filter(Taller.id_taller == taller_id).first()
    if taller is None:
        raise _credenciales_exception

    if not taller.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El taller ha sido desactivado",
        )

    return taller
