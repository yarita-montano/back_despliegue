"""
Servicio de Cloudinary: sube archivos (imágenes/audios) y devuelve la URL.
Las URLs se guardan en la tabla `evidencia`.
"""
import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException, status
from app.core.config import get_settings

settings = get_settings()

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)


_TIPO_A_RESOURCE = {
    "imagen": "image",
    "audio": "video",  # Cloudinary maneja audio dentro de "video"
    "texto": "raw",
}


async def subir_evidencia(
    archivo: UploadFile,
    tipo: str,
    id_incidente: int,
) -> dict:
    """
    Sube un archivo a Cloudinary dentro de la carpeta:
        emergencias/incidente_{id}/
    Retorna:
        {"url": str, "public_id": str}
    """
    if tipo not in _TIPO_A_RESOURCE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo inválido. Debe ser uno de: {list(_TIPO_A_RESOURCE.keys())}",
        )

    try:
        contenido = await archivo.read()
        resultado = cloudinary.uploader.upload(
            contenido,
            folder=f"emergencias/incidente_{id_incidente}",
            resource_type=_TIPO_A_RESOURCE[tipo],
            use_filename=True,
            unique_filename=True,
        )
        return {
            "url": resultado["secure_url"],
            "public_id": resultado["public_id"],
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al subir archivo a Cloudinary: {e}",
        )
