"""add stats_json to fight_participations

Revision ID: 002
Revises: 001
Create Date: 2026-05-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("fight_participations") as batch:
        batch.add_column(sa.Column("stats_json", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("fight_participations") as batch:
        batch.drop_column("stats_json")
