"""
Modelos SQLAlchemy de la aplicación.
Importar desde aquí garantiza que todas las tablas queden registradas en Base.metadata.
"""
from app.models.catalogos import (
    Rol,
    EstadoIncidente,
    CategoriaProblema,
    Prioridad,
    EstadoAsignacion,
    TipoEvidencia,
    MetodoPago,
    EstadoPago,
)
from app.models.usuario import Usuario, Vehiculo
from app.models.taller import Taller, TallerServicio
from app.models.usuario_taller import UsuarioTaller
from app.models.incidente import (
    Incidente,
    Asignacion,
    Evidencia,
    HistorialEstadoIncidente,
    HistorialEstadoAsignacion,
    CandidatoAsignacion,
    Evaluacion,
)
from app.models.transaccional import Notificacion, Pago, Metrica, Mensaje

__all__ = [
    # Catálogos
    "Rol",
    "EstadoIncidente",
    "CategoriaProblema",
    "Prioridad",
    "EstadoAsignacion",
    "TipoEvidencia",
    "MetodoPago",
    "EstadoPago",
    # Usuario / vehículos
    "Usuario",
    "Vehiculo",
    # Taller / técnicos
    "Taller",
    "TallerServicio",
    "Tecnico",
    # Incidentes y asignaciones
    "Incidente",
    "Asignacion",
    "Evidencia",
    "HistorialEstadoIncidente",
    "HistorialEstadoAsignacion",
    "CandidatoAsignacion",
    "Evaluacion",
    # Transaccional
    "Notificacion",
    "Pago",
    "Metrica",
    "Mensaje",
]
