"""ID service — generates BN-YYYY-NNN identifiers using a PostgreSQL counter."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_need import IdCounter


async def generate_id(session: AsyncSession) -> str:
    """Generate the next BN-YYYY-NNN identifier for the current year."""
    current_year = datetime.now(timezone.utc).year

    # Get or create the counter row for this year
    result = await session.execute(
        select(IdCounter).where(IdCounter.year == current_year).with_for_update()
    )
    counter_row = result.scalar_one_or_none()

    if counter_row is None:
        counter_row = IdCounter(year=current_year, counter=1)
        session.add(counter_row)
    else:
        counter_row.counter += 1

    await session.flush()
    return f"BN-{current_year}-{counter_row.counter:03d}"
