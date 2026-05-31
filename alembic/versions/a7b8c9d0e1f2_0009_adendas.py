"""0009_adendas

Modelo Adenda: ampliacion de presupuesto registrada por el tecnico.
Asignacion se congela en 'en_espera_aprobacion' hasta que el cliente responda.

Idempotente: comprueba existencia de la tabla antes de crearla.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(bind, name: str) -> bool:
    return sa.inspect(bind).has_table(name)


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind, "adenda"):
        op.create_table(
            "adenda",
            sa.Column("id_adenda", sa.Integer(), primary_key=True),
            sa.Column("id_tenant", sa.Integer(), sa.ForeignKey("tenant.id_tenant"), nullable=True, index=True),
            sa.Column(
                "id_asignacion",
                sa.Integer(),
                sa.ForeignKey("asignacion.id_asignacion"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "id_tecnico",
                sa.Integer(),
                sa.ForeignKey("usuario.id_usuario"),
                nullable=True,
            ),
            sa.Column("monto_adicional", sa.Numeric(10, 2), nullable=False),
            sa.Column("descripcion", sa.Text(), nullable=False),
            sa.Column("estado", sa.String(20), nullable=False, server_default="pendiente"),
            sa.Column("motivo_cliente", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column("respondida_at", sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint(
                "estado IN ('pendiente','aprobada','rechazada')",
                name="chk_adenda_estado",
            ),
        )

    op.execute(
        "INSERT INTO estado_asignacion (nombre) "
        "SELECT 'en_espera_aprobacion' WHERE NOT EXISTS ("
        "  SELECT 1 FROM estado_asignacion WHERE nombre = 'en_espera_aprobacion'"
        ")"
    )


def downgrade() -> None:
    op.drop_table("adenda")
    op.execute(
        "DELETE FROM estado_asignacion WHERE nombre = 'en_espera_aprobacion'"
    )
