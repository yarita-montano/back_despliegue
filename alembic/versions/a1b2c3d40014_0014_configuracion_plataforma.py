"""0014_configuracion_plataforma

Crea la tabla singleton configuracion_plataforma (super-admin) con la comision
que la plataforma retiene de cada servicio. Antes la comision estaba fija en
10% en el codigo; ahora es configurable por el super-admin.

  - Crea la tabla configuracion_plataforma con:
      * comision_plataforma_pct (default 10)
    e inserta la fila default (id=1).

Idempotente: comprueba existencia de la tabla / fila antes de operar.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d40014"
down_revision: Union[str, None] = "e2f30412330b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(bind, name: str) -> bool:
    return sa.inspect(bind).has_table(name)


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind, "configuracion_plataforma"):
        op.create_table(
            "configuracion_plataforma",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("comision_plataforma_pct", sa.Integer(), nullable=False, server_default="10"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )

    # Sembrar la fila singleton default (solo si la tabla quedo vacia).
    existe_fila = bind.execute(
        sa.text("SELECT 1 FROM configuracion_plataforma WHERE id = 1")
    ).scalar()
    if not existe_fila:
        op.bulk_insert(
            sa.table(
                "configuracion_plataforma",
                sa.column("id", sa.Integer),
                sa.column("comision_plataforma_pct", sa.Integer),
            ),
            [{"id": 1, "comision_plataforma_pct": 10}],
        )


def downgrade() -> None:
    bind = op.get_bind()

    if _has_table(bind, "configuracion_plataforma"):
        op.drop_table("configuracion_plataforma")
