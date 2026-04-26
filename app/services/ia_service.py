
import json
import logging
import re
from typing import List, Optional

import httpx
from google import genai
from google.genai import types
from sqlalchemy.orm import Session

logger = logging.getLogger("ia_service")
logging.basicConfig(level=logging.INFO)

from app.core.config import get_settings
from app.models.incidente import Incidente, Evidencia
from app.models.catalogos import CategoriaProblema, Prioridad, TipoEvidencia
from app.services.asignacion import buscar_y_asignar

settings = get_settings()

_client = genai.Client(api_key=settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else None

_SYSTEM_PROMPT = """Eres un experto en emergencias vehiculares. Analizas reportes de clientes varados en carretera usando:
- La descripcion escrita del usuario
- Imagenes adjuntas del vehiculo/escena (si las hay)
- Audios adjuntos donde el cliente describe el problema hablando (si los hay)

Determinas:
1. La categoria del problema (de una lista fija)
2. La prioridad de atencion (de una lista fija)
3. Un resumen tecnico BREVE en espanol (maximo 200 caracteres, una o dos frases)
4. Tu nivel de confianza en la clasificacion (0.0 a 1.0)

Cuando haya audio, escuchalo para entender lo que el cliente dice sobre el problema e incorpora esa informacion a tu diagnostico.

REGLAS BASE DE PRIORIDAD (ajusta segun la lista fija que recibas):
- Critica: riesgo vital inmediato (accidente con heridos, fuego, humo, colision fuerte, volcadura)
- Alta: cliente varado EN VIA activa sin poder moverse (falla mecanica bloqueando carril, no enciende en carretera)
- Media: problema resoluble pero el cliente no puede continuar (llanta ponchada, bateria muerta, falla electrica) en lugar relativamente seguro
- Baja: mantenimiento o situacion sin urgencia (revision, consulta, problema leve con el vehiculo ya detenido sin riesgo)

AJUSTA LA PRIORIDAD SEGUN EL CONTEXTO que el usuario mencione en su descripcion o audio:

SUBE la prioridad uno o dos niveles si el usuario menciona:
- Esta en autopista, carretera principal, via rapida o zona de alta velocidad
- Es de noche, madrugada, o hay poca visibilidad
- Esta solo/a, es mujer sola, o con menores/ninos/bebes/adulto mayor/mascota
- Mal clima: lluvia fuerte, neblina, tormenta, frio extremo, calor extremo
- Esta bloqueando el trafico o en curva/punto ciego
- Zona peligrosa, insegura, despoblada, sin senal, sin luz
- Siente miedo, ansiedad, dolor, o menciona urgencia ("rapido", "ayuda ya", "no aguanto")
- Combustible agotado en lugar expuesto
- Humo, olor a quemado, ruidos fuertes, fuga visible

BAJA la prioridad uno nivel si el usuario menciona:
- Esta en un estacionamiento, cochera, taller, gasolinera o lugar seguro
- Esta en casa, oficina, centro comercial, zona urbana tranquila
- Puede esperar, no tiene prisa, ya resolvio parcialmente
- Hay acompanantes que lo auxilian, esta con familiares o amigos
- Es de dia con buena visibilidad y clima estable

Si el contexto no aporta informacion especial, mantente en la prioridad base segun la falla.

Responde SIEMPRE con un unico objeto JSON valido, sin texto adicional, sin markdown.
El campo resumen_ia debe ser CORTO (200 caracteres max) y debe mencionar brevemente el factor de contexto si subiste o bajaste la prioridad. Formato:
{"id_categoria": <int>, "id_prioridad": <int>, "resumen_ia": "<texto breve max 200 chars>", "confianza": <float>}"""


_MIME_IMAGEN = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
}

_MIME_AUDIO = {
    "mp3": "audio/mp3",
    "wav": "audio/wav",
    "m4a": "audio/mp4",
    "mp4": "audio/mp4",
    "aac": "audio/aac",
    "ogg": "audio/ogg",
    "webm": "audio/webm",
    "flac": "audio/flac",
}


def _extraer_ext(url: str) -> str:
    match = re.search(r"\.([a-zA-Z0-9]{2,5})(?:\?|$)", url)
    return (match.group(1).lower() if match else "")


def _descargar_archivo(url: str, mime_map: dict) -> Optional[tuple[bytes, str]]:
    try:
        ext = _extraer_ext(url)
        mime = mime_map.get(ext)
        if not mime:
            return None
        resp = httpx.get(url, timeout=20, follow_redirects=True)
        resp.raise_for_status()
        return resp.content, mime
    except Exception:
        return None


