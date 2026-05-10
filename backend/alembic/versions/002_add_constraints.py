"""Add constraints column to business_needs.

Revision ID: 002
Revises: 001
Create Date: 2026-05-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable constraints JSONB column to business_needs."""
    op.add_column(
        "business_needs",
        sa.Column("constraints", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    """Remove constraints column from business_needs."""
    op.drop_column("business_needs", "constraints")
