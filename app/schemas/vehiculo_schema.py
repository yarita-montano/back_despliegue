"""
Esquemas Pydantic para Vehículos (CU-05)
Define qué datos recibe la API (requests) y qué retorna (responses)
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ==========================================
# SCHEMAS PARA REGISTRO (POST /vehiculos/)
# ==========================================

class VehiculoCreate(BaseModel):
    """
    Datos que envía la app móvil (Flutter) para registrar un nuevo vehículo.
    ⚠️ IMPORTANTE: El id_usuario se extrae del JWT token, NO del request.
    
    Ejemplo:
    {
        "placa": "ABC-1234",
        "marca": "Toyota",
        "modelo": "Corolla",
        "anio": 2022,
        "color": "blanco"
    }
    """
    placa: str = Field(..., max_length=20, description="Placa del vehículo (ej: ABC-1234)")
    marca: Optional[str] = Field(None, max_length=50, description="Marca (ej: Toyota)")
    modelo: Optional[str] = Field(None, max_length=50, description="Modelo (ej: Corolla)")
    anio: Optional[int] = Field(None, ge=1900, le=2100, description="Año del vehículo")
    color: Optional[str] = Field(None, max_length=30, description="Color del vehículo")
    
    class Config:
        json_schema_extra = {
            "example": {
                "placa": "ABC-1234",
                "marca": "Toyota",
                "modelo": "Corolla",
                "anio": 2022,
                "color": "blanco"
            }
        }


class VehiculoUpdate(BaseModel):
    """
    Datos para actualizar un vehículo existente (PUT /vehiculos/{id_vehiculo})
    Todos los campos son opcionales.
    """
    placa: Optional[str] = Field(None, max_length=20, description="Nueva placa")
    marca: Optional[str] = Field(None, max_length=50, description="Nueva marca")
    modelo: Optional[str] = Field(None, max_length=50, description="Nuevo modelo")
    anio: Optional[int] = Field(None, ge=1900, le=2100, description="Nuevo año")
    color: Optional[str] = Field(None, max_length=30, description="Nuevo color")
    
    class Config:
        json_schema_extra = {
            "example": {
                "placa": "XYZ-5678",
                "color": "rojo"
            }
        }


# ==========================================
# SCHEMAS PARA RESPUESTAS
# ==========================================

class VehiculoResponse(BaseModel):
    """
    Datos que le devolvemos al cliente tras un registro o consulta exitosa.
    """
    id_vehiculo: int = Field(..., description="ID único del vehículo")
    id_usuario: int = Field(..., description="ID del propietario")
    placa: str = Field(..., description="Placa del vehículo")
    marca: Optional[str] = Field(None, description="Marca del vehículo")
    modelo: Optional[str] = Field(None, description="Modelo del vehículo")
    anio: Optional[int] = Field(None, description="Año del vehículo")
    color: Optional[str] = Field(None, description="Color del vehículo")
    activo: bool = Field(..., description="Si el vehículo está activo")
    created_at: datetime = Field(..., description="Fecha de creación")
    
    class Config:
        from_attributes = True  # Permite leer desde objetos SQLAlchemy
        json_schema_extra = {
            "example": {
                "id_vehiculo": 1,
                "id_usuario": 5,
                "placa": "ABC-1234",
                "marca": "Toyota",
                "modelo": "Corolla",
                "anio": 2022,
                "color": "blanco",
                "activo": True,
                "created_at": "2026-04-15T10:30:00"
            }
        }


class MensajeResponse(BaseModel):
    """Respuesta genérica de éxito o error"""
    mensaje: str = Field(..., description="Mensaje de respuesta")
    detalle: Optional[str] = Field(None, description="Detalles adicionales")
    
    class Config:
        json_schema_extra = {
            "example": {
                "mensaje": "Vehículo eliminado correctamente",
                "detalle": None
            }
        }
