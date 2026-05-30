"""add applied changes idempotency table

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-30
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "applied_changes",
        sa.Column("change_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("new_version", sa.Integer(), nullable=False),
        sa.Column(
            "server_delta",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("applied_changes")
