"""0008_tiempo_estimado_idempotencia

Cambios para el segundo parcial:
  - cotizacion.tiempo_estimado_min: cuanto tarda el taller en reparar.
  - asignacion.tiempo_estimado_reparacion_min: copia al aceptar la cotizacion.
  - incidente.idempotency_key + unique(id_usuario, idempotency_key):
    deduplica reintentos del modo offline.

Idempotente: comprueba existencia de columnas, indices y constraints.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e3b2c9d41a77"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, col: str) -> bool:
    return col in {c["name"] for c in sa.inspect(bind).get_columns(table)}


def _has_index(bind, index_name: str) -> bool:
    return bind.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :n"),
        {"n": index_name},
    ).scalar() is not None


def _has_constraint(bind, name: str) -> bool:
    return bind.execute(
        sa.text("SELECT 1 FROM pg_constraint WHERE conname = :n"),
        {"n": name},
    ).scalar() is not None


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_column(bind, "cotizacion", "tiempo_estimado_min"):
        op.add_column(
            "cotizacion",
            sa.Column("tiempo_estimado_min", sa.Integer(), nullable=True),
        )
    if not _has_column(bind, "asignacion", "tiempo_estimado_reparacion_min"):
        op.add_column(
            "asignacion",
            sa.Column("tiempo_estimado_reparacion_min", sa.Integer(), nullable=True),
        )
    if not _has_column(bind, "incidente", "idempotency_key"):
        op.add_column(
            "incidente",
            sa.Column("idempotency_key", sa.String(length=64), nullable=True),
        )
    if not _has_index(bind, "ix_incidente_idempotency_key"):
        op.create_index(
            "ix_incidente_idempotency_key",
            "incidente",
            ["idempotency_key"],
        )
    if not _has_constraint(bind, "uq_incidente_usuario_idemkey"):
        op.create_unique_constraint(
            "uq_incidente_usuario_idemkey",
            "incidente",
            ["id_usuario", "idempotency_key"],
        )


def downgrade() -> None:
    op.drop_constraint("uq_incidente_usuario_idemkey", "incidente", type_="unique")
    op.drop_index("ix_incidente_idempotency_key", table_name="incidente")
    op.drop_column("incidente", "idempotency_key")
    op.drop_column("asignacion", "tiempo_estimado_reparacion_min")
    op.drop_column("cotizacion", "tiempo_estimado_min")
