"""
Router de Vehículos (CU-05)
Endpoints para:
- Registrar un nuevo vehículo (POST /vehiculos/)
- Listar los vehículos del usuario autenticado (GET /vehiculos/mis-autos)
- Obtener detalles de un vehículo específico (GET /vehiculos/{id_vehiculo})
- Editar un vehículo (PUT /vehiculos/{id_vehiculo})
- Dar de baja lógica un vehículo (DELETE /vehiculos/{id_vehiculo})
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.usuario import Usuario, Vehiculo
from app.schemas.vehiculo_schema import (
    VehiculoCreate,
    VehiculoResponse,
    VehiculoUpdate,
    MensajeResponse
)
from app.core.security import get_current_user

router = APIRouter(
    prefix="/vehiculos",
    tags=["Gestión de Vehículos (CU-05)"],
    responses={
        400: {"description": "Bad Request - Validación fallida"},
        401: {"description": "Unauthorized - Token inválido o expirado"},
        404: {"description": "Not Found - Vehículo no encontrado"},
        409: {"description": "Conflict - Placa ya registrada"}
    }
)


@router.post(
    "/",
    response_model=VehiculoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo vehículo",
    description="Crea un nuevo vehículo asociado al usuario autenticado. "
                "La placa debe ser única y activa para ese usuario."
)
def registrar_vehiculo(
    vehiculo_in: VehiculoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Endpoint para que la app móvil (Flutter) registre un nuevo vehículo.
    
    ⚠️ SEGURIDAD: El id_usuario se extrae del JWT token, NO del request.
    
    **Request:**
    ```json
    {
        "placa": "ABC-1234",
        "marca": "Toyota",
        "modelo": "Corolla",
        "anio": 2022,
        "color": "blanco"
    }
    ```
    
    **Response (201 Created):**
    ```json
    {
        "id_vehiculo": 1,
        "id_usuario": 5,
        "placa": "ABC-1234",
        "marca": "Toyota",
        "modelo": "Corolla",
        "anio": 2022,
        "color": "blanco",
        "activo": true,
        "created_at": "2026-04-15T10:30:00"
    }
    ```
    
    **Errores:**
    - 409: La placa ya está registrada por este usuario
    - 401: Token inválido o expirado
    """
    
    # 1️⃣ Verificar que la placa no esté ya registrada por este usuario (activa)
    vehiculo_existente = db.query(Vehiculo).filter(
        Vehiculo.placa == vehiculo_in.placa,
        Vehiculo.id_usuario == current_user.id_usuario,
        Vehiculo.activo == True
    ).first()
    
    if vehiculo_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La placa '{vehiculo_in.placa}' ya está registrada en tu cuenta"
        )
    
    # 2️⃣ Crear el nuevo vehículo con el id_usuario del token
    nuevo_vehiculo = Vehiculo(
        id_usuario=current_user.id_usuario,
        placa=vehiculo_in.placa,
        marca=vehiculo_in.marca,
        modelo=vehiculo_in.modelo,
        anio=vehiculo_in.anio,
        color=vehiculo_in.color,
        activo=True
    )
    
    # 3️⃣ Guardar en la base de datos
    db.add(nuevo_vehiculo)
    db.commit()
    db.refresh(nuevo_vehiculo)
    
    return nuevo_vehiculo


@router.get(
    "/mis-autos",
    response_model=List[VehiculoResponse],
    summary="Listar mis vehículos",
    description="Retorna todos los vehículos activos del usuario autenticado."
)
def listar_mis_vehiculos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Endpoint para que la app móvil consulte los vehículos del usuario logueado.
    
    ⚠️ SEGURIDAD: Solo retorna vehículos del usuario autenticado.
    
    **Response (200 OK):**
    ```json
    [
        {
            "id_vehiculo": 1,
            "id_usuario": 5,
            "placa": "ABC-1234",
            "marca": "Toyota",
            "modelo": "Corolla",
            "anio": 2022,
            "color": "blanco",
            "activo": true,
            "created_at": "2026-04-15T10:30:00"
        },
        {
            "id_vehiculo": 2,
            "id_usuario": 5,
            "placa": "XYZ-5678",
            "marca": "Honda",
            "modelo": "Civic",
            "anio": 2023,
            "color": "negro",
            "activo": true,
            "created_at": "2026-04-16T14:20:00"
        }
    ]
    ```
    
    **Errores:**
    - 401: Token inválido o expirado
    """
    
    # Obtener todos los vehículos activos del usuario logueado
    mis_autos = db.query(Vehiculo).filter(
        Vehiculo.id_usuario == current_user.id_usuario,
        Vehiculo.activo == True
    ).order_by(Vehiculo.created_at.desc()).all()
    
    return mis_autos


@router.get(
    "/{id_vehiculo}",
    response_model=VehiculoResponse,
    summary="Obtener detalles de un vehículo",
    description="Retorna los detalles de un vehículo específico (solo si es del usuario autenticado)."
)
def obtener_vehiculo(
    id_vehiculo: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Endpoint para obtener detalles de un vehículo específico.
    
    ⚠️ SEGURIDAD: El usuario solo puede ver sus propios vehículos.
    
    **Response (200 OK):**
    ```json
    {
        "id_vehiculo": 1,
        "id_usuario": 5,
        "placa": "ABC-1234",
        "marca": "Toyota",
        "modelo": "Corolla",
        "anio": 2022,
        "color": "blanco",
        "activo": true,
        "created_at": "2026-04-15T10:30:00"
    }
    ```
    
    **Errores:**
    - 404: Vehículo no encontrado o no pertenece al usuario
    - 401: Token inválido o expirado
    """
    
    # Buscar el vehículo
    vehiculo = db.query(Vehiculo).filter(
        Vehiculo.id_vehiculo == id_vehiculo
    ).first()
    
    # Verificar que exista
    if not vehiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehículo no encontrado"
        )
    
    # Verificar que pertenezca al usuario autenticado
    if vehiculo.id_usuario != current_user.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tienes permiso para ver este vehículo"
        )
    
    return vehiculo


