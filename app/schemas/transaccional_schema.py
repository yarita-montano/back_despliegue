"""
Schemas Pydantic para Notificaciones, Mensajes y Pagos.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ── NOTIFICACIONES ────────────────────────────────────────────────────────────

class PushTokenRequest(BaseModel):
    push_token: str = Field(..., min_length=10, description="FCM device token")


class NotificacionResponse(BaseModel):
    id_notificacion: int
    id_usuario: Optional[int] = None
    id_taller: Optional[int] = None
    id_incidente: Optional[int] = None
    titulo: str
    mensaje: str
    leido: bool
    enviado_push: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── MENSAJES ──────────────────────────────────────────────────────────────────

class MensajeCreate(BaseModel):
    contenido: str = Field(..., min_length=1, max_length=2000)


class MensajeResponse(BaseModel):
    id_mensaje: int
    id_incidente: int
    id_usuario: Optional[int] = None
    id_taller: Optional[int] = None
    contenido: str
    leido: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── PAGOS (STUB Stripe) ────────────────────────────────────────────────────────

class PagoIntentRequest(BaseModel):
    id_incidente: int
    monto_total: float = Field(..., gt=0, description="Monto en USD")
    id_metodo_pago: int = Field(default=1, description="ID del método de pago")


class PagoResponse(BaseModel):
    id_pago: int
    id_incidente: int
    monto_total: float
    comision_plataforma: float
    monto_taller: float
    referencia_externa: Optional[str] = None
    estado: str
    created_at: datetime

    class Config:
        from_attributes = True


class PagoClienteItem(BaseModel):
    id_incidente: int
    id_pago: Optional[int] = None
    monto_total: float
    estado: str
    referencia_externa: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StripeIntentResponse(BaseModel):
    client_secret: str
    payment_intent_id: str
    monto_centavos: int


class ConfirmarPagoAppRequest(BaseModel):
    payment_intent_id: str = Field(..., min_length=5, description="ID del PaymentIntent de Stripe")
