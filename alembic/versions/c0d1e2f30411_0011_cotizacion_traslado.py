"""0011_cotizacion_traslado

Anade desglose de traslado a la cotizacion:
  - cotizacion.distancia_km     (km entre taller e incidente)
  - cotizacion.monto_traslado   (taller.tarifa_traslado * distancia_km)

monto_total = monto_servicio + monto_repuestos + monto_traslado

Idempotente: comprueba existencia antes de agregar columnas.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c0d1e2f30411"
down_revision: Union[str, None] = "b8c9d0e1f203"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, col: str) -> bool:
    return col in {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_column(bind, "cotizacion", "distancia_km"):
        op.add_column(
            "cotizacion",
            sa.Column("distancia_km", sa.Numeric(6, 2), nullable=True),
        )
    if not _has_column(bind, "cotizacion", "monto_traslado"):
        op.add_column(
            "cotizacion",
            sa.Column(
                "monto_traslado",
                sa.Numeric(10, 2),
                nullable=True,
                server_default="0",
            ),
        )


def downgrade() -> None:
    op.drop_column("cotizacion", "monto_traslado")
    op.drop_column("cotizacion", "distancia_km")