def clasificar_incidente(db: Session, incidente: Incidente) -> dict:
    """
    Llama a Gemini 2.5 Pro y actualiza el incidente con los campos
    id_categoria, id_prioridad, resumen_ia y clasificacion_ia_confianza.
    """
    if _client is None:
        raise RuntimeError(
            "GEMINI_API_KEY no esta configurada en .env. "
            "Obten una en https://aistudio.google.com/apikey"
        )

    categorias: List[CategoriaProblema] = db.query(CategoriaProblema).all()
    prioridades: List[Prioridad] = db.query(Prioridad).order_by(Prioridad.orden).all()
    evidencias: List[Evidencia] = (
        db.query(Evidencia).filter(Evidencia.id_incidente == incidente.id_incidente).all()
    )

    cat_texto = "\n".join(
        f"- id={c.id_categoria}: {c.nombre} ({c.descripcion or 'sin descripcion'})"
        for c in categorias
    )
    pri_texto = "\n".join(
        f"- id={p.id_prioridad}: {p.nivel} (orden={p.orden})" for p in prioridades
    )

    transcripciones = [ev.transcripcion_audio for ev in evidencias if ev.transcripcion_audio]
    transcripcion_texto = (
        "\n".join(f"- {t}" for t in transcripciones) if transcripciones else "(ninguna)"
    )

    user_prompt = f"""CATEGORIAS DISPONIBLES:
{cat_texto or "(ninguna)"}

PRIORIDADES DISPONIBLES:
{pri_texto or "(ninguna)"}

DESCRIPCION DEL USUARIO:
{incidente.descripcion_usuario or "(no proporcionada)"}

TRANSCRIPCIONES DE AUDIO:
{transcripcion_texto}

UBICACION: lat={incidente.latitud}, lng={incidente.longitud}

Analiza las evidencias (imagenes adjuntas) junto con el texto y responde con el JSON."""

    partes: list = [types.Part.from_text(text=user_prompt)]

    tipos = {t.nombre: t.id_tipo_evidencia for t in db.query(TipoEvidencia).all()}
    id_imagen = tipos.get("imagen")
    id_audio = tipos.get("audio")

    n_imagenes = 0
    n_audios = 0
    for ev in evidencias:
        if id_imagen and ev.id_tipo_evidencia == id_imagen:
            archivo = _descargar_archivo(ev.url_archivo, _MIME_IMAGEN)
            if archivo:
                contenido, mime = archivo
                partes.append(types.Part.from_bytes(data=contenido, mime_type=mime))
                n_imagenes += 1
        elif id_audio and ev.id_tipo_evidencia == id_audio:
            archivo = _descargar_archivo(ev.url_archivo, _MIME_AUDIO)
            if archivo:
                contenido, mime = archivo
                partes.append(types.Part.from_bytes(data=contenido, mime_type=mime))
                n_audios += 1

    logger.info(
        f"[IA] Incidente {incidente.id_incidente}: "
        f"{n_imagenes} imagen(es), {n_audios} audio(s), "
        f"{len(categorias)} categorias, {len(prioridades)} prioridades"
    )

    try:
        respuesta = _client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[types.Content(role="user", parts=partes)],
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.2,
                max_output_tokens=2048,
            ),
        )
    except Exception as e:
        logger.exception(f"[IA] Error llamando a Gemini: {e}")
        raise RuntimeError(f"Error llamando a Gemini: {e}") from e

    respuesta_texto = (respuesta.text or "").strip()
    logger.info(f"[IA] Respuesta Gemini (primeros 500 chars): {respuesta_texto[:500]}")

    match = re.search(r"\{.*\}", respuesta_texto, re.DOTALL)
    if not match:
        logger.error(f"[IA] Respuesta sin JSON: {respuesta_texto}")
        raise ValueError(f"Respuesta IA no contiene JSON: {respuesta_texto}")

    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON invalido de la IA: {e}") from e

    id_categoria = int(data["id_categoria"])
    id_prioridad = int(data["id_prioridad"])
    resumen_ia = str(data.get("resumen_ia", ""))[:1000]
    confianza = float(data.get("confianza", 0.0))

    if not db.get(CategoriaProblema, id_categoria):
        raise ValueError(f"La IA devolvio id_categoria invalido: {id_categoria}")
    if not db.get(Prioridad, id_prioridad):
        raise ValueError(f"La IA devolvio id_prioridad invalido: {id_prioridad}")

    incidente.id_categoria = id_categoria
    incidente.id_prioridad = id_prioridad
    incidente.resumen_ia = resumen_ia
    incidente.clasificacion_ia_confianza = confianza
    incidente.requiere_revision_manual = confianza < 0.6

    db.commit()
    db.refresh(incidente)

    # 🎯 Motor de Asignación Inteligente: Buscar talleres cercanos
    logger.info(f"[IA] Incidente {incidente.id_incidente} clasificado. Ejecutando motor de asignación...")
    try:
        resultado_asignacion = buscar_y_asignar(db, incidente)
        logger.info(f"[IA] Asignación: {resultado_asignacion}")
    except Exception as e:
        logger.warning(f"[IA] Error en motor de asignación: {e}")

    return {
        "id_categoria": id_categoria,
        "id_prioridad": id_prioridad,
        "resumen_ia": resumen_ia,
        "confianza": confianza,
        "requiere_revision_manual": incidente.requiere_revision_manual,
    }
