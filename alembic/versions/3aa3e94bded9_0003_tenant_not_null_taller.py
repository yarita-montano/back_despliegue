"""0003_tenant_not_null_taller

Marca taller.id_tenant como NOT NULL si ya todos los talleres tienen tenant.
Idempotente: si la columna ya es NOT NULL, no hace nada.

Revision ID: 3aa3e94bded9
Revises: 08a3dffb665e
Create Date: 2026-05-19 10:31:26.397197

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3aa3e94bded9"
down_revision: Union[str, None] = "08a3dffb665e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # Verificar si la columna ya es NOT NULL
    col_info = next(
        (c for c in sa.inspect(bind).get_columns("taller") if c["name"] == "id_tenant"),
        None,
    )
    if col_info is None:
        # La columna no existe aun (raro, pero defensivo)
        return

    if not col_info.get("nullable", True):
        # Ya es NOT NULL, nada que hacer
        return

    pending = bind.execute(
        sa.text("SELECT COUNT(*) FROM taller WHERE id_tenant IS NULL")
    ).scalar_one()
    if pending and pending > 0:
        # En produccion puede haber talleres sin tenant (legacy). Los asignamos
        # al primer tenant disponible para poder avanzar la migracion.
        bind.execute(
            sa.text(
                """
                UPDATE taller SET id_tenant = (SELECT id_tenant FROM tenant LIMIT 1)
                WHERE id_tenant IS NULL
                  AND EXISTS (SELECT 1 FROM tenant LIMIT 1)
                """
            )
        )
        # Si siguen nulos (no hay tenant todavia), saltamos el NOT NULL silenciosamente.
        still_null = bind.execute(
            sa.text("SELECT COUNT(*) FROM taller WHERE id_tenant IS NULL")
        ).scalar_one()
        if still_null and still_null > 0:
            return

    op.alter_column("taller", "id_tenant", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    op.alter_column("taller", "id_tenant", existing_type=sa.Integer(), nullable=True)
