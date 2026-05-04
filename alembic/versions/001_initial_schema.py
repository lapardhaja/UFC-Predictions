"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("event_name", sa.String(length=512), nullable=False),
        sa.Column("date", sa.Date(), nullable=True),
        sa.Column("location", sa.String(length=512), nullable=True),
        sa.Column("is_upcoming", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index(op.f("ix_events_event_id"), "events", ["event_id"], unique=False)

    op.create_table(
        "fighters",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("fighter_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("height_cm", sa.Float(), nullable=True),
        sa.Column("reach_cm", sa.Float(), nullable=True),
        sa.Column("weight_lbs", sa.Float(), nullable=True),
        sa.Column("stance", sa.String(length=64), nullable=True),
        sa.Column("dob", sa.Date(), nullable=True),
        sa.Column("wins", sa.Integer(), nullable=True),
        sa.Column("losses", sa.Integer(), nullable=True),
        sa.Column("draws", sa.Integer(), nullable=True),
        sa.Column("nc", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fighter_id"),
    )
    op.create_index(op.f("ix_fighters_fighter_id"), "fighters", ["fighter_id"], unique=False)

    op.create_table(
        "fights",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("fight_id", sa.String(length=256), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("winner_fighter_id", sa.Integer(), nullable=True),
        sa.Column("method", sa.String(length=128), nullable=True),
        sa.Column("round", sa.Integer(), nullable=True),
        sa.Column("time_str", sa.String(length=32), nullable=True),
        sa.Column("weight_class", sa.String(length=128), nullable=True),
        sa.Column("is_title_fight", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.ForeignKeyConstraint(["winner_fighter_id"], ["fighters.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fight_id"),
    )
    op.create_index(op.f("ix_fights_fight_id"), "fights", ["fight_id"], unique=False)

    op.create_table(
        "fight_participations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("fight_id", sa.Integer(), nullable=False),
        sa.Column("fighter_id", sa.Integer(), nullable=False),
        sa.Column("is_fighter_a", sa.Boolean(), nullable=False),
        sa.Column("sig_strikes_landed", sa.Integer(), nullable=True),
        sa.Column("sig_strikes_attempted", sa.Integer(), nullable=True),
        sa.Column("total_strikes_landed", sa.Integer(), nullable=True),
        sa.Column("total_strikes_attempted", sa.Integer(), nullable=True),
        sa.Column("takedowns_landed", sa.Integer(), nullable=True),
        sa.Column("takedowns_attempted", sa.Integer(), nullable=True),
        sa.Column("submission_attempts", sa.Integer(), nullable=True),
        sa.Column("knockdowns", sa.Integer(), nullable=True),
        sa.Column("control_time_seconds", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["fight_id"], ["fights.id"]),
        sa.ForeignKeyConstraint(["fighter_id"], ["fighters.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fight_id", "fighter_id", name="uq_fight_fighter"),
    )


def downgrade() -> None:
    op.drop_table("fight_participations")
    op.drop_index(op.f("ix_fights_fight_id"), table_name="fights")
    op.drop_table("fights")
    op.drop_index(op.f("ix_fighters_fighter_id"), table_name="fighters")
    op.drop_table("fighters")
    op.drop_index(op.f("ix_events_event_id"), table_name="events")
    op.drop_table("events")