@router.put(
    "/{id_vehiculo}",
    response_model=VehiculoResponse,
    summary="Editar un vehículo",
    description="Actualiza los datos de un vehículo existente."
)
def editar_vehiculo(
    id_vehiculo: int,
    vehiculo_in: VehiculoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Endpoint para editar los datos de un vehículo.
    
    ⚠️ SEGURIDAD: El usuario solo puede editar sus propios vehículos.
    
    **Request:**
    ```json
    {
        "placa": "XYZ-5678",
        "color": "rojo"
    }
    ```
    
    **Response (200 OK):**
    ```json
    {
        "id_vehiculo": 1,
        "id_usuario": 5,
        "placa": "XYZ-5678",
        "marca": "Toyota",
        "modelo": "Corolla",
        "anio": 2022,
        "color": "rojo",
        "activo": true,
        "created_at": "2026-04-15T10:30:00"
    }
    ```
    
    **Errores:**
    - 404: Vehículo no encontrado o no pertenece al usuario
    - 409: La nueva placa ya está registrada
    - 401: Token inválido o expirado
    """
    
    # Buscar el vehículo
    vehiculo = db.query(Vehiculo).filter(
        Vehiculo.id_vehiculo == id_vehiculo
    ).first()
    
    # Verificar que exista
    if not vehiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehículo no encontrado"
        )
    
    # Verificar que pertenezca al usuario autenticado
    if vehiculo.id_usuario != current_user.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tienes permiso para editar este vehículo"
        )
    
    # Si se intenta cambiar la placa, validar que no exista otra con esa placa
    if vehiculo_in.placa and vehiculo_in.placa != vehiculo.placa:
        placa_existente = db.query(Vehiculo).filter(
            Vehiculo.placa == vehiculo_in.placa,
            Vehiculo.id_usuario == current_user.id_usuario,
            Vehiculo.activo == True,
            Vehiculo.id_vehiculo != id_vehiculo  # Excluir el actual
        ).first()
        
        if placa_existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"La placa '{vehiculo_in.placa}' ya está registrada en tu cuenta"
            )
    
    # Actualizar solo los campos que vienen en el request
    if vehiculo_in.placa is not None:
        vehiculo.placa = vehiculo_in.placa
    if vehiculo_in.marca is not None:
        vehiculo.marca = vehiculo_in.marca
    if vehiculo_in.modelo is not None:
        vehiculo.modelo = vehiculo_in.modelo
    if vehiculo_in.anio is not None:
        vehiculo.anio = vehiculo_in.anio
    if vehiculo_in.color is not None:
        vehiculo.color = vehiculo_in.color
    
    # Guardar cambios
    db.commit()
    db.refresh(vehiculo)
    
    return vehiculo


@router.delete(
    "/{id_vehiculo}",
    response_model=MensajeResponse,
    status_code=status.HTTP_200_OK,
    summary="Dar de baja un vehículo",
    description="Marca un vehículo como inactivo (baja lógica, no se elimina de la BD)."
)
def eliminar_vehiculo(
    id_vehiculo: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Endpoint para dar de baja un vehículo.
    
    ⚠️ IMPORTANTE: Es una baja lógica (soft delete). El vehículo se marca como inactivo
    pero los datos históricamente se conservan en la BD.
    
    ⚠️ SEGURIDAD: El usuario solo puede dar de baja sus propios vehículos.
    
    **Response (200 OK):**
    ```json
    {
        "mensaje": "Vehículo eliminado correctamente",
        "detalle": "El vehículo ABC-1234 ha sido marcado como inactivo"
    }
    ```
    
    **Errores:**
    - 404: Vehículo no encontrado o no pertenece al usuario
    - 401: Token inválido o expirado
    """
    
    # Buscar el vehículo
    vehiculo = db.query(Vehiculo).filter(
        Vehiculo.id_vehiculo == id_vehiculo
    ).first()
    
    # Verificar que exista
    if not vehiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehículo no encontrado"
        )
    
    # Verificar que pertenezca al usuario autenticado
    if vehiculo.id_usuario != current_user.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tienes permiso para eliminar este vehículo"
        )
    
    # Marcar como inactivo (baja lógica)
    vehiculo.activo = False
    db.commit()
    
    return {
        "mensaje": "Vehículo eliminado correctamente",
        "detalle": f"El vehículo con placa '{vehiculo.placa}' ha sido marcado como inactivo"
    }
