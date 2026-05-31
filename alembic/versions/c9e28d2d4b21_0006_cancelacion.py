"""0006_cancelacion

- Anade tarifa_traslado a taller (default 5.0).
- Anade columnas de cancelacion + compensacion a asignacion.
- Asegura que estado_asignacion tenga 'cancelada' y 'llegado'.

Idempotente: comprueba existencia de columnas antes de agregarlas.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9e28d2d4b21"
down_revision: Union[str, None] = "b7b5c7b8c2a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, col: str) -> bool:
    return col in {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_column(bind, "taller", "tarifa_traslado"):
        op.add_column(
            "taller",
            sa.Column("tarifa_traslado", sa.Numeric(10, 2), nullable=False, server_default="5.00"),
        )

    for col_name, col_def in [
        ("cancelada_at", sa.Column("cancelada_at", sa.DateTime(timezone=True), nullable=True)),
        ("motivo_cancelacion", sa.Column("motivo_cancelacion", sa.String(length=500), nullable=True)),
        ("cancelada_por", sa.Column("cancelada_por", sa.String(length=20), nullable=True)),
        ("compensacion_monto", sa.Column("compensacion_monto", sa.Numeric(10, 2), nullable=True)),
        ("compensacion_pagada", sa.Column("compensacion_pagada", sa.Boolean(), nullable=False, server_default=sa.text("false"))),
    ]:
        if not _has_column(bind, "asignacion", col_name):
            op.add_column("asignacion", col_def)

    for nombre in ("cancelada", "llegado"):
        op.execute(
            sa.text(
                """
            INSERT INTO estado_asignacion (nombre)
            SELECT :n
            WHERE NOT EXISTS (
                SELECT 1 FROM estado_asignacion WHERE nombre = :n
            )
        """
            ).bindparams(n=nombre)
        )


def downgrade() -> None:
    op.drop_column("asignacion", "compensacion_pagada")
    op.drop_column("asignacion", "compensacion_monto")
    op.drop_column("asignacion", "cancelada_por")
    op.drop_column("asignacion", "motivo_cancelacion")
    op.drop_column("asignacion", "cancelada_at")
    op.drop_column("taller", "tarifa_traslado")
