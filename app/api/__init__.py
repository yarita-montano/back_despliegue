"""
Routers de la aplicación
"""
from app.api.users import router as users_router
from app.api.talleres import router as talleres_router
from app.api.vehiculos import router as vehiculos_router
from app.api.incidencias import router as incidencias_router
from app.api.evidencias import router as evidencias_router
from app.api.tecnicos import router as tecnicos_router
from app.api.notificaciones import router as notificaciones_router
from app.api.mensajes import router as mensajes_router
from app.api.pagos import router as pagos_router

__all__ = [
    "users_router",
    "talleres_router",
    "vehiculos_router",
    "incidencias_router",
    "evidencias_router",
    "tecnicos_router",
    "notificaciones_router",
    "mensajes_router",
    "pagos_router",
]
