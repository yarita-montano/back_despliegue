"""0012_cancelacion_porcentajes

Porcentajes de compensacion por cancelacion configurables por tenant:
  - tenant.pct_cancel_pendiente   (default 0)
  - tenant.pct_cancel_aceptada    (default 50)
  - tenant.pct_cancel_en_camino   (default 100)

Antes estaban hardcoded en cancelacion_service.COMPENSACION_POR_ESTADO.
Ahora el admin del tenant los puede ajustar a su modelo de negocio.

Idempotente.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1e2f3041222"
down_revision: Union[str, None] = "c0d1e2f30411"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, col: str) -> bool:
    return col in {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()

    for col, default in [
        ("pct_cancel_pendiente", "0"),
        ("pct_cancel_aceptada", "50"),
        ("pct_cancel_en_camino", "100"),
    ]:
        if not _has_column(bind, "tenant", col):
            op.add_column(
                "tenant",
                sa.Column(
                    col,
                    sa.Integer(),
                    nullable=False,
                    server_default=default,
                ),
            )


def downgrade() -> None:
    op.drop_column("tenant", "pct_cancel_en_camino")
    op.drop_column("tenant", "pct_cancel_aceptada")
    op.drop_column("tenant", "pct_cancel_pendiente")
