"""
Pagos — STUB (Stripe pendiente).

TODO: Integrar Stripe con las claves:
  STRIPE_SECRET_KEY  = sk_...
  STRIPE_WEBHOOK_SECRET = whsec_...

Endpoints:
  POST /pagos/crear-intent   → crea PaymentIntent en Stripe
  POST /pagos/confirmar      → webhook de Stripe (pendiente)
  GET  /pagos/{id_incidente} → consultar estado del pago
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user_model import Usuario
from app.models.transaccional import Pago
from app.schemas.transaccional_schema import PagoIntentRequest, PagoResponse, StripeIntentResponse
from app.core.security import get_current_user

router = APIRouter(
    prefix="/pagos",
    tags=["Pagos (Stripe — pendiente)"],
)


@router.post(
    "/crear-intent",
    response_model=StripeIntentResponse,
    summary="[STUB] Crear PaymentIntent de Stripe",
    description=(
        "PENDIENTE: Requiere configurar STRIPE_SECRET_KEY en el entorno. "
        "Actualmente devuelve un objeto simulado para no bloquear el flujo."
    ),
)
def crear_payment_intent(
    payload: PagoIntentRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    # TODO: Descomentar cuando se agreguen las claves de Stripe
    # import stripe
    # stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    # intent = stripe.PaymentIntent.create(
    #     amount=int(payload.monto_total * 100),
    #     currency="usd",
    #     metadata={"id_incidente": payload.id_incidente, "id_usuario": current_user.id_usuario},
    # )
    # return StripeIntentResponse(
    #     client_secret=intent.client_secret,
    #     payment_intent_id=intent.id,
    #     monto_centavos=intent.amount,
    # )

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Integración con Stripe pendiente. Configure STRIPE_SECRET_KEY en el entorno.",
    )


@router.get(
    "/{id_incidente}",
    response_model=PagoResponse,
    summary="[STUB] Consultar pago de un incidente",
)
def obtener_pago(
    id_incidente: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    pago = db.query(Pago).filter(Pago.id_incidente == id_incidente).first()
    if not pago:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe pago registrado para este incidente",
        )

    estado_obj = pago.estado
    return PagoResponse(
        id_pago=pago.id_pago,
        id_incidente=pago.id_incidente,
        monto_total=float(pago.monto_total),
        comision_plataforma=float(pago.comision_plataforma),
        monto_taller=float(pago.monto_taller),
        referencia_externa=pago.referencia_externa,
        estado=estado_obj.nombre if estado_obj else "desconocido",
        created_at=pago.created_at,
    )
