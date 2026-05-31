"""0013_tiempo_reparacion_servicio

Anade tiempo_estimado_min (minutos) a TallerServicio: el taller configura
cuanto tarda en promedio cada servicio. Se muestra al cliente al seleccionar
taller, junto con un ETA de llegada calculado desde la distancia GPS.

Idempotente.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e2f30412330b"
down_revision: Union[str, None] = "d1e2f3041222"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, col: str) -> bool:
    return col in {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_column(bind, "taller_servicio", "tiempo_estimado_min"):
        op.add_column(
            "taller_servicio",
            sa.Column("tiempo_estimado_min", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("taller_servicio", "tiempo_estimado_min")
