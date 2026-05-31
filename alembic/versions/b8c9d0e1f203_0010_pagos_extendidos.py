"""0010_pagos_extendidos

Pagos Fase 1 y 3:
  - incidente.monto_preautorizacion + stripe_preauth_id
  - pago.tipo (servicio|penalizacion|preauth)

Idempotente: comprueba existencia de columnas y constraints.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c9d0e1f203"
down_revision: Union[str, None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, col: str) -> bool:
    return col in {c["name"] for c in sa.inspect(bind).get_columns(table)}


def _has_constraint(bind, name: str) -> bool:
    return bind.execute(
        sa.text("SELECT 1 FROM pg_constraint WHERE conname = :n"),
        {"n": name},
    ).scalar() is not None


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_column(bind, "incidente", "monto_preautorizacion"):
        op.add_column(
            "incidente",
            sa.Column("monto_preautorizacion", sa.Numeric(10, 2), nullable=True),
        )
    if not _has_column(bind, "incidente", "stripe_preauth_id"):
        op.add_column(
            "incidente",
            sa.Column("stripe_preauth_id", sa.String(length=100), nullable=True),
        )
    if not _has_column(bind, "pago", "tipo"):
        op.add_column(
            "pago",
            sa.Column(
                "tipo",
                sa.String(length=20),
                nullable=False,
                server_default="servicio",
            ),
        )
    if not _has_constraint(bind, "chk_pago_tipo"):
        op.create_check_constraint(
            "chk_pago_tipo",
            "pago",
            "tipo IN ('servicio','penalizacion','preauth')",
        )


def downgrade() -> None:
    op.drop_constraint("chk_pago_tipo", "pago", type_="check")
    op.drop_column("pago", "tipo")
    op.drop_column("incidente", "stripe_preauth_id")
    op.drop_column("incidente", "monto_preautorizacion")
