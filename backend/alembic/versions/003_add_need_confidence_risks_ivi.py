"""Add confidence, risks, justifications, and ivi_scores to business_needs.

Revision ID: 003
Revises: 002
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "business_needs",
        sa.Column("confidence", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "business_needs",
        sa.Column("risks", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "business_needs",
        sa.Column("justifications", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "business_needs",
        sa.Column("ivi_scores", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("business_needs", "ivi_scores")
    op.drop_column("business_needs", "justifications")
    op.drop_column("business_needs", "risks")
    op.drop_column("business_needs", "confidence")
