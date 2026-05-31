"""0007_ubicacion_tecnico

Tabla historica de posiciones del tecnico para reconstruir tracking pasado.
Idempotente: comprueba existencia de la tabla e indice antes de crearlos.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e3b2c9d41a77"
down_revision: Union[str, None] = "c9e28d2d4b21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(bind, name: str) -> bool:
    return sa.inspect(bind).has_table(name)


def _has_index(bind, index_name: str) -> bool:
    return bind.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :n"),
        {"n": index_name},
    ).scalar() is not None


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind, "ubicacion_tecnico"):
        op.create_table(
            "ubicacion_tecnico",
            sa.Column("id_ubicacion", sa.BigInteger(), primary_key=True),
            sa.Column("id_tenant", sa.Integer(), sa.ForeignKey("tenant.id_tenant"), nullable=False, index=True),
            sa.Column("id_usuario", sa.Integer(), sa.ForeignKey("usuario.id_usuario"), nullable=False, index=True),
            sa.Column(
                "id_asignacion",
                sa.Integer(),
                sa.ForeignKey("asignacion.id_asignacion"),
                nullable=True,
                index=True,
            ),
            sa.Column("latitud", sa.Float(), nullable=False),
            sa.Column("longitud", sa.Float(), nullable=False),
            sa.Column("accuracy_m", sa.Float(), nullable=True),
            sa.Column("velocidad_kmh", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )

    if not _has_index(bind, "ix_ubicacion_tecnico_asig_time"):
        op.create_index(
            "ix_ubicacion_tecnico_asig_time",
            "ubicacion_tecnico",
            ["id_asignacion", "created_at"],
        )


def downgrade() -> None:
    op.drop_index("ix_ubicacion_tecnico_asig_time", table_name="ubicacion_tecnico")
    op.drop_table("ubicacion_tecnico")
