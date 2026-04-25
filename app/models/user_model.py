"""
Compatibilidad hacia atrás.
Los modelos reales viven en módulos separados bajo app/models/.
Se mantiene este archivo solo para no romper imports antiguos.
"""
from app.models.catalogos import Rol
from app.models.usuario import Usuario, Vehiculo
from app.models.taller import Taller, TallerServicio
from app.models.usuario_taller import UsuarioTaller

__all__ = ["Rol", "Usuario", "Vehiculo", "Taller", "TallerServicio", "UsuarioTaller"]
