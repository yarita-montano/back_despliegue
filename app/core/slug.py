"""
Generacion de slugs url-friendly para subdominios de tenant.

El slug de un tenant es lo que forma su subdominio:
    "Taller Excelente"  -> slug "taller-excelente" -> taller-excelente.tudominio.space
"""
import re
import unicodedata

from sqlalchemy.orm import Session


def slugify(text: str) -> str:
    """
    Convierte un texto a slug url-friendly:
      - minusculas
      - sin acentos/tildes (NFKD -> ascii)
      - solo [a-z0-9] y guiones; cualquier otra cosa se vuelve guion
      - sin guiones repetidos ni al inicio/fin
      - maximo 50 caracteres (limite de la columna tenant.slug)

    Ej: "Taller Excelente!!" -> "taller-excelente"
    """
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower().strip()
    ascii_text = re.sub(r"[^a-z0-9]+", "-", ascii_text)
    ascii_text = re.sub(r"-{2,}", "-", ascii_text).strip("-")
    return ascii_text[:50]


def unique_tenant_slug(db: Session, base: str) -> str:
    """
    Devuelve un slug UNICO para tenant a partir de `base` (nombre o slug tentativo).
    Si el slug ya existe, agrega sufijo numerico: -2, -3, ...

    Garantiza:
      - longitud minima 3 (la columna/validacion lo exige)
      - unicidad global (bypassa el filtro de tenant con current_tenant=0)
    """
    # import local para evitar ciclos de import en el arranque
    from app.core.tenant_context import current_tenant
    from app.models.tenant import Tenant

    slug = slugify(base) or "taller"
    if len(slug) < 3:
        slug = (slug + "-taller")[:50]

    tok = current_tenant.set(0)  # 0 = bypass del filtro global de tenant
    try:
        candidate = slug
        i = 2
        while db.query(Tenant).filter(Tenant.slug == candidate).first() is not None:
            suffix = f"-{i}"
            candidate = slug[: 50 - len(suffix)] + suffix
            i += 1
        return candidate
    finally:
        current_tenant.reset(tok)
