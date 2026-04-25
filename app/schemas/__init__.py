"""
Esquemas Pydantic de la aplicación
"""
from app.schemas.user_schema import (
    UsuarioCreate,
    UsuarioResponse,
    UsuarioDetailResponse,
    UsuarioUpdate,
    LoginRequest,
    TokenResponse,
    RolResponse,
    MensajeResponse,
)
from app.schemas.taller_schema import (
    TallerLoginRequest,
    TallerUpdate,
    TallerResponse,
    TallerTokenResponse,
    TecnicoCreate,
    TecnicoUpdate,
    TecnicoResponse,
)

__all__ = [
    # Usuario
    "UsuarioCreate",
    "UsuarioResponse",
    "UsuarioDetailResponse",
    "UsuarioUpdate",
    "LoginRequest",
    "TokenResponse",
    "RolResponse",
    "MensajeResponse",
    # Taller
    "TallerLoginRequest",
    "TallerUpdate",
    "TallerResponse",
    "TallerTokenResponse",
    "TecnicoCreate",
    "TecnicoUpdate",
    "TecnicoResponse",
]
