"""Initial schema — business_needs and id_counters tables.

Revision ID: 001
Create Date: 2025-01-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create business_needs and id_counters tables."""
    op.create_table(
        "business_needs",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("pitch", sa.Text(), nullable=False),
        sa.Column("horizon", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("rework_note", sa.Text(), nullable=True),
        sa.Column("duplicate_matches", postgresql.JSONB(), server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index("idx_bn_status", "business_needs", ["status"])
    op.create_index("idx_bn_created", "business_needs", ["created_at"])

    op.create_table(
        "id_counters",
        sa.Column("year", sa.Integer(), primary_key=True),
        sa.Column("counter", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    """Drop all tables."""
    op.drop_index("idx_bn_created", table_name="business_needs")
    op.drop_index("idx_bn_status", table_name="business_needs")
    op.drop_table("business_needs")
    op.drop_table("id_counters")
